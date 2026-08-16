# PROJECT MEMORY — SP500-ai-bubble-monitor

**Purpose:** full handoff for humans and Cursor agents.  
On a new chat, **read this file first**, then `evolutive/README.md`.

Last memory update: **2026-08-16** — technical docs in English (detailed config, Pi ops, tunnel, runbook). Live run 2026-08-15: late bubble / trigger off.

---

## 1. Project identity

| Field | Value |
|-------|--------|
| Author | **Antonio Trento** — [antoniotrento.net](https://antoniotrento.net) |
| Repo / project name | **SP500-ai-bubble-monitor** |
| Historical test folder | `SP500-bubble-monitor` (scratch; no longer home) |
| Current UI brand | `SP500 · Bubble Monitor` (still to align to AI Bubble Monitor) |
| Scenario logic | [`piano-strategia.md`](../piano-strategia.md) (Italian) |
| Evolutive backlog | [`evolutive/`](../evolutive/) (Italian) |
| UI reference | **igedge** style (vanilla HTML/CSS/JS + Python `ThreadingHTTPServer`) — **not Streamlit** |
| Production target | Raspberry Pi + Docker + cron fetch + **Cloudflare Tunnel** (like Gamtrace) |

**Product idea:** do not predict the day it pops; measure:

1. **Fragility (the spring)** — valuations, leverage, concentration, household exposure  
2. **Trigger (the spark)** — HY credit, curve, Fed, recession, AI earnings  

Typical regime in the strategy note: *late bubble — spring coiled, trigger still off*.

---

## 2. How to run it (two commands)

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor

# 1) FETCH + score → writes data/cache/bubble_state.json
python -m engine.run_engine

# 2) Read-only UI (does NOT download data)
python scripts/dashboard_web.py
# → http://localhost:8891
```

- Fresh cache ~**24h** (`cache_max_age_hours` in `config/settings.json`): the engine does not hammer sources.
- `--force` refetches: use rarely.
- Dashboard: `GET /`, `/api/state`, `/salute` — no POST that launches the engine.

**Env:** copy `.env.example` → `.env` with `FRED_API_KEY` (32 chars, free on FRED). Detail: [configuration.md](configuration.md).

---

## 3. Architecture (code as it is)

```
config/settings.json     thresholds, weights, RSS feeds, fetch flags
config/env.py            loads .env
data/ingestion/          fail-soft fetch + JSON cache
data/cache/              local persistence (including bubble_state.json)
engine/
  run_engine.py          pipeline
  indicators.py          assembles indicators
  scoring.py             fragility / trigger / proximity / regime
  presentation.py        alert, cards, charts payload
web/dashboard.html       UI + Chart.js + guide popup
scripts/dashboard_web.py read-only server
tests/                   offline pytest
evolutive/               backlog (01–13)
docs/                    handoff + config + sources + scoring + dashboard + ops/runbook
```

Flow: **engine → `bubble_state.json` → dashboard poll every 60s**.

---

## 4. Data sources — anti-ban lessons (CRITICAL)

### Use (safe / OK from this IP)

| Source | Use |
|--------|-----|
| **FRED API** `api.stlouisfed.org` | Official macro — needs a key |
| Treasury / Fed H.15 / CMV | Fallback curve, funds, Buffett |
| Shiller `ie_data.xls` / multpl | CAPE |
| Slickcharts | Mag7/Top10 weights |
| NY Fed `allmonth.xls` | Recession probability |
| NASDAQ quote API | Mag7 prices/chg (Yahoo replacement) |
| SEC EDGAR atom 8-K | Mag7 filings (browser-like UA required) |
| Fed RSS (+ Yahoo RSS if it holds) | news |

### Do not use / disabled

| Source | Why |
|--------|-----|
| `fredgraph.csv` | timeout from many IPs |
| Yahoo chart/quote Mag7 | 429 — `fetch_yahoo_mag7: false` |
| FINRA HTML | 403 — do not scrape |
| MarketWatch / Stooq HTML | anti-bot |
| Repeated live engine from a Windows PC | ban risk (same issue as Gamtrace/Yahoo) |

### Margin

- Priority (2026-08-10): **official FINRA.org table** → thetrading.tools CSV mirror → FRED Z.1 proxy → seed.
- Strategy note: FINRA debit ~$1.50–1.53T, YoY ~49–51%. Direct FINRA XLS often 403; the **HTML page** and **CSV mirror** return 200.
- FRED Z.1 is fallback only (different methodology, ~$622B).

### CAPE — caution

- Strategy seed: **41.9**.
- Live XLS is sometimes **stale** (seen ~33.3 with `as_of` 2023-09) → moderate score.
- Always check `cape_as_of` / `cape_source` in `data_quality`.

### Buffett

- FRED World Bank series often stops at 2020.
- Prefer **Current Market Valuation (CMV)** when FRED is stale (already implemented in `alt_macro`).

---

## 5. Scoring and alerts — known behavior

### Alert cutoffs (`engine/presentation.py` → `build_alert`)

- `frag ≥ 70` + low trigger → **TARDA BOLLA — INNESCO ANCORA SPENTO** (amber)
- `frag ≥ 55` → VIGILANZA ELEVATA
- below → **RISCHIO CONTENUTO** (green)

### Fix shipped 2026-08-10

- Stale Shiller CAPE → **live multpl** (~42.4)
- Z.1 margin proxy: reduced weight + level/YoY blend + card disclaimer
- Quorum: 2+ of CAPE/Buffett/household extreme → fragility at least 72 → **TARDA BOLLA** if trigger is off
- Test: `test_alert_not_green_when_valuations_extreme_but_margin_proxy_flat`

### Current fragility weights (`settings.json`)

`cape 0.25`, `buffett 0.22`, `household 0.18`, `concentration 0.20`, `margin_debt 0.15` (Z.1 source → margin weight ×0.45).

### Watch order (fixed from the strategy note)

1. Restrictive Fed  
2. Credit stress (HY)  
3. AI / Mag7 earnings  

---

## 6. UI — known facts

- igedge style: CSS tokens, alert hero, KPIs, traffic-light cards, Chart.js.
- Sections: Fragility, Trigger, Under the surface, Watch, News.
- **Bug fixed 2026-08-09:** missing `fact()` → JS crash → empty under/watch/news. Now `fact()` + CSS `.facts` + try/catch.
- **Guides:** “Guida” button on each card → modal with copy in `GUIDES` inside `web/dashboard.html`.
- News often **untagged** and `news_risk` 0 — tagging still to improve.
- SEC 8-K titles are generic “Current report”.

---

## 7. Required production (strategy note + evolutive/13)

Still **to build** (not in code at this memory):

1. Full Docker (dashboard + engine)  
2. Automatic fetch via cron on the Pi  
3. Cloudflare Tunnel on a domain (like Gamtrace)  
4. `docs/` folder — **index + config/ops/runbook written** (2026-08-16, English); Docker/tunnel still contract-only, not code  
5. Brand/path rename everywhere → `SP500-ai-bubble-monitor`  

Checklist: [`evolutive/13-docker-tunnel-docs-rename.md`](../evolutive/13-docker-tunnel-docs-rename.md).

**Ops rule (Gamtrace style):**  
Windows PC = development + offline tests.  
Aggressive live fetch = on the Pi.  
Before suggesting deploy: local pytest/imports; `sed -i 's/\r$//' scripts/pi/*.sh` after copying from Windows.

---

## 8. Key files to touch

| Goal | File |
|------|------|
| Fetch pipeline | `engine/run_engine.py` |
| Score / regime | `engine/scoring.py` |
| Alert / cards | `engine/presentation.py` |
| UI | `web/dashboard.html` |
| Server | `scripts/dashboard_web.py` |
| Thresholds/weights | `config/settings.json` |
| FRED | `data/ingestion/fred.py`, `alt_macro.py` |
| Margin | `finra_margin.py`, `fred_margin.py` |
| Mag7 no-Yahoo | `nasdaq_quotes.py`, `yahoo_prices.py` (off) |
| Under surface | `under_surface.py`, `market_drawdown.py`, `sec_filings.py` |
| Backlog | `evolutive/*.md` |

---

## 9. Observed state

### Run 2026-08-15 (this repo, FRED key, one Windows fetch)

- Alert: **TARDA BOLLA — INNESCO ANCORA SPENTO** (frag 77.3, trig 22.6, prox 59.3)
- CAPE 42.56 (multpl, `as_of` 2026-08-01); Shiller XLS 404
- Buffett 219% (CMV); household 45.8%; Mag7 30.4%; Top10 36.1%
- Margin **FINRA mirror** $1417B, YoY +38.6% (FINRA page 403)
- HY 271 bp, curve +51 bp, Fed funds 3.63%, SPX 7786 (−0.2% 52w, YTD +13.5%)
- Breadth sample: avg dist 52w ~−14%; Mag7 avg dist 52w ~−15%
- NY Fed XLS: failed without `xlrd` (not in requirements)
- `still_seed`: []; `fred_api_key_present`: true
- First fetch ~10 min (rate limit + breadth 40)

### Run 2026-08-09 (historical, pre quality-fix)

- Alert: **RISCHIO CONTENUTO** (frag ~51, trig ~20, prox ~34) — *misleading vs the strategy note*
- Buffett ~219%, household ~45.8%, Mag7 weight ~30.8%, Top10 ~36.8%
- HY ~271 bp (complacency), curve ~46 bp, recession ~26.5%
- Margin Z.1 ~$622B, YoY ~2.1%, proxy source
- CAPE ~33.3 with old `as_of` (quality issue)
- SPX last ~7757, dist 52w ~0%, YTD ~13%
- pytest: **7 passed** (at handoff time)

---

## 10. Do not redo

- Do not reintroduce Streamlit as the main UI.  
- Do not re-enable Yahoo Mag7 by default.  
- Do not scrape FINRA HTML “just because”.  
- Do not add a “Refresh data” button on the public dashboard.  
- Do not replace `evolutive/` with one vague TODO: keep thematic files.  
- Do not delete this memory without migrating it.

---

## 11. Suggested next steps (order)

1. ~~Alert/scoring fix (quorum + margin/CAPE)~~ done 2026-08-10  
2. ~~Fresh CAPE (multpl) + quality docs~~ partial; UI `as_of` badge still to verify  
3. ~~FINRA-mirror margin + Z.1 disclaimer~~  
4. Docker + Pi cron + Cloudflare Tunnel (code; ops docs already written)  
5. `xlrd` in requirements for NY Fed  
6. News tagging + less generic 8-K; average drawdown of all 500 (today a 40-name sample)  

---

## 12. Cursor chat transcripts

The scaffolding conversation lived in a multi-root workspace / old path.  
Cursor agent transcripts **do not** move automatically when the folder is renamed.  
This `docs/PROJECT_MEMORY.md` + `evolutive/` are the portable project memory.
