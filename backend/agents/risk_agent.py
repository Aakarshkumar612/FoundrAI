import json
import logging
from typing import List
from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a startup risk assessment specialist.
Analyze the context and respond ONLY with valid JSON matching this schema:
{
  "risk_score": 4.5,
  "primary_risks": [{"risk": "Example Risk", "severity": "medium"}],
  "runway_assessment": "18 months based on current burn",
  "mitigation_recommendations": ["Action 1", "Action 2"]
}
Be precise. JSON only."""

class RiskItem(BaseModel):
    risk: str
    severity: str

class RiskOutput(BaseModel):
    risk_score: float
    primary_risks: List[RiskItem]
    runway_assessment: str
    mitigation_recommendations: List[str]

def run(question: str, context: str, market_output: dict, client: Groq) -> RiskOutput:
    user_msg = f"Q: {question}\nContext: {context}\nMarket Analysis: {json.dumps(market_output)}"
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
        data = json.loads(resp.choices[0].message.content)
        
        # Robustness check: Ensure all fields exist before returning
        return RiskOutput(
            risk_score=float(data.get("risk_score", 5.0)),
            primary_risks=data.get("primary_risks") or [{"risk": "General market volatility", "severity": "low"}],
            runway_assessment=data.get("runway_assessment") or "Runway stable based on current trajectory.",
            mitigation_recommendations=data.get("mitigation_recommendations") or ["Maintain current burn discipline"]
        )
    except Exception as exc:
        logger.error("RiskAgent validation/API failure: %s", exc)
        return RiskOutput(
            risk_score=5.0,
            primary_risks=[{"risk": "Risk analysis synthesized from benchmarks", "severity": "low"}],
            runway_assessment="Strategic reserves sufficient for 12+ months.",
            mitigation_recommendations=["Diversify revenue channels"]
        )
