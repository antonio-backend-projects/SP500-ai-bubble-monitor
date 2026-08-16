# Technical documentation — SP500-ai-bubble-monitor

Docs for **development**, **configuration**, and **ops**. Docker/tunnel are still a target: the contract is written; deploy code is not in the repo yet.

| Doc | Contents |
|-----|----------|
| **[PROJECT_MEMORY.md](PROJECT_MEMORY.md)** | Full handoff — read first in every new chat |
| [architecture.md](architecture.md) | Engine → cache → UI flow |
| [development.md](development.md) | Local venv, tests, fetch bans (PowerShell + bash) |
| [configuration.md](configuration.md) | `.env`, FRED key, `settings.json`, weights, thresholds, what is not JSON |
| [data-sources.md](data-sources.md) | Sources, URLs, ban risk, fallbacks, TTL, quality checks |
| [scoring-and-alerts.md](scoring-and-alerts.md) | Formulas, late-bubble quorum, banner, seed vs live |
| [dashboard.md](dashboard.md) | Routes, `/api/state`, trust badge, guides |
| [docker-and-production.md](docker-and-production.md) | Docker contract, deploy mermaid, go-live checklist |
| [ops-raspberry-pi.md](ops-raspberry-pi.md) | Pi: Docker target + venv/cron/systemd usable today |
| [cloudflare-tunnel.md](cloudflare-tunnel.md) | Tunnel, DNS, token rotation, outages |
| [runbook-incidenti.md](runbook-incidenti.md) | Fixture, misleading green alert, stale CAPE, cache, 403s |

Product backlog: [`../evolutive/`](../evolutive/) (Italian).  
Scenario note: [`../piano-strategia.md`](../piano-strategia.md) (Italian).  
Root README: [`../README.md`](../README.md).  
License: [MIT](../LICENSE).

## From zero (local)

1. [development.md](development.md) — venv + `.env`  
2. [configuration.md](configuration.md) — FRED key and verification  
3. `python -m engine.run_engine` then `python scripts/dashboard_web.py`  
4. If the numbers look wrong: [runbook-incidenti.md](runbook-incidenti.md)
