"""Charts router: Superset guest token and dashboard list endpoints."""

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.auth.middleware import verify_jwt
from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/charts", tags=["charts"])

_DASHBOARDS = [
    {"id": "revenue-overview", "title": "Revenue Overview",
     "description": "Monthly revenue trend, MoM growth rate, revenue vs burn"},
    {"id": "unit-economics",   "title": "Unit Economics",
     "description": "CAC over time, LTV over time, LTV/CAC ratio, payback period"},
    {"id": "growth-health",    "title": "Growth Health",
     "description": "MRR growth %, churn rate, DAU/MAU trend, NRR waterfall"},
]


class EmbedTokenResponse(BaseModel):
    token: str
    expires_in: int


class Dashboard(BaseModel):
    id: str
    title: str
    description: str
    thumbnail_url: Optional[str] = None


class DashboardListResponse(BaseModel):
    dashboards: List[Dashboard]


async def _superset_access_token(settings: Settings) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.superset_url}/api/v1/security/login",
            json={
                "username": settings.superset_username,
                "password": settings.superset_password,
                "provider": "db",
                "refresh": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def _superset_guest_token(
    settings: Settings, dashboard_id: str, founder_id: str
) -> str:
    access_token = await _superset_access_token(settings)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.superset_url}/api/v1/security/guest_token/",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "resources": [{"type": "dashboard", "id": dashboard_id}],
                "rls": [],
                "user": {
                    "username": f"founder_{founder_id[:8]}",
                    "first_name": "Founder",
                    "last_name": "",
                },
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]


@router.get("/embed-token", response_model=EmbedTokenResponse)
async def get_embed_token(
    dashboard_id: str = "revenue-overview",
    founder: dict = Depends(verify_jwt),
    settings: Settings = Depends(get_settings),
) -> EmbedTokenResponse:
    """Return a short-lived Superset guest token for embedding a dashboard.

    Falls back to a dev-mode mock token when Superset is not configured.
    """
    founder_id: str = founder["sub"]
    logger.info("Embed token: founder=%s dashboard=%s", founder_id, dashboard_id)

    if not settings.superset_password:
        return EmbedTokenResponse(
            token=f"dev-token-{founder_id[:8]}", expires_in=300
        )
    try:
        token = await _superset_guest_token(settings, dashboard_id, founder_id)
        return EmbedTokenResponse(token=token, expires_in=300)
    except httpx.HTTPError as exc:
        logger.error("Superset guest token failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "EXT_FETCH_001", "message": "Superset unavailable"},
        )


@router.get("/dashboards", response_model=DashboardListResponse)
async def list_dashboards(founder: dict = Depends(verify_jwt)) -> DashboardListResponse:
    """List available Superset dashboards."""
    logger.info("Dashboards list: founder=%s", founder["sub"])
    return DashboardListResponse(dashboards=[Dashboard(**d) for d in _DASHBOARDS])
