"""FLAML AutoML trainer for revenue forecasting from historical CSV data."""

import io
import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

TIME_BUDGET_SECONDS = 30
REQUIRED_COLUMNS = {"revenue", "burn_rate", "headcount", "cac", "ltv"}


@dataclass
class TrainResult:
    model_name: str
    rmse: float
    r2: float
    n_rows: int


def _parse_csv(content: bytes):
    """Parse CSV bytes into a pandas DataFrame. Returns None on failure."""
    try:
        import pandas as pd
        df = pd.read_csv(io.BytesIO(content))
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as exc:
        logger.error("CSV parse failed: %s", exc)
        return None


def _engineer_features(df):
    """Add derived features used by FLAML. Modifies df in place and returns it."""
    import pandas as pd

    df = df.copy()
    df["month_index"] = range(len(df))
    df["log_cac"] = np.log1p(df["cac"].clip(lower=0))
    df["log_ltv"] = np.log1p(df["ltv"].clip(lower=0))
    df["ltv_cac_ratio"] = (df["ltv"] / df["cac"].replace(0, np.nan)).fillna(0)
    df["burn_coverage"] = df["revenue"] / df["burn_rate"].replace(0, np.nan).fillna(1)
    return df


def train_revenue_model(
    content: bytes,
    time_budget: int = TIME_BUDGET_SECONDS,
) -> Optional[TrainResult]:
    """Train a FLAML AutoML regression model on financial CSV data.

    Features: month_index, headcount, log_cac, log_ltv, ltv_cac_ratio,
              burn_coverage, burn_rate.
    Target: revenue.

    Args:
        content: Raw CSV bytes (must have REQUIRED_COLUMNS).
        time_budget: FLAML time budget in seconds.

    Returns:
        TrainResult with model name and metrics, or None if training fails.
    """
    try:
        from flaml import AutoML
        from sklearn.metrics import mean_squared_error, r2_score
    except ImportError as exc:
        logger.error("FLAML or scikit-learn not installed: %s", exc)
        return None

    df = _parse_csv(content)
    if df is None:
        return None

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        logger.error("CSV missing required columns: %s", missing)
        return None

    if len(df) < 4:
        logger.error("Not enough rows to train (need >= 4, got %d)", len(df))
        return None

    df = _engineer_features(df)

    feature_cols = [
        "month_index", "headcount", "burn_rate",
        "log_cac", "log_ltv", "ltv_cac_ratio", "burn_coverage",
    ]
    X = df[feature_cols].values
    y = df["revenue"].values

    split = max(1, int(len(df) * 0.8))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    if len(X_val) == 0:
        X_val, y_val = X_train, y_train

    automl = AutoML()
    automl.fit(
        X_train, y_train,
        task="regression",
        metric="rmse",
        time_budget=time_budget,
        verbose=0,
        log_file_name="",
        eval_method="holdout",
        X_val=X_val,
        y_val=y_val,
        estimator_list=["rf", "extra_tree", "histgb", "enet", "lassolars"],
    )

    y_pred = automl.predict(X_val)
    rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))
    r2 = float(r2_score(y_val, y_pred)) if len(y_val) > 1 else 0.0

    model_name = getattr(automl, "best_estimator", "flaml-automl")
    logger.info("FLAML trained: model=%s rmse=%.2f r2=%.3f rows=%d", model_name, rmse, r2, len(df))

    return TrainResult(
        model_name=str(model_name),
        rmse=round(rmse, 2),
        r2=round(r2, 4),
        n_rows=len(df),
    )


def extract_initial_metrics(content: bytes) -> dict:
    """Extract the latest row's financial metrics from a CSV for use as MC seed.

    Args:
        content: Raw CSV bytes.

    Returns:
        Dict with revenue, burn_rate, headcount, cac, ltv (last row values),
        or defaults if parsing fails.
    """
    defaults = {
        "revenue": 85_000.0,
        "burn_rate": 42_000.0,
        "headcount": 12,
        "cac": 450.0,
        "ltv": 2100.0,
    }
    df = _parse_csv(content)
    if df is None or not REQUIRED_COLUMNS.issubset(set(df.columns)) or len(df) == 0:
        return defaults

    last = df.iloc[-1]
    return {
        "revenue": float(last.get("revenue", defaults["revenue"])),
        "burn_rate": float(last.get("burn_rate", defaults["burn_rate"])),
        "headcount": int(last.get("headcount", defaults["headcount"])),
        "cac": float(last.get("cac", defaults["cac"])),
        "ltv": float(last.get("ltv", defaults["ltv"])),
    }


def extract_metrics_from_excel(content: bytes) -> dict:
    """Scan Excel sheets for financial columns and return latest row metrics."""
    defaults = {
        "revenue": 85_000.0, "burn_rate": 42_000.0,
        "headcount": 12, "cac": 450.0, "ltv": 2100.0,
    }
    try:
        import pandas as pd
        xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            df.columns = [str(c).strip().lower() for c in df.columns]
            if REQUIRED_COLUMNS.issubset(set(df.columns)) and len(df) > 0:
                last = df.iloc[-1]
                return {
                    "revenue": float(last.get("revenue", defaults["revenue"])),
                    "burn_rate": float(last.get("burn_rate", defaults["burn_rate"])),
                    "headcount": int(last.get("headcount", defaults["headcount"])),
                    "cac": float(last.get("cac", defaults["cac"])),
                    "ltv": float(last.get("ltv", defaults["ltv"])),
                }
    except Exception as exc:
        logger.error("Excel metric extraction failed: %s", exc)
    return defaults


def extract_metrics_from_text(text: str, groq_client=None) -> dict:
    """Use Groq LLM to pull financial metrics from any extracted text (PDF, Word, TXT, image)."""
    defaults = {
        "revenue": 85_000.0, "burn_rate": 42_000.0,
        "headcount": 12, "cac": 450.0, "ltv": 2100.0,
    }
    if not text.strip() or groq_client is None:
        return defaults

    prompt = (
        "Extract the most recent monthly financial metrics from this text. "
        'Return ONLY valid JSON: {"revenue": float, "burn_rate": float, "headcount": int, "cac": float, "ltv": float}. '
        "Use 0 for any metric not present. No explanation, JSON only.\n\n"
        f"Text:\n{text[:4000]}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or ""
        match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {
                "revenue": float(parsed.get("revenue") or defaults["revenue"]),
                "burn_rate": float(parsed.get("burn_rate") or defaults["burn_rate"]),
                "headcount": int(parsed.get("headcount") or defaults["headcount"]),
                "cac": float(parsed.get("cac") or defaults["cac"]),
                "ltv": float(parsed.get("ltv") or defaults["ltv"]),
            }
    except Exception as exc:
        logger.error("Groq metric extraction failed: %s", exc)
    return defaults
