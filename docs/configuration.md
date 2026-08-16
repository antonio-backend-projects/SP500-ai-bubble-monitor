# Configuration

How to configure the monitor **from scratch**: what belongs in `.env` vs `settings.json`, and what is **not** configurable (it lives in code).

| File | Holds | Secrets? |
|------|--------|----------|
| `.env` | `FRED_API_KEY`, optional `WEB_PORT` | Yes — gitignored |
| `.env.example` | Empty template | No |
| `config/settings.json` | Cache TTL, rate limit, tickers, FRED series, thresholds, weights, RSS | No — do not put the key here |
| `config/env.py` | `.env` loader | — |
| `engine/presentation.py` | **Alert banner** cutoffs (70 / 55 / 40) | No — code only |
| `engine/scoring.py` | Score formulas + late-bubble quorum | No — code only |

After any change to `.env` or `settings.json`, **restart** the engine and/or dashboard: `load_settings()` and `load_env()` cache in-process.

---

## 1. `.env` setup (required for live data)

### Windows (PowerShell)

```powershell
cd C:\Users\hp\Documents\GitHub\SP500-ai-bubble-monitor
copy .env.example .env
notepad .env
```

### Linux / Raspberry Pi (bash)

```bash
cd ~/SP500-ai-bubble-monitor   # adjust path
cp .env.example .env
nano .env
```

Minimum contents:

```env
FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# WEB_PORT=8891
```

- `FRED_API_KEY` — 32 characters, **free**: [create a key on FRED](https://fredaccount.stlouisfed.org/apikeys)
- `WEB_PORT` — default `8891` (igedge often uses `8890`; do not collide)
- `.env` is in `.gitignore`. Do not commit it. Do not paste the key into issues or chat.

Code also accepts `FRED_KEY`. Prefer `FRED_API_KEY`.

### How to get a FRED key

1. Account at https://fred.stlouisfed.org/
2. https://fredaccount.stlouisfed.org/apikeys → **Create API key**
3. Paste into `.env` with no spaces or quotes
4. Check: `python -m engine.run_engine` should log `FRED … via API ok` and `bubble_state.json` → `data_quality.fred_api_key_present: true`

### Key resolution order

`data/ingestion/fred.py` → `_resolve_api_key()`:

1. Environment / `.env` (`FRED_API_KEY` or `FRED_KEY`)
2. Legacy `config/settings.json` → `fred_api_key` (leave `""`)
3. Legacy files `config/fred_api_key.txt` or `config/.fred_api_key` (gitignored)

**Use `.env` only.** A key in `settings.json` would land in git.

### Without a key

The engine **does not crash**. FRED API is skipped; fallbacks remain (`alt_macro`: Treasury, H.15, CMV, …) then cache then seed. Macro is partial and scores are less reliable. The dashboard still starts (fixture if `bubble_state.json` is missing).

---

## 2. `config/settings.json` — field reference

There is no schema validation yet (gap: `evolutive/10`). Malformed JSON → crash on start. After an edit:

```powershell
python -c "import json; json.load(open('config/settings.json', encoding='utf-8')); print('settings ok')"
```

### Fetch / anti-ban

| Key | Default | Effect |
|-----|---------|--------|
| `cache_max_age_hours` | `24` | If the JSON in `data/cache/` is fresher, ingestion **does not** refetch (unless `--force`) |
| `rate_limit_min_sec` | `3.0` | Minimum pause between HTTP calls |
| `rate_limit_max_sec` | `8.0` | Maximum pause (jitter). With `soft=True` (NASDAQ/RSS) this drops to 1–2s |
| `fetch_yahoo_mag7` | `false` | **Keep false.** Yahoo Mag7 429s |
| `fetch_nasdaq_mag7` | `true` | Mag7 quotes via NASDAQ API |
| `breadth_sample_n` | `40` | How many Slickcharts names to sample for 52-week distance. Higher = longer fetch |
| `mag7` | AAPL MSFT NVDA AMZN GOOGL META TSLA | Mag7 tickers (quotes, 8-K, earnings) |
| `index_proxy` | `SPY` | Cap-weight ETF for breadth vs RSP |

First fetch with `breadth_sample_n: 40` and 3–8s pacing can take **~8–12 minutes**. Later runs with a fresh cache are fast.

### FRED series

`fred_series` maps an internal name → series id. Changing an id changes the indicator, not just the label.

| Internal name | Series id | Indicator |
|---------------|-----------|-----------|
| `hy_oas` | `BAMLH0A0HYM2` | ICE BofA HY OAS (bp) |
| `yield_curve_2s10s` | `T10Y2Y` | 10y−2y (%) |
| `fed_funds` | `DFF` | Effective fed funds |
| `buffett_indicator` | `DDDM01USA156NWDB` | Market cap/GDP World Bank — often **stale at 2020**; CMV takes over |
| `household_equity_pct` | `BOGZ1FL153064486Q` | Equity % of household financial assets |
| `gdp` | `GDP` | Nominal GDP |

Leave `fred_api_key` in this file as `""`.

### News

| Key | Role |
|-----|------|
| `news_feeds` | RSS URLs (Fed monetary, Fed all, CNBC, BBC business) |
| `news_keywords` | Families → substring lists. A hit tags the item and increments the tally |

Families: `fed_policy`, `fed_hawkish`, `credit_stress`, `ai_earnings`, `recession`.  
The news score is **not** in settings: formula in `data/ingestion/news_feed.py` (`analyze_news`).

---

## 3. Thresholds — what they mean

Used by `engine/scoring.py` to map a raw value → 0–100 (`_lerp_score` between two anchors). These are **not** the banner cutoffs (those live in `presentation.py`).

| Block | Fields | Reading |
|-------|--------|---------|
| `cape` | `median` 16, `dotcom` 44, `extreme` 40 | Score 0 at 16, 100 at 44. `extreme` 40 is for cards/UI, not the lerp |
| `buffett_pct` | `fire` 200, `extreme` 230 | Lerp from 160 (`fire−40`) to 230 |
| `household_equity_pct` | `dotcom` 38.7, `extreme` 45 | Lerp from 33.7 to 47 |
| `mag7_weight_pct` | `elevated` 25, `extreme` 33 | Lerp from 25 to 38 (`extreme+5`) |
| `hy_oas_bp` | `complacent` 350, `stress` 500 | **High** OAS = trigger. Lerp from 270 to 500. 271 bp → credit score ~0 |
| `recession_prob_pct` | `amber` 25, `red` 40 | Lerp from 15 to 55 |
| `margin_debt_yoy_pct` | `elevated` 20, `extreme` 40 | YoY lerp from 20 to 55 |
| `margin_debt_billion` | `elevated` 800, `extreme` 1400 | Level lerp from 440 to 1400 (**FINRA** scale). On Z.1 (~$600B) this is only indicative |

Raising `extreme` / `stress` makes a 100 score harder. Lowering `median` / `fire` raises the score at the same live value.

---

## 4. Weights — current values

From `config/settings.json` (checked 2026-08-16). Older project memory cited `margin 0.25` / `cape 0.22`: **that is outdated**.

### Fragility

| Key | Weight | Notes |
|-----|--------|-------|
| `cape` | 0.25 | |
| `buffett` | 0.22 | |
| `concentration` | 0.20 | Mag7 weight, not Top 10 |
| `household_equity` | 0.18 | |
| `margin_debt` | 0.15 | If `margin_source` is Z.1 proxy / `bogz1`, weight is **× 0.45** in `build_scores` |

Weights are not renormalized to 1 if you zero one out: `weighted_mean` renormalizes over weights > 0.

### Trigger

| Key | Weight |
|-----|--------|
| `hy_oas` | 0.35 |
| `recession_prob` | 0.20 |
| `yield_curve` | 0.15 |
| `fed_path` | 0.15 |
| `ai_earnings_risk` | 0.15 |

`ai_earnings_risk` is not a settings threshold: the engine blends news + NASDAQ EPS surprise + SEC 8-K.

### Bubble proximity (`composite`)

`0.55 * fragility + 0.30 * trigger + 0.15 * news`

Profiles such as `piano` / `conservative` / `credit_first` **do not exist** yet (`evolutive/10`).

---

## 5. What is not in settings

| Behavior | Where | Values |
|----------|-------|--------|
| Alert banner | `engine/presentation.py` `build_alert` | frag 70 / 55; trig 55 / 40 / 45 |
| Late-bubble quorum | `scoring.py` + `presentation.py` | 2+ of CAPE/Buffett/household with part score ≥ 75 → fragility at least **72** |
| Margin YoY/level blend | `score_margin_combined` | FINRA: 65% YoY + 35% level; Z.1: `max(YoY, level×0.85)` |
| Stale CAPE | `shiller_cape.py` | `MAX_CAPE_AGE_DAYS = 120` → multpl fallback |
| Watch order | `scoring.py` `WATCH_ORDER` | Fed → credit → AI earnings |
| UI guide copy | `web/dashboard.html` `GUIDES` object | |
| Bind address | `scripts/dashboard_web.py` | `0.0.0.0:WEB_PORT` |

Changing “when is it a late bubble” is **not** a JSON edit: change Python and re-run tests.

---

## 6. Engine CLI flags

```powershell
python -m engine.run_engine          # respects 24h cache
python -m engine.run_engine --force  # refetch everything
```

`--force` from a Windows PC: **once**, never in a loop. Production: a dedicated weekly job, not the daily cron.

---

## 7. Verify you are on the config you think you are

```powershell
# Valid JSON
python -c "import json; json.load(open('config/settings.json', encoding='utf-8')); print('settings ok')"

# Key loaded (prints yes/no only, not the value)
python -c "from config.env import get_secret; k=get_secret('FRED_API_KEY'); print('FRED key:', 'set' if k else 'MISSING', 'len', len(k or ''))"

# After an engine run
python -c "import json; s=json.load(open('data/cache/bubble_state.json', encoding='utf-8')); q=s['data_quality']; print('key', q.get('fred_api_key_present')); print('cape', q.get('cape_source'), s['indicators'].get('cape_as_of')); print('margin', q.get('margin_source')); print('alert', s['alert']['headline'])"
```

Always check `cape_as_of`, `cape_source`, `margin_source` in `data_quality`. A CAPE of 33 with `as_of` 2023 is **not** “the market is safe”.

---

## 8. Do not

- Put `FRED_API_KEY` in `settings.json` or in a commit.
- Set `fetch_yahoo_mag7: true` “to see if it works now”.
- Raise `breadth_sample_n` to 500 from a laptop (NASDAQ ban).
- Drop `rate_limit_*` below 1s on a residential IP.
- Expect saving `settings.json` to be enough: **restart** the processes.
- Read a green alert plus extreme Buffett/household and flat Z.1 margin as a market signal: that was the old aggregation defect (now mitigated by quorum + proxy weight).
