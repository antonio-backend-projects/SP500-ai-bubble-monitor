"""
Breadth / 'sotto la superficie' senza Yahoo:

1) SPY vs RSP (cap-weight vs equal-weight) da NASDAQ historical
2) Campione top-N titoli Slickcharts: distanza media dal max 52w (quote NASDAQ)

Non è il drawdown medio di tutti i 500 nomi, ma è il miglior proxy IP-safe
allineato al piano (equal-weight e stress dei leader ampi).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}


def _parse_close_rows(rows: list[dict]) -> list[tuple[str, float]]:
    out = []
    for r in rows or []:
        try:
            # NASDAQ: MM/DD/YYYY
            raw = r.get("date") or ""
            mm, dd, yyyy = raw.split("/")
            iso = f"{yyyy}-{mm.zfill(2)}-{dd.zfill(2)}"
            close = float(str(r.get("close") or "").replace(",", ""))
            out.append((iso, close))
        except Exception:
            continue
    out.sort(key=lambda x: x[0])
    return out


def _stats_from_closes(series: list[tuple[str, float]]) -> dict[str, Any]:
    if len(series) < 5:
        return {}
    last_date, last = series[-1]
    highs = [c for _, c in series]
    hi = max(highs)
    # YTD: primo punto dell'anno corrente
    year = last_date[:4]
    ytd_pts = [c for d, c in series if d.startswith(year)]
    ytd_base = ytd_pts[0] if ytd_pts else series[0][1]
    return {
        "last": last,
        "as_of": last_date,
        "dist_52w_high_pct": round((last / hi - 1.0) * 100.0, 2) if hi else None,
        "ytd_pct": round((last / ytd_base - 1.0) * 100.0, 2) if ytd_base else None,
        "high": hi,
    }


def _fetch_etf_history(symbol: str, *, days: int = 400) -> list[tuple[str, float]]:
    session = get_session()
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    rate_limit(soft=True)
    url = (
        f"https://api.nasdaq.com/api/quote/{symbol}/historical"
        f"?assetclass=etf&fromdate={start.isoformat()}&todate={end.isoformat()}&limit=260"
    )
    resp = session.get(url, timeout=25, headers=HEADERS)
    if resp.status_code in (401, 403, 429):
        raise RuntimeError(f"NASDAQ ETF {symbol} HTTP {resp.status_code}")
    if resp.status_code != 200:
        raise RuntimeError(f"NASDAQ ETF {symbol} HTTP {resp.status_code}")
    rows = (((resp.json() or {}).get("data") or {}).get("tradesTable") or {}).get("rows") or []
    return _parse_close_rows(rows)


def _nasdaq_ticker(raw: str) -> str:
    t = (raw or "").upper().replace(".", "/")  # BRK.B → BRK/B
    return t


def fetch_market_breadth(
    *,
    force: bool = False,
    constituents: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    cache_name = "market_breadth"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached and cached.get("spy_rsp_gap_ytd_pct") is not None:
            return cached

    settings = load_settings()
    sample_n = int(settings.get("breadth_sample_n", 40))

    # --- SPY vs RSP ---
    spy_s = _fetch_etf_history("SPY")
    rsp_s = _fetch_etf_history("RSP")
    spy = _stats_from_closes(spy_s)
    rsp = _stats_from_closes(rsp_s)
    gap_ytd = None
    if spy.get("ytd_pct") is not None and rsp.get("ytd_pct") is not None:
        # positivo: cap-weight batte equal-weight (concentrazione aiuta)
        gap_ytd = round(float(spy["ytd_pct"]) - float(rsp["ytd_pct"]), 2)

    # --- campione titoli ---
    cons = constituents or []
    tickers = []
    for row in cons:
        t = _nasdaq_ticker(str(row.get("ticker") or ""))
        if t and t not in tickers:
            tickers.append(t)
    tickers = tickers[:sample_n]

    session = get_session()
    dists: list[float] = []
    per_ticker: dict[str, float] = {}
    blocked = False
    for t in tickers:
        if blocked:
            break
        try:
            rate_limit(soft=True)
            url = f"https://api.nasdaq.com/api/quote/{t}/info?assetclass=stocks"
            resp = session.get(url, timeout=12, headers=HEADERS)
            if resp.status_code in (401, 403, 429):
                logger.warning("Breadth NASDAQ HTTP %s — stop sample", resp.status_code)
                blocked = True
                break
            if resp.status_code != 200:
                continue
            data = (resp.json() or {}).get("data") or {}
            primary = data.get("primaryData") or {}
            secondary = data.get("secondaryData") or {}
            px_raw = str(primary.get("lastSalePrice") or secondary.get("lastSalePrice") or "")
            px_raw = px_raw.replace("$", "").replace(",", "")
            if not px_raw:
                continue
            px = float(px_raw)
            rng = ((data.get("keyStats") or {}).get("fiftyTwoWeekHighLow") or {}).get("value") or ""
            if " - " not in str(rng):
                continue
            hi = float(str(rng).split(" - ", 1)[1].replace(",", "").strip())
            if hi <= 0:
                continue
            dist = round((px / hi - 1.0) * 100.0, 2)
            dists.append(dist)
            per_ticker[t.replace("/", ".")] = dist
        except Exception as e:
            logger.warning("Breadth %s: %s", t, e)
            time.sleep(0.3)

    avg_dd = round(sum(dists) / len(dists), 2) if dists else None
    below_5 = sum(1 for d in dists if d <= -5.0)
    below_10 = sum(1 for d in dists if d <= -10.0)
    pct_below_5 = round(100.0 * below_5 / len(dists), 1) if dists else None
    pct_below_10 = round(100.0 * below_10 / len(dists), 1) if dists else None

    # Stress 0-100: equal-weight dietro + molti titoli sotto i massimi
    stress = 40.0
    if gap_ytd is not None:
        # se SPY >> RSP, superficie ok / sotto fragile
        stress += max(-15.0, min(25.0, gap_ytd * 1.2))
    if avg_dd is not None:
        # avg -10% → +20 stress circa
        stress += max(0.0, min(35.0, abs(min(0.0, avg_dd)) * 2.0))
    if pct_below_10 is not None:
        stress += max(0.0, min(20.0, pct_below_10 * 0.25))
    stress = round(max(0.0, min(100.0, stress)), 1)

    payload = {
        "spy": spy,
        "rsp": rsp,
        "spy_rsp_gap_ytd_pct": gap_ytd,
        "sample_n_requested": sample_n,
        "sample_n_ok": len(dists),
        "sample_avg_dist_52w_high_pct": avg_dd,
        "sample_pct_names_below_5pct": pct_below_5,
        "sample_pct_names_below_10pct": pct_below_10,
        "sample_dist_by_ticker": per_ticker,
        "breadth_stress_0_100": stress,
        "blocked": blocked,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "NASDAQ historical SPY/RSP + quote sample Slickcharts",
        "note": (
            "Proxy del piano 'drawdown medio titoli': media dist 52w su campione top-N "
            "(non equal-weight di tutti i 500). RSP vs SPY = equal vs cap weight."
        ),
    }
    save_json_cache(cache_name, payload)
    logger.info(
        "Breadth: SPY-RSP YTD gap=%s sample_avg_52w=%s n=%s stress=%s",
        gap_ytd,
        avg_dd,
        len(dists),
        stress,
    )
    return payload
