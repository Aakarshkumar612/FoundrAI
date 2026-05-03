"""Data Analyst Agent — two-pass LLM orchestrated analysis for HTML report generation.

Architecture:
  Pass 1 — OrchestratorAgent (llama-3.1-8b, fast): reads raw data summary, identifies
            critical patterns and directs what the analyst should focus on.
  Pass 2 — DataAnalystAgent (llama-3.3-70b, deep): receives directive + full data,
            produces comprehensive Markdown analysis ready for HTML embedding.
"""

import io
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Model selection ────────────────────────────────────────────────────────────

_ORCHESTRATOR_MODEL = "llama-3.1-8b-instant"   # fast, cheap — just for direction
_ANALYST_MODEL      = "llama-3.3-70b-versatile" # deep analysis, full context

# ── System prompts ─────────────────────────────────────────────────────────────

_ORCHESTRATOR_SYSTEM = """You are the Lead Analytics Orchestrator at FoundrAI.
You receive a financial data summary and direct the analyst team.

Your output is a concise internal briefing (max 200 words) that:
1. Names the 2-3 most critical metrics that need explanation
2. Flags any anomalies or concerning trends with the specific numbers
3. Identifies the biggest opportunity visible in the data
4. States the #1 strategic question this founder should answer

Be precise. Use numbers. This briefing goes to the senior analyst."""


_ANALYST_SYSTEM = """You are a Senior Data Scientist and Financial Analyst with 20 years at top VC firms and investment banks. You receive financial data + orchestrator guidance.

Produce a COMPREHENSIVE advisory analysis in clean Markdown. Structure EXACTLY as follows:

## Executive Summary
[2-3 sentences with THE most important finding and the key metric number]

## Revenue Performance
[Growth trajectory, MoM rates, trend direction — use specific numbers]

## Unit Economics
[LTV/CAC ratio and what it means, burn multiple, capital efficiency — be specific]

## Financial Health
[Burn rate, runway estimate, cash efficiency — concrete assessment]

## Risk Assessment
[Top 3 risks with severity and specific evidence from the numbers]

## Growth Opportunities
[Top 2-3 data-backed opportunities with reasoning]

## Strategic Recommendations
[5 specific, actionable recommendations — each with a reason tied to a number]

## ✅ Must Do This Quarter
- [specific action with target metric] — because [specific number justification]
- [specific action with target metric] — because [specific number justification]
- [specific action with target metric] — because [specific number justification]
- [specific action with target metric] — because [specific number justification]
- [specific action with target metric] — because [specific number justification]

## ❌ Avoid These Mistakes
- [specific mistake founders make in this situation] — risk: [specific consequence with number]
- [specific mistake founders make in this situation] — risk: [specific consequence with number]
- [specific mistake founders make in this situation] — risk: [specific consequence with number]
- [specific mistake founders make in this situation] — risk: [specific consequence with number]
- [specific mistake founders make in this situation] — risk: [specific consequence with number]

## 90-Day Action Plan
### First 30 Days
- [specific action]
### Days 31-60
- [specific action]
### Days 61-90
- [specific action]

Rules:
- **Bold** every key metric and number
- Be prescriptive — tell them exactly what to do
- Every recommendation must reference a specific data point
- The Must Do / Avoid sections are the most important — make them actionable and data-backed
- Write as an advisor in the room, not a report generator"""


# ── Data summary builder ───────────────────────────────────────────────────────

def _build_summary(df: pd.DataFrame) -> str:
    """Build a rich but compact data summary for the LLM."""
    df2 = df.copy()
    df2.columns = [c.strip().lower() for c in df2.columns]
    lines = [f"Rows: {len(df2)}, Columns: {list(df2.columns)}"]

    num_cols = df2.select_dtypes(include="number").columns.tolist()
    for col in num_cols:
        s = df2[col].dropna()
        if len(s) == 0:
            continue
        lines.append(
            f"{col}: first={s.iloc[0]:.1f}  last={s.iloc[-1]:.1f}  "
            f"min={s.min():.1f}  max={s.max():.1f}  mean={s.mean():.1f}"
        )

    # Compute key derived metrics if possible
    try:
        if "revenue" in df2.columns and "burn_rate" in df2.columns:
            first_rev = float(df2["revenue"].iloc[0])
            last_rev  = float(df2["revenue"].iloc[-1])
            last_burn = float(df2["burn_rate"].iloc[-1])
            if first_rev > 0:
                total_growth = (last_rev - first_rev) / first_rev * 100
                lines.append(f"Total revenue growth over period: {total_growth:.1f}%")
            if last_rev > 0:
                burn_mult = last_burn / last_rev
                lines.append(f"Latest burn multiple: {burn_mult:.2f}x (target <1.0 is efficient)")

        if "cac" in df2.columns and "ltv" in df2.columns:
            last_cac = float(df2["cac"].iloc[-1])
            last_ltv = float(df2["ltv"].iloc[-1])
            if last_cac > 0:
                ltv_cac = last_ltv / last_cac
                lines.append(f"Latest LTV/CAC ratio: {ltv_cac:.2f}x (>3x is healthy)")

        # MoM growth rates
        if "revenue" in df2.columns and len(df2) >= 3:
            revs = df2["revenue"].dropna().astype(float).tolist()
            mom_rates = []
            for i in range(1, min(6, len(revs))):
                if revs[i - 1] > 0:
                    mom_rates.append((revs[i] - revs[i - 1]) / revs[i - 1] * 100)
            if mom_rates:
                avg_mom = sum(mom_rates) / len(mom_rates)
                lines.append(f"Average MoM revenue growth (last {len(mom_rates)} months): {avg_mom:.1f}%")
    except Exception:
        pass

    return "\n".join(lines)


# ── Two-pass analysis ──────────────────────────────────────────────────────────

def _orchestrate(summary: str, groq_client) -> str:
    """Pass 1: Orchestrator identifies critical focus areas."""
    try:
        resp = groq_client.chat.completions.create(
            model=_ORCHESTRATOR_MODEL,
            messages=[
                {"role": "system", "content": _ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": f"Financial Data Summary:\n{summary}"},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("Orchestrator pass failed: %s", exc)
        return "Focus on revenue growth trajectory, burn efficiency, and LTV/CAC health."


def _analyse(summary: str, directive: str, groq_client) -> str:
    """Pass 2: Deep analyst produces comprehensive Markdown report."""
    user_msg = (
        f"ORCHESTRATOR DIRECTIVE:\n{directive}\n\n"
        f"FINANCIAL DATA:\n{summary}\n\n"
        "Produce the comprehensive analysis now."
    )
    try:
        resp = groq_client.chat.completions.create(
            model=_ANALYST_MODEL,
            messages=[
                {"role": "system", "content": _ANALYST_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Analyst pass failed: %s", exc)
        return _fallback_analysis(summary, error=str(exc))


def _fallback_analysis(summary: str, error: Optional[str] = None) -> str:
    msg = "Full AI analysis requires a valid Groq API key."
    if error:
        msg = f"AI analysis failed: {error}. Please check your Groq API key and rate limits."
        
    return (
        "## Executive Summary\n"
        f"{msg}\n\n"
        "## Key Metrics\n"
        f"{summary}\n\n"
        "## Recommendations\n"
        "- Review revenue growth trajectory against industry benchmarks\n"
        "- Ensure burn multiple stays below 1.5x for capital efficiency\n"
        "- Target LTV/CAC ratio above 3x for sustainable growth\n"
    )


# ── Public entry point ─────────────────────────────────────────────────────────

def run(df: pd.DataFrame, groq_client=None) -> str:
    """Run two-pass analysis on a financial DataFrame.

    Returns:
        Comprehensive Markdown analysis string ready for HTML embedding.
    """
    summary = _build_summary(df)

    if groq_client is None:
        return _fallback_analysis(summary)

    try:
        directive = _orchestrate(summary, groq_client)
        logger.info("Orchestrator directive: %s", directive[:120])
    except Exception as exc:
        logger.error("Orchestrator failed: %s", exc)
        return _fallback_analysis(summary, error=str(exc))

    return _analyse(summary, directive, groq_client)


def run_from_csv(csv_bytes: bytes, groq_client=None) -> str:
    """Convenience wrapper that parses CSV bytes first."""
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    except Exception as exc:
        logger.error("CSV parse failed in data_analyst_agent: %s", exc)
        return "## Error\nCould not parse financial data."
    return run(df, groq_client)
