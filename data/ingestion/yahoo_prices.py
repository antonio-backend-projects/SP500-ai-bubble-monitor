"""Prezzi Yahoo v8/chart — no yfinance (anti-ban).

Mag7 Yahoo è OPZIONALE: i pesi sull'indice arrivano da Slickcharts.
Su IP già rate-limited (401/429) usiamo cache e usciamo subito.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

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

YAHOO_QUOTE = (
    'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}'
    '?range=5d&interval=1d&_t={cb}'
)


class YahooBlocked(RuntimeError):
    """Yahoo ha risposto 401/403/429 — stop immediato, niente martellate."""


def _warm_yahoo_session() -> None:
    session = get_session()
    try:
        rate_limit(soft=True)
        session.get('https://fc.yahoo.com', timeout=8, headers=random_headers())
    except Exception as e:
        logger.debug('Yahoo cookie warm-up fallito: %s', e)


def _parse_last_close(payload: dict) -> Optional[float]:
    result = (payload.get('chart') or {}).get('result') or []
    if not result:
        return None
    quote = (result[0].get('indicators') or {}).get('quote') or [{}]
    closes = quote[0].get('close') or []
    for c in reversed(closes):
        if c is not None:
            return float(c)
    meta = result[0].get('meta') or {}
    px = meta.get('regularMarketPrice')
    return float(px) if px is not None else None


def _check_blocked(status: int, ticker: str) -> None:
    if status in (401, 403, 429):
        raise YahooBlocked(f'Yahoo HTTP {status} su {ticker} — skip Mag7 Yahoo')


def fetch_quote(ticker: str, *, force: bool = False) -> dict[str, Any]:
    cache_name = f'yahoo_{ticker.lower()}'
    if not force and is_cache_fresh(cache_name):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    try:
        _warm_yahoo_session()
        url = YAHOO_QUOTE.format(ticker=ticker, cb=int(time.time() * 1000))
        # 1 solo tentativo: su 429 i retry peggiorano il ban
        session = get_session()
        rate_limit(soft=True)
        resp = session.get(url, timeout=12, headers=random_headers())
        _check_blocked(resp.status_code, ticker)
        if resp.status_code != 200:
            raise ConnectionError(f'HTTP {resp.status_code}')
        data = resp.json()
        close = _parse_last_close(data)
        result = (data.get('chart') or {}).get('result') or [{}]
        meta = result[0].get('meta') or {}
        payload = {
            'ticker': ticker,
            'price': close,
            'currency': meta.get('currency'),
            'exchange': meta.get('exchangeName'),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'source': 'Yahoo v8/chart',
        }
        save_json_cache(cache_name, payload)
        return payload
    except YahooBlocked:
        raise
    except Exception as e:
        logger.warning('Yahoo %s fallito: %s', ticker, e)
        cached = load_json_cache(cache_name)
        if cached:
            return cached
        raise


def fetch_quotes(tickers: list[str], *, force: bool = False) -> dict[str, dict]:
    out = {}
    for t in tickers:
        try:
            out[t] = fetch_quote(t, force=force)
        except YahooBlocked as e:
            logger.warning('%s', e)
            out[t] = {'ticker': t, 'price': None, 'error': str(e)}
            break
        except Exception as e:
            out[t] = {'ticker': t, 'price': None, 'error': str(e)}
    return out


def fetch_mag7_snapshot(*, force: bool = False) -> dict[str, Any]:
    """
    Snapshot prezzi Mag7 — NON necessario per il peso sull'indice
    (quello arriva da Slickcharts). Disabilitabile da settings.
    """
    cache_name = 'mag7_snapshot'
    settings = load_settings()
    if not settings.get('fetch_yahoo_mag7', False):
        cached = load_json_cache(cache_name) or {}
        logger.info('Yahoo Mag7 disabilitato (fetch_yahoo_mag7=false) — uso Slickcharts per i pesi')
        return {
            'mag7': list(settings.get('mag7', [])),
            'prices': cached.get('prices') or {},
            'market_caps': cached.get('market_caps') or {},
            'mag7_combined_mcap': cached.get('mag7_combined_mcap'),
            'mag7_weight_pct': None,
            'skipped': True,
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'source': 'skipped_yahoo_use_slickcharts',
        }

    if not force and is_cache_fresh(cache_name):
        cached = load_json_cache(cache_name)
        if cached:
            return cached

    mag7 = list(settings.get('mag7', []))
    index_proxy = settings.get('index_proxy', 'SPY')
    names = mag7 + [index_proxy]
    quotes: dict[str, Any] = {}
    mcaps: dict[str, Any] = {}

    try:
        _warm_yahoo_session()
    except Exception:
        pass

    blocked = False
    for t in names:
        if blocked:
            quotes[t] = None
            mcaps[t] = None
            continue
        try:
            url = (
                f'https://query2.finance.yahoo.com/v10/finance/quoteSummary/{t}'
                f'?modules=price&_t={int(time.time()*1000)}'
            )
            rate_limit(soft=True)
            resp = get_session().get(url, timeout=12, headers=random_headers())
            _check_blocked(resp.status_code, t)
            if resp.status_code != 200:
                raise ConnectionError(f'HTTP {resp.status_code}')
            js = resp.json()
            result = ((js.get('quoteSummary') or {}).get('result') or [None])[0] or {}
            price_mod = result.get('price') or {}
            mcap = (price_mod.get('marketCap') or {}).get('raw')
            px = (price_mod.get('regularMarketPrice') or {}).get('raw')
            quotes[t] = float(px) if px is not None else None
            mcaps[t] = float(mcap) if mcap is not None else None
        except YahooBlocked as e:
            logger.warning('%s — interrompo Mag7 Yahoo', e)
            blocked = True
            quotes[t] = None
            mcaps[t] = None
        except Exception as e:
            logger.warning('quoteSummary %s: %s — nessun retry chart (anti-429)', t, e)
            cached_q = load_json_cache(f'yahoo_{t.lower()}')
            quotes[t] = (cached_q or {}).get('price')
            mcaps[t] = None

    if blocked:
        cached = load_json_cache(cache_name)
        if cached:
            cached['note'] = 'Yahoo blocked — restituita cache precedente'
            return cached

    mag7_mcap = sum(v for k, v in mcaps.items() if k in mag7 and v)
    payload = {
        'mag7': mag7,
        'prices': quotes,
        'market_caps': mcaps,
        'mag7_combined_mcap': mag7_mcap if mag7_mcap else None,
        'mag7_weight_pct': None,
        'spy_mcap': mcaps.get(index_proxy),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'Yahoo quoteSummary' if not blocked else 'yahoo_blocked',
    }
    save_json_cache(cache_name, payload)
    return payload
