"""
8-K recenti Mag7 da SEC EDGAR Atom — segnale 'eventi corporate / earnings risk'.
UA obbligatorio stile SEC; poche richieste, cache lunga.
"""
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
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)

# CIK senza leading zeros ok nell'URL
MAG7_CIK = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "TSLA": "0001318605",
}


def fetch_mag7_8k(*, force: bool = False, max_tickers: int = 7) -> dict[str, Any]:
    cache_name = "sec_mag7_8k"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached and cached.get("items") is not None:
            return cached

    settings = load_settings()
    tickers = list(settings.get("mag7", []))[:max_tickers]
    session = get_session()
    headers = {
        # SEC richiede un UA identificabile
        "User-Agent": "SP500BubbleMonitor/1.0 contact@localhost",
        "Accept": "application/atom+xml,application/xml,text/xml,*/*",
    }
    items = []
    for t in tickers:
        cik = MAG7_CIK.get(t)
        if not cik:
            continue
        try:
            rate_limit(soft=True)
            url = (
                "https://www.sec.gov/cgi-bin/browse-edgar"
                f"?action=getcompany&CIK={cik}&type=8-K&count=5&output=atom"
            )
            resp = session.get(url, timeout=15, headers=headers)
            if resp.status_code in (401, 403, 429):
                logger.warning("SEC HTTP %s — stop filings", resp.status_code)
                break
            if resp.status_code != 200:
                continue
            parsed = feedparser.parse(resp.content)
            for entry in (parsed.entries or [])[:3]:
                title = entry.get("title", "")
                items.append({
                    "ticker": t,
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("updated") or entry.get("published") or "",
                    "earnings_like": bool(
                        re.search(
                            r"result|earning|item\s*2\.02|financial|press release|"
                            r"exhibit\s*99|quarterly",
                            title,
                            re.I,
                        )
                    ),
                })
        except Exception as e:
            logger.warning("SEC %s: %s", t, e)

    earnings_hits = sum(1 for it in items if it.get("earnings_like"))
    # Molti 8-K generici: rischio moderato; spike solo se earnings_like alto
    base = 12.0 + min(40.0, earnings_hits * 6.0) + min(20.0, len(items) * 1.5)
    payload = {
        "items": items,
        "earnings_like_count": earnings_hits,
        "tickers_scanned": tickers,
        "ai_filings_risk": round(min(100.0, base), 1),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "SEC EDGAR atom 8-K",
    }
    save_json_cache(cache_name, payload)
    logger.info("SEC 8-K: %s item, earnings_like=%s", len(items), earnings_hits)
    return payload
