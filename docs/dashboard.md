# Dashboard

Server: `python scripts/dashboard_web.py` → http://localhost:8891  
Read-only: `POST` → 405. **No** endpoint launches the engine.

## Routes

| Route | Serves |
|-------|--------|
| `/` | `web/dashboard.html` |
| `/api/state` | Annotated `data/cache/bubble_state.json`; if missing → fixture; if that is missing too → `{empty: true}` |
| `/salute` | `ok` (healthcheck) |

Port: `WEB_PORT` (default `8891`). Bind `0.0.0.0` (LAN). UI poll: `GET /api/state` every 60s. `Cache-Control: no-store`.

## Trust metadata (`_annotate`)

The JSON served is **not** the raw file: the server adds `_` fields so fixture and live are not confused.

| Field | Meaning |
|-------|---------|
| `_served_from` | `cache` or `fixture` |
| `_project` | `SP500-ai-bubble-monitor` |
| `_repo_root` / `_state_path` | Absolute paths |
| `_trust` | `fixture` / `seed` / `live_ok` / `live_partial` / `live_weak` |
| `_trust_label` | UI string |
| `_trust_checks` | Fresh CAPE? FINRA margin? sources |

`live_ok` only if CAPE is non-seed (multpl or Shiller with `as_of` ≥ 2025) **and** margin is FINRA/mirror (not Z.1).

If the page shows **FIXTURE DI TEST**, there is no `bubble_state.json`. Run the engine; do not read the numbers as market data.

## UI blocks

1. Alert hero (red / amber / green) + trust label  
2. KPIs: proximity, fragility, trigger, news  
3. Radar + gauge  
4. Fragility cards + Guide button  
5. CAPE / bar charts  
6. Trigger cards + Guide  
7. HY, curve, Buffett, recession charts  
8. Under the surface (`underFacts`, SEC 8-K)  
9. Watch order + news  

## Guide popup

- `.btn-guide` (`data-guide` = `card.key`)
- Copy in `GUIDES` inside `web/dashboard.html` (not in settings)
- Modal `#guideModal`, close Esc / overlay / ×

## Card keys

`cape`, `buffett`, `household`, `concentration`, `margin`, `under`, `spxdd`,  
`hy_oas`, `curve`, `recession`, `fed`, `ai`, `mag7chg`.

## Historical bug (fixed)

Missing `function fact()` → crash mid-`render()` → empty under/watch/news.  
Now: `fact`, CSS `.facts`, try/catch on the trailing sections. Do not remove `fact()`.

## Do not add to the UI

- Write endpoints / “Refresh data”
- Browser `fetch()` to FRED/NASDAQ
- Streamlit as the main UI
