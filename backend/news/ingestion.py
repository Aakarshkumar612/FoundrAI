"""News ingestion: fetch articles via NewsCatcher, extract full text via News-Please."""

import logging
import time
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from newscatcherapi import NewsCatcherApiClient
except ImportError:
    NewsCatcherApiClient = None  # type: ignore[assignment,misc]

try:
    from newsplease import NewsPlease
except ImportError:
    NewsPlease = None  # type: ignore[assignment,misc]

DEFAULT_TOPICS = [
    "startup funding",
    "SaaS growth",
    "venture capital",
    "startup failure",
    "product market fit",
    "CAC LTV SaaS",
]

MAX_ARTICLES_PER_RUN = 50


@dataclass
class ArticleMeta:
    url: str
    title: str
    published_date: Optional[str]
    source: Optional[str]


@dataclass
class FullArticle:
    url: str
    title: str
    text: str
    author: Optional[str]
    published_date: Optional[str]
    source: Optional[str]


def fetch_news(
    topics: List[str],
    api_key: str,
    max_articles: int = MAX_ARTICLES_PER_RUN,
) -> List[ArticleMeta]:
    """Query NewsCatcher API for articles matching the given topics.

    Args:
        topics: List of keyword strings to search.
        api_key: NewsCatcher API key.
        max_articles: Cap on total articles returned across all topics.

    Returns:
        List of ArticleMeta objects (url, title, date, source).
    """
    if NewsCatcherApiClient is None:
        logger.error("newscatcherapi not installed")
        return []

    client = NewsCatcherApiClient(x_api_key=api_key)
    seen_urls: set = set()
    results: List[ArticleMeta] = []

    per_topic = max(1, max_articles // len(topics))

    for topic in topics:
        if len(results) >= max_articles:
            break
        try:
            resp = client.get_search(
                q=topic,
                lang="en",
                page_size=per_topic,
                sort_by="date",
            )
            articles = (resp or {}).get("articles") or []
            for a in articles:
                url = a.get("link") or a.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(ArticleMeta(
                    url=url,
                    title=a.get("title", ""),
                    published_date=str(a.get("published_date", "")),
                    source=a.get("clean_url") or a.get("rights", ""),
                ))
        except Exception as exc:
            logger.warning("NewsCatcher fetch failed for topic '%s': %s", topic, exc)

    return results[:max_articles]


def fetch_full_article(url: str) -> Optional[FullArticle]:
    """Extract full article text from a URL using News-Please.

    Args:
        url: Article URL to scrape.

    Returns:
        FullArticle on success, None on failure.
    """
    try:
        if NewsPlease is None:
            logger.warning("newsplease not installed")
            return None
        article = NewsPlease.from_url(url, timeout=10)
        if article is None or not article.maintext:
            return None
        return FullArticle(
            url=url,
            title=article.title or "",
            text=article.maintext or "",
            author=", ".join(article.authors) if article.authors else None,
            published_date=str(article.date_publish) if article.date_publish else None,
            source=article.source_domain,
        )
    except Exception as exc:
        logger.warning("News-Please extraction failed for %s: %s", url, exc)
        return None


def ingest_news_batch(
    topics: List[str],
    api_key: str,
    supabase_client=None,
    rag_pipeline=None,
) -> dict:
    """Fetch, deduplicate, store, and index a batch of news articles.

    Args:
        topics: Keywords to search via NewsCatcher.
        api_key: NewsCatcher API key.
        supabase_client: Supabase client for DB writes. None = dry run.
        rag_pipeline: RAGPipeline instance for indexing. None = skip indexing.

    Returns:
        Dict with ingested_count, skipped_duplicates, errors.
    """
    start = time.monotonic()
    ingested = skipped = errors = 0

    articles_meta = fetch_news(topics, api_key)
    logger.info("Fetched %d article candidates", len(articles_meta))

    for meta in articles_meta:
        try:
            # Deduplicate via DB lookup
            if supabase_client is not None:
                exists = (
                    supabase_client.table("news_articles")
                    .select("id")
                    .eq("url", meta.url)
                    .execute()
                )
                if exists.data:
                    skipped += 1
                    continue

            full = fetch_full_article(meta.url)
            if full is None or not full.text.strip():
                errors += 1
                continue

            # Persist raw article
            if supabase_client is not None:
                supabase_client.table("news_articles").insert({
                    "url": full.url,
                    "title": full.title,
                    "author": full.author,
                    "published_date": full.published_date,
                    "source": full.source,
                    "full_text": full.text,
                    "topics": topics,
                    "indexed": False,
                }).execute()

            # Index into RAG
            if rag_pipeline is not None:
                rag_pipeline.index(
                    content=full.text.encode("utf-8"),
                    founder_id="global",   # news is shared across all founders
                    doc_type="news",
                    source_filename=full.url,
                )
                if supabase_client is not None:
                    supabase_client.table("news_articles").update(
                        {"indexed": True}
                    ).eq("url", full.url).execute()

            ingested += 1

        except Exception as exc:
            logger.error("Failed to ingest %s: %s", meta.url, exc)
            errors += 1

    duration = time.monotonic() - start

    # Log run to Supabase
    if supabase_client is not None:
        try:
            supabase_client.table("ingestion_logs").insert({
                "ingested_count": ingested,
                "skipped_count": skipped,
                "error_count": errors,
                "duration_seconds": round(duration, 2),
            }).execute()
        except Exception as exc:
            logger.warning("Failed to write ingestion log: %s", exc)

    logger.info(
        "Ingestion complete: ingested=%d skipped=%d errors=%d duration=%.1fs",
        ingested, skipped, errors, duration,
    )
    return {"ingested_count": ingested, "skipped_duplicates": skipped, "errors": errors}
