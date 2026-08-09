# Evolutive — cosa manca / cosa migliorare

Cartella di backlog per **SP500-ai-bubble-monitor**.  
Memoria acquisita / handoff: [`docs/PROJECT_MEMORY.md`](../docs/PROJECT_MEMORY.md).  
Ogni file elenca gap, idee e priorità *possibili* — non è un impegno di roadmap.

| File | Tema |
|------|------|
| [01-indicatori-fragilita.md](01-indicatori-fragilita.md) | Molla: CAPE, Buffett, famiglie, leva, concentrazione |
| [02-indicatori-innesco.md](02-indicatori-innesco.md) | Credito, Fed, recessione, utili AI |
| [03-sotto-la-superficie.md](03-sotto-la-superficie.md) | Drawdown titoli, Mag7, rotazione |
| [04-fonti-dati-e-anti-ban.md](04-fonti-dati-e-anti-ban.md) | Fonti mancanti, proxy, IP safety |
| [05-scoring-e-alert.md](05-scoring-e-alert.md) | Pesi, soglie, banner fuorvianti |
| [06-news-e-testo.md](06-news-e-testo.md) | RSS, tagging, narrative |
| [07-dashboard-ui-ux.md](07-dashboard-ui-ux.md) | UI, guide, accessibilità |
| [08-storico-e-backtest.md](08-storico-e-backtest.md) | Serie lunghe, scenari 2000/2008 |
| [09-ops-deploy-pi.md](09-ops-deploy-pi.md) | Cron, Pi, Docker, tunnel |
| [10-qualita-test-docs.md](10-qualita-test-docs.md) | Test, `docs/` tecnici, seed |
| [11-scenario-probabilistici.md](11-scenario-probabilistici.md) | Fasce −10/−20, −45/−55 dal piano |
| [12-nice-to-have.md](12-nice-to-have.md) | Extra non essenziali |
| [13-docker-tunnel-docs-rename.md](13-docker-tunnel-docs-rename.md) | **Produzione:** Docker, fetch auto, Cloudflare, docs, rename |

**Priorità suggerite (sintesi):**

1. Allineare scoring/alert a “tarda bolla” senza seed finti  
2. CAPE aggiornato + margin FINRA (o disclaimer forte sul proxy Z.1)  
3. Under-surface: drawdown medio titoli, market breadth  
4. News tagging reale + utili Mag7  
5. Produzione: Docker + cron fetch + Cloudflare Tunnel + `docs/` + rename repo `SP500-ai-bubble-monitor`
