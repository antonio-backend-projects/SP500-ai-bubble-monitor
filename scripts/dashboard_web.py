#!/usr/bin/env python3
"""
SP500 Bubble Monitor — web server READ-ONLY (stile igedge).

Serve:
  /              web/dashboard.html
  /api/state     data/cache/bubble_state.json (fallback fixture)
  /salute        healthcheck

SICUREZZA: solo GET, nessun endpoint che lancia l'engine o scarica dati.
L'aggiornamento dati resta CLI: python -m engine.run_engine
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
        for candidate in (STATE, FIXTURE):
            if os.path.exists(candidate):
                try:
                    with open(candidate, 'rb') as f:
                        body = f.read()
                    # annota se stiamo servendo la fixture
                    if candidate == FIXTURE:
                        try:
                            data = json.loads(body.decode('utf-8'))
                            data['_served_from'] = 'fixture'
                            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                        except Exception:
                            pass
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
        f'bubble-monitor web su :{PORT} (read-only) — {HTML}',
        flush=True,
    )
    ThreadingHTTPServer(('0.0.0.0', PORT), H).serve_forever()
