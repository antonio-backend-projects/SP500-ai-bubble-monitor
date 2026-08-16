# Development

Local setup, tests, and anti-ban rules. Full config: [configuration.md](configuration.md).

## Setup

### Windows (PowerShell)

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
# Set FRED_API_KEY in .env (32 chars) — https://fredaccount.stlouisfed.org/apikeys
```

### Linux / macOS / Pi (bash)

```bash
cd ~/SP500-ai-bubble-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env → FRED_API_KEY
```

`xlrd>=2.0.1` is **not** in `requirements.txt` but is required to parse the NY Fed `.xls`. Without it, recession probability falls back to seed. Install if you want the live series:

```powershell
pip install "xlrd>=2.0.1"
```

## Daily commands

```powershell
python -m pytest tests/ -q
python -m py_compile engine/run_engine.py scripts/dashboard_web.py
python -m engine.run_engine          # network: once, then 24h cache
python scripts/dashboard_web.py      # http://localhost:8891
```

First engine run: several minutes (rate limit + 40-name breadth sample). Later runs with a fresh cache: seconds.

Dashboard **without** an engine run serves `tests/fixtures/sample_bubble_state.json` with a **FIXTURE** badge — that is not the market.

## Tests

```powershell
python -m pytest tests/ -q
```

- `tests/test_scoring.py` — late-bubble scenario from the strategy note.
- `tests/test_presentation.py` — alerts/cards; includes `test_alert_not_green_when_valuations_extreme_but_margin_proxy_flat`.
- UI fixture: `tests/fixtures/sample_bubble_state.json`.

Tests are **offline**. Do not run the engine in CI.

## UI conventions

- Vanilla HTML in `web/dashboard.html` (igedge pattern). **No Streamlit.**
- Guides: JS object `GUIDES` + modal `#guideModal`.
- Helper `fact()` is required for under-surface (bug 2026-08-09: without it, JS crashed mid-`render()`).

## Agent handoff

Before implementing: `docs/PROJECT_MEMORY.md`, `evolutive/README.md`, `piano-strategia.md`. Short rules: `AGENTS.md`.

## Do not (Windows PC / anti-ban)

- Do not loop `python -m engine.run_engine --force`.
- Do not re-enable Yahoo Mag7 (`fetch_yahoo_mag7`).
- Do not scrape FINRA HTML / MarketWatch / Stooq “because the mirror looks ugly”.
- Do not add a dashboard button that launches the engine.
- Do not use this PC as a fetch farm: production = Pi + cron.
- Do not commit `.env`, `data/cache/*`, `config/fred_api_key.txt`.
