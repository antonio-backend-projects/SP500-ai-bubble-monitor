# Cloudflare Tunnel

**Status:** still to do in production (same as Gamtrace). No tunnel token or `config.yml` lives in this repo. Code checklist: [`evolutive/13-docker-tunnel-docs-rename.md`](../evolutive/13-docker-tunnel-docs-rename.md) §4.

The dashboard is **GET only**. The tunnel must point **only** at the dashboard process/container (`8891`), never at a service that runs `run_engine`.

## Idea

```
browser  --HTTPS-->  Cloudflare edge  --tunnel-->  cloudflared on the Pi  -->  http://127.0.0.1:8891
```

Hostname such as `sp500-ai-bubble.<your-domain>` (name TBD). Token and certs **stay off git**.

## Create a tunnel (Zero Trust dashboard)

1. Cloudflare Zero Trust → Networks → Tunnels → **Create a tunnel** (cloudflared)
2. Install `cloudflared` on the Pi (official Cloudflare package; follow current Debian/Pi OS docs)
3. Copy the token **onto the Pi**, not into the repo. Example env (off git):

```bash
# /home/pi/.config/cloudflared/env  — do not commit
TUNNEL_TOKEN=eyJ...
```

4. Public hostname:
   - Type: HTTP
   - URL: `http://127.0.0.1:8891`  
     (if the dashboard is in Docker on the same network: `http://dashboard:8891`)
5. DNS: CNAME hostname → `<tunnel-id>.cfargotunnel.com` (Zero Trust creates this)

## cloudflared as a service

```bash
sudo cloudflared service install "$TUNNEL_TOKEN"
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

Local check before public DNS:

```bash
curl -s http://127.0.0.1:8891/salute
```

Then from a phone / other network: `https://<hostname>/salute` → `ok`.

## Rotate the token

1. Zero Trust → tunnel → refresh/rotate token
2. Update the token on the Pi, `systemctl restart cloudflared`
3. Old token is invalid
4. Do not leave tokens in chat, screenshots, or `git log`

YAML template (if you use a config file instead of token-only) — **path on the Pi**:

```yaml
# /home/pi/.cloudflared/config.yml — NOT in git
tunnel: <TUNNEL_UUID>
credentials-file: /home/pi/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: sp500-ai-bubble.example.com
    service: http://127.0.0.1:8891
  - service: http_status:404
```

## If the tunnel drops

1. `sudo systemctl status cloudflared` and the journal
2. Is the local dashboard still up? `curl http://127.0.0.1:8891/salute`
3. The engine is unrelated: tunnel down ≠ stale data. Stale data = engine cron
4. Cloudflare dashboard → tunnel status; recreate the connector if the Pi changed networks
5. DNS: is the CNAME still on the right tunnel?

## Optional Access

If you do not want a fully public hostname: Cloudflare Access (email allowlist) in front of the app. The dashboard has no login of its own.

## Do not

- Commit the token, `credentials-file`, or a `config.yml` with secrets
- Forward port 8891 on the router (the tunnel is outbound; inbound is not needed)
- Point the tunnel at an `engine` container
- Add a UI fetch button “because Access is in front”
