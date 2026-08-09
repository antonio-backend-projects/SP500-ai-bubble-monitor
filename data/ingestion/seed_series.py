"""Seed storici da piano-strategia — usati solo se il download web fallisce."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _pts(pairs: list[tuple[str, float]]) -> list[dict[str, Any]]:
    return [{'date': d, 'value': v} for d, v in pairs]


SEEDS: dict[str, dict[str, Any]] = {
    'BAMLH0A0HYM2': {  # HY OAS %
        'last_value': 2.71,
        'last_date': '2026-08-01',
        'history': _pts([
            ('2024-01-01', 3.5), ('2024-07-01', 3.1), ('2025-01-01', 2.9),
            ('2025-07-01', 2.8), ('2026-01-01', 2.75), ('2026-08-01', 2.71),
        ]),
    },
    'T10Y2Y': {
        'last_value': 0.50,
        'last_date': '2026-08-01',
        'history': _pts([
            ('2023-07-01', -0.9), ('2024-01-01', -0.3), ('2024-07-01', 0.1),
            ('2025-01-01', 0.3), ('2025-07-01', 0.4), ('2026-08-01', 0.50),
        ]),
    },
    'DFF': {
        'last_value': 4.25,
        'last_date': '2026-08-01',
        'history': _pts([
            ('2022-01-01', 0.1), ('2023-01-01', 4.5), ('2024-01-01', 5.3),
            ('2025-01-01', 4.5), ('2026-08-01', 4.25),
        ]),
    },
    'DDDM01USA156NWDB': {
        'last_value': 234.0,
        'last_date': '2025-10-01',
        'history': _pts([
            ('2000-01-01', 140.0), ('2009-01-01', 60.0), ('2021-01-01', 200.0),
            ('2024-01-01', 195.0), ('2025-10-01', 234.0),
        ]),
    },
    'BOGZ1FL153064486Q': {
        'last_value': 47.1,
        'last_date': '2025-10-01',
        'history': _pts([
            ('2000-01-01', 38.7), ('2009-01-01', 19.0), ('2021-01-01', 40.0),
            ('2024-01-01', 44.0), ('2025-10-01', 47.1),
        ]),
    },
    'GDP': {
        'last_value': 29000.0,
        'last_date': '2025-10-01',
        'history': _pts([('2024-01-01', 28000.0), ('2025-10-01', 29000.0)]),
    },
}


def seed_series(series_id: str) -> dict[str, Any]:
    base = SEEDS.get(series_id, {
        'last_value': None,
        'last_date': None,
        'history': [],
    })
    return {
        'series_id': series_id,
        'last_date': base.get('last_date'),
        'last_value': base.get('last_value'),
        'history': list(base.get('history') or []),
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'seed_from_piano_strategia',
        'note': 'Download web fallito — valori indicativi dal piano fino a connessione ok',
    }
