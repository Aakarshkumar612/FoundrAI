"""Monte Carlo simulation engine for revenue and runway forecasting."""

import logging
from dataclasses import dataclass
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

N_SIMULATIONS = 10_000
BASE_REVENUE = 85_000.0   # fallback MRR when no upload data available (Layer 8 wires real data)
BASE_BURN = 42_000.0
BASE_CASH = 500_000.0     # assumed cash on hand

# Monthly growth rate distributions (mean, std) per scenario
SCENARIO_GROWTH = {
    "bear": (-0.01, 0.05),
    "base": (0.05,  0.04),
    "bull": (0.12,  0.06),
}

BURN_VOLATILITY = 0.08  # std as fraction of monthly burn


@dataclass
class MonthForecast:
    month: int
    p10: float
    p50: float
    p90: float


@dataclass
class SimulationResult:
    forecast: List[MonthForecast]
    runway_p10: float
    runway_p50: float
    runway_p90: float
    simulation_runs: int


def run_monte_carlo(
    months_ahead: int,
    growth_scenario: str,
    initial_revenue: float = BASE_REVENUE,
    initial_burn: float = BASE_BURN,
    initial_cash: float = BASE_CASH,
    cac_change_pct: float = 0.0,
    burn_change_pct: float = 0.0,
    n_simulations: int = N_SIMULATIONS,
    seed: int | None = None,
) -> SimulationResult:
    """Run a vectorised Monte Carlo simulation.

    Each simulation path draws a monthly growth rate from the scenario
    distribution and a burn rate with Gaussian noise. Revenue compounds
    across months; runway is the month where cumulative burn exceeds cash.

    Args:
        months_ahead: Forecast horizon (1–24).
        growth_scenario: 'bear' | 'base' | 'bull'.
        initial_revenue: Starting MRR.
        initial_burn: Starting monthly burn.
        initial_cash: Cash balance at t=0.
        cac_change_pct: CAC increase/decrease as decimal (drags growth 0.3×).
        burn_change_pct: Burn rate increase/decrease as decimal.
        n_simulations: Number of Monte Carlo paths.
        seed: Optional RNG seed for reproducibility.

    Returns:
        SimulationResult with per-month P10/P50/P90 and runway percentiles.
    """
    if growth_scenario not in SCENARIO_GROWTH:
        raise ValueError(f"growth_scenario must be bear/base/bull, got {growth_scenario!r}")

    rng = np.random.default_rng(seed)
    growth_mean, growth_std = SCENARIO_GROWTH[growth_scenario]
    growth_mean -= cac_change_pct * 0.3  # CAC drag on growth

    adjusted_burn = initial_burn * (1 + burn_change_pct)

    # Shape: (n_simulations, months_ahead)
    monthly_growth = rng.normal(growth_mean, growth_std, (n_simulations, months_ahead))
    burn_noise = rng.normal(0, BURN_VOLATILITY, (n_simulations, months_ahead))

    # Revenue paths: compound growth each month
    growth_factors = 1 + monthly_growth                        # (N, M)
    revenue_paths = initial_revenue * np.cumprod(growth_factors, axis=1)  # (N, M)

    # Burn paths: base burn + noise
    burn_paths = adjusted_burn * (1 + burn_noise)              # (N, M)
    burn_paths = np.clip(burn_paths, adjusted_burn * 0.5, adjusted_burn * 2.0)

    # Runway: months until cumulative burn > cash
    cumulative_burn = np.cumsum(burn_paths, axis=1)            # (N, M)
    exhausted = cumulative_burn > initial_cash                  # (N, M) bool

    # For each simulation, find the first month of exhaustion (0-indexed → +1)
    runway_months = np.where(
        exhausted.any(axis=1),
        np.argmax(exhausted, axis=1).astype(float) + 1,
        float(months_ahead) + 1,  # still has cash at end of horizon
    )

    # Build per-month forecast
    forecast: List[MonthForecast] = []
    for m in range(months_ahead):
        col = revenue_paths[:, m]
        forecast.append(MonthForecast(
            month=m + 1,
            p10=round(float(np.percentile(col, 10)), 2),
            p50=round(float(np.percentile(col, 50)), 2),
            p90=round(float(np.percentile(col, 90)), 2),
        ))

    return SimulationResult(
        forecast=forecast,
        runway_p10=round(float(np.percentile(runway_months, 10)), 1),
        runway_p50=round(float(np.percentile(runway_months, 50)), 1),
        runway_p90=round(float(np.percentile(runway_months, 90)), 1),
        simulation_runs=n_simulations,
    )
