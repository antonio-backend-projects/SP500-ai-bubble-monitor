"""Carica `.env` dalla root del progetto — riusabile per tutte le secret."""
from __future__ import annotations

import os
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@lru_cache(maxsize=1)
def load_env() -> str:
    """
    Carica variabili da ROOT/.env (se presente).
    Ritorna il path usato o stringa vuota.
    """
    env_path = os.path.join(ROOT, '.env')
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except ImportError:
        # fallback minimale senza dipendenza
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    k, _, v = line.partition('=')
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
    return env_path if os.path.exists(env_path) else ''


def get_secret(name: str, default: str | None = None) -> str | None:
    """Legge una secret dopo aver caricato `.env`."""
    load_env()
    val = os.environ.get(name)
    if val is None or not str(val).strip():
        return default
    return str(val).strip()
