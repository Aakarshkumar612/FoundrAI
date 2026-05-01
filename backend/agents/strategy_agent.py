"""Strategy synthesis agent — combines all prior agent outputs into recommendations."""

import json
import logging
from typing import List

from groq import Groq
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Llama 3.3-70b for complex synthesis and planning
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a startup strategy advisor synthesizing analysis from specialist agents.
Given the founder's question and all prior analysis, respond ONLY with valid JSON:
{
  "executive_summary": "<2-3 sentence synthesis directly answering the founder's question>",
  "top_3_recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
  "immediate_actions": ["<action 1>", "<action 2>"],
  "30_60_90_day_plan": {
    "30_days": ["<task 1>", "<task 2>"],
    "60_days": ["<task 1>", "<task 2>"],
    "90_days": ["<task 1>", "<task 2>"]
  }
}
JSON only. No markdown."""


class Plan(BaseModel):
    days_30: List[str]
    days_60: List[str]
    days_90: List[str]


class StrategyOutput(BaseModel):
    executive_summary: str
    top_3_recommendations: List[str]
    immediate_actions: List[str]
    plan_30_60_90: Plan


def run(
    question: str,
    market_output: dict,
    risk_output: dict,
    revenue_output: dict,
    client: Groq,
) -> StrategyOutput:
    """Synthesize all agent outputs into a final strategic recommendation.

    Args:
        question: Founder's original question.
        market_output: MarketAgent result dict.
        risk_output: RiskAgent result dict.
        revenue_output: RevenueAgent result dict.
        client: Groq client instance.

    Returns:
        StrategyOutput with recommendations and 30/60/90 day plan.
    """
    combined = {
        "market": market_output,
        "risk": risk_output,
        "revenue": revenue_output,
    }
    user_msg = (
        f"Founder question: {question}\n\n"
        f"Specialist analysis:\n{json.dumps(combined, indent=2)}"
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=800,
            temperature=0.4,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        plan_raw = data.get("30_60_90_day_plan", {})
        return StrategyOutput(
            executive_summary=data.get("executive_summary", ""),
            top_3_recommendations=data.get("top_3_recommendations", []),
            immediate_actions=data.get("immediate_actions", []),
            plan_30_60_90=Plan(
                days_30=plan_raw.get("30_days", []),
                days_60=plan_raw.get("60_days", []),
                days_90=plan_raw.get("90_days", []),
            ),
        )
    except Exception as exc:
        logger.warning("StrategyAgent failed: %s — using fallback", str(exc))
        return StrategyOutput(
            executive_summary="Strategy synthesis requires complete analysis data.",
            top_3_recommendations=["Complete data upload", "Re-run analysis", "Contact support"],
            immediate_actions=["Upload financial CSV"],
            plan_30_60_90=Plan(days_30=[], days_60=[], days_90=[]),
        )
