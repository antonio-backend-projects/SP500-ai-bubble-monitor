"""Margin / leva: prima FRED Z.1 (sicuro), poi scrape FINRA (spesso 403), poi seed."""
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

FINRA_URLS = [
    "https://www.finra.org/investors/learn-to-invest/advanced-investing/margin-statistics",
]

SEED_MARGIN = {
    "as_of": "2026-06-01",
    "debit_balances_billion": 1530.0,
    "credit_balances_billion": -1060.0,
    "yoy_pct": 51.5,
    "source": "seed_from_piano_strategia",
}


def _parse_debit_billions(text: str) -> Optional[dict[str, Any]]:
    text_1 = re.sub(r"\s+", " ", text)
    patterns = [
        (r"Debit\s+Balances[^0-9]{0,120}\$?([0-9]{1,3}(?:,[0-9]{3})+)", "millions_or_raw"),
        (r"margin\s+debt[^0-9]{0,40}\$?([0-9]+(?:\.[0-9]+)?)\s*trillion", "trillion"),
        (r"margin\s+debt[^0-9]{0,40}\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*billion", "billion"),
    ]
    billions = None
    for pat, kind in patterns:
        m = re.search(pat, text_1, re.I)
        if not m:
            continue
        raw = m.group(1).replace(",", "")
        num = float(raw)
        if kind == "trillion":
            billions = num * 1000.0
        elif kind == "billion":
            billions = num
        else:
            billions = num / 1000.0 if num > 10_000 else num
        break
    if billions is None or billions < 100:
        return None
    yoy = None
    ym = re.search(
        r"([+-]?\d+\.?\d*)\s*%\s*(?:YoY|year[- ]over[- ]year|from a year earlier)",
        text_1,
        re.I,
    )
    if ym:
        yoy = float(ym.group(1))
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-01"),
        "debit_balances_billion": round(billions, 2),
        "yoy_pct": yoy,
    }


def fetch_margin_debt(*, force: bool = False) -> dict[str, Any]:
    cache_name = "finra_margin"
    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached and "seed" not in str(cached.get("source", "")).lower():
            return cached

    # 1) FRED Z.1 — sicuro con API key
    try:
        from .fred_margin import fetch_margin_from_fred

        fred_m = fetch_margin_from_fred(force=force)
        save_json_cache(cache_name, fred_m)
        return fred_m
    except Exception as e:
        logger.warning("FRED margin Z.1 fallito: %s — provo FINRA HTML", e)

    # 2) FINRA HTML (spesso 403 — un solo tentativo, niente martello)
    session = get_session()
    for url in FINRA_URLS:
        try:
            rate_limit(soft=True)
            headers = random_headers()
            headers["Referer"] = "https://www.google.com/"
            resp = session.get(url, timeout=12, headers=headers)
            if resp.status_code in (401, 403, 429):
                logger.warning("FINRA HTTP %s — skip scrape", resp.status_code)
                break
            if resp.status_code != 200:
                continue
            parsed = _parse_debit_billions(resp.text)
            if not parsed:
                continue
            parsed["updated_at"] = datetime.now(timezone.utc).isoformat()
            parsed["source"] = "FINRA scrape"
            save_json_cache(cache_name, parsed)
            return parsed
        except Exception as e:
            logger.warning("FINRA scrape fallito: %s", e)
            break

    cached = load_json_cache(cache_name)
    if cached:
        return cached
    seed = dict(SEED_MARGIN)
    seed["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_json_cache(cache_name, seed)
    return seed
