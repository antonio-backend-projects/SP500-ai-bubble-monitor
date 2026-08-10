"""Pesi S&P 500 da Slickcharts — concentrazione Mag7 / Top10 automatica."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from .http_utils import (
    get_with_retry,
    is_cache_fresh,
    load_json_cache,
    load_settings,
    save_json_cache,
)

logger = logging.getLogger(__name__)

URL = 'https://www.slickcharts.com/sp500'

# Alias ticker (GOOGL/GOOG)
ALIASES = {
    'GOOG': 'GOOGL',
    'BRK.B': 'BRK.B',
    'BRK-B': 'BRK.B',
}


def _parse_weights(html: str) -> list[dict[str, Any]]:
    rows = []
    # Righe tabella: Symbol ... Weight
    pattern = re.compile(
        r'href="/symbol/([A-Z0-9.\-]+)"[^>]*>\s*\1\s*</a>.*?'
        r'<td[^>]*>\s*([0-9]+\.[0-9]+)\s*</td>\s*</tr>',
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(html):
        sym = m.group(1).upper().replace('-', '.')
        sym = ALIASES.get(sym, sym)
        rows.append({'ticker': sym, 'weight_pct': float(m.group(2))})

    if rows:
        return rows

    # Fallback più permissivo: sequenze ticker + percentuale
    loose = re.findall(
        r'/symbol/([A-Z]{1,5}(?:\.[A-Z])?).*?([0-9]{1,2}\.[0-9]{1,4})\s*%?',
        html,
        re.I | re.S,
    )
    seen = set()
    for sym, w in loose:
        sym = sym.upper().replace('-', '.')
        sym = ALIASES.get(sym, sym)
        if sym in seen:
            continue
        seen.add(sym)
        rows.append({'ticker': sym, 'weight_pct': float(w)})
        if len(rows) >= 50:
            break
    return rows


def fetch_sp500_weights(*, force: bool = False) -> dict[str, Any]:
    cache_name = 'sp500_weights'
    if not force and is_cache_fresh(cache_name, max_age_hours=24):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    settings = load_settings()
    mag7 = {t.upper() for t in settings.get('mag7', [])}
    # GOOGL conta anche GOOG
    mag7.add('GOOG')

    try:
        resp = get_with_retry(URL, timeout=30)
        rows = _parse_weights(resp.text)
        if len(rows) < 7:
            raise ValueError(f'Slickcharts: solo {len(rows)} pesi parsati')

        top10 = rows[:10]
        top10_weight = round(sum(r['weight_pct'] for r in top10), 2)
        mag7_weight = round(
            sum(r['weight_pct'] for r in rows if r['ticker'] in mag7 or (
                r['ticker'] == 'GOOGL' and 'GOOGL' in mag7
            )),
            2,
        )
        # Unisci GOOG+GOOGL se entrambi
        goog = sum(r['weight_pct'] for r in rows if r['ticker'] in ('GOOG', 'GOOGL'))
        others = sum(
            r['weight_pct'] for r in rows
            if r['ticker'] in mag7 and r['ticker'] not in ('GOOG', 'GOOGL')
        )
        if goog or others:
            mag7_weight = round(others + goog, 2)

        payload = {
            'top10': top10,
            'top10_weight_pct': top10_weight,
            'mag7_weight_pct': mag7_weight,
            'constituents_sample': rows[:50],
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'source': 'slickcharts.com/sp500',
        }
        save_json_cache(cache_name, payload)
        return payload
    except Exception as e:
        logger.warning('Slickcharts fallito: %s', e)
        cached = load_json_cache(cache_name)
        if cached:
            return cached
        # Seed piano-strategia
        seed = {
            'top10_weight_pct': 38.0,
            'mag7_weight_pct': 35.0,
            'top10': [],
            'constituents_sample': [],
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'source': 'seed_from_piano_strategia',
            'error': str(e),
        }
        save_json_cache(cache_name, seed)
        return seed
