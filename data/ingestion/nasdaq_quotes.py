"""
Prezzi Mag7 via API NASDAQ pubblica (alternativa a Yahoo 429).
Rate limit soft + stop immediato su 401/403/429.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from .http_utils import (
    get_session,
    is_cache_fresh,
    load_json_cache,
    load_settings,
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)


def fetch_mag7_nasdaq(*, force: bool = False) -> dict[str, Any]:
    cache_name = "mag7_nasdaq"
    settings = load_settings()
    if not settings.get("fetch_nasdaq_mag7", True):
        return {"skipped": True, "source": "disabled", "prices": {}, "changes": {}}

    if not force and is_cache_fresh(cache_name, max_age_hours=12):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    mag7 = list(settings.get("mag7", []))
    session = get_session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }
    prices: dict[str, Any] = {}
    changes: dict[str, Any] = {}
    blocked = False

    for t in mag7:
        if blocked:
            break
        try:
            rate_limit(soft=True)
            url = f"https://api.nasdaq.com/api/quote/{t}/info?assetclass=stocks"
            resp = session.get(url, timeout=12, headers=headers)
            if resp.status_code in (401, 403, 429):
                logger.warning("NASDAQ HTTP %s su %s — stop Mag7", resp.status_code, t)
                blocked = True
                break
            if resp.status_code != 200:
                logger.warning("NASDAQ %s HTTP %s", t, resp.status_code)
                continue
            data = (resp.json() or {}).get("data") or {}
            primary = data.get("primaryData") or {}
            px_raw = (primary.get("lastSalePrice") or "").replace("$", "").replace(",", "")
            chg_raw = (primary.get("percentageChange") or "").replace("%", "").replace("+", "")
            prices[t] = float(px_raw) if px_raw else None
            try:
                changes[t] = float(chg_raw) if chg_raw else None
            except ValueError:
                changes[t] = None
        except Exception as e:
            logger.warning("NASDAQ %s fallito: %s", t, e)
            time.sleep(0.5)

    if blocked and not prices:
        cached = load_json_cache(cache_name)
        if cached:
            cached["note"] = "nasdaq_blocked_cache"
            return cached

    neg = [v for v in changes.values() if v is not None and v < 0]
    payload = {
        "mag7": mag7,
        "prices": prices,
        "changes_pct": changes,
        "avg_change_pct": round(sum(changes[k] for k in changes if changes[k] is not None) / max(1, len([c for c in changes.values() if c is not None])), 2)
        if any(c is not None for c in changes.values())
        else None,
        "losers": len(neg),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "NASDAQ quote API",
        "blocked": blocked,
    }
    save_json_cache(cache_name, payload)
    return payload
