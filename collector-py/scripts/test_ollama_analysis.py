"""
What:
最小可行的 Ollama 分析 smoke test。

Why:
驗證本機可否用既有資料完成「摘要 -> LLM 分析 -> 結構化輸出」。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loaders.db_loader import DatabaseLoader
from tasks.ollama_analysis import (
    MarketSnapshot,
    build_prompt,
    call_ollama,
    compute_realized_volatility_pct,
)
from tasks.news_context import fetch_news_context


def _get_market_id(conn, symbol: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id
            FROM markets m
            JOIN exchanges e ON e.id = m.exchange_id
            WHERE e.name = 'bybit' AND m.symbol = %s
            LIMIT 1
            """,
            (symbol,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def load_snapshot(symbol: str, timeframe: str, lookback_minutes: int) -> MarketSnapshot:
    db = DatabaseLoader()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=lookback_minutes)

    with db.get_connection() as conn:
        market_id = _get_market_id(conn, symbol)
        if market_id is None:
            raise RuntimeError(f"找不到市場 {symbol} (bybit)")

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT time, high, low, close, volume
                FROM ohlcv
                WHERE market_id = %s
                  AND timeframe = %s
                  AND time >= %s
                ORDER BY time ASC
                """,
                (market_id, timeframe, start_time),
            )
            rows = cur.fetchall()

            if len(rows) < 2:
                raise RuntimeError(
                    f"OHLCV 不足: {symbol} {timeframe} 在最近 {lookback_minutes} 分鐘只有 {len(rows)} 筆"
                )

            highs = [float(row[1]) for row in rows]
            lows = [float(row[2]) for row in rows]
            closes = [float(row[3]) for row in rows]
            volumes = [float(row[4]) for row in rows]

            cur.execute(
                """
                SELECT value
                FROM market_metrics
                WHERE market_id = %s AND name = 'funding_rate'
                ORDER BY time DESC
                LIMIT 1
                """,
                (market_id,),
            )
            funding_row = cur.fetchone()

            cur.execute(
                """
                SELECT value
                FROM market_metrics
                WHERE market_id = %s AND name = 'open_interest'
                ORDER BY time DESC
                LIMIT 1
                """,
                (market_id,),
            )
            oi_row = cur.fetchone()

            cur.execute(
                """
                SELECT value, classification
                FROM global_indicators
                WHERE category = 'sentiment' AND name = 'fear_greed'
                ORDER BY time DESC
                LIMIT 1
                """
            )
            fear_greed_row = cur.fetchone()

            cur.execute(
                """
                SELECT COALESCE(SUM(value), 0)
                FROM global_indicators
                WHERE category = 'etf'
                  AND time >= NOW() - INTERVAL '24 hours'
                """
            )
            etf_row = cur.fetchone()

    snapshot = MarketSnapshot(
        symbol=symbol,
        timeframe=timeframe,
        window_start=rows[0][0],
        window_end=rows[-1][0],
        candle_count=len(rows),
        close_first=closes[0],
        close_last=closes[-1],
        pct_change=((closes[-1] - closes[0]) / closes[0]) * 100 if closes[0] else 0.0,
        intrawindow_range_pct=((max(highs) - min(lows)) / closes[0]) * 100 if closes[0] else 0.0,
        realized_volatility_pct=compute_realized_volatility_pct(closes),
        volume_sum=sum(volumes),
        latest_funding_rate=float(funding_row[0]) if funding_row else None,
        latest_open_interest=float(oi_row[0]) if oi_row else None,
        fear_greed_value=float(fear_greed_row[0]) if fear_greed_row else None,
        fear_greed_classification=fear_greed_row[1] if fear_greed_row else None,
        etf_net_flow_24h_usd=float(etf_row[0]) if etf_row else None,
    )
    db.close()
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Ollama 分析 smoke test")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="1m")
    parser.add_argument("--minutes", type=int, default=180)
    parser.add_argument("--model", default="glm-4.7:cloud")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--news-lookback-hours", type=int, default=12)
    parser.add_argument("--news-max-items", type=int, default=10)
    parser.add_argument("--disable-news", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    snapshot = load_snapshot(args.symbol, args.timeframe, args.minutes)
    news_context = None
    if not args.disable_news:
        try:
            news_context = fetch_news_context(
                symbol=args.symbol,
                lookback_hours=args.news_lookback_hours,
                max_items=args.news_max_items,
                timeout_seconds=min(args.timeout_seconds, 30),
            )
        except Exception as exc:
            logger.warning(f"新聞抓取失敗，改用 fallback: {exc}")
            news_context = {
                "lookback_hours": args.news_lookback_hours,
                "items_count": 0,
                "aggregate_sentiment": 0.0,
                "risk_flags": ["news_unavailable"],
                "top_events": [],
            }

    prompt = build_prompt(snapshot, news_context=news_context)

    print("=== Ollama Analysis Smoke Test ===")
    print(f"symbol={args.symbol} timeframe={args.timeframe} minutes={args.minutes}")
    print(
        "data_window="
        f"{snapshot.window_start.isoformat()} ~ {snapshot.window_end.isoformat()} "
        f"candles={snapshot.candle_count}"
    )
    if news_context is not None:
        print(
            "news_context="
            f"items={news_context.get('items_count', 0)} "
            f"sentiment={news_context.get('aggregate_sentiment', 0.0)} "
            f"risk_flags={news_context.get('risk_flags', [])}"
        )

    if args.dry_run:
        print("--- Prompt Preview (first 600 chars) ---")
        print(prompt[:600])
        return

    result = call_ollama(
        model=args.model,
        prompt=prompt,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
    )
    print("--- Analysis JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    logger.success("Ollama 分析 smoke test 完成")


if __name__ == "__main__":
    main()
