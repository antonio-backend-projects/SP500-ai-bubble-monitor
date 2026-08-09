# Configuration

## `.env` (secret, gitignored)

```env
FRED_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# WEB_PORT=8891
```

Caricato da `config/env.py` all’avvio engine/dashboard.

## `config/settings.json`

Campi importanti:

| Chiave | Ruolo |
|--------|-------|
| `cache_max_age_hours` | default 24 |
| `rate_limit_min_sec` / `max_sec` | pacing HTTP |
| `mag7` | ticker list |
| `fred_series` | map nomi → series id FRED |
| `thresholds` | soglie CAPE, Buffett, HY, margin YoY, ecc. |
| `weights.fragility` / `trigger` / `composite` | pesi score |
| `news_feeds` / `news_keywords` | RSS + tagging |
| `fetch_yahoo_mag7` | **false** |
| `fetch_nasdaq_mag7` | **true** (consigliato) |

## Pesi fragilità attuali (nota)

`margin_debt: 0.25` è il peso più alto. Con YoY proxy basso azzera la media — vedi scoring docs.

## Soglie alert (codice, non settings)

In `engine/presentation.py` `build_alert`: frag 70 / 55.  
Candidate fix: quorum indicatori estremi (evolutive/05).
