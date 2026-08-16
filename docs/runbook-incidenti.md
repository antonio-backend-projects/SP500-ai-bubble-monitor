# Incident runbook

What to do when the dashboard lies, the cache is dead, or a source is down. This is monitor ops, not market advice.

## 1. I see “late bubble 91” numbers but it is a fixture

**Symptom:** `_trust` / label **FIXTURE DI TEST**; `updated_at` frozen (e.g. 2026-08-09 in the sample).

**Cause:** missing `data/cache/bubble_state.json`.

**Fix:**

```powershell
python -m engine.run_engine
# then reload http://localhost:8891
```

Do not treat the fixture as a signal.

## 2. Green alert with record Buffett/household

**Symptom:** headline **RISCHIO CONTENUTO** while Buffett ≥ 200% and household ≥ 45%.

**Historical cause:** stale Shiller CAPE (~33, `as_of` 2023) + low Z.1 margin YoY zeroed the average. That does **not** mean the market is safe.

**Check in** `/api/state`:

- `data_quality.cape_source` / `indicators.cape_as_of`
- `data_quality.margin_source` (Z.1 vs FINRA/thetrading.tools)
- `parts.fragility` for cape / buffett / household

**Expected today:** quorum (2+ extremes → fragility ≥ 72) and reduced Z.1 weight. If it is green again, that is a regression: do not hand-edit JSON; open `evolutive/05` and `tests/test_presentation.py`.

## 3. CAPE too low vs the strategy note (~42)

**Symptom:** CAPE 30–34, moderate fragility score.

**Cause:** Shiller XLS 404 or an old file. Correct fallback = **multpl** with current-month `as_of`.

**Fix:** do not `--force` in a burst. If the stale Shiller cache is < 24h old, wait or `--force` **once**. Check `cape_source`. Seed 41.9 only if both sources are dead.

## 4. Margin ~$600B / YoY ~2%

**Symptom:** calm margin card; proxy disclaimer.

**Cause:** FINRA HTML 403 and CSV mirror down → FRED Z.1 (different methodology).

**Fix:** accept the proxy at reduced weight; do not scrape FINRA. When the mirror returns, the next fetch (or one `--force` on the Pi) restores ~$1.4T. Compare `margin_source`.

## 5. Recession stuck at 25% seed

**Symptom:** `recession_source` seed; log `Import xlrd failed`.

**Fix:**

```powershell
pip install "xlrd>=2.0.1"
# on the Pi, one engine run (NY Fed cache not fresh, or --force once)
```

Do not add an HTML scrape of the NY Fed.

## 6. FRED timeout / `fred_api_key_present: false`

**Cause:** missing `.env`, bad key, or something still hitting `fredgraph.csv` (must not happen in current code).

**Fix:** 32-char key in `.env`, restart engine. Treasury/H.15/CMV fallbacks keep pieces alive, not everything. See [configuration.md](configuration.md).

## 7. Engine “stuck” 10+ minutes

**Normal** on the first fetch: 3–8s rate limit × `breadth_sample_n` (40) + Shiller retries. Watch the logs: after `News digest` comes `Breadth`. Do not kill at the first silence.

If it sits **beyond ~20 min** on the same URL: Ctrl+C, reuse partial cache, no immediate `--force`.

## 8. Corrupt cache / invalid JSON

**Symptom:** `/api/state` with `error`, or a blank dashboard.

```powershell
# Windows: move suspect JSON; do not wipe the whole cache unless needed
mkdir data\cache\broken -ErrorAction SilentlyContinue
move data\cache\bubble_state.json data\cache\broken\
python -m engine.run_engine
```

Without state the dashboard falls back to the fixture. An honest fixture beats a half-written JSON.

## 9. `updated_at` older than 36h (production)

Dead engine cron or fail-soft fetch onto an old seed.

1. Cron / engine container logs
2. `curl /salute` (dashboard can be up on stale data)
3. One engine run **on the Pi**, not the laptop
4. Optional (not in code yet): Telegram alert if stale > 36h

## 10. Burst of 429 / 403

Stop. No `--force`. Raise `rate_limit_*` in settings, wait 24h, fetch from the Pi. Yahoo Mag7 stays **off**. A 403 on the official FINRA page is expected: fall through to the mirror, not a retry loop.

## 11. Wrong repo / folder

The server prints: open **SP500-ai-bubble-monitor**, not `SP500-bubble-monitor`. Two dashboards = two caches, different numbers.

## 12. High news score, poor tagging

Generic Fed headlines (`fed_policy`) inflate the tally. SEC 8-K titles are often “Current report”. Known limit (`evolutive/06`), not a crash. Do not hand-edit the score in JSON.
