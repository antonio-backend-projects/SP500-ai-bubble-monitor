# Produzione: Docker, fetch auto, Cloudflare tunnel, docs, rename

Requisito da `piano-strategia.md` (righe 136–138).

> Incapsulare tutto in Docker per deploy Raspberry più rapido e ordinato;  
> fetch dati automatico in produzione;  
> esposizione su dominio via **Cloudflare Tunnel** (come Gamtrace);  
> cartella **`docs/`** con documentazione tecnica minuziosa (sviluppo + configurazione);  
> nome progetto/repo definitivo: **`SP500-ai-bubble-monitor`** (la cartella attuale è solo appoggio di test).

---

## 1. Rename progetto / repo

- [ ] Repo GitHub definitivo: `SP500-ai-bubble-monitor`
- [ ] Rinominare brand in UI: *SP500 · AI Bubble Monitor* (o stringa unica coerente)
- [ ] Aggiornare paths, README, `.env.example`, commenti, `evolutive/`, piano
- [ ] Decidere se la cartella locale di test resta symlink / viene migrata 1:1
- [ ] Package/module paths: evitare hardcode del vecchio nome cartella
- [ ] Immagini Docker / compose project name allineati al nuovo nome

---

## 2. Docker — tutto incapsulato

Obiettivo: sul Pi `git pull` / `update.sh` + `docker compose up` senza installare Python a mano.

- [ ] `Dockerfile` multi-stage o lean (Python slim) per:
  - servizio **dashboard** (read-only, porta interna es. 8891)
  - servizio / profile **engine** (fetch + scoring → scrive cache)
- [ ] `docker-compose.yml` (+ override Pi se serve)
  - `dashboard`: always on
  - `engine`: profile `manual` **e** schedulato (cron host o container `ofelia`/`supercronic`)
- [ ] Volume named o bind: es. `/home/…/sp500-ai-bubble-data/cache` → `/app/data/cache`
- [ ] `.env` montato o `env_file` (FRED_API_KEY, WEB_PORT, TZ)
- [ ] Healthcheck Compose su `/salute`
- [ ] Build riproducibile; pin base image digest se possibile
- [ ] Documentare: **mai** lanciare engine fetch aggressivo dal PC Windows (ban IP) — solo test offline / Pi

Script Pi (stile Gamtrace):

- [ ] `scripts/pi/update.sh` — pull, `sed` CRLF, `compose build`, `up -d dashboard`
- [ ] `scripts/pi/run_engine.sh` — `compose --profile manual run --rm engine`
- [ ] `scripts/pi/README.md` (o meglio puntare a `docs/ops-raspberry-pi.md`)

---

## 3. Fetch automatico in produzione

La UI **non** scarica dati. Solo l’engine, a schedule.

- [ ] Cron sul Pi (es. serale, post-close US) che lancia il container engine
- [ ] Idempotenza: cache TTL rispettata; `--force` solo su job dedicato settimanale
- [ ] Se fetch fallisce → dashboard resta sull’ultimo `bubble_state.json` buono + badge “stale”
- [ ] Log per fonte (ok/fail) in volume o `logging` driver
- [ ] Alert ops se `updated_at` di `bubble_state` > 36h (Telegram/email opzionale)
- [ ] Rate limit e lista fonti “safe” invariata (no Yahoo hammer)

---

## 4. Dominio + Cloudflare Tunnel (come Gamtrace)

- [ ] Container o servizio host `cloudflared` con tunnel verso `dashboard:8891`
- [ ] Config tunnel (YAML) **fuori dal repo** o template senza secret
- [ ] Hostname pubblico tipo `sp500-ai-bubble.…` / nome scelto
- [ ] Solo HTTP read-only esposto; nessun endpoint che triggera fetch
- [ ] Documentare in `docs/`:
  - creazione tunnel Cloudflare
  - DNS route
  - rotate token
  - cosa fare se il tunnel cade
- [ ] Opzionale: Access policy Cloudflare (email allowlist) se non si vuole pubblico assoluto

---

## 5. Cartella `docs/` tecnica (minuziosa)

Scritta 2026-08-16 (config + ops + runbook). Tenere al passo col codice. Docker/tunnel restano da implementare nel repo.

Struttura proposta:

```
docs/
  README.md                 # indice docs
  architecture.md           # flusso engine → cache → UI
  development.md            # setup venv, test offline, divieti fetch
  configuration.md          # settings.json, .env, pesi, soglie
  data-sources.md           # ogni fonte: URL, rischio ban, fallback, TTL
  scoring-and-alerts.md     # formule, quorum tarda-bolla, caveat seed
  dashboard.md              # route, API /api/state, guide popup
  docker-and-production.md  # build, compose, volumi, profili (nome file reale; non docker.md)
  ops-raspberry-pi.md       # deploy, cron, update.sh, troubleshooting
  cloudflare-tunnel.md      # esposizione dominio
  runbook-incidenti.md      # cache corrotta, FRED down, alert verde fuorviante
  changelog-ops.md          # note release ops (opzionale)
```

Requisiti di qualità docs:

- [x] Ogni procedura con comandi **copy-paste** (PowerShell + bash Pi)
- [x] Sezione “cosa non fare” (Yahoo live, FINRA scrape, force dal laptop)
- [x] Diagramma mermaid del deploy produzione (`docs/docker-and-production.md`)
- [x] Checklist go-live (env, tunnel, primo engine, verifica UI)
- [x] Link da README root → `docs/` e da `evolutive/` → `docs/`

File (2026-08-16): indice, architecture, development, configuration, data-sources, scoring-and-alerts, dashboard, docker-and-production, ops-raspberry-pi, cloudflare-tunnel, runbook-incidenti.  
**Non fatto:** Docker/compose/script Pi nel codice — i doc descrivono il contratto, non sostituiscono l’implementazione.

---

## 6. Criteri “fatto” (definition of done produzione)

1. `docker compose up -d` sul Pi → dashboard risponde in LAN  
2. Cron engine aggiorna `bubble_state.json` senza intervento  
3. Tunnel Cloudflare → hostname HTTPS pubblico  
4. `docs/` copre dev + config + ops in modo ripetibile da zero — **docs sì (2026-08-16)**; compose/tunnel codice ancora no  
5. Repo rinominato / pubblicato come **SP500-ai-bubble-monitor**
