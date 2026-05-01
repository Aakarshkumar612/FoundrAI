"""Upload router: multi-format file upload (CSV, Excel, PDF, Word, images)."""

import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

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


def _is_financial_csv(content: bytes) -> bool:
    try:
        df = pd.read_csv(io.BytesIO(content), nrows=1)
        cols = {c.lower().strip() for c in df.columns}
        return FINANCIAL_COLUMNS.issubset(cols)
    except Exception:
        return False


def _parse_csv_meta(content: bytes):
    try:
        df = pd.read_csv(io.BytesIO(content))
        return len(df), list(df.columns)
    except Exception:
        return None, None


def _insert_financial_rows(content: bytes, upload_id: str, founder_id: str, sb) -> None:
    """Persist all rows from a financial CSV into financial_rows for Superset dashboards."""
    if sb is None:
        return
    try:
        df = pd.read_csv(io.BytesIO(content))
        df.columns = [c.strip().lower() for c in df.columns]
        rows = [
            {
                "upload_id": upload_id,
                "founder_id": founder_id,
                "month": str(row.get("month", "")),
                "revenue": float(row.get("revenue", 0) or 0),
                "burn_rate": float(row.get("burn_rate", 0) or 0),
                "headcount": int(row.get("headcount", 0) or 0),
                "cac": float(row.get("cac", 0) or 0),
                "ltv": float(row.get("ltv", 0) or 0),
            }
            for _, row in df.iterrows()
        ]
        sb.table("financial_rows").insert(rows).execute()
        logger.info("Inserted %d financial rows for upload_id=%s", len(rows), upload_id)
    except Exception as exc:
        logger.error("financial_rows insert failed for upload_id=%s: %s", upload_id, exc)


@router.post("/financials", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_financials(
    file: UploadFile = File(...),
    founder: dict = Depends(verify_jwt),
    settings: Settings = Depends(get_settings),
) -> UploadResponse:
    """Accept any supported file, store raw bytes in Supabase Storage, extract
    text, and index into RAG.

    Supported: CSV, Excel (.xlsx/.xls), PDF, Word (.docx), images (JPG/PNG/WebP), TXT.
    Max size: 50 MB. Raw file stored in Supabase Storage bucket 'founder-uploads'.

    CSV files with financial columns are additionally processed for Monte Carlo
    simulation seeding (metrics stored as JSONB in uploads table).

    Args:
        file: Multipart file upload.
        founder: Verified JWT claims.
        settings: App settings.

    Returns:
        UploadResponse with upload_id, file type, metadata, and storage path.
    """
    founder_id: str = founder["sub"]
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()

    # ── Extension check ───────────────────────────────────────────────────────
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

    # ── Size check ────────────────────────────────────────────────────────────
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "API_INPUT_001",
                "message": f"File exceeds 50 MB limit ({len(contents) / 1_048_576:.1f} MB)",
            },
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "API_INPUT_001", "message": "File is empty"},
        )

    # ── Classify ──────────────────────────────────────────────────────────────
    is_financial = ext == ".csv" and _is_financial_csv(contents)
    doc_type = get_doc_type(filename)
    row_count, columns = (None, None)
    metrics: dict = {}

    if ext == ".csv":
        row_count, columns = _parse_csv_meta(contents)
        if is_financial:
            metrics = extract_initial_metrics(contents)

    # ── Text extraction ───────────────────────────────────────────────────────
    groq_client = None
    try:
        from groq import Groq
        groq_client = Groq(api_key=settings.groq_api_key)
    except Exception:
        pass

    extracted_text = extract_text(contents, filename, groq_client=groq_client)

    # ── Metrics extraction for non-financial-CSV formats ─────────────────────
    if not metrics:
        if ext in (".xlsx", ".xls"):
            metrics = extract_metrics_from_excel(contents)
        else:
            metrics = extract_metrics_from_text(extracted_text, groq_client)
    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "API_INPUT_001",
                "message": "Could not extract any text from the file",
            },
        )

    upload_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    storage_path = f"founders/{founder_id}/{upload_id}/{filename}"

    # ── Supabase Storage — store raw file ────────────────────────────────────
    sb = get_supabase_client()
    if is_financial:
        _insert_financial_rows(contents, upload_id, founder_id, sb)
    saved_path = upload_file(
        content=contents,
        storage_path=storage_path,
        content_type=get_mime_type(filename),
        supabase_client=sb,
    )
    if saved_path is None:
        logger.warning("Storage unavailable — raw file not saved for upload_id=%s", upload_id)

    # ── Supabase DB — persist metadata ────────────────────────────────────────
    if sb is not None:
        try:
            sb.table("uploads").insert({
                "id": upload_id,
                "founder_id": founder_id,
                "filename": filename,
                "file_type": doc_type,
                "row_count": row_count or 0,
                "columns": columns or [],
                "initial_metrics": metrics,
                "upload_status": "ready",
                "gcs_path": saved_path,   # reusing column for Supabase Storage path
            }).execute()
        except Exception as exc:
            logger.error("DB insert failed for upload_id=%s: %s", upload_id, exc)

    # ── RAG indexing ──────────────────────────────────────────────────────────
    try:
        rag = RAGPipeline(supabase_client=sb)
        rag.index(
            content=extracted_text.encode("utf-8"),
            founder_id=founder_id,
            doc_type=doc_type,
            source_filename=filename,
        )
        if sb is not None:
            sb.table("uploads").update(
                {"upload_status": "indexed"}
            ).eq("id", upload_id).execute()
    except Exception as exc:
        logger.error("RAG indexing failed for upload_id=%s: %s", upload_id, exc)

    logger.info(
        "Upload complete: founder=%s upload_id=%s file=%s size=%.1fMB financial=%s stored=%s",
        founder_id, upload_id, filename, len(contents) / 1_048_576, is_financial, saved_path is not None,
    )

    return UploadResponse(
        upload_id=upload_id,
        filename=filename,
        file_type=doc_type,
        row_count=row_count,
        columns=columns,
        uploaded_at=uploaded_at,
        is_financial=is_financial,
        storage_path=saved_path,
    )
