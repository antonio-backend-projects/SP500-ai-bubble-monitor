"""
Margin debt FINRA (debit balances) + fallback FRED Z.1 + seed.

Priorità (testate 2026-08-10, IP-safe):
1. Pagina ufficiale FINRA margin-statistics (tabella HTML, HTTP 200)
2. Mirror CSV thetrading.tools (stessa serie, con YoY già calcolato)
3. FRED Z.1 proxy (metodologia diversa — non sostituisce FINRA)
4. Seed da piano-strategia
"""
from __future__ import annotations

import csv
import io
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

FINRA_PAGE = (
    "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
)
MIRROR_CSV = "https://www.thetrading.tools/data/indicators/margin-debt.csv"

MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

SEED_MARGIN = {
    "as_of": "2026-06-01",
    "debit_balances_billion": 1530.0,
    "credit_balances_billion": -1060.0,
    "free_credit_cash_billion": None,
    "free_credit_margin_billion": None,
    "yoy_pct": 51.5,
    "source": "seed_from_piano_strategia",
}

ROW_RE = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{2})\s+"
    r"([0-9,]+)\s+([0-9,]+)\s+([0-9,]+)",
    re.I,
)


def _millions_to_billions(raw: str | float) -> float:
    num = float(str(raw).replace(",", ""))
    # FINRA pubblica in milioni USD
    return round(num / 1000.0, 2)


def _yoy_from_history(history: list[dict[str, Any]]) -> Optional[float]:
    if len(history) < 13:
        # prova comunque stesso mese anno prima se presente
        pass
    last = history[-1]
    last_date = str(last.get("date") or "")
    if len(last_date) < 7:
        return None
    try:
        y = int(last_date[:4])
        m = last_date[5:7]
        target = f"{y - 1}-{m}"
        prev = [h for h in history if str(h.get("date", "")).startswith(target)]
        if not prev:
            return None
        a = float(last["debit_balances_billion"])
        b = float(prev[-1]["debit_balances_billion"])
        if b:
            return round((a / b - 1.0) * 100.0, 1)
    except Exception:
        return None
    return None


def _payload_from_rows(
    rows: list[dict[str, Any]],
    *,
    source: str,
) -> Optional[dict[str, Any]]:
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: str(r.get("date") or ""))
    last = rows[-1]
    yoy = last.get("yoy_pct")
    if yoy is None:
        yoy = _yoy_from_history(rows)
    cash = last.get("free_credit_cash_billion")
    marg = last.get("free_credit_margin_billion")
    credit_net = None
    if cash is not None and marg is not None:
        # piano: credit balances a minimo storico negativo (debit - free credits)
        credit_net = round(float(cash) + float(marg) - float(last["debit_balances_billion"]), 2)
    return {
        "as_of": last.get("date"),
        "debit_balances_billion": float(last["debit_balances_billion"]),
        "free_credit_cash_billion": cash,
        "free_credit_margin_billion": marg,
        "credit_balances_billion": credit_net,
        "yoy_pct": yoy,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "history": [
            {
                "date": r.get("date"),
                "debit_balances_billion": r.get("debit_balances_billion"),
                "yoy_pct": r.get("yoy_pct"),
            }
            for r in rows[-120:]
        ],
    }


def fetch_finra_from_page(*, force: bool = False) -> dict[str, Any]:
    cache_name = "finra_margin_official"
    if not force and is_cache_fresh(cache_name, max_age_hours=48):
        cached = load_json_cache(cache_name)
        if cached and cached.get("debit_balances_billion"):
            return cached

    session = get_session()
    rate_limit(soft=True)
    headers = random_headers()
    headers["Referer"] = "https://www.google.com/"
    resp = session.get(FINRA_PAGE, timeout=25, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"FINRA page HTTP {resp.status_code}")

    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = re.sub(r"\s+", " ", text)
    rows: list[dict[str, Any]] = []
    for m in ROW_RE.finditer(text):
        mon, yy, debit, cash, credit_m = m.groups()
        month = MONTHS[mon.lower()[:3]]
        year = 2000 + int(yy)
        rows.append(
            {
                "date": f"{year:04d}-{month:02d}-01",
                "debit_balances_billion": _millions_to_billions(debit),
                "free_credit_cash_billion": _millions_to_billions(cash),
                "free_credit_margin_billion": _millions_to_billions(credit_m),
            }
        )
    # dedupe by date keeping last
    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        by_date[r["date"]] = r
    payload = _payload_from_rows(list(by_date.values()), source="FINRA.org margin-statistics (official table)")
    if not payload:
        raise RuntimeError("FINRA page: nessuna riga debit parsata")
    save_json_cache(cache_name, payload)
    logger.info(
        "FINRA official ok: $%sB YoY=%s as_of=%s",
        payload["debit_balances_billion"],
        payload.get("yoy_pct"),
        payload.get("as_of"),
    )
    return payload


def fetch_finra_from_mirror_csv(*, force: bool = False) -> dict[str, Any]:
    cache_name = "finra_margin_mirror_csv"
    if not force and is_cache_fresh(cache_name, max_age_hours=48):
        cached = load_json_cache(cache_name)
        if cached and cached.get("debit_balances_billion"):
            return cached

    session = get_session()
    rate_limit(soft=True)
    headers = random_headers()
    headers["Accept"] = "text/csv,*/*"
    resp = session.get(MIRROR_CSV, timeout=20, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Mirror CSV HTTP {resp.status_code}")
    reader = csv.DictReader(io.StringIO(resp.text))
    rows: list[dict[str, Any]] = []
    for row in reader:
        try:
            debit_m = float(row["debit_balances"])
            yoy = float(row["debit_yoy"]) if row.get("debit_yoy") not in (None, "") else None
            cash = float(row["free_credit_cash"]) if row.get("free_credit_cash") not in (None, "") else None
            cred = float(row["free_credit_margin"]) if row.get("free_credit_margin") not in (None, "") else None
        except (KeyError, ValueError):
            continue
        rows.append(
            {
                "date": str(row.get("date") or "")[:10],
                "debit_balances_billion": round(debit_m / 1000.0, 2),
                "yoy_pct": yoy,
                "free_credit_cash_billion": round(cash / 1000.0, 2) if cash is not None else None,
                "free_credit_margin_billion": round(cred / 1000.0, 2) if cred is not None else None,
            }
        )
    payload = _payload_from_rows(
        rows,
        source="thetrading.tools margin-debt.csv (FINRA mirror)",
    )
    if not payload:
        raise RuntimeError("Mirror CSV vuoto")
    save_json_cache(cache_name, payload)
    logger.info(
        "FINRA mirror CSV ok: $%sB YoY=%s",
        payload["debit_balances_billion"],
        payload.get("yoy_pct"),
    )
    return payload


def fetch_margin_debt(*, force: bool = False) -> dict[str, Any]:
    cache_name = "finra_margin"
    if not force and is_cache_fresh(cache_name, max_age_hours=48):
        cached = load_json_cache(cache_name)
        src = str((cached or {}).get("source") or "").lower()
        if cached and "seed" not in src and "z.1" not in src and "proxy" not in src:
            return cached

    errors: list[str] = []

    # 1) FINRA ufficiale
    try:
        official = fetch_finra_from_page(force=force)
        save_json_cache(cache_name, official)
        return official
    except Exception as e:
        errors.append(f"FINRA page: {e}")
        logger.warning("FINRA official fallito: %s", e)

    # 2) Mirror CSV
    try:
        mirror = fetch_finra_from_mirror_csv(force=force)
        save_json_cache(cache_name, mirror)
        return mirror
    except Exception as e:
        errors.append(f"mirror CSV: {e}")
        logger.warning("FINRA mirror CSV fallito: %s", e)

    # 3) FRED Z.1 proxy
    try:
        from .fred_margin import fetch_margin_from_fred

        fred_m = fetch_margin_from_fred(force=force)
        save_json_cache(cache_name, fred_m)
        return fred_m
    except Exception as e:
        errors.append(f"FRED Z.1: {e}")
        logger.warning("FRED margin Z.1 fallito: %s", e)

    cached = load_json_cache(cache_name)
    if cached:
        return cached

    seed = dict(SEED_MARGIN)
    seed["updated_at"] = datetime.now(timezone.utc).isoformat()
    seed["error"] = "; ".join(errors)
    save_json_cache(cache_name, seed)
    return seed
