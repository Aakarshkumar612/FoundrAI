"""Market analyst agent — assesses market size, competitors, and opportunities."""

import json
import logging
import re
from typing import List

from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are an expert market analyst for startup founders.
Analyze the provided context and respond ONLY with valid JSON matching this exact schema:
{
  "market_size_assessment": "<TAM/SAM/SOM analysis in 2 sentences>",
  "competitor_threats": ["<threat 1>", "<threat 2>", "<threat 3>"],
  "opportunity_areas": ["<opportunity 1>", "<opportunity 2>"],
  "confidence": <float 0.0-1.0>
}
Be specific and grounded in the provided data. No markdown, no explanation — JSON only."""


class MarketOutput(BaseModel):
    market_size_assessment: str
    competitor_threats: List[str]
    opportunity_areas: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


def run(question: str, context: str, client: Groq) -> MarketOutput:
    """Run the market agent against the founder's question and RAG context.

    Args:
        question: Founder's natural language question.
        context: RAG-retrieved passages from founder docs + news.
        client: Groq client instance.

    Returns:
        MarketOutput with market assessment, threats, and opportunities.
    """
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
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or "{}"
        return MarketOutput(**json.loads(raw))
    except Exception as exc:
        logger.warning("MarketAgent failed: %s — using fallback", str(exc))
        return MarketOutput(
            market_size_assessment="Market analysis unavailable due to processing error.",
            competitor_threats=["Analysis pending"],
            opportunity_areas=["Analysis pending"],
            confidence=0.0,
        )
