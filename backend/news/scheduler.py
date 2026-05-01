"""News ingestion scheduler: runs ingest_news_batch every 4 hours via APScheduler."""

import logging
from typing import Optional

import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.news.ingestion import DEFAULT_TOPICS, ingest_news_batch

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _run_ingestion(api_key: str, supabase_client=None, rag_pipeline=None) -> None:
    """Synchronous wrapper called by APScheduler."""
    logger.info("Scheduled news ingestion starting")
    try:
        # Use asyncio.run to call the async ingestion function from a sync thread
        result = asyncio.run(ingest_news_batch(
            topics=DEFAULT_TOPICS,
            api_key=api_key,
            supabase_client=supabase_client,
            rag_pipeline=rag_pipeline,
        ))
        logger.info("Scheduled ingestion result: %s", result)
    except Exception as exc:
        logger.error("Scheduled ingestion failed: %s", exc)


def start_scheduler(
    api_key: str,
    supabase_client=None,
    rag_pipeline=None,
    interval_hours: int = 4,
) -> BackgroundScheduler:
    """Start the APScheduler BackgroundScheduler with a job.

    Args:
        api_key: NewsCatcher API key.
        supabase_client: Supabase client for DB writes. None = dry run.
        rag_pipeline: RAGPipeline instance for indexing. None = skip indexing.
        interval_hours: How often to run ingestion (default 4).

    Returns:
        Running BackgroundScheduler instance.
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running — skipping start")
        return _scheduler

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_ingestion,
        trigger=IntervalTrigger(hours=interval_hours),
        kwargs={
            "api_key": api_key,
            "supabase_client": supabase_client,
            "rag_pipeline": rag_pipeline,
        },
        id="news_ingestion",
        name="News Ingestion",
        replace_existing=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("News scheduler started — interval=%dh", interval_hours)
    return _scheduler


def stop_scheduler() -> None:
    """Stop the scheduler gracefully if running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("News scheduler stopped")
    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Return the current scheduler instance (or None if not started)."""
    return _scheduler
