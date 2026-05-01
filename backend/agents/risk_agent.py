"""Risk assessment agent — scores startup risk and recommends mitigations."""

import json
import logging
from typing import List

from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are a startup risk assessment specialist.
Analyze the provided financial context and market analysis, then respond ONLY with valid JSON:
{
  "risk_score": <float 0.0-10.0, where 10 is maximum risk>,
  "primary_risks": [
    {"risk": "<risk description>", "severity": "<high|medium|low>"}
  ],
  "runway_assessment": "<runway estimate in plain English, e.g. 14 months at current burn>",
  "mitigation_recommendations": ["<action 1>", "<action 2>", "<action 3>"]
}
JSON only. No markdown."""


class RiskItem(BaseModel):
    risk: str
    severity: str = Field(pattern="^(high|medium|low)$")


class RiskOutput(BaseModel):
    risk_score: float = Field(ge=0.0, le=10.0)
    primary_risks: List[RiskItem]
    runway_assessment: str
    mitigation_recommendations: List[str]


def run(question: str, context: str, market_output: dict, client: Groq) -> RiskOutput:
    """Run the risk agent using context and market agent output.

    Args:
        question: Founder's question.
        context: RAG context passages.
        market_output: Parsed output from MarketAgent.
        client: Groq client instance.

    Returns:
        RiskOutput with risk score, primary risks, and mitigations.
    """
    user_msg = (
        f"Founder question: {question}\n\n"
        f"Context:\n{context}\n\n"
        f"Market analysis:\n{json.dumps(market_output)}"
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or "{}"
        return RiskOutput(**json.loads(raw))
    except Exception as exc:
        logger.warning("RiskAgent failed: %s — using fallback", str(exc))
        return RiskOutput(
            risk_score=5.0,
            primary_risks=[{"risk": "Risk analysis unavailable", "severity": "medium"}],
            runway_assessment="Runway calculation requires complete financial data.",
            mitigation_recommendations=["Provide complete financial data for full analysis"],
        )
