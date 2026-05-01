"""Simulate router: Monte Carlo simulation seeded from stored financial metrics."""

import logging
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.auth.middleware import verify_jwt
from backend.automl.monte_carlo import BASE_BURN, BASE_CASH, BASE_REVENUE, run_monte_carlo
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])


class SimulateRequest(BaseModel):
    upload_id: str
    months_ahead: int = Field(default=12, ge=1, le=24)
    cac_change_pct: float = Field(default=0.0, description="CAC change as decimal, e.g. 0.20 = +20%")
    burn_change_pct: float = Field(default=0.0, description="Burn rate change as decimal")
    growth_scenario: Literal["bear", "base", "bull"] = "base"


class ForecastMonth(BaseModel):
    month: int
    p10: float
    p50: float
    p90: float


class SimulateResponse(BaseModel):
    simulation_id: Optional[str] = None
    forecast: List[ForecastMonth]
    runway_months: float
    runway_p10: float
    runway_p90: float
    model_used: str
    simulation_runs: int


def _fetch_metrics(founder_id: str, upload_id: str) -> dict:
    """Load initial_metrics JSON from the uploads row.

    Falls back to empty dict (MC uses defaults) when Supabase is unavailable
    or the upload_id doesn't belong to this founder.
    """
    sb = get_supabase_client()
    if sb is None:
        return {}
    try:
        row = (
            sb.table("uploads")
            .select("initial_metrics")
            .eq("id", upload_id)
            .eq("founder_id", founder_id)
            .single()
            .execute()
        )
        return (row.data or {}).get("initial_metrics") or {}
    except Exception as exc:
        logger.warning("Could not load metrics for upload_id=%s: %s", upload_id, exc)
        return {}


@router.post("", response_model=SimulateResponse)
async def simulate(
    body: SimulateRequest,
    founder: dict = Depends(verify_jwt),
) -> SimulateResponse:
    """Run Monte Carlo simulation seeded from founder's uploaded financial data.

    Args:
        body: Simulation parameters.
        founder: Verified JWT claims.

    Returns:
        SimulateResponse with P10/P50/P90 bands and runway estimates.
    """
    founder_id: str = founder["sub"]
    logger.info(
        "Simulation: founder=%s upload=%s months=%d scenario=%s",
        founder_id, body.upload_id, body.months_ahead, body.growth_scenario,
    )

    metrics = _fetch_metrics(founder_id, body.upload_id)
    revenue = metrics.get("revenue", BASE_REVENUE)
    burn = metrics.get("burn_rate", BASE_BURN)

    result = run_monte_carlo(
        months_ahead=body.months_ahead,
        growth_scenario=body.growth_scenario,
        initial_revenue=revenue,
        initial_burn=burn,
        initial_cash=revenue * 6,   # 6-month revenue as cash proxy when no explicit balance
        cac_change_pct=body.cac_change_pct,
        burn_change_pct=body.burn_change_pct,
    )

    forecast_list = [
        ForecastMonth(month=m.month, p10=m.p10, p50=m.p50, p90=m.p90)
        for m in result.forecast
    ]

    simulation_id = _persist_result(
        founder_id=founder_id,
        upload_id=body.upload_id,
        months_ahead=body.months_ahead,
        growth_scenario=body.growth_scenario,
        forecast_list=forecast_list,
        runway_p10=result.runway_p10,
        runway_p50=result.runway_p50,
        runway_p90=result.runway_p90,
    )

    return SimulateResponse(
        simulation_id=simulation_id,
        forecast=forecast_list,
        runway_months=result.runway_p50,
        runway_p10=result.runway_p10,
        runway_p90=result.runway_p90,
        model_used="monte-carlo-10k",
        simulation_runs=result.simulation_runs,
    )


def _persist_result(
    founder_id: str,
    upload_id: str,
    months_ahead: int,
    growth_scenario: str,
    forecast_list: List[ForecastMonth],
    runway_p10: float,
    runway_p50: float,
    runway_p90: float,
) -> Optional[str]:
    """Persist simulation output to simulation_results table. Returns simulation_id or None."""
    sb = get_supabase_client()
    if sb is None:
        return None
    sim_id = str(uuid.uuid4())
    try:
        sb.table("simulation_results").insert({
            "id": sim_id,
            "founder_id": founder_id,
            "upload_id": upload_id,
            "months_ahead": months_ahead,
            "growth_scenario": growth_scenario,
            "forecast": [m.model_dump() for m in forecast_list],
            "runway_p10": runway_p10,
            "runway_p50": runway_p50,
            "runway_p90": runway_p90,
        }).execute()
        logger.info("Simulation persisted: id=%s founder=%s", sim_id, founder_id)
        return sim_id
    except Exception as exc:
        logger.error("Simulation persist failed founder=%s: %s", founder_id, exc)
        return None
