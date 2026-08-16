# Ops / deploy / Raspberry Pi — cosa manca

Allineabile allo stile **Gamtrace**: PC = dev/test offline; Pi = produzione + cron + tunnel.

Vedi anche il requisito produzione completo:  
→ [13-docker-tunnel-docs-rename.md](13-docker-tunnel-docs-rename.md)  
Docs già scritte: [`docs/ops-raspberry-pi.md`](../docs/ops-raspberry-pi.md), [`docs/cloudflare-tunnel.md`](../docs/cloudflare-tunnel.md), [`docs/docker-and-production.md`](../docs/docker-and-production.md).

## Gap

### Docker (obbligatorio per deploy ordinato)
- [ ] Incapsulare **tutto** (dashboard + engine) in Docker
- [ ] `docker-compose.yml` con volume cache persistente
- [ ] Profile `manual` per engine; dashboard sempre up
- [ ] Healthcheck `/salute`
- [ ] `scripts/pi/update.sh` + fix CRLF post-copia Windows

### Fetch automatico in produzione
- [ ] Cron giornaliero che lancia solo il container engine
- [ ] UI senza pulsanti download (read-only) — invariato
- [ ] Badge/state stale se cache troppo vecchia
- [ ] Log fetch per fonte

### Dominio + Cloudflare Tunnel
- [ ] Stesso schema Gamtrace: `cloudflared` → servizio dashboard
- [ ] Hostname pubblico HTTPS
- [x] Token/config fuori git; docs di setup in `docs/cloudflare-tunnel.md`

### Sicurezza
- [ ] Nessun endpoint che lancia l’engine dal web
- [ ] Secrets solo `.env` sul Pi
- [ ] Opzionale Cloudflare Access

### Dev machine
- [ ] Test offline / pytest; niente fetch Yahoo dal PC
- [ ] Fixture per UI se cache vuota
