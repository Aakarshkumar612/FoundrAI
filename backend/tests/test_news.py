"""Tests for Layer 6: news ingestion pipeline and scheduler."""

from unittest.mock import MagicMock, patch

import pytest

from backend.news.ingestion import (
    ArticleMeta,
    FullArticle,
    fetch_full_article,
    fetch_news,
    ingest_news_batch,
)
from backend.news.scheduler import get_scheduler, start_scheduler, stop_scheduler


# ── fetch_news tests ──────────────────────────────────────────────────────────

class TestFetchNews:
    def _mock_client(self, articles):
        client = MagicMock()
        client.get_search.return_value = {"articles": articles}
        return client

    def _article(self, n: int) -> dict:
        return {
            "link": f"https://example.com/article-{n}",
            "title": f"Article {n}",
            "published_date": "2026-04-30",
            "clean_url": f"example{n}.com",
        }

    def test_returns_article_meta_list(self):
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=self._mock_client([self._article(1)])):
            results = fetch_news(["startup funding"], api_key="key")
        assert len(results) == 1
        assert isinstance(results[0], ArticleMeta)
        assert results[0].url == "https://example.com/article-1"

    def test_deduplicates_same_url(self):
        duplicate = self._article(1)
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=self._mock_client([duplicate, duplicate])):
            results = fetch_news(["startup funding"], api_key="key")
        assert len(results) == 1

    def test_respects_max_articles(self):
        articles = [self._article(i) for i in range(20)]
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=self._mock_client(articles)):
            results = fetch_news(["startup funding"], api_key="key", max_articles=5)
        assert len(results) <= 5

    def test_skips_articles_with_no_url(self):
        no_url = {"title": "No URL article", "published_date": "2026-04-30"}
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=self._mock_client([no_url, self._article(2)])):
            results = fetch_news(["startup funding"], api_key="key")
        assert all(r.url for r in results)
        assert len(results) == 1

    def test_handles_api_exception_gracefully(self):
        client = MagicMock()
        client.get_search.side_effect = Exception("Network error")
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=client):
            results = fetch_news(["startup funding"], api_key="key")
        assert results == []

    def test_missing_newscatcher_import_returns_empty(self):
        with patch("backend.news.ingestion.NewsCatcherApiClient", None):
            results = fetch_news(["topic"], api_key="key")
        assert results == []

    def test_multi_topic_deduplicates_across_topics(self):
        shared = self._article(99)
        client = MagicMock()
        client.get_search.return_value = {"articles": [shared]}
        with patch("backend.news.ingestion.NewsCatcherApiClient", return_value=client):
            results = fetch_news(["topic1", "topic2"], api_key="key")
        assert len(results) == 1


# ── fetch_full_article tests ──────────────────────────────────────────────────

class TestFetchFullArticle:
    def _mock_article(self, text="Main article body.", title="Test Title"):
        a = MagicMock()
        a.maintext = text
        a.title = title
        a.authors = ["Jane Doe"]
        a.date_publish = None
        a.source_domain = "example.com"
        return a

    def test_returns_full_article_on_success(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.return_value = self._mock_article()
            result = fetch_full_article("https://example.com/story")
        assert isinstance(result, FullArticle)
        assert result.text == "Main article body."
        assert result.author == "Jane Doe"

    def test_returns_none_when_no_maintext(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.return_value = self._mock_article(text="")
            result = fetch_full_article("https://example.com/story")
        assert result is None

    def test_returns_none_when_article_is_none(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.return_value = None
            result = fetch_full_article("https://example.com/story")
        assert result is None

    def test_returns_none_on_exception(self):
        with patch("backend.news.ingestion.NewsPlease") as np:
            np.from_url.side_effect = Exception("Timeout")
            result = fetch_full_article("https://example.com/story")
        assert result is None

    def test_handles_no_authors(self):
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

    def test_dry_run_no_db_returns_ingested_count(self):
        with (
            patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]),
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            result = ingest_news_batch(["topic"], api_key="key", supabase_client=None)
        assert result["ingested_count"] == 1
        assert result["skipped_duplicates"] == 0
        assert result["errors"] == 0

    def test_skips_existing_urls(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "existing"}])
        with patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]):
            result = ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        assert result["skipped_duplicates"] == 1
        assert result["ingested_count"] == 0

    def test_counts_error_when_full_article_fails(self):
        with (
            patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]),
            patch("backend.news.ingestion.fetch_full_article", return_value=None),
        ):
            result = ingest_news_batch(["topic"], api_key="key", supabase_client=None)
        assert result["errors"] == 1

    def test_indexes_into_rag_pipeline(self):
        rag = MagicMock()
        with (
            patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]),
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            result = ingest_news_batch(["topic"], api_key="key", supabase_client=None, rag_pipeline=rag)
        rag.index.assert_called_once()
        assert result["ingested_count"] == 1

    def test_writes_ingestion_log_to_supabase(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        with (
            patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]),
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        # Should write to news_articles AND ingestion_logs
        table_calls = [call.args[0] for call in sb.table.call_args_list]
        assert "ingestion_logs" in table_calls

    def test_empty_fetch_returns_zero_counts(self):
        with patch("backend.news.ingestion.fetch_news", return_value=[]):
            result = ingest_news_batch(["topic"], api_key="key")
        assert result == {"ingested_count": 0, "skipped_duplicates": 0, "errors": 0}

    def test_ingestion_log_failure_does_not_raise(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        sb.table.return_value.insert.return_value.execute.side_effect = Exception("Log write failed")
        with (
            patch("backend.news.ingestion.fetch_news", return_value=[self._meta(1)]),
            patch("backend.news.ingestion.fetch_full_article", return_value=self._full(1)),
        ):
            # Should not raise even if log write fails
            result = ingest_news_batch(["topic"], api_key="key", supabase_client=sb)
        assert "ingested_count" in result


# ── scheduler tests ───────────────────────────────────────────────────────────

class TestScheduler:
    def teardown_method(self):
        stop_scheduler()

    def test_start_scheduler_registers_job(self):
        scheduler = start_scheduler(api_key="test-key", interval_hours=4)
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "news_ingestion" in job_ids
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
        stop_scheduler()
