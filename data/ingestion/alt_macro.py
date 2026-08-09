"""
Fallback macro quando FRED graph CSV è irraggiungibile.
Host che rispondono da questo PC: Treasury, Fed H.15, CMV, TradingEconomics.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from .http_utils import (
    get_session,
    is_cache_fresh,
    load_json_cache,
    random_headers,
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_treasury_2s10s(*, force: bool = False) -> dict[str, Any]:
    """Spread 10y-2y in punti percentuali (come FRED T10Y2Y)."""
    cache_name = "alt_treasury_2s10s"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    year = datetime.now().year
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        f"TextView?type=daily_treasury_yield_curve&field_tdr_date_value={year}"
    )
    rate_limit(soft=True)
    resp = get_session().get(url, timeout=25, headers=random_headers())
    if resp.status_code != 200:
        raise ConnectionError(f"Treasury HTTP {resp.status_code}")
    html = resp.text

    headers = [
        re.sub("<[^>]+>", "", h).strip()
        for h in re.findall(r"<th[^>]*>(.*?)</th>", html, re.I | re.S)
    ]
    # Dedup / trova indici 2 Yr e 10 Yr nell'ultima tabella yield curve
    try:
        i2 = headers.index("2 Yr")
        i10 = headers.index("10 Yr")
    except ValueError as e:
        raise ValueError("Colonne 2 Yr / 10 Yr non trovate in Treasury HTML") from e

    history = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.I | re.S):
        tds = [
            re.sub("<[^>]+>", "", t).strip()
            for t in re.findall(r"<td[^>]*>(.*?)</td>", row, re.I | re.S)
        ]
        if len(tds) <= max(i2, i10):
            continue
        if not re.match(r"\d{2}/\d{2}/\d{4}", tds[0] or ""):
            continue
        try:
            y2 = float(tds[i2])
            y10 = float(tds[i10])
        except (TypeError, ValueError):
            continue
        # mm/dd/yyyy → iso
        mm, dd, yyyy = tds[0].split("/")
        history.append({
            "date": f"{yyyy}-{mm}-{dd}",
            "value": round(y10 - y2, 4),
            "y2": y2,
            "y10": y10,
        })

    if not history:
        raise ValueError("Nessuna riga yield curve Treasury")

    history.sort(key=lambda r: r["date"])
    last = history[-1]
    payload = {
        "last_date": last["date"],
        "last_value": last["value"],  # punti percentuali
        "history": [{"date": h["date"], "value": h["value"]} for h in history[-260:]],
        "updated_at": _now(),
        "source": "US Treasury daily yield curve",
    }
    save_json_cache(cache_name, payload)
    return payload


def fetch_fed_funds_h15(*, force: bool = False) -> dict[str, Any]:
    cache_name = "alt_fed_funds_h15"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    url = "https://www.federalreserve.gov/releases/h15/"
    rate_limit(soft=True)
    resp = get_session().get(url, timeout=20, headers=random_headers())
    if resp.status_code != 200:
        raise ConnectionError(f"H.15 HTTP {resp.status_code}")
    m = re.search(
        r"Federal funds \(effective\).*?<td class=\"data\"[^>]*>\s*&nbsp;([0-9.]+)\s*&nbsp;",
        resp.text,
        re.I | re.S,
    )
    if not m:
        m = re.search(
            r"Federal funds.*?(?:effective)?[^0-9]{0,60}([0-9]\.[0-9]{1,2})",
            resp.text,
            re.I | re.S,
        )
    if not m:
        raise ValueError("Fed funds non trovato in H.15")
    val = float(m.group(1))
    payload = {
        "last_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_value": val,
        "history": [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "value": val}],
        "updated_at": _now(),
        "source": "Federal Reserve H.15",
    }
    save_json_cache(cache_name, payload)
    return payload


def fetch_buffett_cmv(*, force: bool = False) -> dict[str, Any]:
    cache_name = "alt_buffett_cmv"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    url = "https://www.currentmarketvaluation.com/models/buffett-indicator.php"
    rate_limit(soft=True)
    resp = get_session().get(url, timeout=25, headers=random_headers())
    if resp.status_code != 200:
        raise ConnectionError(f"CMV HTTP {resp.status_code}")
    m = re.search(
        r"Buffett Indicator as\s*([0-9]+(?:\.[0-9]+)?)%",
        resp.text,
        re.I,
    )
    if not m:
        raise ValueError("Buffett % non trovato su CMV")
    val = float(m.group(1))
    payload = {
        "last_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_value": val,
        "history": [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "value": val}],
        "updated_at": _now(),
        "source": "currentmarketvaluation.com",
    }
    save_json_cache(cache_name, payload)
    return payload


def fetch_hy_oas_te(*, force: bool = False) -> dict[str, Any]:
    """High yield spread da TradingEconomics (percentuali, come FRED)."""
    cache_name = "alt_hy_oas_te"
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    url = "https://tradingeconomics.com/united-states/high-yield-spread"
    rate_limit(soft=True)
    resp = get_session().get(url, timeout=25, headers=random_headers())
    if resp.status_code != 200:
        raise ConnectionError(f"TE HTTP {resp.status_code}")
    text = resp.text
    val = None
    for pat in (
        r'id="actual"[^>]*>\s*([0-9]+(?:\.[0-9]+)?)',
        r'"Last"\s*:\s*([0-9]+(?:\.[0-9]+)?)',
        r"High Yield Spread[^0-9]{0,80}([0-9]\.[0-9]{2})",
        r"actual[:\s]+([0-9]\.[0-9]{2})",
    ):
        m = re.search(pat, text, re.I)
        if m:
            cand = float(m.group(1))
            if 1.0 <= cand <= 20.0:  # spread in punti %
                val = cand
                break
    if val is None:
        raise ValueError("HY spread non parsato da TradingEconomics")
    payload = {
        "last_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_value": val,
        "history": [{"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "value": val}],
        "updated_at": _now(),
        "source": "TradingEconomics high-yield-spread",
    }
    save_json_cache(cache_name, payload)
    return payload


def _is_stale(series: dict, *, max_age_days: int = 400) -> bool:
    """True se last_date è troppo vecchia (es. serie annuali FRED ferme al 2020)."""
    d = series.get("last_date")
    if not d:
        return True
    try:
        dt = datetime.strptime(str(d)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return True
    age = (datetime.now(timezone.utc) - dt).days
    return age > max_age_days


def _is_weak(series: Optional[dict], *, max_age_days: int = 400) -> bool:
    if not series:
        return True
    src = str(series.get("source") or "")
    if series.get("last_value") is None:
        return True
    if "seed" in src.lower():
        return True
    if _is_stale(series, max_age_days=max_age_days):
        return True
    return False


def enrich_fred_bundle_with_alts(bundle: dict, *, force: bool = False) -> dict:
    """Sostituisce serie deboli con alternate live."""
    series = bundle.setdefault("series", {})
    alts_used = []

    def put(key: str, series_id: str, alt: dict):
        series[key] = {
            "series_id": series_id,
            "last_date": alt.get("last_date"),
            "last_value": alt.get("last_value"),
            "history": alt.get("history") or [],
            "updated_at": alt.get("updated_at"),
            "source": alt.get("source"),
        }
        alts_used.append(key)

    try:
        if _is_weak(series.get("yield_curve_2s10s")):
            put("yield_curve_2s10s", "T10Y2Y", fetch_treasury_2s10s(force=force))
    except Exception as e:
        logger.warning("alt treasury: %s", e)

    try:
        if _is_weak(series.get("fed_funds")):
            put("fed_funds", "DFF", fetch_fed_funds_h15(force=force))
    except Exception as e:
        logger.warning("alt H15: %s", e)

    try:
        # FRED DDDM01… è annuale e spesso ferma a anni fa → CMV è la lettura corrente
        old_b = series.get("buffett_indicator") or {}
        if _is_weak(old_b, max_age_days=400):
            old_date = old_b.get("last_date")
            put("buffett_indicator", "DDDM01USA156NWDB", fetch_buffett_cmv(force=force))
            logger.info(
                "Buffett: usata CMV live (FRED World Bank last=%s, troppo vecchia)",
                old_date,
            )
    except Exception as e:
        logger.warning("alt CMV buffett: %s", e)

    try:
        if _is_weak(series.get("hy_oas")):
            put("hy_oas", "BAMLH0A0HYM2", fetch_hy_oas_te(force=force))
    except Exception as e:
        logger.warning("alt TE HY: %s", e)

    bundle["alts_used"] = alts_used
    return bundle
