# SP500 AI Bubble Monitor

Repo: **SP500-ai-bubble-monitor**. Monitor di **fragilità vs innesco** per il mercato azionario USA (bolla AI): distingue quanto è "carica la molla" (valutazioni, leva, concentrazione) da cosa storicamente fa scattare il crollo (spread credito, curva, Fed, utili AI).

| Doc | Perché |
|-----|--------|
| [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md) | **Memoria completa** del progetto (handoff chat/agent) |
| [`docs/`](docs/) | Docs tecnici (architettura, fonti, scoring, ops) |
| [`evolutive/`](evolutive/) | Backlog di ciò che manca |
| [`piano-strategia.md`](piano-strategia.md) | Logica di scenario |
| [`AGENTS.md`](AGENTS.md) | Istruzioni per agent Cursor |

UI: **vanilla HTML + CSS + JS** (stile [igedge](../igedge)), server Python read-only. Niente Streamlit.

## Installazione

```bash
cd SP500-ai-bubble-monitor
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

## Esecuzione engine

Aggiorna cache e calcola `data/cache/bubble_state.json`:

```bash
python -m engine.run_engine
```

- `--force` — ignora cache fresca e riscarica (usare con moderazione).
- Ogni modulo è **fail-soft**: download fallito → cache locale o seed.

Preferire **cron/server** per l'engine; sul PC di sviluppo aprire solo la dashboard sulla cache/fixture.

## Dashboard web (igedge-style)

```bash
python scripts/dashboard_web.py
# → http://localhost:8891
```

Porta: `WEB_PORT` (default `8891`, per non collidere con igedge su `8890`).

| Route | Contenuto |
|-------|-----------|
| `/` | `web/dashboard.html` |
| `/api/state` | `data/cache/bubble_state.json` (fallback fixture) |
| `/salute` | healthcheck |

La UI mostra:
- **Alert a tutta larghezza** (rosso/ambra/verde) — capisci subito se siamo vicini allo scoppio
- Card semaforo per ogni indicatore con spiegazione in italiano
- Grafici: radar rischio, gauge, barre fragilità/innesco, serie storiche CAPE / HY OAS / curva / Buffett / recessione
- Watch list + news taggate

Il server è **solo lettura**. I dati li aggiorna l’engine:

```bash
python -m engine.run_engine
```

Fonti scaricate in automatico: FRED, Shiller/multpl (CAPE), FINRA (margin), Slickcharts (pesi Mag7/Top10), NY Fed (prob. recessione), Yahoo Mag7, RSS Fed/mercato.

## Architettura

```
config/settings.json     # soglie, pesi, feed RSS
data/ingestion/          # FRED, Shiller, FINRA, Yahoo Mag7, news
data/cache/              # JSON persistenti (24h default)
engine/
  indicators.py
  scoring.py
  run_engine.py
web/dashboard.html       # UI leggera (CSS tokens igedge)
scripts/dashboard_web.py # ThreadingHTTPServer read-only
tests/                   # pytest offline
```

### Flusso

1. Engine (cron/CLI) → `bubble_state.json`
2. Dashboard → `GET /api/state` ogni 60s
3. Hero = regime; KPI = prossimità / fragilità / innesco / news

## FRED: perché falliva e come si risolve

`fred.stlouisfed.org/graph/fredgraph.csv` da molti IP **va in timeout** (non è “mettilo sul Pi”).
`api.stlouisfed.org` invece **risponde in ~1 secondo**.

1. Crea una API key gratis: https://fredaccount.stlouisfed.org/apikeys  
2. Copia `.env.example` → `.env` nella root del repo e inserisci la key:
   ```env
   FRED_API_KEY=la_tua_chiave_32_char
   ```
3. Rilancia: `python -m engine.run_engine`

(`.env` è in `.gitignore` — non finisce su git.)

**Senza key** l’engine usa comunque fallback live:
Treasury (curva 2s10s), Fed H.15 (fed funds), CurrentMarketValuation (Buffett), TradingEconomics (HY spread), NY Fed XLS (recessione), Slickcharts, Shiller, RSS.

## Fonti

| Fonte | Uso | Note |
|-------|-----|------|
| **FRED API** | Macro ufficiale | Richiede key gratis; host veloce |
| **Treasury / H.15 / CMV / TE** | Fallback macro | Se CSV FRED timeout |
| **Shiller / multpl** | CAPE | |
| **Slickcharts** | Pesi Mag7/Top10 | |
| **NY Fed XLS** | Prob. recessione | |
| **FINRA / mirror** | Margin debt | FINRA spesso 403 |
| **RSS** | News | Yahoo + Fed |
| **Yahoo Mag7** | Off di default | 401/429 |

Cache default **24h**.

## Test

```bash
python -m pytest tests/test_scoring.py -q
python -m py_compile scripts/dashboard_web.py
```

## Disclaimer

Analisi di scenario su dati pubblici. **Non è consulenza finanziaria.**
