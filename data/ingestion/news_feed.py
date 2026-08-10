"""News fondamentali via RSS — usa requests Session (urlopen SSL fallisce spesso)."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import feedparser

from .http_utils import (
    get_session,
    is_cache_fresh,
    load_json_cache,
    load_settings,
    random_headers,
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    "https://www.federalreserve.gov/feeds/press_monetary.xml",
    "https://www.federalreserve.gov/feeds/press_all.xml",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "http://feeds.bbci.co.uk/news/business/rss.xml",
]


def _fetch_feed(url: str, limit: int = 12) -> list[dict]:
    try:
        rate_limit(soft=True)
        resp = get_session().get(url, timeout=20, headers=random_headers())
        if resp.status_code != 200:
            raise ConnectionError(f"HTTP {resp.status_code}")
        parsed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning("RSS fallito %s: %s", url, e)
        return []

    items = []
    for entry in (parsed.entries or [])[:limit]:
        items.append({
            "title": entry.get("title", ""),
            "summary": re.sub("<[^<]+?>", "", entry.get("summary", "") or "")[:400],
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "source": url,
        })
    return items


def _score_keywords(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for k in keywords if k.lower() in t)


def analyze_news(items: list[dict], keyword_map: dict) -> dict[str, Any]:
    tallies = {k: 0 for k in keyword_map}
    tagged = []
    for it in items:
        blob = f"{it.get('title', '')} {it.get('summary', '')}"
        tags = []
        for family, kws in keyword_map.items():
            hits = _score_keywords(blob, kws)
            if hits:
                tallies[family] += hits
                tags.append(family)
        row = dict(it)
        row["tags"] = tags
        tagged.append(row)

    weighted = (
        tallies.get("fed_policy", 0) * 0.35
        + tallies.get("fed_hawkish", 0) * 1.5
        + tallies.get("credit_stress", 0) * 1.7
        + tallies.get("ai_earnings", 0) * 1.3
        + tallies.get("recession", 0) * 1.4
    )
    # Base >0 se ci sono headline Fed/mercato rilevanti; tetto 100
    news_score = max(0.0, min(100.0, 8.0 + weighted * 5.5)) if tagged else 0.0
    if tallies.get("fed_policy", 0) == 0 and tallies.get("fed_hawkish", 0) == 0:
        # niente Fed: non forzare score alto solo per volume feed
        news_score = max(0.0, min(100.0, weighted * 5.5))
    return {
        "tallies": tallies,
        "total_hits": sum(tallies.values()),
        "news_risk_score": round(news_score, 1),
        "items": tagged,
        "tagged_count": sum(1 for it in tagged if it.get("tags")),
    }


def fetch_news_digest(*, force: bool = False) -> dict[str, Any]:
    cache_name = "news_digest"
    if not force and is_cache_fresh(cache_name, max_age_hours=6):
        cached = load_json_cache(cache_name)
        if cached and (cached.get("item_count") or 0) > 0:
            return cached

    settings = load_settings()
    feeds = settings.get("news_feeds") or DEFAULT_FEEDS
    keyword_map = settings.get("news_keywords", {})
    items: list[dict] = []
    for url in feeds:
        items.extend(_fetch_feed(url))

    # dedupe per titolo
    seen = set()
    unique = []
    for it in items:
        t = (it.get("title") or "").strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        unique.append(it)

    analysis = analyze_news(unique, keyword_map)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "feed_count": len(feeds),
        "item_count": len(unique),
        **analysis,
    }
    save_json_cache(cache_name, payload)
    logger.info("News digest: %s item", len(unique))
    return payload
