"""Pipeline: fetch web/cache → indicatori → scoring → presentation → bubble_state.json."""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config.env import load_env

load_env()

from data.ingestion.finra_margin import fetch_margin_debt
from data.ingestion.fred import fetch_fred_bundle
from data.ingestion.http_utils import CACHE_DIR, load_json_cache, save_json_cache
from data.ingestion.mag7_earnings import fetch_mag7_earnings
from data.ingestion.market_breadth import fetch_market_breadth
from data.ingestion.market_drawdown import fetch_spx_drawdown
from data.ingestion.nasdaq_quotes import fetch_mag7_nasdaq
from data.ingestion.news_feed import fetch_news_digest
from data.ingestion.nyfed_recession import fetch_recession_prob
from data.ingestion.sec_filings import fetch_mag7_8k
from data.ingestion.shiller_cape import fetch_cape
from data.ingestion.slickcharts_weights import fetch_sp500_weights
from data.ingestion.under_surface import build_under_surface
from data.ingestion.yahoo_prices import fetch_mag7_snapshot
from engine.indicators import assemble_indicators
from engine.presentation import enrich_state
from engine.scoring import build_scores

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

BUBBLE_STATE = 'bubble_state'


def _safe_fetch(
    fn: Callable[..., dict[str, Any]],
    cache_name: str,
    *,
    force: bool = False,
    label: str = '',
) -> dict[str, Any]:
    name = label or cache_name
    try:
        return fn(force=force)
    except Exception as exc:
        logger.warning('%s fallito: %s — fallback cache', name, exc)
        cached = load_json_cache(cache_name)
        if cached:
            return cached
        return {'error': str(exc), 'source': 'empty_fallback'}


def main(*, force: bool = False) -> dict[str, Any]:
    logger.info('Avvio engine (force=%s)', force)

    fred_bundle = _safe_fetch(fetch_fred_bundle, 'fred_bundle', force=force, label='FRED')
    cape = _safe_fetch(fetch_cape, 'shiller_cape', force=force, label='CAPE')
    margin = _safe_fetch(fetch_margin_debt, 'finra_margin', force=force, label='Margin/Z.1')
    weights = _safe_fetch(fetch_sp500_weights, 'sp500_weights', force=force, label='Slickcharts')
    mag7 = _safe_fetch(fetch_mag7_snapshot, 'mag7_snapshot', force=force, label='Mag7 Yahoo')
    nasdaq = _safe_fetch(fetch_mag7_nasdaq, 'mag7_nasdaq', force=force, label='Mag7 NASDAQ')
    earnings = _safe_fetch(fetch_mag7_earnings, 'mag7_earnings', force=force, label='Mag7 EPS')
    drawdown = _safe_fetch(fetch_spx_drawdown, 'spx_drawdown', force=force, label='SPX FRED')
    filings = _safe_fetch(fetch_mag7_8k, 'sec_mag7_8k', force=force, label='SEC 8-K')
    recession = _safe_fetch(fetch_recession_prob, 'nyfed_recession', force=force, label='NY Fed')
    news = _safe_fetch(fetch_news_digest, 'news_digest', force=force, label='News RSS')

    def _breadth(**kwargs):
        return fetch_market_breadth(
            force=force,
            constituents=weights.get('constituents_sample') or weights.get('top10') or [],
        )

    breadth = _safe_fetch(_breadth, 'market_breadth', force=force, label='Breadth SPY/RSP')

    filings_for_under = dict(filings)
    filings_for_under['earnings_bundle'] = earnings

    under = build_under_surface(
        weights=weights,
        news=news,
        drawdown=drawdown,
        nasdaq=nasdaq,
        filings=filings_for_under,
        breadth=breadth,
        force=True,
    )

    indicators = assemble_indicators(
        fred_bundle, cape, margin, mag7, news,
        recession=recession,
        weights=weights,
        under_surface=under,
    )
    # Blend rischio utili AI: news keyword + NASDAQ EPS surprise + SEC 8-K
    base = float(indicators.get('ai_earnings_risk') or 0)
    eps_r = earnings.get('ai_earnings_risk')
    sec_r = filings.get('ai_filings_risk')
    parts = [(base, 0.25)]
    if eps_r is not None:
        parts.append((float(eps_r), 0.55))
    if sec_r is not None:
        parts.append((float(sec_r), 0.20))
    wsum = sum(w for _, w in parts) or 1.0
    indicators['ai_earnings_risk'] = round(
        min(100.0, sum(v * w for v, w in parts) / wsum),
        1,
    )
    indicators['mag7_avg_eps_surprise_pct'] = earnings.get('avg_surprise_pct')
    indicators['mag7_eps_miss_count'] = earnings.get('miss_count')
    indicators['mag7_earnings_source'] = earnings.get('source')
    indicators['mag7_avg_dist_52w_high_pct'] = under.get('mag7_avg_dist_52w_high_pct')

    scores = build_scores(indicators)
    presentation = enrich_state(
        indicators, scores,
        fred_bundle=fred_bundle,
        cape=cape,
        recession=recession,
    )

    fred_sources = {
        k: (v or {}).get('source')
        for k, v in (fred_bundle.get('series') or {}).items()
    }
    state = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'indicators': indicators,
        **scores,
        **presentation,
        'under_surface': under,
        'data_quality': {
            'fred_api_key_present': bool(fred_bundle.get('api_key_present')),
            'fred_alts_used': fred_bundle.get('alts_used') or [],
            'fred_sources': fred_sources,
            'cape_source': cape.get('source'),
            'weights_source': weights.get('source'),
            'recession_source': recession.get('source'),
            'margin_source': margin.get('source'),
            'drawdown_source': drawdown.get('source'),
            'nasdaq_source': nasdaq.get('source'),
            'sec_source': filings.get('source'),
            'earnings_source': earnings.get('source'),
            'breadth_source': breadth.get('source'),
            'news_items': len((news.get('items') or [])),
            'news_tagged': news.get('tagged_count'),
            'news_score': news.get('news_risk_score'),
            'under_surface_source': under.get('source'),
            'buffett_note': (
                'CMV ~219% (metodologia Wilshire/GDP CMV). '
                'Il piano cita ~234% da altre stime — direzione uguale, livello diverso.'
            ),
        },
    }

    os.makedirs(CACHE_DIR, exist_ok=True)
    path = save_json_cache(BUBBLE_STATE, state)
    logger.info('Stato bolla salvato: %s', path)
    return state


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='SP500 Bubble Monitor — core engine')
    parser.add_argument('--force', action='store_true', help='Ignora cache fresca e riscarica')
    args = parser.parse_args()
    result = main(force=args.force)
    alert = result.get('alert') or {}
    dq = result.get('data_quality') or {}
    weak = [
        k for k, src in (dq.get('fred_sources') or {}).items()
        if src and 'seed' in str(src).lower()
    ]
    if dq.get('margin_source') and 'seed' in str(dq.get('margin_source')).lower():
        weak.append('margin_debt')
    print(json.dumps({
        'alert': alert.get('headline'),
        'one_liner': alert.get('one_liner'),
        'bubble_proximity': result.get('bubble_proximity'),
        'regime': result.get('regime'),
        'fragility_score': result.get('fragility_score'),
        'trigger_score': result.get('trigger_score'),
        'under_surface': {
            'dist_52w': (result.get('under_surface') or {}).get('dist_52w_high_pct'),
            'ytd': (result.get('under_surface') or {}).get('ytd_pct'),
            'mag7_avg_chg': (result.get('under_surface') or {}).get('mag7_avg_change_pct'),
            'margin_src': dq.get('margin_source'),
        },
        'data_quality': dq,
        'still_seed': weak,
        'hint': (
            None if dq.get('fred_api_key_present')
            else 'Imposta FRED_API_KEY in .env'
        ),
    }, ensure_ascii=False, indent=2))
