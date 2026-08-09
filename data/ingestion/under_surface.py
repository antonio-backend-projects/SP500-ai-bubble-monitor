"""Segnali sotto la superficie: drawdown SPX (FRED) + Mag7 NASDAQ + filings SEC."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .http_utils import is_cache_fresh, load_json_cache, save_json_cache

logger = logging.getLogger(__name__)


def build_under_surface(
    *,
    weights: dict[str, Any],
    news: dict[str, Any],
    drawdown: dict[str, Any] | None = None,
    nasdaq: dict[str, Any] | None = None,
    filings: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    cache_name = "under_surface"
    if not force and is_cache_fresh(cache_name, max_age_hours=12):
        cached = load_json_cache(cache_name)
        if cached and cached.get("dist_52w_high_pct") is not None:
            return cached

    drawdown = drawdown or {}
    nasdaq = nasdaq or {}
    filings = filings or {}
    mag7 = weights.get("mag7_weight_pct")
    top10 = weights.get("top10_weight_pct")
    top = weights.get("top10") or []

    conc_stress = None
    if top10 is not None:
        conc_stress = max(0.0, min(100.0, (float(top10) - 25.0) / 13.0 * 100.0))

    dist = drawdown.get("dist_52w_high_pct")
    ytd = drawdown.get("ytd_pct")
    max_dd = drawdown.get("max_drawdown_1y_pct")

    # Stress prezzo: vicino ai massimi = froth; drawdown profondo = già in correzione
    price_stress = None
    if dist is not None:
        # 0% dal max → stress alto (cara); -20% → stress medio diverso (washout)
        if dist >= -3:
            price_stress = 75.0 + min(25.0, abs(dist) * 2)
        elif dist >= -10:
            price_stress = 45.0
        else:
            price_stress = 30.0

    changes = nasdaq.get("changes_pct") or {}
    mag7_avg = nasdaq.get("avg_change_pct")
    losers = nasdaq.get("losers")

    tallies = news.get("tallies") or {}
    rotation_hits = int(tallies.get("ai_earnings", 0)) + int(tallies.get("recession", 0))
    filings_risk = filings.get("ai_filings_risk")

    payload = {
        "mag7_weight_pct": mag7,
        "top10_weight_pct": top10,
        "top10_leaders": top[:10],
        "concentration_stress_0_100": round(conc_stress, 1) if conc_stress is not None else None,
        "spx_last": drawdown.get("last"),
        "spx_as_of": drawdown.get("as_of"),
        "dist_52w_high_pct": dist,
        "ytd_pct": ytd,
        "max_drawdown_1y_pct": max_dd,
        "ret_1m_pct": drawdown.get("ret_1m_pct"),
        "ret_3m_pct": drawdown.get("ret_3m_pct"),
        "price_stress_0_100": round(price_stress, 1) if price_stress is not None else None,
        "mag7_prices": nasdaq.get("prices") or {},
        "mag7_changes_pct": changes,
        "mag7_avg_change_pct": mag7_avg,
        "mag7_losers": losers,
        "sec_8k_items": (filings.get("items") or [])[:8],
        "sec_earnings_like_count": filings.get("earnings_like_count"),
        "filings_risk_0_100": filings_risk,
        "news_rotation_hits": rotation_hits,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "+".join(
            x for x in [
                drawdown.get("source"),
                nasdaq.get("source"),
                filings.get("source"),
                weights.get("source"),
            ] if x
        ) or "composite",
    }
    save_json_cache(cache_name, payload)
    return payload
