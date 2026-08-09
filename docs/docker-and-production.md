# Docker and production (target)

**Stato:** pianificato — vedi checklist completa in  
[`evolutive/13-docker-tunnel-docs-rename.md`](../evolutive/13-docker-tunnel-docs-rename.md).

## Obiettivi

1. Tutto in Docker (dashboard + engine)  
2. Fetch **automatico** in produzione (cron), mai dalla UI  
3. Esposizione HTTPS via **Cloudflare Tunnel** (pattern Gamtrace)  
4. Volume persistente cache sul Pi  
5. Docs ops ripetibili (questa cartella)

## Bozza compose (da implementare)

```yaml
# bozza — non ancora nel repo
services:
  dashboard:
    build: .
    ports: ["8891:8891"]
    env_file: .env
    volumes:
      - bubble-cache:/app/data/cache
    restart: unless-stopped
  engine:
    build: .
    profiles: ["manual"]
    env_file: .env
    volumes:
      - bubble-cache:/app/data/cache
    command: ["python", "-m", "engine.run_engine"]
volumes:
  bubble-cache:
```

Cron host esempio:

```bash
# sera, post close US — timezone Europe/Rome o America/New_York
0 22 * * 1-5 cd /home/.../SP500-ai-bubble-monitor && docker compose --profile manual run --rm engine
```

## Cloudflare Tunnel

- `cloudflared` punta a `http://localhost:8891` (o service docker)  
- Token fuori git  
- Nessun endpoint write/fetch esposto  

## Regola Windows

Non usare il PC di sviluppo come fetch farm. Test = pytest + UI su cache.
