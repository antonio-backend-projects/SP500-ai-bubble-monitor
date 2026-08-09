"""CAPE da multpl.com — fallback se lo xls Shiller non è scaricabile."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from .http_utils import get_with_retry, is_cache_fresh, load_json_cache, save_json_cache

logger = logging.getLogger(__name__)

MULTPL_URL = 'https://www.multpl.com/shiller-pe'


def _parse_multpl(html: str) -> Optional[dict[str, Any]]:
    # Valore corrente tipico in #current
    m = re.search(
        r'id="current"[^>]*>\s*([0-9]+(?:\.[0-9]+)?)',
        html,
        re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r'Shiller\s*PE[^0-9]{0,40}([0-9]{2,3}(?:\.[0-9]+)?)',
            html,
            re.IGNORECASE,
        )
    if not m:
        return None
    cape = float(m.group(1))
    if not (5.0 < cape < 80.0):
        return None
    return {
        'cape': cape,
        'as_of': datetime.now(timezone.utc).strftime('%Y-%m-01'),
        'source': 'multpl.com shiller-pe',
        'history': [],
    }


def fetch_multpl_cape(*, force: bool = False) -> dict[str, Any]:
    cache_name = 'multpl_cape'
    if not force and is_cache_fresh(cache_name, max_age_hours=72):
        cached = load_json_cache(cache_name)
        if cached:
            return cached
    try:
        resp = get_with_retry(MULTPL_URL, timeout=25)
        parsed = _parse_multpl(resp.text)
        if not parsed:
            raise ValueError('Parsing multpl CAPE fallito')
        parsed['updated_at'] = datetime.now(timezone.utc).isoformat()
        save_json_cache(cache_name, parsed)
        return parsed
    except Exception as e:
        logger.warning('multpl CAPE fallito: %s', e)
        cached = load_json_cache(cache_name)
        if cached:
            return cached
        raise
