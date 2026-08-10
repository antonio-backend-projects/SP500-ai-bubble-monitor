"""Trasforma score+indicatori in alert, card leggibili e serie per grafici."""
from __future__ import annotations

from typing import Any, Optional


def _status(score: Optional[float]) -> str:
    if score is None:
        return 'unknown'
    if score >= 70:
        return 'red'
    if score >= 45:
        return 'amber'
    return 'green'


def _hist(series: Optional[dict], *, value_key: str = 'value', n: int = 90) -> list[dict]:
    if not series:
        return []
    hist = series.get('history') or []
    out = []
    for row in hist[-n:]:
        val = row.get(value_key)
        if val is None and value_key != 'value':
            val = row.get('value')
        if val is None and 'cape' in row:
            val = row.get('cape')
        if val is None:
            continue
        out.append({'date': row.get('date'), 'value': val})
    return out


def build_alert(scores: dict[str, Any]) -> dict[str, Any]:
    frag = float(scores.get('fragility_score') or 0)
    trig = float(scores.get('trigger_score') or 0)
    prox = float(scores.get('bubble_proximity') or 0)
    regime = scores.get('regime') or ''
    parts_f = (scores.get('parts') or {}).get('fragility') or {}
    parts_t = (scores.get('parts') or {}).get('trigger') or {}

    # Quorum: Buffett/CAPE/famiglie estremi → almeno tarda bolla se innesco spento
    extreme_val = sum(
        1
        for key in ('cape', 'buffett', 'household_equity')
        if float(parts_f.get(key) or 0) >= 75.0
    )
    if extreme_val >= 2 and frag < 70 and trig < 40:
        frag = max(frag, 72.0)

    if frag >= 70 and trig >= 55:
        level = 'red'
        headline = 'ALLERTA SCOPPIO'
        summary = (
            'Fragilità estrema e innesco attivo. Storicamente è la zona in cui '
            'le bolle si sgonfiano in fretta: priorità assoluta a Fed, credito e utili AI.'
        )
    elif frag >= 70 and trig >= 40:
        level = 'red'
        headline = 'MOLLA CARICA — INNESCO IN FORMAZIONE'
        summary = (
            'La molla è già al livello bolla; l\'innesco sta salendo. '
            'Non è ancora il crollo, ma il margine di errore si sta chiudendo.'
        )
    elif frag >= 70:
        level = 'amber'
        headline = 'TARDA BOLLA — INNESCO ANCORA SPENTO'
        summary = (
            'Valutazioni, leva e concentrazione da fine-ciclo. '
            'Manca (per ora) lo scatto tipico: allargamento credit spreads o stretta Fed.'
        )
    elif frag >= 55 or trig >= 45:
        level = 'amber'
        headline = 'VIGILANZA ELEVATA'
        summary = 'Segnali misti: non è calma piatta. Monitorare i tre trigger del piano.'
    else:
        level = 'green'
        headline = 'RISCHIO CONTENUTO'
        summary = 'Nessun allarme bolla imminente dai proxy attuali.'

    flashing = []
    for name, sc in {**parts_f, **parts_t}.items():
        if sc is not None and sc >= 70:
            flashing.append(name)

    return {
        'level': level,
        'headline': headline,
        'summary': summary,
        'regime': regime,
        'urgency': round(min(100.0, frag * 0.6 + trig * 0.4), 1),
        'proximity': prox,
        'flashing': flashing,
        'one_liner': f'{headline}: fragilità {frag:.0f}/100 · innesco {trig:.0f}/100 · prossimità {prox:.0f}/100',
    }


def build_cards(indicators: dict[str, Any], scores: dict[str, Any]) -> list[dict[str, Any]]:
    thr = (indicators.get('thresholds_ref') or {})
    pf = (scores.get('parts') or {}).get('fragility') or {}
    pt = (scores.get('parts') or {}).get('trigger') or {}

    def card(
        key: str,
        title: str,
        group: str,
        value: Any,
        unit: str,
        score: Optional[float],
        meaning: str,
        ref: str,
    ) -> dict[str, Any]:
        return {
            'key': key,
            'title': title,
            'group': group,
            'value': value,
            'unit': unit,
            'score': score,
            'status': _status(score),
            'meaning': meaning,
            'reference': ref,
        }

    return [
        card(
            'cape', 'CAPE Shiller', 'fragility',
            indicators.get('cape'), '',
            pf.get('cape'),
            'Quanto gli utili decennali giustificano i prezzi. Sopra 40 è territorio 1999-2000.',
            f"Mediana storica ~{thr.get('cape', {}).get('median', 16)} · estremo {thr.get('cape', {}).get('extreme', 40)}",
        ),
        card(
            'buffett', 'Buffett indicator', 'fragility',
            indicators.get('buffett_pct'), '%',
            pf.get('buffett'),
            'Capitalizzazione azionaria USA vs PIL. Sopra 200% Buffett diceva "giocare col fuoco".',
            f"Fuoco {thr.get('buffett_pct', {}).get('fire', 200)}% · estremo {thr.get('buffett_pct', {}).get('extreme', 230)}%",
        ),
        card(
            'household', 'Equity famiglie USA', 'fragility',
            indicators.get('household_equity_pct'), '%',
            pf.get('household_equity'),
            'Quota del patrimonio finanziario in azioni. Record = più effetto ricchezza e meno cuscinetto.',
            f"Picco Dot-com {thr.get('household_equity_pct', {}).get('dotcom', 38.7)}%",
        ),
        card(
            'concentration', 'Peso Mag7 / Top10', 'fragility',
            indicators.get('mag7_weight_pct'), '%',
            pf.get('concentration'),
            'Concentrazione dell\'indice nei mega-cap AI. Una trimestrale muove tutto l\'S&P.',
            f"Top10: {indicators.get('top10_weight_pct')}% · soglia estrema Mag7 {thr.get('mag7_weight_pct', {}).get('extreme', 33)}%",
        ),
        card(
            'margin', 'Margin debt', 'fragility',
            indicators.get('margin_debt_yoy_pct'), '% YoY',
            pf.get('margin_debt'),
            'Leva speculativa. I picchi di margin debt hanno anticipato i massimi del 2000, 2007, 2021.',
            (
                f"Livello: ${indicators.get('margin_debit_billion')}B · "
                f"{indicators.get('margin_source') or 'n/d'}"
                + (
                    ' · ATTENZIONE: proxy Z.1 ≠ debit FINRA del piano'
                    if 'z.1' in str(indicators.get('margin_source') or '').lower()
                    or 'proxy' in str(indicators.get('margin_source') or '').lower()
                    else ''
                )
            ),
        ),
        card(
            'hy_oas', 'HY credit spread', 'trigger',
            indicators.get('hy_oas_bp'), 'bp',
            pt.get('hy_oas'),
            'Stress del credito. Stretto = compiacenza; in allargamento = spesso precede i crolli.',
            f"Compiacenza <{thr.get('hy_oas_bp', {}).get('complacent', 350)} bp · stress {thr.get('hy_oas_bp', {}).get('stress', 500)}+",
        ),
        card(
            'curve', 'Curva 2s10s', 'trigger',
            indicators.get('yield_curve_2s10s_bp'), 'bp',
            pt.get('yield_curve'),
            'Tardo-ciclo: uscita dall\'inversione con curva appena positiva = ambra, non rosso.',
            'Inversione <0 · tardo-ciclo 0–80 bp',
        ),
        card(
            'recession', 'Prob. recessione', 'trigger',
            indicators.get('recession_prob_pct'), '%',
            pt.get('recession_prob'),
            'Proxy NY Fed / curva. Una recessione è ciò che rende i ribassi davvero profondi.',
            f"Ambra {thr.get('recession_prob_pct', {}).get('amber', 25)}% · rosso {thr.get('recession_prob_pct', {}).get('red', 40)}%",
        ),
        card(
            'fed', 'Fed funds', 'trigger',
            indicators.get('fed_funds_pct'), '%',
            pt.get('fed_path'),
            'Policy restrittiva: fu l\'inasprimento a bucare il 2000. Sorvegliare tono hawkish.',
            f"Funds {indicators.get('fed_funds_pct')}%",
        ),
        card(
            'ai', 'Rischio utili AI', 'trigger',
            indicators.get('ai_earnings_risk'), '/100',
            pt.get('ai_earnings_risk'),
            'Delusioni su capex/earnings Mag7: terzo innesco del piano, il più specifico della bolla AI.',
            'Da news + keyword earnings/AI',
        ),
        card(
            'under', 'Stress concentrazione', 'fragility',
            indicators.get('concentration_stress_0_100'), '/100',
            indicators.get('concentration_stress_0_100'),
            'Quanto l\'indice dipende dai mega-cap (proxy del rischio "sotto la superficie").',
            f"Top10 {indicators.get('top10_weight_pct')}% · Mag7 {indicators.get('mag7_weight_pct')}%",
        ),
        card(
            'spxdd', 'S&P vs max 52w', 'fragility',
            indicators.get('dist_52w_high_pct'), '%',
            None,
            'Distanza dal massimo a ~1y (FRED SP500). Vicino a 0% = mercato caro; washout tipico −3/−8%.',
            f"YTD {indicators.get('ytd_pct')}% · maxDD 1y {indicators.get('max_drawdown_1y_pct')}%",
        ),
        card(
            'mag7chg', 'Mag7 variazione media', 'trigger',
            indicators.get('mag7_avg_change_pct'), '%',
            None,
            'Momentum giornaliero Mag7 da NASDAQ (senza Yahoo). Debolezza concentrata = stress AI.',
            'Fonte: api.nasdaq.com quote',
        ),
    ]


def build_charts(
    indicators: dict[str, Any],
    scores: dict[str, Any],
    *,
    fred_bundle: Optional[dict] = None,
    cape: Optional[dict] = None,
    recession: Optional[dict] = None,
) -> dict[str, Any]:
    fred_bundle = fred_bundle or {}
    series = fred_bundle.get('series') or {}

    pf = (scores.get('parts') or {}).get('fragility') or {}
    pt = (scores.get('parts') or {}).get('trigger') or {}

    radar = {
        'labels': ['CAPE', 'Buffett', 'Famiglie', 'Mag7', 'Margin', 'HY OAS', 'Curva', 'Recessione', 'Fed', 'AI'],
        'values': [
            pf.get('cape') or 0,
            pf.get('buffett') or 0,
            pf.get('household_equity') or 0,
            pf.get('concentration') or 0,
            pf.get('margin_debt') or 0,
            pt.get('hy_oas') or 0,
            pt.get('yield_curve') or 0,
            pt.get('recession_prob') or 0,
            pt.get('fed_path') or 0,
            pt.get('ai_earnings_risk') or 0,
        ],
    }

    bars = {
        'fragility': [
            {'label': 'CAPE', 'value': pf.get('cape')},
            {'label': 'Buffett', 'value': pf.get('buffett')},
            {'label': 'Famiglie', 'value': pf.get('household_equity')},
            {'label': 'Mag7', 'value': pf.get('concentration')},
            {'label': 'Margin', 'value': pf.get('margin_debt')},
        ],
        'trigger': [
            {'label': 'HY OAS', 'value': pt.get('hy_oas')},
            {'label': 'Curva', 'value': pt.get('yield_curve')},
            {'label': 'Recessione', 'value': pt.get('recession_prob')},
            {'label': 'Fed', 'value': pt.get('fed_path')},
            {'label': 'AI earnings', 'value': pt.get('ai_earnings_risk')},
        ],
    }

    # HY OAS in bp per il grafico
    hy_hist = _hist(series.get('hy_oas'))
    for row in hy_hist:
        v = row['value']
        row['value'] = round(v * 100.0, 1) if v is not None and v < 50 else v

    curve_hist = _hist(series.get('yield_curve_2s10s'))
    for row in curve_hist:
        v = row['value']
        row['value'] = round(v * 100.0, 1) if v is not None and abs(v) < 50 else v

    return {
        'radar': radar,
        'bars': bars,
        'gauge': {
            'proximity': scores.get('bubble_proximity'),
            'fragility': scores.get('fragility_score'),
            'trigger': scores.get('trigger_score'),
            'news': scores.get('news_score'),
        },
        'series': {
            'cape': (
                _hist(cape, value_key='cape', n=120) if cape
                else _hist({
                    'history': [
                        {'date': x.get('date'), 'value': x.get('cape')}
                        for x in (indicators.get('cape_history') or [])
                    ]
                }, n=120)
            ),
            'hy_oas_bp': hy_hist,
            'yield_curve_bp': curve_hist,
            'buffett_pct': _hist(series.get('buffett_indicator'), n=120),
            'household_equity_pct': _hist(series.get('household_equity_pct'), n=80),
            'recession_prob_pct': _hist(recession, n=80) if recession else [],
            'fed_funds': _hist(series.get('fed_funds'), n=120),
        },
        'thresholds': {
            'hy_oas_complacent': 350,
            'hy_oas_stress': 500,
            'cape_extreme': 40,
            'buffett_fire': 200,
        },
    }


def enrich_state(
    indicators: dict[str, Any],
    scores: dict[str, Any],
    *,
    fred_bundle: Optional[dict] = None,
    cape: Optional[dict] = None,
    recession: Optional[dict] = None,
) -> dict[str, Any]:
    alert = build_alert(scores)
    cards = build_cards(indicators, scores)
    charts = build_charts(
        indicators, scores,
        fred_bundle=fred_bundle,
        cape=cape,
        recession=recession,
    )
    return {
        'alert': alert,
        'cards': cards,
        'charts': charts,
    }
