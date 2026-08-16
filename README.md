# SP500 AI Bubble Monitor

A **fragility vs trigger** monitor for the US equity market in the AI-boom regime.

It does **not** predict the day a bubble pops. It measures two separate things:

1. **Fragility (the spring)** — valuations, leverage, concentration, household equity exposure  
2. **Trigger (the spark)** — credit stress, the yield curve, Fed path, recession odds, AI/Mag7 earnings risk  

Typical reading from the strategy note: *late bubble — spring coiled, trigger still off*. High CAPE / Buffett / household equity can coexist with complacent HY spreads. That combination is the point of the dashboard, not a bug.

**Not financial advice.** Scenario analysis on public data.

---

## Quick start

You need Python 3.11+ and a free [FRED API key](https://fredaccount.stlouisfed.org/apikeys) (32 characters).

**Windows (PowerShell)**

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env   # set FRED_API_KEY=...

python -m engine.run_engine          # first run: several minutes
python scripts/dashboard_web.py      # http://localhost:8891
```

**Linux / macOS**

```bash
cd SP500-ai-bubble-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env → FRED_API_KEY=...

python -m engine.run_engine
python scripts/dashboard_web.py      # http://localhost:8891
```

Two processes, two jobs:

| Command | What it does | Network? |
|---------|----------------|----------|
| `python -m engine.run_engine` | Fetches sources, scores, writes `data/cache/bubble_state.json` | Yes (24h cache) |
| `python scripts/dashboard_web.py` | Serves the UI + JSON | No — disk only |

The dashboard is **read-only**. There is no “refresh data” button. Re-run the engine when you want new numbers. `--force` bypasses the 24h cache; use it rarely, never in a loop from a home IP.

Full setup and settings: [docs/development.md](docs/development.md), [docs/configuration.md](docs/configuration.md).

---

## How to read the dashboard

Open **http://localhost:8891** after an engine run.

| Banner (as shown in UI) | Meaning |
|-------------------------|---------|
| **TARDA BOLLA — INNESCO ANCORA SPENTO** | Late bubble: valuations/leverage extreme, credit/Fed spark still quiet |
| **MOLLA CARICA — INNESCO IN FORMAZIONE** | Spring coiled and the trigger is rising |
| **ALLERTA SCOPPIO** | Fragility and trigger both high |
| **VIGILANZA ELEVATA** | Mixed — not calm |
| **RISCHIO CONTENUTO** | No bubble-imminent signal from *current proxies* |

Treat a green **RISCHIO CONTENUTO** banner with Buffett ≥ 200% and household equity ≥ 45% as a **data-quality problem**, not “the market is safe”. See [docs/runbook-incidenti.md](docs/runbook-incidenti.md).

Also check the trust badge:

- **FIXTURE** — no live `bubble_state.json`; you are looking at test data  
- **LIVE** / partial / weak — inspect `cape_as_of` and `margin_source` in `/api/state`

Reference live run (2026-08-15): fragility **77**, trigger **23**, proximity **59** — late bubble, trigger off. CAPE 42.6, Buffett 219%, household 45.8%, FINRA-mirror margin $1.42T (+39% YoY), HY OAS 271 bp.

---

## Architecture

```
engine (CLI/cron)  →  data/cache/bubble_state.json  →  dashboard poll /api/state every 60s
```

Vanilla HTML/CSS/JS (`web/dashboard.html`, igedge-style). **Not Streamlit.** Python `ThreadingHTTPServer`, port **8891** (`WEB_PORT`).

```
config/settings.json      thresholds, weights, RSS, fetch flags
config/env.py             loads .env
data/ingestion/           fail-soft fetch + JSON cache
engine/run_engine.py      pipeline
engine/scoring.py         fragility / trigger / proximity / regime
engine/presentation.py    alert, cards, chart payload
scripts/dashboard_web.py  read-only HTTP
tests/                    offline pytest
```

Detail: [docs/architecture.md](docs/architecture.md).

### Routes

| Route | Serves |
|-------|--------|
| `/` | `web/dashboard.html` |
| `/api/state` | Cached state (or test fixture) plus trust metadata |
| `/salute` | Healthcheck (`ok`) |

POST → 405. The UI never fetches FRED/NASDAQ from the browser.

---

## Data sources

Prefer official APIs. Probe before wiring a new host. Default cache **24 hours**; HTTP pacing 3–8s.

| Indicator | Primary | Fallback |
|-----------|---------|----------|
| Macro (HY OAS, curve, funds, household, GDP, SPX) | **FRED API** | Treasury / Fed H.15 |
| Buffett (cap/GDP) | Current Market Valuation | FRED World Bank (often stuck at 2020) |
| CAPE | Shiller XLS | **multpl.com** if stale/404 |
| Margin debt | FINRA page | **thetrading.tools CSV** → FRED Z.1 proxy → seed |
| Mag7 / Top 10 weights | Slickcharts | — |
| Mag7 quotes & EPS | NASDAQ API | Yahoo Mag7 **off** (`fetch_yahoo_mag7: false`) |
| Recession odds | NY Fed `allmonth.xls` | seed (needs `xlrd`) |
| Mag7 8-K | SEC EDGAR atom | — |
| News | Fed / CNBC / BBC RSS | — |

**Do not use:** `fredgraph.csv` (timeouts), Yahoo Mag7 charts (429), FINRA HTML hammering (403), MarketWatch/Stooq scrapes.

Without a FRED key the engine still starts (Treasury, H.15, CMV, …) but macro quality drops. `.env` is gitignored — never commit the key.

Source matrix and ban notes: [docs/data-sources.md](docs/data-sources.md).

---

## Configuration (short)

| File | Holds | Secrets? |
|------|--------|----------|
| `.env` | `FRED_API_KEY`, optional `WEB_PORT` | Yes |
| `config/settings.json` | Cache TTL, rate limits, FRED series, thresholds, weights, RSS | No — leave `fred_api_key` empty |

Alert banner cutoffs (70 / 55 / 40) live in `engine/presentation.py`, not JSON. After editing settings or `.env`, **restart** engine and dashboard.

Field-by-field reference: [docs/configuration.md](docs/configuration.md).

---

## Tests

```powershell
python -m pytest tests/ -q
```

Offline only. Do not run the live engine in CI.

---

## Production (not in the repo yet)

Target: Raspberry Pi + Docker + evening cron for the engine + **Cloudflare Tunnel** (same pattern as Gamtrace).

Until `Dockerfile` / compose exist, a Pi can still run the venv + systemd + cron. Windows is for development and pytest; do not use a laptop as a fetch farm.

- [docs/docker-and-production.md](docs/docker-and-production.md)  
- [docs/ops-raspberry-pi.md](docs/ops-raspberry-pi.md)  
- [docs/cloudflare-tunnel.md](docs/cloudflare-tunnel.md)

---

## Documentation

| Doc | What it’s for |
|-----|----------------|
| [docs/README.md](docs/README.md) | **Index** |
| [docs/PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md) | Agent/human handoff — read first in a new chat |
| [docs/configuration.md](docs/configuration.md) | `.env`, settings, weights, thresholds |
| [docs/scoring-and-alerts.md](docs/scoring-and-alerts.md) | Formulas, late-bubble quorum, banner |
| [docs/runbook-incidenti.md](docs/runbook-incidenti.md) | Fixture, misleading green alert, stale CAPE, 403s |
| [evolutive/](evolutive/) | Backlog (Italian) |
| [piano-strategia.md](piano-strategia.md) | Scenario logic (Italian) |
| [AGENTS.md](AGENTS.md) | Cursor agent rules |

---

## Hard rules

- Do not reintroduce Streamlit as the main UI.  
- Do not turn Yahoo Mag7 back on by default.  
- Do not scrape FINRA HTML “just to try”.  
- Do not add a public “refresh data” control.  
- Do not loop `run_engine --force` from Windows.
