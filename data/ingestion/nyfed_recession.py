"""Probabilità recessione NY Fed — file .xls (anche se URL finisce in .csv)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional

import pandas as pd

from .http_utils import get_session, is_cache_fresh, load_json_cache, random_headers, rate_limit, save_json_cache

logger = logging.getLogger(__name__)

NYFED_URLS = [
    "https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.xls",
    "https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.csv",
]

SEED = {
    "probability_pct": 25.0,
    "as_of": "2026-08-01",
    "source": "seed_from_piano_strategia",
}


def _parse_nyfed_xls(content: bytes) -> Optional[dict[str, Any]]:
    df = pd.read_excel(BytesIO(content), sheet_name="rec_prob")
    # Normalizza nomi
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = cols.get("date")
    prob_col = cols.get("rec_prob") or cols.get("recession_probability")
    if date_col is None or prob_col is None:
        # fallback posizionale: Date, ..., Rec_prob
        date_col = df.columns[0]
        for c in df.columns:
            if "rec" in str(c).lower() and "prob" in str(c).lower():
                prob_col = c
                break
    if prob_col is None:
        return None

    work = df[[date_col, prob_col]].copy()
    work["value"] = pd.to_numeric(work[prob_col], errors="coerce")
    work["date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["date", "value"])
    # Escludi proiezioni future pure (senza yield) — tieni fino a oggi+2m
    today = pd.Timestamp.now(tz=None).normalize()
    work = work[work["date"] <= today + pd.DateOffset(months=2)]
    if work["value"].max() <= 1.5:
        work["value"] = work["value"] * 100.0
    work = work.sort_values("date")
    history = [
        {"date": r["date"].strftime("%Y-%m-%d"), "value": round(float(r["value"]), 2)}
        for _, r in work.tail(120).iterrows()
    ]
    if not history:
        return None
    last = history[-1]
    return {
        "probability_pct": last["value"],
        "as_of": last["date"],
        "history": history,
        "source": "NY Fed allmonth.xls (Rec_prob)",
    }


def fetch_recession_prob(*, force: bool = False) -> dict[str, Any]:
    cache_name = "nyfed_recession"
    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached and "seed" not in str(cached.get("source", "")).lower():
            return cached

    last_err = None
    for url in NYFED_URLS:
        try:
            rate_limit(soft=True)
            resp = get_session().get(url, timeout=30, headers=random_headers())
            if resp.status_code != 200:
                raise ConnectionError(f"HTTP {resp.status_code}")
            # È sempre OLE2 Excel
            if resp.content[:4] == b"\xd0\xcf\x11\xe0" or True:
                parsed = _parse_nyfed_xls(resp.content)
            else:
                parsed = None
            if not parsed:
                raise ValueError("Parse NY Fed fallito")
            parsed["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_json_cache(cache_name, parsed)
            logger.info("NY Fed recession ok: %s%%", parsed.get("probability_pct"))
            return parsed
        except Exception as e:
            last_err = e
            logger.warning("NY Fed fallito (%s): %s", url, e)

    cached = load_json_cache(cache_name)
    if cached:
        return cached
    seed = dict(SEED)
    seed["updated_at"] = datetime.now(timezone.utc).isoformat()
    seed["error"] = str(last_err)
    save_json_cache(cache_name, seed)
    return seed
