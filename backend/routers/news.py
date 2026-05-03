"""Public news router — no authentication required."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query
from backend.storage.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])

EXCERPT_LENGTH = 240


@router.get("/articles")
async def list_articles(
    limit: int = Query(default=50, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    topics: Optional[str] = Query(default=None, description="Comma-separated topics for contextual news"),
):
    """Return news articles. When topics= provided, fetches live NewsCatcher results first.
    Public — no Bearer token needed.
    """
    # ── Live topic-based fetch from NewsCatcher ────────────────────────────────
    if topics and topics.strip():
        topic_list = [t.strip() for t in topics.split(",") if t.strip()][:5]
        live = await _fetch_live_news(topic_list, per_topic=8)
        if live:
            return {"articles": live, "total": len(live), "source": "live", "topics": topic_list}

    # ── DB fetch (default / fallback) ─────────────────────────────────────────
    sb = get_supabase_client()
    if sb is None:
        return {"articles": [], "total": 0, "source": "db"}

    try:
        result = (
            sb.table("news_articles")
            .select("id, title, source, published_date, url, topics, full_text")
            .order("published_date", desc=True)
            .limit(limit)
            .execute()
        )
        articles = result.data or []
    except Exception as exc:
        logger.error("news_articles fetch failed: %s", exc)
        return {"articles": [], "total": 0, "source": "db"}

    output = []
    for a in articles:
        full_text = a.get("full_text") or ""
        excerpt = full_text[:EXCERPT_LENGTH].strip()
        if len(full_text) > EXCERPT_LENGTH:
            last_space = excerpt.rfind(" ")
            excerpt = (excerpt[:last_space] if last_space > 0 else excerpt) + "…"
        output.append({
            "id": a.get("id"),
            "title": a.get("title") or "",
            "source": a.get("source") or "",
            "published_date": a.get("published_date") or "",
            "url": a.get("url") or "",
            "topics": a.get("topics") or [],
            "excerpt": excerpt,
        })

    if search:
        q = search.lower()
        output = [
            a for a in output
            if q in (a["title"] or "").lower()
            or q in (a["source"] or "").lower()
            or any(q in t.lower() for t in (a["topics"] or []))
        ]

    return {"articles": output, "total": len(output), "source": "db"}


async def _fetch_live_news(topics: List[str], per_topic: int = 6) -> List[dict]:
    """Fetch articles from NewsCatcher for these topics synchronously."""
    from backend.config import get_settings
    from backend.services.news_intelligence import fetch_news_for_topics
    settings = get_settings()
    if not settings.newscatcher_api_key:
        return []
    try:
        articles = await fetch_news_for_topics(
            topics=topics,
            api_key=settings.newscatcher_api_key,
            max_per_topic=per_topic,
        )
        return articles
    except Exception as exc:
        logger.warning("Live news fetch failed: %s", exc)
        return []
