"""
What:
提供最小可行的 Ollama 分析流程：將市場摘要轉為提示詞，呼叫 Ollama，並解析結果。

Why:
在不動既有排程與資料收集流程下，先驗證「抓取資料 -> 模型分析 -> 結構化輸出」可行性。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any

import requests


@dataclass
class MarketSnapshot:
    symbol: str
    timeframe: str
    window_start: datetime
    window_end: datetime
    candle_count: int
    close_first: float
    close_last: float
    pct_change: float
    intrawindow_range_pct: float
    realized_volatility_pct: float
    volume_sum: float
    latest_funding_rate: float | None
    latest_open_interest: float | None
    fear_greed_value: float | None
    fear_greed_classification: str | None
    etf_net_flow_24h_usd: float | None


def build_prompt(snapshot: MarketSnapshot, news_context: dict[str, Any] | None = None) -> str:
    """建立固定格式提示詞，要求模型輸出 JSON。"""
    payload = {
        "symbol": snapshot.symbol,
        "timeframe": snapshot.timeframe,
        "window_start_utc": snapshot.window_start.isoformat(),
        "window_end_utc": snapshot.window_end.isoformat(),
        "candle_count": snapshot.candle_count,
        "price": {
            "close_first": round(snapshot.close_first, 6),
            "close_last": round(snapshot.close_last, 6),
            "pct_change": round(snapshot.pct_change, 4),
            "intrawindow_range_pct": round(snapshot.intrawindow_range_pct, 4),
            "realized_volatility_pct": round(snapshot.realized_volatility_pct, 4),
            "volume_sum": round(snapshot.volume_sum, 4),
        },
        "derivatives": {
            "latest_funding_rate": snapshot.latest_funding_rate,
            "latest_open_interest": snapshot.latest_open_interest,
        },
        "macro_sentiment": {
            "fear_greed_value": snapshot.fear_greed_value,
            "fear_greed_classification": snapshot.fear_greed_classification,
            "etf_net_flow_24h_usd": snapshot.etf_net_flow_24h_usd,
        },
        "news_context": news_context or {
            "items_count": 0,
            "aggregate_sentiment": 0.0,
            "risk_flags": ["news_unavailable"],
            "top_events": [],
        },
    }
    return (
        "你是加密量化分析助手。請根據資料輸出 JSON，不要輸出其他文字。\n"
        "JSON schema:\n"
        "{\n"
        '  "trend": "bullish|bearish|sideways",\n'
        '  "risk_level": "low|medium|high",\n'
        '  "confidence": 0-1,\n'
        '  "signals": ["最多3條重點"],\n'
        '  "news_impact_assessment": "事件對市場影響摘要(80字內)",\n'
        '  "action_adjustment": "enter|wait|reduce_risk",\n'
        '  "rationale": "100字以內，說明依據"\n'
        "}\n"
        f"DATA:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def parse_json_object(raw_text: str) -> dict[str, Any]:
    """從模型輸出中提取 JSON 物件。"""
    text = raw_text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model output does not contain JSON object")
        return json.loads(text[start : end + 1])


def call_ollama(
    model: str,
    prompt: str,
    base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: int = 60,
    max_retries: int = 2,
) -> dict[str, Any]:
    """呼叫 Ollama chat API，回傳解析後的 JSON 結果。"""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "stream": False,
                    "messages": [{"role": "user", "content": prompt}],
                    "options": {"temperature": 0.1},
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = body.get("message", {}).get("content", "")
            parsed = parse_json_object(content)
            parsed["_model"] = model
            parsed["_generated_at"] = datetime.now(timezone.utc).isoformat()
            return parsed
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(min(2 * attempt, 5))
    raise RuntimeError(f"Ollama request failed after {max_retries} attempts: {last_error}")


def compute_realized_volatility_pct(closes: list[float]) -> float:
    """使用簡化報酬率標準差估計波動率百分比。"""
    if len(closes) < 2:
        return 0.0
    returns: list[float] = []
    for idx in range(1, len(closes)):
        prev = closes[idx - 1]
        curr = closes[idx]
        if prev == 0:
            continue
        returns.append((curr - prev) / prev)
    if not returns:
        return 0.0
    return pstdev(returns) * 100
