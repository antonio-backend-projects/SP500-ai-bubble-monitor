"""HTTP helpers: session, rate limit, cache JSON — stile Gamtrace anti-ban.

Author: Antonio Trento — https://antoniotrento.net
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_DIR = os.path.join(ROOT, 'data', 'cache')
CONFIG_PATH = os.path.join(ROOT, 'config', 'settings.json')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]

_session: Optional[requests.Session] = None
_last_request_time = 0.0
_settings_cache: Optional[dict] = None


def load_settings() -> dict:
    global _settings_cache
    if _settings_cache is None:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _settings_cache = json.load(f)
    return _settings_cache


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.verify = False
        _session.headers.update({
            'User-Agent': USER_AGENTS[0],
            'Accept': 'text/html,application/json,text/csv,*/*',
            'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
            'Connection': 'keep-alive',
        })
    return _session


def random_headers() -> dict:
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/json,text/csv,*/*',
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Connection': 'keep-alive',
    }


def rate_limit(*, soft: bool = False) -> None:
    """Delay jitter tra richieste per non sembrare un bot."""
    global _last_request_time
    settings = load_settings()
    lo = float(settings.get('rate_limit_min_sec', 3.0))
    hi = float(settings.get('rate_limit_max_sec', 8.0))
    if soft:
        lo = min(lo, 1.0)
        hi = min(hi, 2.0)
    now = time.monotonic()
    elapsed = now - _last_request_time
    need = lo + random.uniform(0, max(0.0, hi - lo))
    if _last_request_time > 0 and elapsed < need:
        time.sleep(need - elapsed)
    _last_request_time = time.monotonic()


def cache_path(name: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not name.endswith('.json'):
        name = f'{name}.json'
    return os.path.join(CACHE_DIR, name)


def is_cache_fresh(name: str, max_age_hours: Optional[float] = None) -> bool:
    path = cache_path(name)
    if not os.path.exists(path):
        return False
    if max_age_hours is None:
        max_age_hours = float(load_settings().get('cache_max_age_hours', 24))
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(
        os.path.getmtime(path), tz=timezone.utc
    )
    return age < timedelta(hours=max_age_hours)


def load_json_cache(name: str) -> Optional[Any]:
    path = cache_path(name)
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_cache(name: str, payload: Any) -> str:
    path = cache_path(name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    logger.info('Cache salvata: %s', path)
    return path


def get_with_retry(
    url: str,
    *,
    max_retries: int = 2,
    timeout: int = 20,
    headers: Optional[dict] = None,
    soft_rate_limit: bool = False,
) -> requests.Response:
    """GET con rate limit, retry/backoff e jitter."""
    session = get_session()
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 2):
        rate_limit(soft=soft_rate_limit)
        try:
            resp = session.get(url, timeout=timeout, headers=headers or random_headers())
            if resp.status_code != 200:
                raise ConnectionError(f'HTTP {resp.status_code} for {url}')
            return resp
        except Exception as e:
            last_err = e
            logger.warning('Tentativo %s fallito: %s', attempt, e)
            if attempt <= max_retries:
                time.sleep(min(4.0, (2 ** attempt) + random.uniform(0, 1.0)))
    raise RuntimeError(f'Request failed: {url}') from last_err
