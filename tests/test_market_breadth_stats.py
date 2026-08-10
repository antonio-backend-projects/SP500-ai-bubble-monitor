"""Stats breadth offline (niente rete)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.ingestion.market_breadth import _stats_from_closes


def test_stats_ytd_and_drawdown():
    series = [
        ("2025-12-31", 100.0),
        ("2026-01-02", 102.0),
        ("2026-03-01", 110.0),
        ("2026-06-01", 105.0),
        ("2026-08-01", 108.0),
    ]
    st = _stats_from_closes(series)
    assert st["last"] == 108.0
    assert st["dist_52w_high_pct"] == round((108 / 110 - 1) * 100, 2)
    assert st["ytd_pct"] == round((108 / 102 - 1) * 100, 2)
