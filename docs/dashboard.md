# Dashboard

## Server

`python scripts/dashboard_web.py`

| Route | Contenuto |
|-------|-----------|
| `/` | `web/dashboard.html` |
| `/api/state` | `data/cache/bubble_state.json` (fallback fixture) |
| `/salute` | `ok` |

Read-only: POST → 405.

## UI blocks

1. Alert hero (level red/amber/green)  
2. KPI: prossimità, fragilità, innesco, news  
3. Radar + gauge  
4. Card fragilità + guide  
5. Grafici CAPE / barre  
6. Card innesco + guide  
7. Grafici HY, curva, Buffett, recessione  
8. Sotto la superficie (`underFacts`, SEC list)  
9. Watch order + news  

## Guide popup

- Bottone `.btn-guide` su ogni card (`data-guide` = `card.key`)  
- Testi in `GUIDES` (JS)  
- Modal `#guideModal`, chiudi Esc / overlay / ×  

## Bug storico

Mancava `function fact()` → crash a metà `render()` → under/watch/news vuoti.  
Risolto: definire `fact`, CSS `.facts`, try/catch sulle sezioni finali.

## Card keys

`cape`, `buffett`, `household`, `concentration`, `margin`, `under`, `spxdd`,  
`hy_oas`, `curve`, `recession`, `fed`, `ai`, `mag7chg`.
