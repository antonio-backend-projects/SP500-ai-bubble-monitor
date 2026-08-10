"""Parse offline della tabella FINRA (niente rete)."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.ingestion.finra_margin import ROW_RE, _millions_to_billions, _payload_from_rows


def test_millions_to_billions():
    assert _millions_to_billions("1,502,072") == 1502.07


def test_row_regex_and_payload():
    sample = (
        "Jun-26 1,502,072 217,441 223,412 "
        "May-26 1,415,557 206,600 217,256 "
        "Jun-25 1,007,900 200,000 210,000"
    )
    rows = []
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for m in ROW_RE.finditer(sample):
        mon, yy, debit, cash, cred = m.groups()
        rows.append(
            {
                "date": f"{2000 + int(yy):04d}-{months[mon.lower()[:3]]:02d}-01",
                "debit_balances_billion": _millions_to_billions(debit),
                "free_credit_cash_billion": _millions_to_billions(cash),
                "free_credit_margin_billion": _millions_to_billions(cred),
            }
        )
    payload = _payload_from_rows(rows, source="test")
    assert payload is not None
    assert payload["debit_balances_billion"] == 1502.07
    assert payload["as_of"] == "2026-06-01"
    assert payload["yoy_pct"] is not None
    assert payload["yoy_pct"] > 40.0
