"""Tests for Layer 7: Monte Carlo simulation engine and FLAML trainer."""

import numpy as np
import pytest

from backend.automl.monte_carlo import (
    BASE_BURN,
    BASE_CASH,
    BASE_REVENUE,
    SimulationResult,
    run_monte_carlo,
)
from backend.automl.trainer import (
    TrainResult,
    extract_initial_metrics,
    extract_metrics_from_excel,
    extract_metrics_from_text,
    train_revenue_model,
)

SEED = 42

# ── Monte Carlo tests ─────────────────────────────────────────────────────────

class TestMonteCarlo:
    def _run(self, scenario="base", months=12, **kwargs) -> SimulationResult:
        return run_monte_carlo(months, scenario, seed=SEED, **kwargs)

    def test_returns_simulation_result(self):
        result = self._run()
        assert isinstance(result, SimulationResult)

    def test_forecast_length_matches_months(self):
        result = self._run(months=6)
        assert len(result.forecast) == 6

    def test_forecast_months_are_sequential(self):
        result = self._run(months=12)
        assert [m.month for m in result.forecast] == list(range(1, 13))

    def test_p10_lte_p50_lte_p90(self):
        result = self._run()
        for m in result.forecast:
            assert m.p10 <= m.p50 <= m.p90, f"Month {m.month}: p10={m.p10} p50={m.p50} p90={m.p90}"

    def test_bull_p50_exceeds_bear_p50(self):
        bear = self._run(scenario="bear")
        bull = self._run(scenario="bull")
        last_bear = bear.forecast[-1].p50
        last_bull = bull.forecast[-1].p50
        assert last_bull > last_bear

    def test_runway_p10_lte_p50_lte_p90(self):
        result = self._run()
        assert result.runway_p10 <= result.runway_p50 <= result.runway_p90

    def test_bear_runway_shorter_than_bull(self):
        bear = self._run(scenario="bear")
        bull = self._run(scenario="bull")
        assert bear.runway_p50 <= bull.runway_p50

    def test_simulation_runs_matches_requested(self):
        result = run_monte_carlo(12, "base", n_simulations=1000, seed=SEED)
        assert result.simulation_runs == 1000

    def test_invalid_scenario_raises(self):
        with pytest.raises(ValueError):
            run_monte_carlo(12, "moon")

    def test_cac_increase_reduces_revenue(self):
        baseline = self._run(cac_change_pct=0.0)
        high_cac = self._run(cac_change_pct=0.5)
        assert high_cac.forecast[-1].p50 < baseline.forecast[-1].p50

    def test_burn_increase_reduces_runway(self):
        baseline = self._run(burn_change_pct=0.0)
        high_burn = self._run(burn_change_pct=1.0)
        assert high_burn.runway_p50 <= baseline.runway_p50

    def test_seed_produces_deterministic_output(self):
        r1 = run_monte_carlo(12, "base", seed=99)
        r2 = run_monte_carlo(12, "base", seed=99)
        assert r1.forecast[0].p50 == r2.forecast[0].p50

    def test_different_seeds_produce_different_output(self):
        r1 = run_monte_carlo(12, "base", seed=1)
        r2 = run_monte_carlo(12, "base", seed=2)
        assert r1.forecast[-1].p50 != r2.forecast[-1].p50

    def test_p_values_are_positive(self):
        result = self._run(scenario="bull")
        for m in result.forecast:
            assert m.p10 > 0

    def test_24_month_horizon(self):
        result = self._run(months=24)
        assert len(result.forecast) == 24
        assert result.forecast[-1].month == 24

    def test_custom_initial_revenue(self):
        result = run_monte_carlo(12, "base", initial_revenue=200_000.0, seed=SEED)
        assert result.forecast[0].p50 > BASE_REVENUE  # higher starting revenue

    def test_low_cash_shortens_runway(self):
        rich = run_monte_carlo(12, "base", initial_cash=5_000_000, seed=SEED)
        poor = run_monte_carlo(12, "base", initial_cash=50_000, seed=SEED)
        assert poor.runway_p50 <= rich.runway_p50


# ── FLAML trainer tests ───────────────────────────────────────────────────────

VALID_CSV = (
    b"month,revenue,burn_rate,headcount,cac,ltv\n"
    b"2024-01,70000,38000, 9,380,1900\n"
    b"2024-02,74000,39000, 9,385,1930\n"
    b"2024-03,78000,39500,10,390,1960\n"
    b"2024-04,82000,40000,10,395,1990\n"
    b"2024-05,86000,40500,11,400,2020\n"
    b"2024-06,91000,41000,11,405,2050\n"
    b"2024-07,96000,41500,12,410,2080\n"
    b"2024-08,101000,42000,12,415,2110\n"
    b"2024-09,107000,42500,13,420,2140\n"
    b"2024-10,113000,43000,13,425,2170\n"
    b"2024-11,119000,43500,14,430,2200\n"
    b"2024-12,126000,44000,14,435,2230\n"
    b"2025-01,133000,44500,15,440,2260\n"
    b"2025-02,140000,45000,15,445,2290\n"
    b"2025-03,148000,45500,16,450,2320\n"
    b"2025-04,156000,46000,16,455,2350\n"
    b"2025-05,165000,46500,17,460,2380\n"
    b"2025-06,174000,47000,17,465,2410\n"
    b"2025-07,183000,47500,18,470,2440\n"
    b"2025-08,193000,48000,18,475,2470\n"
    b"2025-09,204000,48500,19,480,2500\n"
    b"2025-10,215000,49000,19,485,2530\n"
    b"2025-11,226000,49500,20,490,2560\n"
    b"2025-12,238000,50000,20,495,2590\n"
)

MISSING_COL_CSV = b"month,revenue,headcount\n2025-01,80000,10\n2025-02,86000,11\n"

SHORT_CSV = b"month,revenue,burn_rate,headcount,cac,ltv\n2025-01,80000,40000,10,400,2000\n"


class TestFLAMLTrainer:
    def test_returns_train_result(self):
        result = train_revenue_model(VALID_CSV, time_budget=5)
        assert isinstance(result, TrainResult)

    def test_model_name_is_non_empty(self):
        result = train_revenue_model(VALID_CSV, time_budget=5)
        assert result.model_name

    def test_rmse_is_positive(self):
        result = train_revenue_model(VALID_CSV, time_budget=5)
        assert result.rmse >= 0

    def test_n_rows_matches_csv(self):
        result = train_revenue_model(VALID_CSV, time_budget=5)
        assert result.n_rows == 24

    def test_missing_columns_returns_none(self):
        result = train_revenue_model(MISSING_COL_CSV, time_budget=5)
        assert result is None

    def test_too_few_rows_returns_none(self):
        result = train_revenue_model(SHORT_CSV, time_budget=5)
        assert result is None

    def test_invalid_bytes_returns_none(self):
        result = train_revenue_model(b"not,a,csv\x00\xff", time_budget=5)
        assert result is None


# ── extract_initial_metrics tests ─────────────────────────────────────────────

class TestExtractInitialMetrics:
    def test_returns_last_row_values(self):
        metrics = extract_initial_metrics(VALID_CSV)
        assert metrics["revenue"] == 238_000.0
        assert metrics["burn_rate"] == 50_000.0
        assert metrics["headcount"] == 20

    def test_returns_defaults_on_bad_csv(self):
        metrics = extract_initial_metrics(b"garbage")
        assert metrics["revenue"] == 85_000.0

    def test_returns_defaults_on_missing_columns(self):
        metrics = extract_initial_metrics(MISSING_COL_CSV)
        assert metrics["revenue"] == 85_000.0

    def test_all_required_keys_present(self):
        metrics = extract_initial_metrics(VALID_CSV)
        for key in ("revenue", "burn_rate", "headcount", "cac", "ltv"):
            assert key in metrics


# ── extract_metrics_from_excel tests ─────────────────────────────────────────

class TestExtractMetricsFromExcel:
    def _make_excel(self, has_financial_cols: bool) -> bytes:
        import io
        import pandas as pd
        if has_financial_cols:
            df = pd.DataFrame([
                {"month": "2025-01", "revenue": 120000, "burn_rate": 55000,
                 "headcount": 18, "cac": 410, "ltv": 2200},
                {"month": "2025-02", "revenue": 130000, "burn_rate": 56000,
                 "headcount": 19, "cac": 420, "ltv": 2300},
            ])
        else:
            df = pd.DataFrame([{"name": "Alice", "age": 30}])
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        return buf.getvalue()

    def test_extracts_last_row_from_financial_sheet(self):
        metrics = extract_metrics_from_excel(self._make_excel(True))
        assert metrics["revenue"] == 130_000.0
        assert metrics["burn_rate"] == 56_000.0
        assert metrics["headcount"] == 19

    def test_falls_back_to_defaults_when_no_financial_cols(self):
        metrics = extract_metrics_from_excel(self._make_excel(False))
        assert metrics["revenue"] == 85_000.0

    def test_all_keys_present(self):
        metrics = extract_metrics_from_excel(self._make_excel(True))
        for key in ("revenue", "burn_rate", "headcount", "cac", "ltv"):
            assert key in metrics

    def test_invalid_bytes_returns_defaults(self):
        metrics = extract_metrics_from_excel(b"not excel")
        assert metrics["revenue"] == 85_000.0


# ── extract_metrics_from_text tests ──────────────────────────────────────────

class TestExtractMetricsFromText:
    def test_returns_defaults_when_no_groq_client(self):
        metrics = extract_metrics_from_text("revenue: 200000, burn: 50000", groq_client=None)
        assert metrics["revenue"] == 85_000.0

    def test_returns_defaults_on_empty_text(self):
        metrics = extract_metrics_from_text("", groq_client=None)
        assert metrics["revenue"] == 85_000.0

    def test_all_keys_present_without_client(self):
        metrics = extract_metrics_from_text("some text", groq_client=None)
        for key in ("revenue", "burn_rate", "headcount", "cac", "ltv"):
            assert key in metrics
