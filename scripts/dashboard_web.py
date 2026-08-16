#!/usr/bin/env python3
"""
SP500 AI Bubble Monitor — web server READ-ONLY (stile igedge).

Serve:
  /              web/dashboard.html
  /api/state     data/cache/bubble_state.json (+ metadati fiducia)
  /salute        healthcheck

SICUREZZA: solo GET, nessun endpoint che lancia l'engine o scarica dati.

Author: Antonio Trento — https://antoniotrento.net
License: MIT
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from config.env import load_env
    load_env()
except Exception:
    pass

HTML = os.path.join(ROOT, 'web', 'dashboard.html')
STATE = os.path.join(ROOT, 'data', 'cache', 'bubble_state.json')
FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'sample_bubble_state.json')
PORT = int(os.getenv('WEB_PORT', '8891'))
PROJECT = 'SP500-ai-bubble-monitor'


def _annotate(data: dict, *, served_from: str) -> dict:
    """Metadati anti-confusione: quale repo / quale file / se i pezzi chiave sono affidabili."""
    q = data.get('data_quality') or {}
    ind = data.get('indicators') or {}
    margin_src = str(q.get('margin_source') or ind.get('margin_source') or '')
    cape_src = str(q.get('cape_source') or ind.get('cape_source') or '')
    cape_as_of = str(ind.get('cape_as_of') or '')

    finra_ok = (
        'finra' in margin_src.lower()
        or 'thetrading.tools' in margin_src.lower()
        or 'margin-statistics' in margin_src.lower()
    ) and 'z.1' not in margin_src.lower() and 'proxy' not in margin_src.lower()
    cape_ok = 'seed' not in cape_src.lower() and (
        'multpl' in cape_src.lower()
        or ('shiller' in cape_src.lower() and cape_as_of[:4] >= '2025')
    )
    seedish = bool(data.get('still_seed')) or 'seed' in margin_src.lower() or 'seed' in cape_src.lower()

    if served_from == 'fixture':
        trust = 'fixture'
        trust_label = 'FIXTURE DI TEST — non usare come segnale'
    elif seedish:
        trust = 'seed'
        trust_label = 'DATI PARZIALMENTE SEED — non affidabile al 100%'
    elif finra_ok and cape_ok:
        trust = 'live_ok'
        trust_label = 'DATI LIVE AFFIDABILI (CAPE + margin FINRA + FRED)'
    elif cape_ok:
        trust = 'live_partial'
        trust_label = 'LIVE PARZIALE — margin non FINRA (proxy/altro)'
    else:
        trust = 'live_weak'
        trust_label = 'LIVE DEBOLE — CAPE o margin da verificare'

    data['_served_from'] = served_from
    data['_project'] = PROJECT
    data['_repo_root'] = ROOT
    data['_state_path'] = STATE if served_from == 'cache' else FIXTURE
    data['_trust'] = trust
    data['_trust_label'] = trust_label
    data['_trust_checks'] = {
        'finra_margin': finra_ok,
        'cape_fresh': cape_ok,
        'margin_source': margin_src,
        'cape_source': cape_src,
        'cape_as_of': cape_as_of,
        'buffett': ind.get('buffett_pct'),
        'household': ind.get('household_equity_pct'),
        'margin_billion': ind.get('margin_debit_billion'),
        'margin_yoy': ind.get('margin_debt_yoy_pct'),
        'cape': ind.get('cape'),
        'alert': (data.get('alert') or {}).get('headline'),
        'fragility': data.get('fragility_score'),
        'trigger': data.get('trigger_score'),
    }
    return data


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/index.html'):
            self._file(HTML, 'text/html; charset=utf-8',
                       fallback=b'<h1>dashboard.html mancante</h1>')
        elif path == '/api/state':
            self._state()
        elif path == '/salute':
            self._send(200, 'text/plain; charset=utf-8', b'ok')
        else:
            self._send(404, 'text/plain; charset=utf-8', b'not found')

    def do_POST(self):
        self._send(405, 'text/plain; charset=utf-8', b'read-only')

    def _state(self):
        if os.path.exists(STATE):
            try:
                with open(STATE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data = _annotate(data, served_from='cache')
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self._send(200, 'application/json; charset=utf-8', body)
                return
            except Exception as e:
                self._send(
                    200,
                    'application/json; charset=utf-8',
                    json.dumps({'error': str(e)}).encode('utf-8'),
                )
                return
        if os.path.exists(FIXTURE):
            try:
                with open(FIXTURE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data = _annotate(data, served_from='fixture')
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                self._send(200, 'application/json; charset=utf-8', body)
                return
            except Exception as e:
                self._send(
                    200,
                    'application/json; charset=utf-8',
                    json.dumps({'error': str(e)}).encode('utf-8'),
                )
                return
        self._send(
            200,
            'application/json; charset=utf-8',
            json.dumps({
                'empty': True,
                'note': 'Nessun bubble_state.json — esegui python -m engine.run_engine',
                '_project': PROJECT,
                '_repo_root': ROOT,
            }).encode('utf-8'),
        )

    def _file(self, path, mime, fallback=b''):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                self._send(200, mime, f.read())
        else:
            self._send(404 if fallback == b'' else 200, mime, fallback)

    def _send(self, code, mime, body):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(
            f'{datetime.now().isoformat(timespec="seconds")} web '
            f'{self.address_string()} {fmt % args}',
            flush=True,
        )


if __name__ == '__main__':
    print(
        f'{PROJECT} web su :{PORT} (read-only)\n'
        f'  ROOT  = {ROOT}\n'
        f'  STATE = {STATE}\n'
        f'  Author: Antonio Trento — https://antoniotrento.net\n'
        f'  Apri SOLO questa cartella — non SP500-bubble-monitor (vecchia, dati stale)',
        flush=True,
    )
    ThreadingHTTPServer(('0.0.0.0', PORT), H).serve_forever()
