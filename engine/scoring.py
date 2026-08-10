"""Scoring fragilità vs innesco — logica da piano-strategia.md."""
from __future__ import annotations

from typing import Any, Optional

from data.ingestion.http_utils import load_settings

WATCH_ORDER = [
    {
        'rank': 1,
        'theme': 'Fed restrittiva',
        'detail': (
            'Sorpresa hawkish o rialzi — variabile che storicamente '
            'ha bucato la bolla del 2000.'
        ),
    },
    {
        'rank': 2,
        'theme': 'Stress credito',
        'detail': (
            'Allargamento HY OAS oltre soglia tardo-ciclo; '
            'il credito precede spesso i crolli azionari.'
        ),
    },
    {
        'rank': 3,
        'theme': 'Utili AI / Mag7',
        'detail': (
            'Delusione earnings sui nomi che reggono l\'indice; '
            'concentrazione amplifica l\'impatto.'
        ),
    },
]


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _lerp_score(
    value: Optional[float],
    low: float,
    high: float,
    *,
    invert: bool = False,
) -> float:
    """Mappa value in [low, high] → punteggio 0–100."""
    if value is None:
        return 50.0
    if high == low:
        return 50.0
    t = (float(value) - low) / (high - low)
    t = _clamp(t, 0.0, 1.0)
    score = t * 100.0
    return (100.0 - score) if invert else score


def score_cape(cape: Optional[float], thresholds: dict) -> float:
    median = float(thresholds.get('median', 16.0))
    dotcom = float(thresholds.get('dotcom', 44.0))
    return round(_lerp_score(cape, median, dotcom), 1)


def score_buffett(pct: Optional[float], thresholds: dict) -> float:
    fire = float(thresholds.get('fire', 200.0))
    extreme = float(thresholds.get('extreme', 230.0))
    return round(_lerp_score(pct, fire - 40.0, extreme), 1)


def score_household(pct: Optional[float], thresholds: dict) -> float:
    dotcom = float(thresholds.get('dotcom', 38.7))
    extreme = float(thresholds.get('extreme', 45.0))
    return round(_lerp_score(pct, dotcom - 5.0, extreme + 2.0), 1)


def score_concentration(weight_pct: Optional[float], thresholds: dict) -> float:
    elevated = float(thresholds.get('elevated', 25.0))
    extreme = float(thresholds.get('extreme', 33.0))
    return round(_lerp_score(weight_pct, elevated, extreme + 5.0), 1)


def score_margin(yoy_pct: Optional[float], thresholds: dict) -> float:
    elevated = float(thresholds.get('elevated', 20.0))
    extreme = float(thresholds.get('extreme', 40.0))
    return round(_lerp_score(yoy_pct, elevated, extreme + 15.0), 1)


def score_margin_level(billion: Optional[float], thresholds: dict) -> float:
    """Livello debit/proxy in $B (scala FINRA-like; su Z.1 è solo indicativo)."""
    elevated = float(thresholds.get('elevated', 800.0))
    extreme = float(thresholds.get('extreme', 1400.0))
    return round(_lerp_score(billion, elevated * 0.55, extreme), 1)


def score_margin_combined(
    yoy_pct: Optional[float],
    billion: Optional[float],
    *,
    yoy_thr: dict,
    level_thr: dict,
    source: str = '',
) -> float:
    """
    Blend YoY + livello.
    Se la fonte è proxy Z.1 (≠ FINRA), il YoY basso non deve azzerare tutto:
    peso minore sul YoY e tetto sul contributo del pezzo.
    """
    yoy_s = score_margin(yoy_pct, yoy_thr)
    lvl_s = score_margin_level(billion, level_thr)
    src = (source or '').lower()
    is_proxy = 'z.1' in src or 'proxy' in src or 'bogz1' in src
    if is_proxy:
        # Z.1: privilegia il max tra YoY e livello (scala diversa da FINRA)
        return round(max(yoy_s, lvl_s * 0.85), 1)
    return round(0.65 * yoy_s + 0.35 * lvl_s, 1)


def _is_margin_proxy(source: str = '') -> bool:
    src = (source or '').lower()
    return 'z.1' in src or 'proxy' in src or 'bogz1' in src


def score_hy_oas(bp: Optional[float], thresholds: dict) -> float:
    """OAS alto = stress credito = innesco più probabile."""
    complacent = float(thresholds.get('complacent', 350.0))
    stress = float(thresholds.get('stress', 500.0))
    return round(_lerp_score(bp, complacent - 80.0, stress), 1)


def score_yield_curve(bp: Optional[float]) -> float:
    """Curva piatta/invertita = innesco tardo-ciclo più probabile."""
    if bp is None:
        return 35.0
    if bp < 0:
        return round(_clamp(45.0 + abs(bp) * 0.9), 1)
    # 0–80 bp: tardo-ciclo / ambra (uscita da inversione)
    if bp <= 80:
        return round(35.0 + (80.0 - bp) * 0.25, 1)
    # steepening ampio = meno tensione ciclica
    return round(_clamp(35.0 - (bp - 80.0) * 0.15), 1)


def score_recession_prob(pct: Optional[float], thresholds: dict) -> float:
    amber = float(thresholds.get('amber', 25.0))
    red = float(thresholds.get('red', 40.0))
    return round(_lerp_score(pct, amber - 10.0, red + 15.0), 1)


def score_fed_path(
    fed_funds: Optional[float],
    fed_hawkish_hits: int = 0,
) -> float:
    """Fed restrittiva + headline hawkish = rischio innesco."""
    base = 25.0
    if fed_funds is not None:
        base = _lerp_score(fed_funds, 2.0, 5.5)
    news_boost = min(35.0, fed_hawkish_hits * 8.0)
    return round(_clamp(base * 0.65 + news_boost), 1)


def weighted_mean(pairs: list[tuple[float, float]]) -> float:
    """Media pesata; ignora pesi con score mancante."""
    num = 0.0
    den = 0.0
    for score, weight in pairs:
        if weight <= 0:
            continue
        num += score * weight
        den += weight
    return round(num / den, 1) if den > 0 else 0.0


def classify_regime(
    fragility: float,
    trigger: float,
    *,
    news_score: float = 0.0,
) -> str:
    if fragility >= 70 and trigger < 40:
        return 'Tarda bolla — molla carica, innesco spento'
    if fragility >= 65 and trigger >= 55:
        return 'Allerta scoppio — fragilità e innesco entrambi elevati'
    if fragility >= 60 and trigger >= 45:
        return 'Tensione acuta — innesco in formazione'
    if fragility >= 55 and trigger >= 40:
        return 'Tensione crescente — sorvegliare spread e Fed'
    if fragility >= 45 and trigger < 35:
        return 'Valutazioni tese — innesco ancora assente'
    if trigger >= 55 and fragility < 55:
        return 'Innesco attivo — fragilità moderata'
    if fragility < 40 and trigger < 30 and news_score < 25:
        return 'Regime tranquillo'
    return 'Misto — monitoraggio standard'


def build_scores(indicators: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    thresholds = settings.get('thresholds', {})
    weights = settings.get('weights', {})
    frag_w = weights.get('fragility', {})
    trig_w = weights.get('trigger', {})
    comp_w = weights.get('composite', {})

    news = indicators.get('news') or {}
    tallies = news.get('tallies') or {}

    margin_source = str(indicators.get('margin_source') or '')
    frag_parts = {
        'cape': score_cape(indicators.get('cape'), thresholds.get('cape', {})),
        'buffett': score_buffett(indicators.get('buffett_pct'), thresholds.get('buffett_pct', {})),
        'household_equity': score_household(
            indicators.get('household_equity_pct'),
            thresholds.get('household_equity_pct', {}),
        ),
        'concentration': score_concentration(
            indicators.get('mag7_weight_pct'),
            thresholds.get('mag7_weight_pct', {}),
        ),
        'margin_debt': score_margin_combined(
            indicators.get('margin_debt_yoy_pct'),
            indicators.get('margin_debit_billion'),
            yoy_thr=thresholds.get('margin_debt_yoy_pct', {}),
            level_thr=thresholds.get('margin_debt_billion', {}),
            source=margin_source,
        ),
    }

    trig_parts = {
        'hy_oas': score_hy_oas(indicators.get('hy_oas_bp'), thresholds.get('hy_oas_bp', {})),
        'yield_curve': score_yield_curve(indicators.get('yield_curve_2s10s_bp')),
        'recession_prob': score_recession_prob(
            indicators.get('recession_prob_pct'),
            thresholds.get('recession_prob_pct', {}),
        ),
        'fed_path': score_fed_path(
            indicators.get('fed_funds_pct'),
            int(tallies.get('fed_hawkish', 0)),
        ),
        'ai_earnings_risk': float(indicators.get('ai_earnings_risk') or 0.0),
    }

    margin_w = float(frag_w.get('margin_debt', 0.15))
    # Proxy Z.1 non deve dominare la media (metodologia ≠ FINRA debit balances)
    if _is_margin_proxy(margin_source):
        margin_w *= 0.45

    fragility_score = weighted_mean([
        (frag_parts['cape'], float(frag_w.get('cape', 0.25))),
        (frag_parts['buffett'], float(frag_w.get('buffett', 0.22))),
        (frag_parts['household_equity'], float(frag_w.get('household_equity', 0.18))),
        (frag_parts['concentration'], float(frag_w.get('concentration', 0.20))),
        (frag_parts['margin_debt'], margin_w),
    ])

    # Quorum valutazioni estreme: non lasciare un pezzo debole abbassare sotto "tarda bolla"
    extreme_bits = sum(
        1
        for key in ('cape', 'buffett', 'household_equity')
        if float(frag_parts.get(key) or 0) >= 75.0
    )
    if extreme_bits >= 2:
        fragility_score = max(fragility_score, 72.0)

    trigger_score = weighted_mean([
        (trig_parts['hy_oas'], float(trig_w.get('hy_oas', 0.35))),
        (trig_parts['yield_curve'], float(trig_w.get('yield_curve', 0.15))),
        (trig_parts['recession_prob'], float(trig_w.get('recession_prob', 0.20))),
        (trig_parts['fed_path'], float(trig_w.get('fed_path', 0.15))),
        (trig_parts['ai_earnings_risk'], float(trig_w.get('ai_earnings_risk', 0.15))),
    ])

    news_score = float(news.get('news_risk_score') or indicators.get('news_risk_score') or 0.0)

    bubble_proximity = round(
        fragility_score * float(comp_w.get('fragility', 0.55))
        + trigger_score * float(comp_w.get('trigger', 0.30))
        + news_score * float(comp_w.get('news', 0.15)),
        1,
    )

    regime = classify_regime(fragility_score, trigger_score, news_score=news_score)

    return {
        'fragility_score': fragility_score,
        'trigger_score': trigger_score,
        'news_score': round(news_score, 1),
        'bubble_proximity': bubble_proximity,
        'parts': {
            'fragility': frag_parts,
            'trigger': trig_parts,
        },
        'regime': regime,
        'watch_order': list(WATCH_ORDER),
    }
