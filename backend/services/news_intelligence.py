"""News intelligence — extract topics from CSV data and fetch related articles."""

import logging
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


async def extract_topics_from_csv(csv_bytes: bytes, filename: str, groq_client) -> List[str]:
    """Use Groq to extract 3-5 relevant search topics from a CSV summary."""
    if groq_client is None:
        return _fallback_topics(filename)
    try:
        import io
        import pandas as pd
        df = pd.read_csv(io.BytesIO(csv_bytes))
        cols = list(df.columns)
        n_rows = len(df)
        obj_cols = df.select_dtypes(include="object").columns.tolist()
        sample_vals: List[str] = []
        for col in obj_cols[:2]:
            top = df[col].dropna().value_counts().head(5).index.tolist()
            sample_vals += [str(v) for v in top]

        prompt = (
            f"This CSV file is named '{filename}' and has {n_rows} rows with columns: {cols}.\n"
            f"Sample categorical values: {sample_vals[:15]}\n\n"
            "Extract 4-5 concise, specific search topics that capture the business/industry context of this data. "
            "Topics should be good news search queries.\n"
            "Respond with ONLY a JSON array of strings, e.g. [\"SaaS growth\", \"ARR benchmarks\", \"B2B software\"]"
        )
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=120,
            response_format={"type": "json_object"},
        )
        import json
        content = resp.choices[0].message.content.strip()
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [str(t) for t in parsed[:5]]
        # Some models return {"topics": [...]}
        for v in parsed.values():
            if isinstance(v, list):
                return [str(t) for t in v[:5]]
    except Exception as exc:
        logger.warning("Topic extraction failed: %s", exc)
    return _fallback_topics(filename)


def _fallback_topics(filename: str) -> List[str]:
    name = filename.lower()
    if "saas" in name:
        return ["SaaS growth", "B2B software", "startup funding", "ARR benchmarks"]
    if "financ" in name or "revenue" in name:
        return ["startup revenue growth", "venture capital", "SaaS metrics", "burn rate optimization"]
    if "market" in name:
        return ["market trends", "startup ecosystem", "product market fit", "SaaS industry"]
    return ["startup funding", "SaaS growth", "venture capital", "product market fit"]


async def fetch_news_for_topics(
    topics: List[str],
    api_key: str,
    max_per_topic: int = 5,
) -> List[dict]:
    """Fetch articles from NewsCatcher for the given topics.

    Returns a list of article dicts with: title, url, source, published_date, excerpt, topics.
    """
    if not api_key or not topics:
        return []

    results: List[dict] = []
    seen_urls: set = set()

    async with httpx.AsyncClient(timeout=12.0) as client:
        for topic in topics:
            if len(results) >= max_per_topic * len(topics):
                break
            try:
                resp = await client.get(
                    "https://api.newscatcherapi.com/v2/search",
                    params={"q": topic, "lang": "en", "page_size": max_per_topic, "sort_by": "date"},
                    headers={"x-api-key": api_key},
                )
                if resp.status_code != 200:
                    logger.warning("NewsCatcher %d for topic '%s'", resp.status_code, topic)
                    continue
                articles = resp.json().get("articles") or []
                for a in articles:
                    url = a.get("link") or a.get("url", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    excerpt = (a.get("excerpt") or a.get("summary") or a.get("title") or "")[:280].strip()
                    results.append({
                        "id": url,
                        "title": a.get("title") or "",
                        "url": url,
                        "source": a.get("clean_url") or a.get("rights") or "",
                        "published_date": str(a.get("published_date") or ""),
                        "excerpt": excerpt,
                        "topics": [topic],
                    })
            except Exception as exc:
                logger.warning("NewsCatcher fetch failed for '%s': %s", topic, exc)

    return results
