"""Test offline scoring — scenario tarda bolla da piano-strategia."""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.scoring import build_scores, classify_regime


@pytest.fixture
def late_bubble_indicators() -> dict:
    """Valori indicativi inizio agosto 2026 (piano-strategia.md)."""
    return {
        'cape': 41.9,
        'buffett_pct': 234.0,
        'household_equity_pct': 47.0,
        'mag7_weight_pct': 35.0,
        'margin_debt_yoy_pct': 51.5,
        'hy_oas_bp': 271.0,
        'yield_curve_2s10s_bp': 50.0,
        'recession_prob_pct': 25.0,
        'fed_funds_pct': 4.25,
        'ai_earnings_risk': 15.0,
        'news': {
            'news_risk_score': 22.0,
            'tallies': {
                'fed_hawkish': 1,
                'credit_stress': 0,
                'ai_earnings': 1,
                'recession': 0,
            },
            'items': [],
        },
    }


def test_late_bubble_high_fragility_low_trigger(late_bubble_indicators):
    result = build_scores(late_bubble_indicators)

    assert result['fragility_score'] >= 70.0
    assert result['trigger_score'] < 55.0
    assert 'Tarda bolla' in result['regime']
    assert result['bubble_proximity'] > 50.0
    assert len(result['watch_order']) == 3


def test_fragility_parts_all_elevated(late_bubble_indicators):
    result = build_scores(late_bubble_indicators)
    frag = result['parts']['fragility']

    assert frag['cape'] >= 75.0
    assert frag['buffett'] >= 70.0
    assert frag['margin_debt'] >= 60.0


def test_trigger_hy_oas_complacent(late_bubble_indicators):
    result = build_scores(late_bubble_indicators)
    trig = result['parts']['trigger']

    assert trig['hy_oas'] < 45.0


def test_classify_regime_direct():
    label = classify_regime(fragility=75.0, trigger=30.0)
    assert label == 'Tarda bolla — molla carica, innesco spento'
