"""Agent orchestrator: runs the 4-agent pipeline and emits SSE events.

Architecture note: we use direct Groq client calls with sequential chaining
instead of AutoGen GroupChat. Our pipeline is strictly ordered
(market→risk→revenue→strategy) with no dynamic routing, so GroupChat adds
complexity with no benefit. Each agent gets only the output it needs from
the previous one — minimizing tokens sent per call.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from groq import Groq

from backend.agents import market_agent, risk_agent, revenue_agent, strategy_agent
from backend.config import get_settings
from backend.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(rag_chunks: List[dict]) -> str:
    """Format RAG chunks into a compact context string for agent prompts."""
    if not rag_chunks:
        return "No additional context available."
    lines = []
    for i, chunk in enumerate(rag_chunks, 1):
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "").strip()
        lines.append(f"[{i}] ({source}): {text}")
    return "\n".join(lines)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(
    question: str,
    founder_id: Optional[str] = None,
    rag_chunks: Optional[List[dict]] = None,
    rag_pipeline: Optional[RAGPipeline] = None,
) -> AsyncGenerator[str, None]:
    """Run the 4-agent pipeline and yield SSE events for each step.

    Agents run sequentially in a threadpool executor (Groq calls are blocking).
    Each agent's output feeds as input to the next. If any agent fails, the
    pipeline continues with its fallback output — partial results are better
    than no results.

    Args:
        question: Founder's natural language question.
        founder_id: UUID of the founder (used for RAG retrieval).
        rag_chunks: Pre-retrieved chunks (used in tests; skips live retrieval).
        rag_pipeline: RAGPipeline instance. If provided and rag_chunks is None,
                      retrieves live context before running agents.

    Yields:
        SSE-formatted strings for rag_context, agent_update, final, error events.
    """
    settings = get_settings()
    groq_client = Groq(api_key=settings.groq_api_key)
    loop = asyncio.get_event_loop()

    # Live RAG retrieval if pipeline provided and no pre-fetched chunks
    if rag_chunks is not None:
        chunks = rag_chunks
    elif rag_pipeline is not None and founder_id:
        try:
            retrieved = await loop.run_in_executor(
                None, rag_pipeline.query, question, founder_id, 5
            )
            chunks = [
                {"text": c.text, "source": c.source, "score": c.score}
                for c in retrieved
            ]
        except Exception as exc:
            logger.warning("RAG retrieval failed — proceeding without context: %s", exc)
            chunks = []
    else:
        chunks = []

    context = _build_context(chunks)

    # Emit RAG context event
    yield _sse("rag_context", {"chunks": chunks})

    # ── Market agent ──────────────────────────────────────────────────────────
    try:
        market_out = await loop.run_in_executor(
            None, market_agent.run, question, context, groq_client
        )
        market_dict = market_out.model_dump()
        yield _sse("agent_update", {
            "agent_name": "MarketAgent",
            "content": json.dumps(market_dict),
            "timestamp": _ts(),
        })
    except Exception as exc:
        logger.error("MarketAgent pipeline error: %s", str(exc))
        market_dict = {}
        yield _sse("agent_update", {
            "agent_name": "MarketAgent",
            "content": json.dumps({"error": str(exc)}),
            "timestamp": _ts(),
        })

    # ── Risk agent ────────────────────────────────────────────────────────────
    try:
        risk_out = await loop.run_in_executor(
            None, risk_agent.run, question, context, market_dict, groq_client
        )
        risk_dict = risk_out.model_dump()
        yield _sse("agent_update", {
            "agent_name": "RiskAgent",
            "content": json.dumps(risk_dict),
            "timestamp": _ts(),
        })
    except Exception as exc:
        logger.error("RiskAgent pipeline error: %s", str(exc))
        risk_dict = {}
        yield _sse("agent_update", {
            "agent_name": "RiskAgent",
            "content": json.dumps({"error": str(exc)}),
            "timestamp": _ts(),
        })

    # ── Revenue agent ─────────────────────────────────────────────────────────
    try:
        rev_out = await loop.run_in_executor(
            None, revenue_agent.run, question, context, risk_dict, groq_client
        )
        rev_dict = rev_out.model_dump()
        yield _sse("agent_update", {
            "agent_name": "RevenueAgent",
            "content": json.dumps(rev_dict),
            "timestamp": _ts(),
        })
    except Exception as exc:
        logger.error("RevenueAgent pipeline error: %s", str(exc))
        rev_dict = {}
        yield _sse("agent_update", {
            "agent_name": "RevenueAgent",
            "content": json.dumps({"error": str(exc)}),
            "timestamp": _ts(),
        })

    # ── Strategy agent ────────────────────────────────────────────────────────
    try:
        strat_out = await loop.run_in_executor(
            None, strategy_agent.run, question, market_dict, risk_dict, rev_dict, groq_client
        )
        strat_dict = strat_out.model_dump()
        yield _sse("agent_update", {
            "agent_name": "StrategyAgent",
            "content": json.dumps(strat_dict),
            "timestamp": _ts(),
        })
    except Exception as exc:
        logger.error("StrategyAgent pipeline error: %s", str(exc))
        strat_dict = {}
        yield _sse("agent_update", {
            "agent_name": "StrategyAgent",
            "content": json.dumps({"error": str(exc)}),
            "timestamp": _ts(),
        })

    # ── Final summary event ───────────────────────────────────────────────────
    yield _sse("final", {
        "status": "complete",
        "agents_ran": ["MarketAgent", "RiskAgent", "RevenueAgent", "StrategyAgent"],
        "rag_chunks_used": len(chunks),
    })
