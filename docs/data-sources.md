# Data sources

Principio: **probe prima, implementa dopo**. Nessuna fonte nuova senza test status/ban.

## Matrice

| Indicatore | Fonte primaria | Fallback | Note |
|------------|----------------|----------|------|
| HY OAS | FRED API `BAMLH0A0HYM2` | TE / altri alt | |
| 2s10s | FRED `T10Y2Y` | Treasury | |
| Fed funds | FRED `DFF` | H.15 | |
| Buffett | CMV preferito se WB stale | FRED `DDDM01USA156NWDB` | WB spesso 2020 |
| Household equity | FRED Z.1 | — | record vs Dot-com 38.7% |
| GDP | FRED `GDP` | — | |
| CAPE | Shiller XLS | multpl / seed 41.9 | verificare stale |
| Margin FINRA | FINRA.org margin-statistics (tabella) | Mirror CSV thetrading.tools → FRED Z.1 → seed | Debit balances ufficiali; xlsx diretto spesso 403 |
| Pesi Mag7/Top10 | Slickcharts | — | |
| Mag7 quote | NASDAQ API | Yahoo OFF | |
| SPX drawdown | FRED `SP500` | — | |
| Recession | NY Fed XLS | — | |
| 8-K Mag7 | SEC atom | — | UA corretto |
| News | RSS Fed (+ Yahoo RSS) | — | tagging debole |

## Vietate / rischiose

- `fred.stlouisfed.org/graph/fredgraph.csv` — timeout  
- Yahoo v8/chart Mag7 — 429  
- FINRA pages — 403  
- Stooq/MarketWatch HTML — anti-bot  

## Cache

- Path: `data/cache/`  
- Freshness: `is_cache_fresh()` + `cache_max_age_hours`  
- Output UI: `bubble_state.json`  
- Probe temporanei `_probe*` andrebbero gitignored/puliti  

## data_quality

Il blocco in `bubble_state.json` elenca `*_source`, `fred_alts_used`, `news_items`, presenza API key. Usarlo in UI footer (già parziale).
