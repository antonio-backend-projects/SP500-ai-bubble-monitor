# Data sources

Principle: **probe first, implement after**. No new source without a status/ban test. Default TTL: `cache_max_age_hours` (24). Pacing: `rate_limit_min_sec`–`max_sec` (3–8s; soft 1–2s).

## Matrix (code as of 2026-08)

| Indicator | Primary | Fallback | Ban / notes |
|-----------|---------|----------|-------------|
| HY OAS | FRED API `BAMLH0A0HYM2` | TradingEconomics / seed | Do not use `fredgraph.csv` (timeout) |
| 2s10s | FRED `T10Y2Y` | Treasury daily | |
| Fed funds | FRED `DFF` | Fed H.15 | |
| Buffett | **CMV** `currentmarketvaluation.com` if WB is stale | FRED `DDDM01USA156NWDB` | WB often stuck at 2020. CMV ~219% ≠ ~234% cited in the strategy note (same direction) |
| Household equity | FRED Z.1 `BOGZ1FL153064486Q` | — | Record vs Dot-com 38.7% |
| GDP | FRED `GDP` | — | |
| CAPE | Shiller `ie_data.xls` | **multpl.com shiller-pe** if XLS 404 or `as_of` > 120 days | Strategy seed 41.9. Shiller wsimg URL 404 (2026-08-15) |
| Margin | FINRA.org margin-statistics (HTML) | **CSV mirror** `thetrading.tools` → FRED Z.1 `BOGZ1FL663067003Q` → seed | FINRA XLS and often the page → 403. Z.1 ≠ FINRA debit (~$0.6T vs ~$1.4T) |
| Mag7/Top10 weights | Slickcharts `/sp500` | — | |
| Mag7 quote / chg | NASDAQ quote API | Yahoo **OFF** | |
| Mag7 EPS surprise | NASDAQ earnings-surprise | — | |
| SPX last / 52w / YTD | FRED `SP500` | — | |
| Breadth | NASDAQ historical SPY + RSP + top-N quote sample | — | Slow part of the fetch |
| Recession | NY Fed `allmonth.xls` | seed 25% | Needs `xlrd>=2.0.1` (not in requirements) |
| Mag7 8-K | SEC EDGAR atom | — | Browser-like User-Agent required |
| News | Fed + CNBC + BBC RSS | — | Keyword tagging; many Fed headlines = `fed_policy` |

## Reference URLs (do not hammer by hand)

- FRED API: `https://api.stlouisfed.org/fred/series/observations?series_id=…&api_key=…&file_type=json`
- Shiller: `http://www.econ.yale.edu/~shiller/data/ie_data.xls` (wsimg mirror sometimes 404)
- Multpl: Shiller PE page (parser in `multpl_cape.py`)
- FINRA: `https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics`
- Margin mirror: `https://www.thetrading.tools/data/indicators/margin-debt.csv`
- NY Fed: `https://www.newyorkfed.org/medialibrary/media/research/capital_markets/allmonth.xls`
- NASDAQ quote: `https://api.nasdaq.com/api/quote/{SYM}/…` with Origin/Referer nasdaq.com
- SEC: 8-K atom per Mag7 CIK

## Banned / risky

| Source | Why |
|--------|-----|
| `fred.stlouisfed.org/graph/fredgraph.csv` | Timeout from many IPs |
| Yahoo v8 chart/quote Mag7 | 429 — `fetch_yahoo_mag7: false` |
| Direct FINRA xlsx | Frequent 403; do not retry-loop |
| Stooq / MarketWatch HTML | Anti-bot |
| Repeated engine `--force` from a Windows PC | Same IP, same Gamtrace/Yahoo problem |

## Cache

- Path: `data/cache/`
- One JSON per source (`fred_bundle.json`, `finra_margin.json`, `shiller_cape.json`, …) plus `bubble_state.json`
- Temporary `_probe*` files must stay gitignored
- `data_quality` in `bubble_state.json`: `*_source`, `fred_alts_used`, `fred_api_key_present`, `news_items` / `news_tagged`

## Quality checklist (after every live run)

1. `cape_source` + `cape_as_of` — if Shiller is stale, this should be **multpl** with a recent month  
2. `margin_source` — should contain `finra` or `thetrading.tools`, not only `Z.1` / `proxy`  
3. `still_seed` empty  
4. `fred_api_key_present: true`

Reference run 2026-08-15 (Windows, one fetch): CAPE multpl 42.56 `as_of` 2026-08-01; FINRA-mirror margin $1417B YoY +38.6%; FRED API ok; Shiller XLS 404; FINRA HTML 403; NY Fed failed (missing `xlrd`).
