"""
Utili Mag7 da NASDAQ earnings-surprise API (EPS vs consensus).
Alternativa IP-safe a Yahoo; poche richieste, cache 24h.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from .http_utils import (
    get_session,
    is_cache_fresh,
    load_json_cache,
    load_settings,
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)


def _f(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def fetch_mag7_earnings(*, force: bool = False) -> dict[str, Any]:
    cache_name = "mag7_earnings"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached and cached.get("rows") is not None:
            return cached

    settings = load_settings()
    tickers = list(settings.get("mag7", []))
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

    rows: list[dict[str, Any]] = []
    blocked = False
    for t in tickers:
        if blocked:
            break
        try:
            rate_limit(soft=True)
            url = f"https://api.nasdaq.com/api/company/{t}/earnings-surprise"
            resp = session.get(url, timeout=15, headers=headers)
            if resp.status_code in (401, 403, 429):
                logger.warning("NASDAQ earnings HTTP %s — stop", resp.status_code)
                blocked = True
                break
            if resp.status_code != 200:
                continue
            table = (
                ((resp.json() or {}).get("data") or {}).get("earningsSurpriseTable") or {}
            )
            latest = (table.get("rows") or [None])[0]
            if not latest:
                continue
            surprise = _f(latest.get("percentageSurprise"))
            rows.append(
                {
                    "ticker": t,
                    "fiscal_qtr": latest.get("fiscalQtrEnd"),
                    "date_reported": latest.get("dateReported"),
                    "eps": _f(latest.get("eps")),
                    "consensus": _f(latest.get("consensusForecast")),
                    "surprise_pct": surprise,
                    "miss": surprise is not None and surprise < 0,
                }
            )
        except Exception as e:
            logger.warning("NASDAQ earnings %s: %s", t, e)
            time.sleep(0.4)

    if blocked and not rows:
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    surprises = [r["surprise_pct"] for r in rows if r.get("surprise_pct") is not None]
    misses = sum(1 for r in rows if r.get("miss"))
    avg_surprise = round(sum(surprises) / len(surprises), 2) if surprises else None

    # Score rischio: miss e surprise deboli alzano; beat ampi abbassano
    if not surprises:
        risk = 25.0
    else:
        risk = 35.0
        risk += misses * 18.0
        risk += max(0.0, -float(avg_surprise or 0) * 4.0)
        risk -= max(0.0, float(avg_surprise or 0) * 1.5)
        risk = max(0.0, min(100.0, risk))

    payload = {
        "rows": rows,
        "tickers": tickers,
        "miss_count": misses,
        "avg_surprise_pct": avg_surprise,
        "ai_earnings_risk": round(risk, 1),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "NASDAQ earnings-surprise API",
        "blocked": blocked,
        "note": "EPS reportato vs consensus; non è guidance/capex AI puro.",
    }
    save_json_cache(cache_name, payload)
    logger.info(
        "Mag7 earnings: %s ticker, miss=%s avg_surprise=%s risk=%s",
        len(rows),
        misses,
        avg_surprise,
        payload["ai_earnings_risk"],
    )
    return payload
