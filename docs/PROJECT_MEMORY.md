# PROJECT MEMORY — SP500-ai-bubble-monitor

**Scopo di questo file:** handoff completo per umani e agent Cursor.  
Se apri questo repo in una chat nuova, **leggi prima questo file**, poi `evolutive/README.md`.

Ultimo aggiornamento memoria: **2026-08-10** — + market breadth: SPY/RSP YTD + campione top-40 dist 52w (NASDAQ), senza Yahoo.

---

## 1. Identità progetto

| Campo | Valore |
|-------|--------|
| Nome repo / progetto | **SP500-ai-bubble-monitor** |
| Cartella di test storica | `SP500-bubble-monitor` (appoggio; non è più la home) |
| Brand UI attuale | `SP500 · Bubble Monitor` (da allineare a AI Bubble Monitor) |
| Logica di scenario | [`piano-strategia.md`](../piano-strategia.md) |
| Backlog evolutivo | [`evolutive/`](../evolutive/) |
| UI reference | stile **igedge** (vanilla HTML/CSS/JS + Python `ThreadingHTTPServer`) — **non Streamlit** |
| Produzione target | Raspberry Pi + Docker + cron fetch + **Cloudflare Tunnel** (come Gamtrace) |

**Idea di prodotto:** non prevedere il giorno dello scoppio; misurare:

1. **Fragilità (molla)** — valutazioni, leva, concentrazione, esposizione famiglie  
2. **Innesco** — credito HY, curva, Fed, recessione, utili AI  

Regime tipico del piano: *tarda bolla — molla carica, innesco spento*.

---

## 2. Come si usa (due comandi)

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor

# 1) FETCH + score → scrive data/cache/bubble_state.json
python -m engine.run_engine

# 2) UI read-only (NON scarica dati)
python scripts/dashboard_web.py
# → http://localhost:8891
```

- Cache fresca ~**24h** (`cache_max_age_hours` in `config/settings.json`): l’engine non martella le fonti.
- `--force` riscarica: usare raramente.
- Dashboard: `GET /`, `/api/state`, `/salute` — nessun POST che lancia engine.

**Env:** copiare `.env.example` → `.env` con `FRED_API_KEY` (32 char, gratis su FRED).

---

## 3. Architettura (stato codice)

```
config/settings.json     soglie, pesi, feed RSS, flag fetch
config/env.py            carica .env
data/ingestion/          fetch fail-soft + cache JSON
data/cache/              persistenza locale (anche bubble_state.json)
engine/
  run_engine.py          pipeline
  indicators.py          assembla indicatori
  scoring.py             fragilità / innesco / prossimità / regime
  presentation.py        alert, cards, charts payload
web/dashboard.html       UI + Chart.js + guide popup
scripts/dashboard_web.py server read-only
tests/                   pytest offline
evolutive/               backlog (01–13)
docs/                    questa memoria + docs tecnici
```

Flusso: **engine → `bubble_state.json` → dashboard poll ogni 60s**.

---

## 4. Fonti dati — lezioni anti-ban (CRITICO)

### Usare (sicure / ok da questo IP)
| Fonte | Uso |
|-------|-----|
| **FRED API** `api.stlouisfed.org` | Macro ufficiale — richiede key |
| Treasury / Fed H.15 / CMV | Fallback curva, funds, Buffett |
| Shiller `ie_data.xls` / multpl | CAPE |
| Slickcharts | pesi Mag7/Top10 |
| NY Fed `allmonth.xls` | prob. recessione |
| NASDAQ quote API | Mag7 prices/chg (Yahoo sostituito) |
| SEC EDGAR atom 8-K | filing Mag7 (UA browser-like obbligatorio) |
| RSS Fed (+ Yahoo RSS se regge) | news |

### NON usare / disabilitati
| Fonte | Perché |
|-------|--------|
| `fredgraph.csv` | timeout da molti IP |
| Yahoo chart/quote Mag7 | 429 — `fetch_yahoo_mag7: false` |
| FINRA HTML | 403 — non scrapeare |
| MarketWatch / Stooq HTML | anti-bot |
| Engine live ripetuto dal PC Windows | rischio ban (stesso problema Gamtrace/Yahoo) |

### Margin
- Priorità (2026-08-10): **FINRA.org tabella ufficiale** → mirror CSV thetrading.tools → FRED Z.1 proxy → seed.
- Piano: FINRA debit ~$1.50–1.53T, YoY ~49–51%. XLS diretto FINRA spesso 403; la **pagina HTML** e il **CSV mirror** rispondono 200.
- FRED Z.1 resta solo fallback (metodologia diversa, ~$622B).

### CAPE — attenzione
- Seed piano: **41.9**.
- Live da XLS a volte **stale** (visto ~33.3 con `as_of` 2023-09) → score moderato.
- Sempre controllare `cape_as_of` / `cape_source` in `data_quality`.

### Buffett
- Serie FRED World Bank spesso ferma al 2020.
- Preferire **Current Market Valuation (CMV)** quando FRED è stale (già implementato in `alt_macro`).

---

## 5. Scoring e alert — bug/comportamento noto

### Soglie alert (`engine/presentation.py` → `build_alert`)
- `frag ≥ 70` + innesco basso → **TARDA BOLLA — INNESCO ANCORA SPENTO** (amber)
- `frag ≥ 55` → VIGILANZA
- sotto → **RISCHIO CONTENUTO** (green)

### Fix fatto 2026-08-10
- CAPE stale Shiller → **multpl live** (~42.4)
- Margin proxy Z.1: peso ridotto + blend livello/YoY + disclaimer in card
- Quorum: 2+ tra CAPE/Buffett/household estremi → fragilità almeno 72 → **TARDA BOLLA** se innesco spento
- Test: `test_alert_not_green_when_valuations_extreme_but_margin_proxy_flat`

### Pesi fragilità attuali (`settings.json`)
`cape 0.22`, `buffett 0.18`, `household 0.15`, `concentration 0.20`, `margin_debt 0.25`.

### Watch order (fisso dal piano)
1. Fed restrittiva  
2. Stress credito (HY)  
3. Utili AI / Mag7  

---

## 6. UI — fatti noti

- Stile igedge: CSS tokens, alert hero, KPI, card semaforo, Chart.js.
- Sezioni: Fragilità, Innesco, Sotto la superficie, Watch, News.
- **Bug risolto 2026-08-09:** `fact()` mancava → JS crash → sezioni under/watch/news vuote. Ora `fact()` + CSS `.facts` + try/catch.
- **Guide:** bottone “Guida” su ogni card → modal con testo in `GUIDES` dentro `web/dashboard.html`.
- News spesso **untagged** e `news_risk` 0 — tagging da migliorare.
- 8-K SEC mostrano titoli generici “Current report”.

---

## 7. Produzione richiesta (piano + evolutive/13)

Ancora **da fare** (non in codice al momento della memoria):

1. Docker completo (dashboard + engine)  
2. Fetch automatico via cron sul Pi  
3. Cloudflare Tunnel su dominio (come Gamtrace)  
4. Cartella `docs/` minuziosa (questa è l’inizio)  
5. Rename brand/path ovunque → `SP500-ai-bubble-monitor`  

Dettaglio checklist: [`evolutive/13-docker-tunnel-docs-rename.md`](../evolutive/13-docker-tunnel-docs-rename.md).

**Regola ops (stile Gamtrace):**  
PC Windows = sviluppo + test offline.  
Fetch live aggressivo = sul Pi.  
Prima di suggerire deploy: pytest/import locali; `sed -i 's/\r$//' scripts/pi/*.sh` dopo copia da Windows.

---

## 8. File chiave da toccare

| Obiettivo | File |
|-----------|------|
| Pipeline fetch | `engine/run_engine.py` |
| Score / regime | `engine/scoring.py` |
| Alert / card | `engine/presentation.py` |
| UI | `web/dashboard.html` |
| Server | `scripts/dashboard_web.py` |
| Soglie/pesi | `config/settings.json` |
| FRED | `data/ingestion/fred.py`, `alt_macro.py` |
| Margin | `finra_margin.py`, `fred_margin.py` |
| Mag7 no-Yahoo | `nasdaq_quotes.py`, `yahoo_prices.py` (off) |
| Under surface | `under_surface.py`, `market_drawdown.py`, `sec_filings.py` |
| Backlog | `evolutive/*.md` |

---

## 9. Stato osservato (run 2026-08-09)

Valori tipici visti in dashboard dopo fetch live (indicativi):

- Alert: **RISCHIO CONTENUTO** (frag ~51, trig ~20, prox ~34) — *fuorviante rispetto al piano*
- Buffett ~219%, household ~45.8%, Mag7 weight ~30.8%, Top10 ~36.8%
- HY ~271 bp (compiacenza), curve ~46 bp, recession ~26.5%
- Margin Z.1 ~$622B, YoY ~2.1%, source proxy
- CAPE ~33.3 con as_of vecchio (problema qualità)
- SPX last ~7757, dist 52w ~0%, YTD ~13%
- `still_seed`: [] dopo integrazioni FRED/NASDAQ/SEC
- pytest: **7 passed** (al momento del handoff)

---

## 10. Cosa NON rifare

- Non reintrodurre Streamlit come UI principale.  
- Non riattivare Yahoo Mag7 di default.  
- Non scrapeare FINRA HTML “tanto per”.  
- Non aggiungere bottone “Aggiorna dati” sulla dashboard pubblica.  
- Non sostituire `evolutive/` con un unico TODO vago: tenere file tematici.  
- Non cancellare questa memoria senza migrarla.

---

## 11. Prossimi passi consigliati (ordine)

1. Fix alert/scoring (quorum tarda-bolla + margin/CAPE)  
2. CAPE fresco + badge `as_of` in UI  
3. Disclaimer margin Z.1 vs FINRA  
4. Docker + docs ops + tunnel (produzione)  
5. Under-surface: breadth / drawdown medio titoli  
6. News tagging + utili Mag7 veri  

---

## 12. Transcript chat Cursor

La conversazione di scaffolding viveva nel workspace multi-root / path vecchio.  
I transcript agent Cursor **non** si spostano automaticamente col rename della cartella.  
Questa `docs/PROJECT_MEMORY.md` + `evolutive/` sono la memoria portabile del progetto.
