# Qualità, test, documentazione — cosa manca

La documentazione tecnica **minuziosa** (sviluppo + configurazione + ops) è un requisito esplicito del piano: cartella `docs/` dedicata.  
Dettaglio struttura → [13-docker-tunnel-docs-rename.md](13-docker-tunnel-docs-rename.md) §5.

## Test
- [ ] Test presentation alert con input “live realistici” (Buffett alto, margin YoY basso) → non green fuorviante
- [ ] Test ingestion con HTTP mock (nessuna rete)
- [ ] Test `as_of` stale → flag quality
- [ ] Snapshot test HTML minimale (presenza `#fragCards`, modal guida)
- [ ] Coverage scoring per ogni funzione `score_*`
- [ ] Smoke test Docker: build + `/salute` + `/api/state`

## Dati / seed
- [ ] Separare chiaramente `seed` vs `live` in ogni JSON cache
- [ ] Vietare seed silenziosi in produzione (fail soft sì, ma badge obbligatorio)
- [ ] Pulizia file probe `data/cache/_probe*` dal repo / gitignore

## Docs tecnici (`docs/` — da creare)
- [ ] `docs/README.md` indice
- [ ] Architecture, development, configuration
- [ ] Data sources (anti-ban, fallback, TTL)
- [ ] Scoring/alerts, dashboard API
- [ ] Docker, Raspberry Pi ops, Cloudflare tunnel
- [ ] Runbook incidenti + checklist go-live
- [ ] Comandi copy-paste PowerShell **e** bash
- [ ] Sezione “cosa non fare” (fetch aggressivi dal laptop)

## Docs repo root
- [ ] README aggiornato al nome **SP500-ai-bubble-monitor**
- [ ] Link README → `docs/` e → `evolutive/`
- [ ] Changelog umano

## Config
- [ ] Validazione schema `settings.json`
- [ ] Profili pesi: `piano`, `conservative`, `credit_first`
