"""Tagging news: Fed headline non deve restare untagged."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.ingestion.news_feed import analyze_news
from data.ingestion.http_utils import load_settings


def test_fomc_headline_gets_fed_tags():
    settings = load_settings()
    kw = settings.get("news_keywords") or {}
    items = [
        {
            "title": "Federal Reserve issues FOMC statement",
            "summary": "Monetary policy decision of the Federal Open Market Committee",
            "link": "https://example.com/1",
        },
        {
            "title": "Nvidia earnings miss and AI capex cut guidance",
            "summary": "Magnificent 7 AI spending under pressure",
            "link": "https://example.com/2",
        },
    ]
    out = analyze_news(items, kw)
    assert out["tallies"].get("fed_policy", 0) >= 1
    assert out["tallies"].get("ai_earnings", 0) >= 1
    assert out["news_risk_score"] > 0
    assert out["tagged_count"] >= 2
