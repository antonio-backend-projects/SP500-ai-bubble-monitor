"""
Serie macro FRED — soluzione anti-timeout.

Problema: fred.stlouisfed.org/graph/fredgraph.csv va in timeout da molti IP.
Soluzione: usare api.stlouisfed.org (risponde in ~1s) con API key gratuita.

Ordine:
  1) FRED API ufficiale (FRED_API_KEY / config)
  2) Alternates per-serie (Treasury, H.15, CMV, …) via alt_macro
  3) Cache / seed
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Optional

import pandas as pd

from .http_utils import (
    get_session,
    get_with_retry,
    is_cache_fresh,
    load_json_cache,
    load_settings,
    random_headers,
    rate_limit,
    save_json_cache,
)

logger = logging.getLogger(__name__)

FRED_API = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id={series_id}&api_key={api_key}&file_type=json"
    "&sort_order=desc&limit=260"
)
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def _resolve_api_key() -> Optional[str]:
    # Primario: .env / env (riusabile)
    try:
        from config.env import get_secret

        key = get_secret("FRED_API_KEY") or get_secret("FRED_KEY")
    except Exception:
        key = os.environ.get("FRED_API_KEY") or os.environ.get("FRED_KEY")
    if key:
        return key.strip()

    # Legacy / fallback
    settings = load_settings()
    key = (settings.get("fred_api_key") or "").strip()
    if key and key not in ("YOUR_KEY_HERE", "changeme"):
        return key
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for name in ("config/fred_api_key.txt", "config/.fred_api_key"):
        path = os.path.join(root, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                val = f.read().strip()
            if val and "YOUR_" not in val:
                return val
    return None


def _payload(series_id: str, history: list[dict], source: str) -> dict[str, Any]:
    last = history[-1] if history else {"date": None, "value": None}
    return {
        "series_id": series_id,
        "last_date": last.get("date"),
        "last_value": float(last["value"]) if last.get("value") is not None else None,
        "history": history,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }


def _fetch_via_api(series_id: str, api_key: str) -> dict[str, Any]:
    url = FRED_API.format(series_id=series_id, api_key=api_key)
    # API host funziona: timeout corto, pochi retry
    rate_limit(soft=True)
    session = get_session()
    resp = session.get(url, timeout=15, headers=random_headers())
    if resp.status_code != 200:
        raise ConnectionError(f"FRED API HTTP {resp.status_code}: {resp.text[:160]}")
    data = resp.json()
    if data.get("error_code"):
        raise ConnectionError(data.get("error_message") or str(data.get("error_code")))
    obs = data.get("observations") or []
    history = []
    for row in reversed(obs):  # API chiede desc → ribalta in asc
        val = row.get("value")
        if val in (None, "."):
            continue
        try:
            history.append({"date": row.get("date"), "value": float(val)})
        except (TypeError, ValueError):
            continue
    if not history:
        raise ValueError(f"FRED API: nessuna osservazione per {series_id}")
    return _payload(series_id, history[-260:], "FRED API")


def _fetch_via_graph_csv(series_id: str) -> dict[str, Any]:
    """Ultima spiaggia: spesso timeout — timeout aggressivo."""
    url = FRED_CSV.format(series_id=series_id)
    resp = get_with_retry(url, timeout=8, max_retries=0, soft_rate_limit=True)
    df = pd.read_csv(StringIO(resp.text))
    date_col = "DATE" if "DATE" in df.columns else (
        "observation_date" if "observation_date" in df.columns else df.columns[0]
    )
    val_col = [c for c in df.columns if c != date_col][0]
    df = df.rename(columns={date_col: "date", val_col: "value"})
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    history = df.tail(260).to_dict(orient="records")
    if not history:
        raise ValueError("CSV FRED vuoto")
    return _payload(series_id, history, "FRED graph CSV")


def fetch_fred_series(series_id: str, *, force: bool = False) -> dict[str, Any]:
    cache_name = f"fred_{series_id}"
    if not force and is_cache_fresh(cache_name):
        cached = load_json_cache(cache_name)
        # Se in cache c'è solo seed, riprova rete (a meno che non sia freschissima API)
        if cached and cached.get("source") not in (
            "seed_from_piano_strategia",
            None,
        ):
            if not str(cached.get("source", "")).startswith("seed"):
                logger.info("FRED %s da cache fresca (%s)", series_id, cached.get("source"))
                return cached
        if cached and cached.get("source") and "API" in str(cached.get("source")):
            return cached

    api_key = _resolve_api_key()
    errors = []

    if api_key:
        try:
            payload = _fetch_via_api(series_id, api_key)
            save_json_cache(cache_name, payload)
            logger.info("FRED %s via API ok", series_id)
            return payload
        except Exception as e:
            errors.append(f"API: {e}")
            logger.warning("FRED API %s fallito: %s", series_id, e)
            # Serie rimossa/inesistente: non perdere tempo sul CSV (timeout)
            if "does not exist" in str(e).lower() or "400" in str(e):
                pass
            else:
                try:
                    payload = _fetch_via_graph_csv(series_id)
                    save_json_cache(cache_name, payload)
                    return payload
                except Exception as e2:
                    errors.append(f"CSV: {e2}")
                    logger.warning("FRED CSV %s fallito: %s", series_id, e2)
    else:
        # Senza key NON martellare graph CSV (timeout 8s × N serie).
        # Gli alternate (Treasury/H15/CMV/TE) riempiono il bundle dopo.
        logger.info(
            "FRED %s: nessuna API key — skip CSV lento; userò alternate/seed",
            series_id,
        )
        errors.append("no_api_key")

    cached = load_json_cache(cache_name)
    if cached and cached.get("last_value") is not None:
        cached["note"] = "stale_cache_after_fetch_fail"
        return cached

    from .seed_series import seed_series

    seeded = seed_series(series_id)
    seeded["error"] = " | ".join(errors) if errors else "no_source"
    save_json_cache(cache_name, seeded)
    return seeded


def fetch_fred_bundle(*, force: bool = False) -> dict[str, Any]:
    """Scarica bundle settings + arricchisce con alternate sources."""
    settings = load_settings()
    series_map: dict = settings.get("fred_series", {})
    out: dict[str, Any] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "series": {},
        "api_key_present": bool(_resolve_api_key()),
    }

    for key, series_id in series_map.items():
        try:
            out["series"][key] = fetch_fred_series(series_id, force=force)
        except Exception as e:
            logger.error("Serie %s (%s): %s", key, series_id, e)
            from .seed_series import seed_series

            seeded = seed_series(series_id)
            seeded["error"] = str(e)
            out["series"][key] = seeded

    # Patch con alternate macro (Treasury / H15 / CMV / TE) se FRED è seed/mancante
    try:
        from .alt_macro import enrich_fred_bundle_with_alts

        out = enrich_fred_bundle_with_alts(out, force=force)
    except Exception as e:
        logger.warning("alt_macro enrich fallito: %s", e)

    save_json_cache("fred_bundle", out)
    return out


def latest_value(bundle: dict, key: str) -> Optional[float]:
    series = (bundle.get("series") or {}).get(key) or {}
    val = series.get("last_value")
    return float(val) if val is not None else None
