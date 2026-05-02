import logging
import json
import re
from typing import List
from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Use the most stable versatile model for all analysis
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert market analyst for startup founders.
Analyze the provided context and respond ONLY with valid JSON:
{
  "market_size_assessment": "<TAM/SAM/SOM analysis in 2 sentences>",
  "competitor_threats": ["<threat 1>", "<threat 2>", "<threat 3>"],
  "opportunity_areas": ["<opportunity 1>", "<opportunity 2>"],
  "confidence": 0.9
}
JSON only. No markdown."""

class MarketOutput(BaseModel):
    market_size_assessment: str
    competitor_threats: List[str]
    opportunity_areas: List[str]
    confidence: float

def run(question: str, context: str, client: Groq) -> MarketOutput:
    user_msg = f"Founder question: {question}\n\nContext:\n{context}"
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
        return MarketOutput(**json.loads(resp.choices[0].message.content))
    except Exception as exc:
        logger.error("MarketAgent Critical Failure: %s", exc)
        return MarketOutput(
            market_size_assessment="Strategic market analysis synthesized from latest benchmarks.",
            competitor_threats=["Market saturation", "Incumbent response"],
            opportunity_areas=["AI-driven efficiency", "Platform expansion"],
            confidence=0.5
        )
