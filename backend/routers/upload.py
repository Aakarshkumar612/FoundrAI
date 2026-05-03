"""Upload router: multi-format file upload (CSV, Excel, PDF, Word, images)."""

import io
import logging
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from pydantic import BaseModel
from groq import Groq

from backend.auth.middleware import verify_jwt
from backend.config import Settings, get_settings
from backend.storage.supabase_client import get_supabase_client
from backend.storage.supabase_storage import upload_file, get_mime_type
from backend.storage.extractors import SUPPORTED_EXTENSIONS, extract_text, get_doc_type
from backend.rag.pipeline import RAGPipeline
from backend.automl.trainer import (
    extract_initial_metrics,
    extract_metrics_from_excel,
    extract_metrics_from_text,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

FINANCIAL_COLUMNS = {"revenue", "burn_rate", "headcount", "cac", "ltv"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    file_type: str
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    uploaded_at: str
    is_financial: bool
    storage_path: Optional[str] = None


def _insert_financial_rows(content: bytes, upload_id: str, founder_id: str, sb) -> None:
    """Persist all rows from a financial CSV into financial_rows for Superset dashboards."""
    if sb is None:
        return
    try:
        df = pd.read_csv(io.BytesIO(content))
        df.columns = [c.strip().lower() for c in df.columns]

        def _clean_num(val, is_int=False):
            if pd.isna(val): return 0
            # Remove currency symbols and commas
            s = re.sub(r'[^\d.-]', '', str(val))
            try:
                fval = float(s)
                import math
                if math.isnan(fval) or math.isinf(fval): return 0
                return int(fval) if is_int else fval
            except (ValueError, TypeError):
                return 0

        rows = [
            {
                "upload_id": upload_id,
                "founder_id": founder_id,
                "month": str(row.get("month", "")),
                "revenue": _clean_num(row.get("revenue")),
                "burn_rate": _clean_num(row.get("burn_rate")),
                "headcount": _clean_num(row.get("headcount"), is_int=True),
                "cac": _clean_num(row.get("cac")),
                "ltv": _clean_num(row.get("ltv")),
            }
            for _, row in df.iterrows()
        ]
        # Significantly larger chunk size for faster network throughput
        for i in range(0, len(rows), 1000):
            sb.table("financial_rows").insert(rows[i:i+1000]).execute()
        
        logger.info("Inserted %d financial rows for upload_id=%s", len(rows), upload_id)
    except Exception as exc:
        logger.error("financial_rows insert failed for upload_id=%s: %s", upload_id, exc)


def _process_upload_background(
    contents: bytes,
    filename: str,
    upload_id: str,
    founder_id: str,
    doc_type: str,
    is_financial: bool,
    storage_path: str,
    groq_api_key: Optional[str] = None
):
    """Heavy processing task to run in the background (Storage + RAG + Metrics)."""
    sb = get_supabase_client()
    if sb is None:
        logger.error("Background task failed: Supabase client not available")
        return

    try:
        # 1. Upload to Supabase Storage first (critical for other paths)
        upload_file(
            content=contents,
            storage_path=storage_path,
            content_type=get_mime_type(filename),
            supabase_client=sb,
        )

        # 2. Text extraction
        groq_client = None
        if groq_api_key:
            try:
                groq_client = Groq(api_key=groq_api_key)
            except Exception:
                pass
        
        extracted_text = extract_text(contents, filename, groq_client=groq_client)
        
        # 3. Metrics & Metadata (do full parse here in background)
        metrics = {}
        row_count = 0
        columns = []
        ext = Path(filename).suffix.lower()
        
        if ext == ".csv":
            try:
                df = pd.read_csv(io.BytesIO(contents))
                row_count = len(df)
                columns = list(df.columns)
                if is_financial:
                    metrics = extract_initial_metrics(contents)
                    _insert_financial_rows(contents, upload_id, founder_id, sb)
            except Exception as e:
                logger.warning("Background CSV parse failed: %s", e)
        elif ext in (".xlsx", ".xls"):
            metrics = extract_metrics_from_excel(contents)
        else:
            metrics = extract_metrics_from_text(extracted_text, groq_client)

        if not extracted_text.strip():
            extracted_text = f"Document: {filename}\nType: {doc_type}\nNo text content found."

        # 4. Update metadata in DB (including final row_count/columns)
        sb.table("uploads").update({
            "initial_metrics": metrics,
            "row_count": row_count,
            "columns": columns,
            "upload_status": "ready",
        }).eq("id", upload_id).execute()

        # 5. RAG indexing
        rag = RAGPipeline(supabase_client=sb)
        rag.index(
            content=extracted_text.encode("utf-8"),
            founder_id=founder_id,
            doc_type=doc_type,
            source_filename=filename,
        )
        
        sb.table("uploads").update(
            {"upload_status": "indexed"}
        ).eq("id", upload_id).execute()
        
        logger.info("Background processing complete for upload_id=%s", upload_id)

    except Exception as exc:
        logger.error("Background processing failed for upload_id=%s: %s", upload_id, exc)
        try:
            sb.table("uploads").update({"upload_status": "error"}).eq("id", upload_id).execute()
        except:
            pass


@router.post("/financials", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_financials(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    founder: dict = Depends(verify_jwt),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Accept any supported file and return immediately. 
    All processing (Storage upload, RAG, Metrics) happens in background.
    """
    founder_id: str = founder["sub"]
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "API_INPUT_001",
                "message": (
                    f"Unsupported file type '{ext}'. "
                    f"Accepted: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
                ),
            },
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "API_INPUT_001", "message": "File is empty"},
        )

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "API_INPUT_001",
                "message": f"File exceeds 50 MB limit ({len(contents) / 1_048_576:.1f} MB)",
            },
        )

    # ── Shallow Metadata (Header only) ──────────────────────────────────────
    doc_type = get_doc_type(filename)
    is_financial = False
    columns = []

    if ext == ".csv":
        try:
            # Read ONLY the header (nrows=0) — extremely fast
            df_head = pd.read_csv(io.BytesIO(contents), nrows=0)
            columns = list(df_head.columns)
            cols_set = {c.lower().strip() for c in columns}
            is_financial = FINANCIAL_COLUMNS.issubset(cols_set)
        except Exception:
            pass

    upload_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    storage_path = f"founders/{founder_id}/{upload_id}/{filename}"

    # ── Supabase DB — initial placeholder metadata ──────────────────────────
    sb = get_supabase_client()
    if sb is not None:
        try:
            sb.table("uploads").insert({
                "id": upload_id,
                "founder_id": founder_id,
                "filename": filename,
                "file_type": doc_type,
                "row_count": 0, # To be updated in background
                "columns": columns,
                "initial_metrics": {},
                "upload_status": "processing",
                "storage_path": storage_path,
            }).execute()

            if is_financial:
                sb.table("founders").update({
                    "active_upload_id": upload_id
                }).eq("id", founder_id).execute()
        except Exception as exc:
            logger.error("Initial DB insert failed: %s", exc)

    # ── Background Task (Everything else) ────────────────────────────────────
    background_tasks.add_task(
        _process_upload_background,
        contents,
        filename,
        upload_id,
        founder_id,
        doc_type,
        is_financial,
        storage_path,
        settings.groq_api_key
    )

    return UploadResponse(
        upload_id=upload_id,
        filename=filename,
        file_type=doc_type,
        row_count=0, # Client knows it's processing
        columns=columns,
        uploaded_at=uploaded_at,
        is_financial=is_financial,
        storage_path=storage_path,
    )
