"""
What:
自動抓取公開 RSS 新聞，轉成可供量化分析的結構化事件特徵。

Why:
讓模型具備時事上下文，降低只看價格/衍生品造成的盲點。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests


@dataclass
class NewsItem:
    title: str
    source: str
    published_at: datetime
    link: str
    sentiment: float
    urgency: str
    tags: list[str]


POSITIVE_KEYWORDS = {
    "approval", "approved", "inflow", "surge", "rally", "gain", "bullish", "breakout",
}
NEGATIVE_KEYWORDS = {
    "hack", "lawsuit", "ban", "outflow", "crash", "drop", "selloff", "bearish", "liquidation",
}
URGENT_KEYWORDS = {"breaking", "urgent", "emergency", "sec", "fed", "fomc", "cpi", "nfp"}


def _score_sentiment(title: str) -> float:
    text = title.lower()
    pos = sum(1 for k in POSITIVE_KEYWORDS if k in text)
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k in text)
    if pos == neg:
        return 0.0
    return max(min((pos - neg) / 3.0, 1.0), -1.0)


def _infer_tags(title: str) -> list[str]:
    text = title.lower()
    tags: list[str] = []
    if "etf" in text:
        tags.append("etf")
    if any(k in text for k in ("sec", "regulation", "lawsuit", "policy", "ban")):
        tags.append("regulation")
    if any(k in text for k in ("hack", "exploit", "breach")):
        tags.append("security")
    if any(k in text for k in ("fed", "fomc", "cpi", "inflation", "rates", "treasury")):
        tags.append("macro")
    if not tags:
        tags.append("market")
    return tags


def _infer_urgency(title: str) -> str:
    text = title.lower()
    return "high" if any(k in text for k in URGENT_KEYWORDS) else "medium"


def _parse_rss_items(xml_text: str, source: str) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    rows: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        link = (item.findtext("link") or "").strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        try:
            published_at = parsedate_to_datetime(pub_date_raw).astimezone(timezone.utc)
        except Exception:
            published_at = datetime.now(timezone.utc)
        rows.append(
            NewsItem(
                title=title,
                source=source,
                published_at=published_at,
                link=link,
                sentiment=_score_sentiment(title),
                urgency=_infer_urgency(title),
                tags=_infer_tags(title),
            )
        )
    return rows


def fetch_news_context(
    symbol: str,
    lookback_hours: int = 12,
    max_items: int = 12,
    timeout_seconds: int = 15,
) -> dict[str, Any]:
    """
    從 Google News RSS 取得加密/宏觀新聞，輸出結構化摘要。
    """
    base = "https://news.google.com/rss/search"
    queries = [
        f"{symbol} OR Bitcoin crypto when:1d",
        "crypto ETF SEC regulation when:1d",
        "Fed CPI inflation rates Bitcoin when:1d",
    ]
    urls = [f"{base}?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en" for q in queries]

    all_items: list[NewsItem] = []
    for url in urls:
        resp = requests.get(url, timeout=timeout_seconds)
        resp.raise_for_status()
        all_items.extend(_parse_rss_items(resp.text, "google_news"))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    filtered = [x for x in all_items if x.published_at >= cutoff]
    filtered.sort(key=lambda x: x.published_at, reverse=True)

    dedup: dict[str, NewsItem] = {}
    for item in filtered:
        key = item.title.lower()
        if key not in dedup:
            dedup[key] = item
    top = list(dedup.values())[:max_items]

    if not top:
        return {
            "lookback_hours": lookback_hours,
            "items_count": 0,
            "aggregate_sentiment": 0.0,
            "risk_flags": ["no_recent_news"],
            "top_events": [],
        }

    agg_sent = sum(item.sentiment for item in top) / len(top)
    high_urgency = sum(1 for item in top if item.urgency == "high")
    risk_flags: list[str] = []
    if high_urgency >= 3:
        risk_flags.append("event_risk_high")
    if any("security" in item.tags for item in top):
        risk_flags.append("security_incident_risk")
    if any("regulation" in item.tags for item in top):
        risk_flags.append("regulatory_risk")

    return {
        "lookback_hours": lookback_hours,
        "items_count": len(top),
        "aggregate_sentiment": round(agg_sent, 4),
        "risk_flags": risk_flags,
        "top_events": [
            {
                "title": item.title,
                "source": item.source,
                "published_at": item.published_at.isoformat(),
                "sentiment": item.sentiment,
                "urgency": item.urgency,
                "tags": item.tags,
                "link": item.link,
            }
            for item in top
        ],
    }
