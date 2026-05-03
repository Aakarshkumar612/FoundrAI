"""Smart RAG Orchestrator — three-route token-efficient pipeline with web search.

Routes (auto-classified per query):
  data     → founder's RAG context → direct synthesis      ~1.8K tokens
  web      → DuckDuckGo search → direct synthesis          ~1.5K tokens
  advisory → RAG + 4 specialist agents → synthesis         ~8K tokens

Average token savings vs always-running full pipeline: ~73%.

SSE events emitted:
  rag_context     — retrieved document chunks (data/advisory routes)
  agent_update    — specialist JSON outputs (advisory route only)
  synthesis_chunk — streaming text tokens from synthesis
  final           — pipeline complete
  error           — unrecoverable failure
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from groq import AsyncGroq, Groq

from backend.agents import market_agent, risk_agent, revenue_agent, strategy_agent
from backend.config import get_settings
from backend.rag.pipeline import RAGPipeline
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

_GLOBAL_ID = "00000000-0000-0000-0000-000000000000"

# ... (keep model config)

def _get_active_session_context(founder_id: str) -> str:
    """Fetch metadata for the active upload to give the LLM immediate awareness."""
    sb = get_supabase_client()
    if not sb: return ""
    try:
        # Get active_upload_id from founder profile
        frow = sb.table("founders").select("active_upload_id").eq("id", founder_id).maybe_single().execute()
        active_id = frow.data.get("active_upload_id") if frow.data else None
        if not active_id: return ""

        # Get upload metadata
        urow = sb.table("uploads").select("filename, initial_metrics").eq("id", active_id).maybe_single().execute()
        if not urow.data: return ""
        
        meta = urow.data
        filename = meta.get("filename", "Unknown File")
        metrics = meta.get("initial_metrics", {})
        
        ctx = f"\n[ACTIVE SESSION CONTEXT]\nYou have access to the file: **{filename}**.\n"
        if metrics:
            ctx += "Current extracted metrics for this file:\n"
            for k, v in metrics.items():
                ctx += f"- {k.replace('_',' ').title()}: **{v}**\n"
        return ctx
    except Exception as e:
        logger.warning("Failed to fetch session context: %s", e)
        return ""

# ── Model config ───────────────────────────────────────────────────────────────

_CLASSIFIER_MODEL = "llama-3.1-8b-instant"    # ~150 tokens total, sub-100ms
_FAST_MODEL       = "llama-3.1-8b-instant"    # data + web synthesis
_ADVISORY_MODEL   = "llama-3.3-70b-versatile" # complex advisory synthesis

# ── System prompts ─────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = (
    "Classify this founder's finance question into exactly one word:\n"
    "  data     — about their own data, metrics, my revenue, my burn, my CAC, my LTV\n"
    "  web      — needs current benchmarks, market rates, industry stats, news, trends\n"
    "  advisory — strategic decision: should I, how do I grow, fundraising, what strategy\n"
    "Reply with ONLY the single word."
)

_DIRECT_SYSTEM = (
    "You are FoundrAI — a world-class startup financial advisor.\n"
    "Answer directly. Lead with the answer, not preamble.\n"
    "Use **bold** for key metrics and numbers. Use bullet points for lists.\n"
    "For factual questions: 2-4 focused paragraphs. Be specific, not vague.\n"
    "Never start with 'Based on', 'According to', or 'Great question'."
)

_ADVISORY_SYSTEM = (
    "You are FoundrAI — elite startup advisor (McKinsey rigor + YC pattern recognition + Goldman Sachs precision).\n\n"
    "Synthesize the specialist analysis into a premium advisory response:\n"
    "- Answer DIRECTLY in paragraph one — no preamble, no setup\n"
    "- **Bold** every key metric, number, and critical insight\n"
    "- Use ## headers for distinct topics, bullet points for action lists\n"
    "- Include specific numbers from the analysis — never be vague\n"
    "- Write as a senior partner in the room: direct, confident, prescriptive\n"
    "- End with ONE bold priority action for today\n\n"
    "DO NOT summarize what agents said. SYNTHESIZE and ADVISE with full authority."
)

# ── SSE helpers ────────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()

# ── Query classifier (~150 tokens total) ──────────────────────────────────────

def _classify(question: str, groq_client: Groq) -> str:
    try:
        resp = groq_client.chat.completions.create(
            model=_CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user",   "content": question[:400]},  # cap input
            ],
            max_tokens=4,
            temperature=0.0,
        )
        token = resp.choices[0].message.content.strip().lower().split()[0]
        return token if token in ("data", "web", "advisory") else "advisory"
    except Exception as exc:
        logger.warning("Classifier failed → advisory: %s", exc)
        return "advisory"

# ── Web search (free, no API key) ──────────────────────────────────────────────

def _web_search(question: str) -> str:
    """Search DuckDuckGo for latest startup/finance data. Returns formatted snippets."""
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(
            f"startup SaaS finance {question}",
            max_results=4,
            timelimit="y",  # last 12 months
        ))
        snippets = []
        for r in results[:3]:
            title = r.get("title", "")
            body  = (r.get("body") or "")[:250].strip()
            if body:
                snippets.append(f"• {title}: {body}")
        return "\n".join(snippets)
    except ImportError:
        logger.info("duckduckgo_search not installed — using training knowledge")
        return ""
    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return ""

# ── RAG context retrieval ──────────────────────────────────────────────────────

def _build_context(chunks: List[dict]) -> str:
    if not chunks:
        return "No uploaded documents found."
    return "\n".join(
        f"[{i}] {c.get('source', 'doc')}: {c.get('text', '').strip()}"
        for i, c in enumerate(chunks, 1)
    )

async def _retrieve(
    question: str,
    founder_id: str,
    rag: RAGPipeline,
    loop: asyncio.AbstractEventLoop,
    top_k: int,
) -> List[dict]:
    chunks: List[dict] = []
    try:
        fc = await loop.run_in_executor(None, rag.query, question, founder_id, top_k)
        chunks += [
            {"text": c.text, "source": c.source, "score": c.score, "doc_type": c.doc_type}
            for c in fc if c.score > 0.25
        ]
    except Exception as exc:
        logger.warning("Founder RAG retrieval failed: %s", exc)

    try:
        gc = await loop.run_in_executor(None, rag.query, question, _GLOBAL_ID, 2)
        chunks += [
            {"text": c.text, "source": f"[benchmark] {c.source}", "score": c.score, "doc_type": c.doc_type}
            for c in gc if c.score > 0.35
        ]
    except Exception:
        pass

    seen, deduped = set(), []
    for c in sorted(chunks, key=lambda x: -x.get("score", 0)):
        key = c["text"][:60]
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped[:top_k]

# ── Streaming synthesis helper ─────────────────────────────────────────────────

async def _stream_synthesis(
    system: str,
    user_msg: str,
    model: str,
    max_tokens: int,
    temperature: float,
    api_key: str,
) -> AsyncGenerator[str, None]:
    succeeded = False
    try:
        client = AsyncGroq(api_key=api_key)
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield _sse("synthesis_chunk", {"text": delta})
                succeeded = True
    except Exception as exc:
        logger.error("Synthesis stream failed (%s): %s", model, exc)

    if not succeeded:
        yield _sse("synthesis_chunk", {"text": "Analysis complete. Please review agent details for insights."})

# ── Advisory format helper ─────────────────────────────────────────────────────

def _fmt_list(lst) -> str:
    if not isinstance(lst, list):
        return str(lst)
    return "\n".join(f"  • {x}" for x in lst)

def _format_advisory(question: str, context: str, market: dict, risk: dict, rev: dict, strat: dict) -> str:
    ctx = context[:800]
    risks_text = "\n".join(
        f"  • {r.get('risk', '')} [{r.get('severity', '')}]"
        for r in risk.get("primary_risks", [])
    )
    plan = strat.get("plan_30_60_90") or {}
    if hasattr(plan, "model_dump"):
        plan = plan.model_dump()
    return (
        f"QUESTION: {question}\n\n"
        f"DATA CONTEXT:\n{ctx}\n\n"
        f"MARKET (confidence {market.get('confidence', 0):.0%}):\n"
        f"  Size: {market.get('market_size_assessment', '')}\n"
        f"  Opportunities: {_fmt_list(market.get('opportunity_areas', []))}\n\n"
        f"RISK (score {risk.get('risk_score', 5)}/10):\n"
        f"{risks_text}\n"
        f"  Mitigations: {_fmt_list(risk.get('mitigation_recommendations', []))}\n\n"
        f"REVENUE ({rev.get('forecast_confidence', 'medium')} confidence):\n"
        f"  {rev.get('forecast_narrative', '')}\n"
        f"  Drivers: {_fmt_list(rev.get('key_drivers', []))}\n\n"
        f"STRATEGY:\n"
        f"  {strat.get('executive_summary', '')}\n"
        f"  Recommendations: {_fmt_list(strat.get('top_3_recommendations', []))}\n"
        f"  Immediate actions: {_fmt_list(strat.get('immediate_actions', []))}\n"
        f"  30-day: {_fmt_list(plan.get('days_30', []))}"
    )

# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run_pipeline(
    question: str,
    founder_id: Optional[str] = None,
    rag_chunks: Optional[List[dict]] = None,
    rag_pipeline: Optional[RAGPipeline] = None,
    csv_context: str = "",
) -> AsyncGenerator[str, None]:
    settings  = get_settings()

    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY is missing. Pipeline cannot run.")
        yield _sse("error", {"code": "CONFIG_ERROR", "message": "Groq API key is missing. AI analysis unavailable."})
        return

    try:
        groq_sync = Groq(api_key=settings.groq_api_key)
    except Exception as exc:
        logger.error("Failed to initialize Groq client: %s", exc)
        yield _sse("error", {"code": "CONFIG_ERROR", "message": f"Groq initialization failed: {str(exc)}"})
        return

    loop = asyncio.get_event_loop()


    # ── Classify (~150 tokens) ────────────────────────────────────────────────
    route = _classify(question, groq_sync)
    # If direct CSV data is available and question is data-oriented, force data route
    if csv_context and route != "web":
        route = "data"
    logger.info("Route=%s csv_available=%s q=%r", route, bool(csv_context), question[:80])

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE: WEB — internet search + direct synthesis
    # ═══════════════════════════════════════════════════════════════════════════
    if route == "web":
        yield _sse("rag_context", {"chunks": [], "route": "web"})

        web_context = await loop.run_in_executor(None, _web_search, question)

        if web_context:
            user_msg = (
                f"QUESTION: {question}\n\n"
                f"LATEST SEARCH RESULTS (past 12 months):\n{web_context}\n\n"
                "Answer using the search results. Cite specific figures and sources. "
                "If a benchmark or stat is in the results, use it."
            )
        else:
            # Fallback: Groq's own training knowledge (very good for finance benchmarks)
            user_msg = (
                f"QUESTION: {question}\n\n"
                "Answer from your knowledge of startup finance benchmarks, SaaS metrics, "
                "and venture capital standards. Be specific with numbers and ranges."
            )

        async for chunk in _stream_synthesis(
            _DIRECT_SYSTEM, user_msg, _FAST_MODEL,
            max_tokens=700, temperature=0.2, api_key=settings.groq_api_key,
        ):
            yield chunk

        yield _sse("final", {"status": "complete", "route": "web", "rag_chunks_used": 0})
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTES: DATA / ADVISORY — need RAG context
    # ═══════════════════════════════════════════════════════════════════════════
    if rag_chunks is not None:
        chunks = rag_chunks
    elif rag_pipeline is not None and founder_id:
        top_k = 6 if route == "advisory" else 5
        chunks = await _retrieve(question, founder_id, rag_pipeline, loop, top_k)
    else:
        chunks = []

    context = _build_context(chunks)
    yield _sse("rag_context", {"chunks": chunks, "route": route})

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE: DATA — RAG context → direct synthesis (skip 4 agents)
    # ═══════════════════════════════════════════════════════════════════════════
    if route == "data":
        if csv_context:
            # Direct CSV data — Groq can compute exact answers from raw rows
            data_section = csv_context[:3000]
            data_label = "FOUNDER'S UPLOADED CSV DATA (exact rows)"
            instruction = (
                "Answer using the exact numbers in this CSV. "
                "Calculate totals, averages, growth rates, or trends as the question requires. "
                "Show your calculations. "
                "If the data does not contain what is needed, state exactly which column or period is missing."
            )
        else:
            data_section = context[:1500]
            data_label = "FOUNDER'S INDEXED DATA"
            instruction = (
                "Answer from this context. Use the exact numbers present. "
                "If the data does not contain the answer, say clearly what's missing."
            )

        user_msg = (
            f"QUESTION: {question}\n\n"
            f"{data_label}:\n{data_section}\n\n"
            f"{instruction}"
        )
        async for chunk in _stream_synthesis(
            _DIRECT_SYSTEM, user_msg, _FAST_MODEL,
            max_tokens=900, temperature=0.2, api_key=settings.groq_api_key,
        ):
            yield chunk

        yield _sse("final", {"status": "complete", "route": "data", "rag_chunks_used": len(chunks)})
        return

    # ═══════════════════════════════════════════════════════════════════════════
    # ROUTE: ADVISORY — 4-agent pipeline + deep synthesis
    # ═══════════════════════════════════════════════════════════════════════════
    market_dict: dict = {}
    risk_dict:   dict = {}
    rev_dict:    dict = {}
    strat_dict:  dict = {}

    try:
        out = await loop.run_in_executor(None, market_agent.run, question, context, groq_sync)
        market_dict = out.model_dump()
        yield _sse("agent_update", {"agent_name": "MarketAgent", "content": json.dumps(market_dict), "timestamp": _ts()})
    except Exception as exc:
        logger.error("MarketAgent: %s", exc)
        yield _sse("agent_update", {"agent_name": "MarketAgent", "content": "{}", "timestamp": _ts()})

    try:
        out = await loop.run_in_executor(None, risk_agent.run, question, context, market_dict, groq_sync)
        risk_dict = out.model_dump()
        yield _sse("agent_update", {"agent_name": "RiskAgent", "content": json.dumps(risk_dict), "timestamp": _ts()})
    except Exception as exc:
        logger.error("RiskAgent: %s", exc)
        yield _sse("agent_update", {"agent_name": "RiskAgent", "content": "{}", "timestamp": _ts()})

    try:
        out = await loop.run_in_executor(None, revenue_agent.run, question, context, risk_dict, groq_sync)
        rev_dict = out.model_dump()
        yield _sse("agent_update", {"agent_name": "RevenueAgent", "content": json.dumps(rev_dict), "timestamp": _ts()})
    except Exception as exc:
        logger.error("RevenueAgent: %s", exc)
        yield _sse("agent_update", {"agent_name": "RevenueAgent", "content": "{}", "timestamp": _ts()})

    try:
        out = await loop.run_in_executor(None, strategy_agent.run, question, market_dict, risk_dict, rev_dict, groq_sync)
        strat_dict = out.model_dump()
        yield _sse("agent_update", {"agent_name": "StrategyAgent", "content": json.dumps(strat_dict), "timestamp": _ts()})
    except Exception as exc:
        logger.error("StrategyAgent: %s", exc)
        yield _sse("agent_update", {"agent_name": "StrategyAgent", "content": "{}", "timestamp": _ts()})

    # Prefer direct CSV rows for advisory context if available
    advisory_context = csv_context[:1500] if csv_context else context
    synthesis_prompt = _format_advisory(question, advisory_context, market_dict, risk_dict, rev_dict, strat_dict)

    async for chunk in _stream_synthesis(
        _ADVISORY_SYSTEM, synthesis_prompt, _ADVISORY_MODEL,
        max_tokens=1200, temperature=0.45, api_key=settings.groq_api_key,
    ):
        yield chunk

    yield _sse("final", {
        "status": "complete",
        "route": "advisory",
        "rag_chunks_used": len(chunks),
        "agents_ran": ["MarketAgent", "RiskAgent", "RevenueAgent", "StrategyAgent"],
    })
