# Fonti dati e anti-ban — cosa manca

Principio: **testare la fonte prima di cablare**; niente hammer su Yahoo/FINRA HTML.

## Fonti attuali “ok”
- FRED API (`api.stlouisfed.org`) + key `.env`
- Treasury / H.15 / CMV fallback
- Shiller XLS / multpl
- Slickcharts
- NY Fed XLS
- NASDAQ quote API
- SEC EDGAR atom (UA corretto)
- RSS Fed (+ Yahoo RSS se regge)

## Fonti bloccate / rischiose (non ripristinare alla cieca)
- Yahoo chart/quote massivo → 429
- FINRA HTML → 403
- MarketWatch / molti scrape → 401/anti-bot
- Stooq HTML anti-bot
- `fredgraph.csv` timeout da alcuni IP

## Gap di sourcing da chiudere

### Margin FINRA ufficiale
- [ ] Endpoint/CSV/API mirror stabile (o download manuale → cache)
- [ ] Pipeline “upload CSV FINRA” in `data/cache/` senza scrape
- [ ] Documentare differenza Z.1 vs FINRA in UI + README

### CAPE aggiornato
- [ ] Verificare URL Shiller che restituisce mese corrente
- [ ] Fallback multpl con data check (`as_of` max age)
- [ ] Se stale > N mesi → warning rosso in quality bar, non silenzioso

### Utili / prezzi
- [ ] Alternativa Yahoo: NASDAQ + SEC + (eventuale) Stooq CSV se passa probe
- [ ] Earnings da feed RSS company IR ( Mag7) 
- [ ] Mai reintrodurre Yahoo Mag7 di default

### Credito / Fed path
- [ ] Probe fonti FedWatch / futures senza API a pagamento
- [ ] Evitare TradingEconomics scrape aggressivo (già fragile)

### Infrastruttura fetch
- [ ] Registry fonti: `{nome, url, last_ok, last_status, ban_risk}`
- [ ] Script `scripts/probe_sources.py` (solo probe, rate-limited) in CI locale opzionale
- [ ] Log “fonte usata” per ogni indicatore già in `data_quality` → esportabile
- [ ] Cache per-fonte con TTL diversi (HY daily, Z.1 quarterly)
