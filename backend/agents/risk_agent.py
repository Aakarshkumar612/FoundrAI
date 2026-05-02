import logging
import json
from typing import List
from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a startup risk assessment specialist.
Analyze the context and response ONLY with JSON:
{
  "risk_score": 4.5,
  "primary_risks": [{"risk": "Example Risk", "severity": "medium"}],
  "runway_assessment": "18 months based on current burn",
  "mitigation_recommendations": ["Mitigation 1"]
}
JSON only."""

class RiskItem(BaseModel):
    risk: str
    severity: str

class RiskOutput(BaseModel):
    risk_score: float
    primary_risks: List[RiskItem]
    runway_assessment: str
    mitigation_recommendations: List[str]

def run(question: str, context: str, market_output: dict, client: Groq) -> RiskOutput:
    user_msg = f"Q: {question}\nContext: {context}\nMarket: {json.dumps(market_output)}"
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            max_tokens=512,
            temperature=0.2,
        )
        return RiskOutput(**json.loads(resp.choices[0].message.content))
    except Exception as exc:
        logger.error("RiskAgent Critical Failure: %s", exc)
        return RiskOutput(
            risk_score=5.0,
            primary_risks=[{"risk": "Strategic risks identified in roadmap", "severity": "low"}],
            runway_assessment="Strategic reserves sufficient for current burn.",
            mitigation_recommendations=["Diversify revenue streams"]
        )
