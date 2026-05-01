"""Revenue forecasting agent — quantitative analysis using DeepSeek-R1."""

import json
import logging
import re
from typing import List

from groq import Groq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# DeepSeek-R1 for strong quantitative reasoning
MODEL = "deepseek-r1-distill-llama-70b"

SYSTEM_PROMPT = """You are a quantitative revenue forecasting analyst for startups.
Analyze the financial data and risk assessment, then respond with valid JSON only:
{
  "forecast_narrative": "<2-3 sentence revenue outlook based on the data>",
  "key_drivers": ["<driver 1>", "<driver 2>", "<driver 3>"],
  "growth_levers": ["<lever 1>", "<lever 2>"],
  "forecast_confidence": "<high|medium|low>"
}
JSON only. No markdown, no <think> tags in your response."""


class RevenueOutput(BaseModel):
    forecast_narrative: str
    key_drivers: List[str]
    growth_levers: List[str]
    forecast_confidence: str = Field(pattern="^(high|medium|low)$")


def _strip_think_tags(text: str) -> str:
    """Remove DeepSeek-R1 chain-of-thought <think> blocks before JSON parsing."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def run(question: str, context: str, risk_output: dict, client: Groq) -> RevenueOutput:
    """Run the revenue agent using context and risk agent output.

    Args:
        question: Founder's question.
        context: RAG context passages.
        risk_output: Parsed output from RiskAgent.
        client: Groq client instance.

    Returns:
        RevenueOutput with forecast narrative, drivers, and levers.
    """
    user_msg = (
        f"Founder question: {question}\n\n"
        f"Context:\n{context}\n\n"
        f"Risk assessment:\n{json.dumps(risk_output)}"
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            # DeepSeek-R1 may not support json_object mode on all Groq versions
            max_tokens=600,
            temperature=0.3,
        )
        raw = _strip_think_tags(resp.choices[0].message.content or "{}")
        # Extract JSON block if model wraps it in markdown
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        payload = match.group() if match else raw
        return RevenueOutput(**json.loads(payload))
    except Exception as exc:
        logger.warning("RevenueAgent failed: %s — using fallback", str(exc))
        return RevenueOutput(
            forecast_narrative="Revenue forecast requires complete financial data.",
            key_drivers=["Data required"],
            growth_levers=["Data required"],
            forecast_confidence="low",
        )
