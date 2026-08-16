# Raspberry Pi ops

**Status:** target procedure (Gamtrace-style). `scripts/pi/*.sh` and Docker images are **still to be written** — see [`evolutive/13-docker-tunnel-docs-rename.md`](../evolutive/13-docker-tunnel-docs-rename.md). Until then you can run a venv + Python cron (same contract: read-only UI, scheduled engine).

Config: [configuration.md](configuration.md). Tunnel: [cloudflare-tunnel.md](cloudflare-tunnel.md).

## Machine roles

| Machine | Role |
|---------|------|
| Windows PC | Code, pytest, dashboard on cache. Rare live fetch, never `--force` in a loop |
| Raspberry Pi | Dashboard 24/7 + engine cron + Cloudflare Tunnel |

## Paths and CRLF

Clone on the Pi (e.g. `/home/pi/SP500-ai-bubble-monitor`). Bash scripts copied from Windows: strip CRLF **before** running them.

```bash
sed -i 's/\r$//' scripts/pi/*.sh
chmod +x scripts/pi/*.sh
```

When they exist, the intended scripts:

| Script | Role |
|--------|------|
| `scripts/pi/update.sh` | `git pull`, CRLF fix, `docker compose build`, `up -d dashboard` |
| `scripts/pi/run_engine.sh` | `docker compose --profile manual run --rm engine` |

## Variant A — Docker (goal)

```bash
cd /home/pi/SP500-ai-bubble-monitor
cp .env.example .env
nano .env   # FRED_API_KEY
docker compose build
docker compose up -d dashboard
curl -s http://127.0.0.1:8891/salute
docker compose --profile manual run --rm engine
```

Persistent cache volume: do not delete the volume between `compose down` runs if you want to keep the last `bubble_state.json`.

Cron (`crontab -e`):

```bash
0 22 * * 1-5 cd /home/pi/SP500-ai-bubble-monitor && docker compose --profile manual run --rm engine >> /home/pi/logs/bubble-engine.log 2>&1
```

Timezone: `TZ=Europe/Rome` or `America/New_York` (post-US-close ~22:00 Rome in summer).

## Variant B — venv without Docker (usable today)

```bash
cd /home/pi/SP500-ai-bubble-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install "xlrd>=2.0.1"
cp .env.example .env && nano .env

# dashboard (systemd or tmux)
nohup .venv/bin/python scripts/dashboard_web.py >> /home/pi/logs/bubble-web.log 2>&1 &

# one fetch
.venv/bin/python -m engine.run_engine
```

Cron:

```bash
0 22 * * 1-5 cd /home/pi/SP500-ai-bubble-monitor && .venv/bin/python -m engine.run_engine >> /home/pi/logs/bubble-engine.log 2>&1
```

Example systemd unit (dashboard):

```ini
[Unit]
Description=SP500 AI Bubble Monitor dashboard
After=network.target

[Service]
WorkingDirectory=/home/pi/SP500-ai-bubble-monitor
EnvironmentFile=/home/pi/SP500-ai-bubble-monitor/.env
ExecStart=/home/pi/SP500-ai-bubble-monitor/.venv/bin/python scripts/dashboard_web.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo cp bubble-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bubble-dashboard
```

## Verify

```bash
curl -s http://127.0.0.1:8891/salute
curl -s http://127.0.0.1:8891/api/state | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('_trust'), d.get('alert',{}).get('headline'), d.get('updated_at'))"
```

If `_trust` is `fixture` or `updated_at` is older than 36h → the engine is not running. Runbook: [runbook-incidenti.md](runbook-incidenti.md).

## Do not (on the Pi)

- Expose the dashboard in the clear on the internet without a tunnel (or at least Access)
- Mount an endpoint that launches the engine
- `git commit` `.env`
- `--force` every evening
