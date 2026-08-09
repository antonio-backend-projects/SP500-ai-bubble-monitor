"""CAPE di Shiller — download dataset Yale (xls/csv) con fallback cache/seed."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Optional

import pandas as pd

from .http_utils import (
    get_with_retry,
    is_cache_fresh,
    load_json_cache,
    save_json_cache,
)

logger = logging.getLogger(__name__)

# Dataset ufficiale Robert Shiller
SHILLER_URLS = [
    'https://img1.wsimg.com/blobby/go/e5e77e0b-5bb0-4550-aafe-ff29b3994f5a/downloads/ie_data.xls',
    'http://www.econ.yale.edu/~shiller/data/ie_data.xls',
]

# Seed dal piano-strategia (inizio agosto 2026)
SEED_CAPE = {
    'cape': 41.9,
    'as_of': '2026-08-01',
    'source': 'seed_from_piano_strategia',
}


def _extract_cape_from_xls(content: bytes) -> Optional[dict[str, Any]]:
    try:
        df = pd.read_excel(BytesIO(content), sheet_name='Data', header=None)
    except Exception:
        # openpyxl/xlrd mancante o formato diverso
        return None

    # Cerca riga header con "CAPE" o "P/E10"
    cape_col = None
    date_col = 0
    header_row = None
    for i in range(min(20, len(df))):
        row = [str(x).strip().lower() if pd.notna(x) else '' for x in df.iloc[i].tolist()]
        for j, cell in enumerate(row):
            if 'cape' in cell or cell in ('p/e10', 'pe10'):
                cape_col = j
                header_row = i
                break
        if cape_col is not None:
            break
    if cape_col is None:
        # Layout classico Shiller: colonna CAPE spesso index 12-13
        cape_col = 12
        header_row = 6

    def _try_col(col: int) -> list[dict]:
        values = []
        for i in range((header_row or 0) + 1, len(df)):
            raw_date = df.iloc[i, date_col]
            raw_cape = df.iloc[i, col] if col < df.shape[1] else None
            if pd.isna(raw_cape):
                continue
            try:
                cape = float(raw_cape)
            except (TypeError, ValueError):
                continue
            # CAPE reale è tipicamente 5–80; scarta colonne sbagliate (ratio, decimali)
            if not (5.0 <= cape <= 80.0):
                continue
            as_of = None
            try:
                if isinstance(raw_date, (int, float)):
                    year = int(raw_date)
                    month = int(round((raw_date - year) * 100)) or 1
                    month = min(max(month, 1), 12)
                    as_of = f'{year:04d}-{month:02d}-01'
                else:
                    as_of = str(pd.to_datetime(raw_date).date())
            except Exception:
                as_of = None
            values.append({'date': as_of, 'cape': cape})
        return values

    values = _try_col(cape_col)
    if len(values) < 20:
        # Prova colonne vicine tipiche del file Shiller
        for alt in (12, 13, 10, 11, 14, 15):
            if alt == cape_col:
                continue
            cand = _try_col(alt)
            if len(cand) > len(values):
                values = cand
                cape_col = alt

    if not values:
        return None
    last = values[-1]
    return {
        'cape': float(last['cape']),
        'as_of': last.get('date'),
        'history': values[-120:],
        'source': 'Shiller ie_data.xls',
    }


def fetch_cape(*, force: bool = False) -> dict[str, Any]:
    cache_name = 'shiller_cape'
    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    last_err = None
    for url in SHILLER_URLS:
        try:
            resp = get_with_retry(url, timeout=40)
            parsed = _extract_cape_from_xls(resp.content)
            if not parsed:
                raise ValueError('Impossibile estrarre CAPE dal file')
            parsed['updated_at'] = datetime.now(timezone.utc).isoformat()
            save_json_cache(cache_name, parsed)
            return parsed
        except Exception as e:
            last_err = e
            logger.warning('CAPE download fallito (%s): %s', url, e)

    cached = load_json_cache(cache_name)
    if cached:
        return cached

    # Fallback web: multpl.com
    try:
        from .multpl_cape import fetch_multpl_cape

        multpl = fetch_multpl_cape(force=force)
        if multpl.get('cape') is not None:
            multpl['fallback_of'] = 'shiller_xls'
            save_json_cache(cache_name, multpl)
            return multpl
    except Exception as e:
        logger.warning('Fallback multpl fallito: %s', e)

    seed = dict(SEED_CAPE)
    seed['updated_at'] = datetime.now(timezone.utc).isoformat()
    seed['error'] = str(last_err)
    save_json_cache(cache_name, seed)
    return seed
