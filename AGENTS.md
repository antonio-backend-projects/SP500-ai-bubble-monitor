# AGENTS.md — istruzioni per agent Cursor

Repo: **SP500-ai-bubble-monitor**

## Prima di qualsiasi modifica

1. Leggi [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md)  
2. Leggi [`evolutive/README.md`](evolutive/README.md) per il backlog  
3. Scenario prodotto: [`piano-strategia.md`](piano-strategia.md)

## Vincoli hard

- UI = vanilla HTML (`web/dashboard.html`) stile igedge — **no Streamlit**  
- Dashboard **read-only**: non aggiungere endpoint che lanciano fetch  
- Yahoo Mag7 **off**; preferire NASDAQ / SEC / FRED API  
- Non scrapare FINRA HTML; margin = Z.1 proxy con disclaimer  
- Probe fonti prima di cablare; rate limit; cache 24h  
- PC Windows: evitare fetch aggressivi / `--force` ripetuti  

## Comandi tipici

```powershell
python -m pytest tests/ -q
python -m engine.run_engine
python scripts/dashboard_web.py
```

## Produzione (todo)

Docker + cron engine + Cloudflare Tunnel + docs ops — dettagli in `docs/docker-and-production.md` e `evolutive/13-*.md`.

## Memoria chat

Le chat Cursor non migrano col path della cartella. La memoria portabile è **`docs/` + `evolutive/` + questo file**.
