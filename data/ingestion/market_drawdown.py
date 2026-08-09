"""Drawdown S&P 500 da FRED SP500 (API key) — niente Yahoo."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .fred import fetch_fred_series
from .http_utils import is_cache_fresh, load_json_cache, save_json_cache

logger = logging.getLogger(__name__)


def _f(v) -> Optional[float]:
    try:
        if v in (None, "."):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_spx_drawdown(*, force: bool = False) -> dict[str, Any]:
    cache_name = "spx_drawdown"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached and cached.get("last") is not None:
            return cached

    # FRED SP500 ha storia lunga; chiediamo più punti via API limit
    # fetch_fred_series usa limit=260 (~1y trading days)
    series = fetch_fred_series("SP500", force=force)
    hist = [
        {"date": h.get("date"), "value": _f(h.get("value"))}
        for h in (series.get("history") or [])
    ]
    hist = [h for h in hist if h["value"] is not None]
    if len(hist) < 20:
        raise RuntimeError("FRED SP500 history troppo corta")

    closes = [h["value"] for h in hist]
    last = closes[-1]
    peak = max(closes)
    trough = min(closes)
    dist_52w_high = round((last / peak - 1.0) * 100.0, 2)
    # max drawdown nel campione
    run_peak = closes[0]
    max_dd = 0.0
    for c in closes:
        run_peak = max(run_peak, c)
        dd = c / run_peak - 1.0
        max_dd = min(max_dd, dd)

    # YTD: primo punto dell'anno corrente
    year = str(hist[-1]["date"])[:4]
    ytd_pts = [h for h in hist if str(h["date"]).startswith(year)]
    ytd = None
    if ytd_pts:
        ytd = round((last / ytd_pts[0]["value"] - 1.0) * 100.0, 2)

    # ritorno ~3m / ~1m (approx 63/21 trading days)
    def ret(n: int) -> Optional[float]:
        if len(closes) <= n:
            return None
        return round((last / closes[-1 - n] - 1.0) * 100.0, 2)

    payload = {
        "last": last,
        "as_of": hist[-1]["date"],
        "peak": peak,
        "dist_52w_high_pct": dist_52w_high,
        "max_drawdown_1y_pct": round(max_dd * 100.0, 2),
        "ytd_pct": ytd,
        "ret_1m_pct": ret(21),
        "ret_3m_pct": ret(63),
        "history": hist[-120:],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "FRED SP500",
    }
    save_json_cache(cache_name, payload)
    logger.info(
        "SPX drawdown: last=%s dist52w=%s%% ytd=%s%%",
        last, dist_52w_high, ytd,
    )
    return payload
