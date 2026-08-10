"""CAPE di Shiller — XLS Yale, rifiuta stale, fallback multpl (live)."""
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

SHILLER_URLS = [
    'https://img1.wsimg.com/blobby/go/e5e77e0b-5bb0-4550-aafe-ff29b3994f5a/downloads/ie_data.xls',
    'http://www.econ.yale.edu/~shiller/data/ie_data.xls',
]

SEED_CAPE = {
    'cape': 41.9,
    'as_of': '2026-08-01',
    'source': 'seed_from_piano_strategia',
}

# Se as_of è più vecchio di N mesi, il CAPE non è usabile come "live"
MAX_CAPE_AGE_DAYS = 120


def _parse_as_of(as_of: Optional[str]) -> Optional[datetime]:
    if not as_of:
        return None
    try:
        return datetime.fromisoformat(str(as_of)[:10]).replace(tzinfo=timezone.utc)
    except Exception:
        return None


def is_cape_stale(payload: Optional[dict[str, Any]], *, max_age_days: int = MAX_CAPE_AGE_DAYS) -> bool:
    if not payload or payload.get('cape') is None:
        return True
    src = str(payload.get('source') or '').lower()
    if 'seed' in src:
        return True
    dt = _parse_as_of(payload.get('as_of'))
    if dt is None:
        return True
    age = datetime.now(timezone.utc) - dt
    return age.days > max_age_days


def _extract_cape_from_xls(content: bytes) -> Optional[dict[str, Any]]:
    try:
        df = pd.read_excel(BytesIO(content), sheet_name='Data', header=None)
    except Exception:
        return None

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


def _try_multpl(*, force: bool = False) -> Optional[dict[str, Any]]:
    try:
        from .multpl_cape import fetch_multpl_cape

        multpl = fetch_multpl_cape(force=force)
        if multpl.get('cape') is not None and not is_cape_stale(multpl):
            return multpl
    except Exception as e:
        logger.warning('Fallback multpl fallito: %s', e)
    return None


def fetch_cape(*, force: bool = False) -> dict[str, Any]:
    cache_name = 'shiller_cape'

    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached and not is_cape_stale(cached):
            return cached
        # cache "fresca" ma CAPE as_of vecchio → prova multpl subito
        multpl = _try_multpl(force=True)
        if multpl:
            multpl['fallback_of'] = 'stale_shiller_cache'
            save_json_cache(cache_name, multpl)
            logger.info('CAPE: usata multpl (cache Shiller stale as_of=%s)', (cached or {}).get('as_of'))
            return multpl

    last_err = None
    for url in SHILLER_URLS:
        try:
            resp = get_with_retry(url, timeout=40)
            parsed = _extract_cape_from_xls(resp.content)
            if not parsed:
                raise ValueError('Impossibile estrarre CAPE dal file')
            if is_cape_stale(parsed):
                logger.warning(
                    'CAPE Shiller scaricato ma stale (as_of=%s) — provo multpl',
                    parsed.get('as_of'),
                )
                multpl = _try_multpl(force=True)
                if multpl:
                    multpl['fallback_of'] = 'stale_shiller_xls'
                    multpl['shiller_stale_as_of'] = parsed.get('as_of')
                    # tieni history Shiller se utile
                    if parsed.get('history') and not multpl.get('history'):
                        multpl['history'] = parsed['history']
                    save_json_cache(cache_name, multpl)
                    return multpl
            parsed['updated_at'] = datetime.now(timezone.utc).isoformat()
            save_json_cache(cache_name, parsed)
            return parsed
        except Exception as e:
            last_err = e
            logger.warning('CAPE download fallito (%s): %s', url, e)

    multpl = _try_multpl(force=True)
    if multpl:
        multpl['fallback_of'] = 'shiller_xls_failed'
        save_json_cache(cache_name, multpl)
        return multpl

    cached = load_json_cache(cache_name)
    if cached and not is_cape_stale(cached):
        return cached

    seed = dict(SEED_CAPE)
    seed['updated_at'] = datetime.now(timezone.utc).isoformat()
    seed['error'] = str(last_err)
    save_json_cache(cache_name, seed)
    return seed
