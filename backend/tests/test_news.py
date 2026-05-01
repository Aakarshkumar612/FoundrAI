"""Tests for Layer news ingestion and scheduling."""

import logging
from typing import Generator
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from backend.news.ingestion import (
    DEFAULT_TOPICS,
    ArticleMeta,
    FullArticle,
    fetch_full_article,
    fetch_news,
    ingest_news_batch,
)
from backend.news.scheduler import (
    get_scheduler,
    start_scheduler,
    stop_scheduler,
)

logger = logging.getLogger(__name__)


# ── fetch_news tests ─────────────────────────────────────────────────────────

class TestFetchNews:
    @pytest.mark.asyncio
    async def test_fetch_news_returns_meta_list(self):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "articles": [
                    {"link": "https://example.com/1", "title": "T1", "published_date": "2026", "clean_url": "e.com"}
                ]
            }
            mock_get.return_value = mock_resp
            
            result = await fetch_news(["topic"], api_key="test-key", max_articles=1)
            
        assert len(result) == 1
        assert result[0].url == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_fetch_news_handles_api_error(self):
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            
            result = await fetch_news(["topic"], api_key="bad-key")
            
        assert result == []


# ── fetch_full_article tests ──────────────────────────────────────────────────

class TestFetchFullArticle:
    def _mock_article(self):
        mock = MagicMock()
        mock.title = "Sample Title"
        mock.maintext = "Sample content of the article."
        mock.authors = ["John Doe"]
        mock.date_publish = "2026-04-30 10:00:00"
        mock.source_domain = "example.com"
        return mock

    def test_returns_full_article_on_success(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.return_value = self._mock_article()
            result = fetch_full_article("https://example.com/story")
        
        assert result is not None
        assert result.title == "Sample Title"
        assert "content" in result.text
        assert result.source == "example.com"

    def test_returns_none_on_missing_text(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            art = self._mock_article()
            art.maintext = None
            np.from_url.return_value = art
            result = fetch_full_article("https://example.com/story")
        assert result is None

    def test_handles_extraction_exception(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.side_effect = Exception("Scraper blocked")
            result = fetch_full_article("https://example.com/story")
        assert result is None

    def test_handles_missing_authors(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            article = self._mock_article()
            article.authors = []
            np.from_url.return_value = article
            result = fetch_full_article("https://example.com/story")
        assert result.author is None


# ── ingest_news_batch tests ───────────────────────────────────────────────────

class TestIngestNewsBatch:
    def _meta(self, n=1) -> ArticleMeta:
        return ArticleMeta(
            url=f"https://example.com/article-{n}",
            title=f"Article {n}",
            published_date="2026-04-30",
            source="example.com",
        )

    def _full(self, n=1) -> FullArticle:
        return FullArticle(
            url=f"https://example.com/article-{n}",
            title=f"Article {n}",
            text="Substantial article text about startup growth and SaaS metrics.",
            author="Author Name",
            published_date="2026-04-30",
            source="example.com",
        )

    @pytest.mark.asyncio
    async def test_dry_run_no_db_returns_ingested_count(self):
        with (
            patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch,
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            mock_fetch.return_value = [self._meta(1)]
            result = await ingest_news_batch(["topic"], api_key="key", supabase_client=None)
        assert result["ingested_count"] == 1
        assert result["skipped_duplicates"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_skips_existing_urls(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "existing"}])
        with patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [self._meta(1)]
            result = await ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        assert result["skipped_duplicates"] == 1
        assert result["ingested_count"] == 0

    @pytest.mark.asyncio
    async def test_counts_error_when_full_article_fails(self):
        with (
            patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch,
            patch("backend.news.ingestion.fetch_full_article", return_value=None),
        ):
            mock_fetch.return_value = [self._meta(1)]
            result = await ingest_news_batch(["topic"], api_key="key", supabase_client=None)
        assert result["errors"] == 1

    @pytest.mark.asyncio
    async def test_indexes_into_rag_pipeline(self):
        rag = MagicMock()
        with (
            patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch,
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            mock_fetch.return_value = [self._meta(1)]
            result = await ingest_news_batch(["topic"], api_key="key", supabase_client=None, rag_pipeline=rag)
        rag.index.assert_called_once()
        assert result["ingested_count"] == 1

    @pytest.mark.asyncio
    async def test_writes_ingestion_log_to_supabase(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        with (
            patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch,
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            mock_fetch.return_value = [self._meta(1)]
            await ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        
        table_calls = [call.args[0] for call in sb.table.call_args_list]
        assert "ingestion_logs" in table_calls

    @pytest.mark.asyncio
    async def test_empty_fetch_returns_zero_counts(self):
        with patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            result = await ingest_news_batch(["topic"], api_key="key")
        assert result == {"ingested_count": 0, "skipped_duplicates": 0, "errors": 0}

    @pytest.mark.asyncio
    async def test_ingestion_log_failure_does_not_raise(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        # Fail on log insert only
        def table_mock(name):
            m = MagicMock()
            if name == "ingestion_logs":
                m.insert.return_value.execute.side_effect = Exception("DB error")
            else:
                m.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            return m
        
        sb.table.side_effect = table_mock
        with (
            patch("backend.news.ingestion.fetch_news", new_callable=AsyncMock) as mock_fetch,
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            mock_fetch.return_value = [self._meta(1)]
            # Should not raise even if log write fails
            result = await ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        assert "ingested_count" in result


# ── scheduler tests ───────────────────────────────────────────────────────────

class TestScheduler:
    def teardown_method(self):
        stop_scheduler()

    def test_start_scheduler_returns_running_scheduler(self):
        scheduler = start_scheduler(api_key="test-key")
        assert scheduler.running
        stop_scheduler()

    def test_stop_scheduler_stops_it(self):
        start_scheduler(api_key="test-key")
        stop_scheduler()
        assert get_scheduler() is None

    def test_double_start_is_idempotent(self):
        s1 = start_scheduler(api_key="test-key")
        s2 = start_scheduler(api_key="test-key")
        assert s1 is s2
        stop_scheduler()

    def test_stop_when_not_started_is_noop(self):
        stop_scheduler()  # should not raise

    def test_get_scheduler_none_before_start(self):
        assert get_scheduler() is None

    def test_get_scheduler_returns_instance_after_start(self):
        start_scheduler(api_key="test-key")
        assert get_scheduler() is not None
