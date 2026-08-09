"""Assembla indicatori grezzi da cache/download in un unico bundle per lo scoring."""
from __future__ import annotations

from typing import Any, Optional

from data.ingestion.fred import latest_value
from data.ingestion.http_utils import load_settings

DEFAULT_SPX_MCAP_USD = 52e12


def _to_basis_points(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    v = float(value)
    if abs(v) < 50.0:
        return round(v * 100.0, 1)
    return round(v, 1)


def compute_buffett(fred_bundle: dict) -> tuple[Optional[float], str]:
    """
    Buffett = market cap / GDP in %.
    Nota: FRED DDDM01USA156NWDB (World Bank) è annuale e può essere ferma a anni fa.
    Se la serie nel bundle arriva da CMV (current), usiamo quella.
    """
    series = (fred_bundle.get('series') or {}).get('buffett_indicator') or {}
    direct = series.get('last_value')
    src = str(series.get('source') or '')
    if direct is not None:
        val = float(direct)
        if val < 10:
            val *= 100.0
        label = src if src else 'FRED DDDM01USA156NWDB'
        if 'currentmarketvaluation' in src.lower() or 'cmv' in src.lower():
            label = 'currentmarketvaluation.com (live)'
        elif 'FRED' in src:
            label = f"FRED DDDM01USA156NWDB ({series.get('last_date')})"
        return round(val, 1), label
    return None, 'missing'


def estimate_mag7_weight(mag7: dict, weights: dict) -> Optional[float]:
    if weights and weights.get('mag7_weight_pct') is not None:
        return float(weights['mag7_weight_pct'])
    if mag7 and mag7.get('mag7_weight_pct') is not None:
        return float(mag7['mag7_weight_pct'])
    combined = (mag7 or {}).get('mag7_combined_mcap')
    if combined and float(combined) > 0:
        return round(float(combined) / DEFAULT_SPX_MCAP_USD * 100.0, 1)
    return None


def estimate_ai_earnings_risk(news: dict[str, Any]) -> float:
    tallies = news.get('tallies') or {}
    hits = int(tallies.get('ai_earnings', 0))
    credit = int(tallies.get('credit_stress', 0))
    fed = int(tallies.get('fed_hawkish', 0))
    raw = 20.0 + hits * 10.0 + credit * 4.0 + fed * 2.0
    return round(min(100.0, max(0.0, raw)), 1)


def assemble_indicators(
    fred_bundle: dict[str, Any],
    cape: dict[str, Any],
    margin: dict[str, Any],
    mag7: dict[str, Any],
    news: dict[str, Any],
    *,
    recession: Optional[dict[str, Any]] = None,
    weights: Optional[dict[str, Any]] = None,
    under_surface: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    settings = load_settings()
    thr = settings.get('thresholds', {})
    recession = recession or {}
    weights = weights or {}
    under_surface = under_surface or {}

    hy_raw = latest_value(fred_bundle, 'hy_oas')
    curve_raw = latest_value(fred_bundle, 'yield_curve_2s10s')
    fed_funds = latest_value(fred_bundle, 'fed_funds')
    household = latest_value(fred_bundle, 'household_equity_pct')
    buffett, buffett_src = compute_buffett(fred_bundle)

    yield_bp = _to_basis_points(curve_raw)
    mag7_weight = estimate_mag7_weight(mag7, weights)
    top10 = weights.get('top10_weight_pct')

    rec_prob = recession.get('probability_pct')
    if rec_prob is None:
        # euristica residua da curva
        bp = yield_bp or 0.0
        if bp < 0:
            rec_prob = min(60.0, 28.0 + abs(bp) * 0.75)
        elif bp < 75:
            rec_prob = 18.0 + (75.0 - bp) * 0.12
        else:
            rec_prob = max(8.0, 22.0 - (bp - 75.0) * 0.08)
        rec_prob = round(rec_prob, 1)

    return {
        'cape': cape.get('cape'),
        'cape_as_of': cape.get('as_of'),
        'cape_source': cape.get('source'),
        'cape_history': cape.get('history') or [],
        'buffett_pct': buffett,
        'buffett_source': buffett_src,
        'household_equity_pct': household,
        'mag7_weight_pct': mag7_weight,
        'top10_weight_pct': top10,
        'top10': weights.get('top10') or [],
        'mag7_combined_mcap': mag7.get('mag7_combined_mcap'),
        'margin_debt_yoy_pct': margin.get('yoy_pct'),
        'margin_debit_billion': margin.get('debit_balances_billion'),
        'margin_as_of': margin.get('as_of'),
        'margin_source': margin.get('source'),
        'hy_oas_bp': _to_basis_points(hy_raw),
        'yield_curve_2s10s_bp': yield_bp,
        'yield_curve_2s10s_pct': curve_raw,
        'recession_prob_pct': rec_prob,
        'recession_source': recession.get('source'),
        'fed_funds_pct': fed_funds,
        'ai_earnings_risk': estimate_ai_earnings_risk(news),
        'news': news,
        'news_risk_score': news.get('news_risk_score'),
        'concentration_stress_0_100': under_surface.get('concentration_stress_0_100'),
        'dist_52w_high_pct': under_surface.get('dist_52w_high_pct'),
        'ytd_pct': under_surface.get('ytd_pct'),
        'max_drawdown_1y_pct': under_surface.get('max_drawdown_1y_pct'),
        'mag7_avg_change_pct': under_surface.get('mag7_avg_change_pct'),
        'under_surface': under_surface,
        'thresholds_ref': thr,
        'fred_series_sources': {
            k: (v or {}).get('source')
            for k, v in (fred_bundle.get('series') or {}).items()
        },
        'sources': {
            'fred_updated_at': fred_bundle.get('updated_at'),
            'fred_api_key_present': bool(fred_bundle.get('api_key_present')),
            'fred_alts_used': fred_bundle.get('alts_used') or [],
            'cape_updated_at': cape.get('updated_at'),
            'margin_updated_at': margin.get('updated_at'),
            'mag7_updated_at': mag7.get('updated_at'),
            'weights_updated_at': weights.get('updated_at'),
            'recession_updated_at': recession.get('updated_at'),
            'news_updated_at': news.get('updated_at'),
            'cape_source': cape.get('source'),
            'weights_source': weights.get('source'),
            'recession_source': recession.get('source'),
            'buffett_source': buffett_src,
            'under_surface_source': under_surface.get('source'),
        },
    }
