import io
import logging
from typing import Optional

import httpx
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from groq import Groq
from pydantic import BaseModel

from backend.auth.middleware import get_current_founder
from backend.config import get_settings
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/charts", tags=["charts"])

_DASHBOARDS = [
    {"id": "4bc06298-4a86-49d0-8ae3-4e950491ccfe", "title": "Revenue Overview",
     "description": "Monthly revenue trend, MoM growth rate, revenue vs burn"},
    {"id": "e9989c39-e035-4b88-ace6-00e1d861aeba", "title": "Unit Economics",
     "description": "CAC over time, LTV over time, LTV/CAC ratio, payback period"},
    {"id": "b8555714-3213-4598-bf6b-ba9b6baa3827", "title": "Growth Health",
     "description": "MRR growth %, churn rate, DAU/MAU trend, NRR waterfall"},
]


class EmbedTokenResponse(BaseModel):
    token: str
    dashboard_id: str
    superset_url: str
    expires_in: int = 300


@router.get("/dashboards")
async def list_dashboards(founder=Depends(get_current_founder)):
    return {"dashboards": _DASHBOARDS}


@router.get("/embed-token", response_model=EmbedTokenResponse)
async def get_embed_token(
    dashboard_id: str = _DASHBOARDS[0]["id"],
    founder=Depends(get_current_founder),
):
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.superset_url}/api/v1/security/login",
                json={
                    "username": settings.superset_username,
                    "password": settings.superset_password,
                    "provider": "db",
                    "refresh": False,
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            admin_token = resp.json()["access_token"]
        except Exception as e:
            logger.error("Superset login failed: %s", e)
            raise HTTPException(status_code=502, detail="BI Service unavailable")

        try:
            user_id = founder.get("sub")
            resp2 = await client.post(
                f"{settings.superset_url}/api/v1/security/guest_token/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "user": {"username": str(user_id), "first_name": "Founder", "last_name": ""},
                    "resources": [{"type": "dashboard", "id": dashboard_id}],
                    "rls": [],
                },
                timeout=10.0,
            )
            resp2.raise_for_status()
            return EmbedTokenResponse(
                token=resp2.json()["token"],
                dashboard_id=dashboard_id,
                superset_url=settings.superset_url,
            )
        except Exception as e:
            logger.error("Guest token generation failed: %s", e)
            raise HTTPException(status_code=500, detail="Failed to sync with BI service")


@router.get("/financial-data")
async def get_financial_data(
    limit: int = 24,
    founder=Depends(get_current_founder),
):
    founder_id = founder.get("sub")
    sb = get_supabase_client()
    if sb is None:
        return {"rows": []}
    try:
        result = (
            sb.table("financial_rows")
            .select("month, revenue, burn_rate, headcount, cac, ltv")
            .eq("founder_id", founder_id)
            .order("month", desc=False)
            .limit(limit)
            .execute()
        )
        return {"rows": result.data or []}
    except Exception as exc:
        logger.error("financial_rows fetch failed: %s", exc)
        return {"rows": []}


@router.post("/auto-report", response_class=HTMLResponse)
async def auto_analysis_report(founder=Depends(get_current_founder)):
    """Generate a comprehensive AI analytics report from all uploaded data.

    Priority order:
      1. financial_rows table (structured data from financial CSVs with exact columns)
      2. Raw CSV/Excel uploads downloaded from Supabase Storage (any CSV works)
      3. No-data HTML if neither source has content
    """
    from backend.agents.data_analyst_agent import run as analyst_run
    from backend.services.report_generator import generate_report_from_df, generate_report
    from backend.storage.supabase_storage import download_file

    founder_id = founder.get("sub")
    settings = get_settings()
    sb = get_supabase_client()

    # ── Groq client ───────────────────────────────────────────────────────────
    groq_client = None
    if settings.groq_api_key:
        try:
            groq_client = Groq(api_key=settings.groq_api_key)
            logger.info("Groq client initialized for report generation")
        except Exception as exc:
            logger.error("Failed to initialize Groq client: %s", exc)
    else:
        logger.warning("GROQ_API_KEY is missing in settings")

    # ── Path 1: financial_rows (strict 5-column format) ───────────────────────
    rows = []
    if sb is not None:
        try:
            result = (
                sb.table("financial_rows")
                .select("month, revenue, burn_rate, headcount, cac, ltv")
                .eq("founder_id", founder_id)
                .order("month", desc=False)
                .limit(60)
                .execute()
            )
            rows = result.data or []
        except Exception as exc:
            logger.error("financial_rows fetch failed: %s", exc)

    if rows:
        try:
            df = pd.DataFrame(rows)
            analysis_markdown = analyst_run(df, groq_client)
            html = generate_report_from_df(df, analysis_markdown)
            return HTMLResponse(content=html, status_code=200)
        except Exception as exc:
            logger.error("Report from financial_rows failed: %s", exc)
            # fall through to raw-upload fallback

    # ── Path 2: raw CSV/Excel from storage (works with any column layout) ─────
    if sb is not None:
        recent_uploads = []
        try:
            # 1. Try to get the specific active upload first
            founder_row = sb.table("founders").select("active_upload_id").eq("id", founder_id).maybe_single().execute()
            active_id = founder_row.data.get("active_upload_id") if founder_row.data else None
            
            query = sb.table("uploads").select("id, filename, storage_path, file_type, created_at").eq("founder_id", founder_id).eq("file_type", "financial")
            
            if active_id:
                # Prioritize the active one
                result = query.eq("id", active_id).maybe_single().execute()
                if result.data:
                    recent_uploads = [result.data]
            
            if not recent_uploads:
                # Fallback to most recent if no active or active not found
                result = query.order("created_at", desc=True).limit(5).execute()
                recent_uploads = result.data or []
        except Exception as exc:
            logger.error("uploads fetch failed: %s", exc)

        for upload in recent_uploads:
            storage_path = upload.get("storage_path")
            filename = upload.get("filename", "data.csv")
            if not storage_path:
                continue
            try:
                csv_bytes = download_file(storage_path, sb)
                if csv_bytes:
                    html = generate_report(csv_bytes, filename, groq_client)
                    return HTMLResponse(content=html, status_code=200)
            except Exception as exc:
                logger.error("Report from upload '%s' failed: %s", filename, exc)
                continue

    # ── No data available ─────────────────────────────────────────────────────
    return HTMLResponse(content=_no_data_html(), status_code=200)


def _no_data_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>No Data — FoundrAI</title>
<style>
  body{background:#080810;color:#e2e8f0;font-family:-apple-system,sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
  .box{text-align:center;padding:48px;border:1px solid #1e1e30;border-radius:20px;
       background:#0f0f1a;max-width:440px}
  h2{font-size:22px;font-weight:700;margin-bottom:12px}
  p{color:#6b7280;font-size:14px;line-height:1.6;margin-bottom:24px}
  a{display:inline-block;padding:12px 28px;border-radius:12px;
    background:linear-gradient(135deg,#6366f1,#a855f7);
    color:#fff;font-weight:700;font-size:13px;text-decoration:none}
</style>
</head>
<body>
<div class="box">
  <div style="font-size:48px;margin-bottom:16px">📊</div>
  <h2>No Financial Data Yet</h2>
  <p>Upload a financial CSV (with revenue, burn_rate, headcount, cac, ltv columns)
     to generate your AI analytics dashboard.</p>
  <a href="/upload">Upload Financial Data</a>
</div>
</body>
</html>"""
