# Scoring and alerts

Two axes, from [`piano-strategia.md`](../piano-strategia.md): **do not** predict the day a bubble pops; measure spring vs spark.

Code: `engine/scoring.py`, `engine/presentation.py`. Numeric weights/thresholds: [configuration.md](configuration.md).

## Two axes + proximity

- **Fragility** = weighted mean of CAPE, Buffett, household, concentration (Mag7 weight), margin (YoY+level)
- **Trigger** = weighted mean of HY OAS, curve, recession, Fed path, AI earnings risk
- **News** = 0–100 from RSS keywords (`analyze_news`)
- **Proximity** = `0.55 * frag + 0.30 * trig + 0.15 * news` (`weights.composite`)

Text regime: `classify_regime()` (e.g. *Tarda bolla — molla carica, innesco spento* if frag ≥ 70 and trig < 40).

Fixed watch order: (1) restrictive Fed (2) HY credit stress (3) AI / Mag7 earnings.

## Mapping a raw value → 0–100

`_lerp_score(value, low, high)`: `low` → 0, `high` → 100, clamped. Some functions invert (HY: wide spread = high trigger).

Examples with defaults:

| Part | Typical late-bubble input | Score ~ |
|------|---------------------------|---------|
| CAPE 42.6 | lerp 16→44 | ~95 |
| Buffett 219% | lerp 160→230 | ~84 |
| Household 45.8% | lerp 33.7→47 | ~91 |
| Mag7 weight 30% | lerp 25→38 | ~41 |
| HY OAS 271 bp | lerp 270→500 | ~0 (complacency) |
| Curve +51 bp | 0–80 bp = late cycle | ~42 |

**FINRA** margin: `0.65 * YoY_score + 0.35 * level_score`.  
**Z.1 proxy** margin: settings weight × 0.45 and score = `max(YoY, level×0.85)` so a ~2% YoY on a $622B proxy does not zero out fragility.

`ai_earnings_risk` on indicators is already 0–100 (engine blend: news 0.25 + NASDAQ EPS 0.55 + 8-K 0.20).

## Late-bubble quorum (fix 2026-08-10)

If **at least 2** of `cape`, `buffett`, `household_equity` have part score ≥ 75:

- `build_scores` raises `fragility_score` to at least **72**
- `build_alert` does the same if the trigger is < 40

This blocks a green **RISCHIO CONTENUTO** banner when Buffett/household are at records and Z.1 margin is flat. Test: `test_alert_not_green_when_valuations_extreme_but_margin_proxy_flat`.

## Alert banner (`build_alert`)

Cutoffs are **in code**, not in `settings.json`. Headlines below are the strings shown in the UI.

| Condition (after quorum) | Level | Headline |
|--------------------------|-------|----------|
| frag ≥ 70 and trig ≥ 55 | red | ALLERTA SCOPPIO |
| frag ≥ 70 and trig ≥ 40 | red | MOLLA CARICA — INNESCO IN FORMAZIONE |
| frag ≥ 70 | amber | TARDA BOLLA — INNESCO ANCORA SPENTO |
| frag ≥ 55 **or** trig ≥ 45 | amber | VIGILANZA ELEVATA |
| else | green | RISCHIO CONTENUTO |

Card traffic lights: score ≥ 70 red, ≥ 45 amber, below green (`_status`).

## Seed vs live caveat

History 2026-08-09: strategy-note inputs (CAPE 41.9, margin YoY 51%) → late bubble. Live with stale Shiller CAPE ~33 and Z.1 margin YoY ~2 → **misleading green** even with Buffett ~219 and household ~46. That was an aggregation defect, not “the market is calm”.

Mitigations already in code: CAPE → multpl if stale; FINRA-mirror margin; reduced Z.1 weight; quorum.

Still true:

- HY ~271 bp < 350 → credit trigger low (**correct** vs the strategy note)
- Always check `data_quality` / the UI trust badge
- The test fixture (`sample_bubble_state.json`) has fragility ~91: **do not** treat it as a signal

## Live run 2026-08-15 (reference)

Alert **TARDA BOLLA — INNESCO ANCORA SPENTO**: fragility 77.3, trigger 22.6, proximity 59.3. CAPE 42.56 (multpl), Buffett 219% (CMV), household 45.8%, FINRA-mirror margin $1417B YoY 38.6%, HY 271 bp, SPX 7786 (−0.2% 52w, YTD +13.5%).
