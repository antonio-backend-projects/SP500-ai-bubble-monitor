# Scoring and alerts

## Due assi

- **Fragilità** = media pesata CAPE, Buffett, household, concentration, margin YoY  
- **Innesco** = media pesata HY OAS, curva, recession, Fed path, AI earnings risk  
- **Prossimità** = mix fragilità + innesco + news (`weights.composite`)

Regime testuale: `classify_regime()` in `engine/scoring.py`.

## Alert banner (`build_alert`)

| Condizione | Level | Headline |
|------------|-------|----------|
| frag≥70 & trig≥55 | red | ALLERTA SCOPPIO |
| frag≥70 & trig≥40 | red | MOLLA CARICA — INNESCO IN FORMAZIONE |
| frag≥70 | amber | TARDA BOLLA — INNESCO ANCORA SPENTO |
| frag≥55 o trig≥45 | amber | VIGILANZA ELEVATA |
| else | green | RISCHIO CONTENUTO |

## Caveat seed vs live (2026-08-09)

Con input da `piano-strategia` (CAPE 41.9, margin YoY 51.5) → tarda bolla.  
Con live (CAPE stale ~33, margin Z.1 YoY ~2) → green “rischio contenuto” **anche se** Buffett~219 e household~46.

Questo è un **difetto del modello di aggregazione**, non un segnale di mercato calmo.

### Fix candidati

1. Quorum: 2+ indicatori fragilità in zona estrema → almeno amber tarda-bolla  
2. Abbassare peso margin se `source` contiene `Z.1` / `proxy`  
3. Score margin = blend(livello normalizzato, YoY)  
4. Se CAPE `as_of` > N mesi → escludi o warning, non usare come “safe”  
5. Test di regressione: input piano → headline deve contenere TARDA BOLLA / VIGILANZA

## HY / innesco

HY ~271 bp < 350 → score credito basso (corretto rispetto al piano: innesco spento).
