"""
Leva / margin loans via FRED Z.1 (API key) — alternativa sicura a FINRA HTML (403).

Serie: BOGZ1FL663067003Q
  Security Brokers and Dealers; Receivables Due from Customers
  (Margin Loans and Other Receivables); Asset, Level

Nota: non è identica a FINRA Debit Balances (metodologia diversa, trimestrale),
ma è il miglior proxy ufficiale scaricabile senza ban IP.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .fred import fetch_fred_series
from .http_utils import is_cache_fresh, load_json_cache, save_json_cache

logger = logging.getLogger(__name__)

SERIES_ID = "BOGZ1FL663067003Q"


def fetch_margin_from_fred(*, force: bool = False) -> dict[str, Any]:
    cache_name = "fred_margin_z1"
    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached and cached.get("debit_balances_billion") is not None:
            return cached

    series = fetch_fred_series(SERIES_ID, force=force)
    if series.get("last_value") is None or "seed" in str(series.get("source", "")).lower():
        raise RuntimeError(f"FRED margin series non disponibile: {series.get('error')}")

    # Livelli Z.1 tipicamente in milioni di USD
    level = float(series["last_value"])
    billions = level / 1000.0 if level > 50_000 else level

    hist = series.get("history") or []
    yoy = None
    if len(hist) >= 5:
        # cerca punto ~1y prima
        last_date = hist[-1].get("date")
        try:
            y = int(str(last_date)[:4])
            target = f"{y-1}-"
            prev = [h for h in hist if str(h.get("date", "")).startswith(target)]
            if prev:
                prev_v = float(prev[-1]["value"])
                prev_b = prev_v / 1000.0 if prev_v > 50_000 else prev_v
                if prev_b:
                    yoy = round((billions / prev_b - 1.0) * 100.0, 1)
        except Exception:
            yoy = None
    if yoy is None and len(hist) >= 2:
        prev_v = float(hist[-2]["value"])
        prev_b = prev_v / 1000.0 if prev_v > 50_000 else prev_v
        if prev_b:
            yoy = round((billions / prev_b - 1.0) * 100.0, 1)

    payload = {
        "as_of": series.get("last_date"),
        "debit_balances_billion": round(billions, 2),
        "yoy_pct": yoy,
        "raw_level": level,
        "series_id": SERIES_ID,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "FRED Z.1 BOGZ1FL663067003Q (margin loans proxy)",
        "note": "Proxy Fed Z.1, non FINRA debit balances (metodologia diversa).",
        "history": [
            {
                "date": h.get("date"),
                "value": round(
                    (float(h["value"]) / 1000.0)
                    if float(h["value"]) > 50_000
                    else float(h["value"]),
                    2,
                ),
            }
            for h in hist
            if h.get("value") is not None
        ],
    }
    save_json_cache(cache_name, payload)
    logger.info("Margin Z.1 ok: $%sB YoY=%s", payload["debit_balances_billion"], yoy)
    return payload
