"""Test alert/cards offline — nessuno scaricamento rete."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.presentation import build_alert, build_cards, enrich_state
from engine.scoring import build_scores


def _late_bubble():
    return {
        'cape': 41.9,
        'buffett_pct': 234.0,
        'household_equity_pct': 47.0,
        'mag7_weight_pct': 35.0,
        'top10_weight_pct': 38.0,
        'margin_debt_yoy_pct': 51.5,
        'margin_debit_billion': 1530.0,
        'hy_oas_bp': 271.0,
        'yield_curve_2s10s_bp': 50.0,
        'recession_prob_pct': 25.0,
        'fed_funds_pct': 4.25,
        'ai_earnings_risk': 15.0,
        'thresholds_ref': {},
        'news': {
            'news_risk_score': 22.0,
            'tallies': {'fed_hawkish': 1, 'credit_stress': 0, 'ai_earnings': 1, 'recession': 0},
            'items': [],
        },
    }


def test_alert_late_bubble_amber():
    scores = build_scores(_late_bubble())
    alert = build_alert(scores)
    assert alert['level'] == 'amber'
    assert 'TARDA BOLLA' in alert['headline'] or 'BOLLA' in alert['headline']
    assert alert['urgency'] >= 50


def test_alert_not_green_when_valuations_extreme_but_margin_proxy_flat():
    """Caso reale: CAPE/Buffett/famiglie alti, margin Z.1 YoY basso → NON rischio contenuto."""
    ind = _late_bubble()
    ind['cape'] = 42.4
    ind['buffett_pct'] = 219.0
    ind['household_equity_pct'] = 45.8
    ind['mag7_weight_pct'] = 30.8
    ind['margin_debt_yoy_pct'] = 2.1
    ind['margin_debit_billion'] = 622.0
    ind['margin_source'] = 'FRED Z.1 BOGZ1FL663067003Q (margin loans proxy)'
    scores = build_scores(ind)
    alert = build_alert(scores)
    assert alert['level'] in ('amber', 'red')
    assert 'CONTENUTO' not in alert['headline']
    assert scores['fragility_score'] >= 70.0


def test_alert_burst_red():
    ind = _late_bubble()
    ind['hy_oas_bp'] = 520.0
    ind['recession_prob_pct'] = 45.0
    ind['ai_earnings_risk'] = 80.0
    ind['news']['news_risk_score'] = 70.0
    scores = build_scores(ind)
    # forza trigger alto se i pezzi non bastano
    scores['fragility_score'] = 85.0
    scores['trigger_score'] = 60.0
    alert = build_alert(scores)
    assert alert['level'] == 'red'
    assert 'ALLERTA' in alert['headline'] or 'INNESCO' in alert['headline']


def test_cards_and_enrich():
    ind = _late_bubble()
    scores = build_scores(ind)
    cards = build_cards(ind, scores)
    assert len(cards) >= 8
    assert any(c['group'] == 'fragility' for c in cards)
    assert any(c['group'] == 'trigger' for c in cards)
    enriched = enrich_state(ind, scores)
    assert 'alert' in enriched and 'charts' in enriched and 'cards' in enriched
