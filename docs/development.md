# Development

## Setup

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# inserire FRED_API_KEY in .env
```

## Comandi quotidiani

```powershell
python -m pytest tests/ -q
python -m py_compile engine/run_engine.py scripts/dashboard_web.py
python -m engine.run_engine          # rete: moderazione
python scripts/dashboard_web.py      # http://localhost:8891
```

## Divieti (PC Windows / anti-ban)

- Non loopare `run_engine --force`.
- Non riattivare Yahoo Mag7 di default.
- Non scrapare FINRA HTML / MarketWatch.
- La dashboard non deve mai triggerare download.

## Test

- `tests/test_scoring.py` — scenario tarda bolla da piano (input seed-like).
- `tests/test_presentation.py` — alert/cards.
- Fixture: `tests/fixtures/sample_bubble_state.json` se cache assente.

## Convenzioni UI

- Vanilla HTML in `web/dashboard.html` (pattern igedge).
- Guide indicatori: oggetto JS `GUIDES` + modal `#guideModal`.
- Helper `fact()` obbligatorio per la sezione under-surface.

## Handoff agent

Leggere `docs/PROJECT_MEMORY.md` e `evolutive/README.md` prima di implementare.
