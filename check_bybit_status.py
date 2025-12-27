#!/usr/bin/env python
"""檢查 Bybit collector 狀態"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv("collector-py/.env")

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", 5432),
    database=os.getenv("POSTGRES_DB", "crypto_db"),
    user=os.getenv("POSTGRES_USER", "crypto"),
    password=os.getenv("POSTGRES_PASSWORD", "crypto_pass")
)

cur = conn.cursor()

# 查詢 Bybit 各交易對的最新數據
cur.execute("""
    SELECT m.symbol,
           (SELECT MAX(open_time) FROM ohlcv WHERE market_id = m.id) as latest_ohlcv,
           (SELECT COUNT(*) FROM trades WHERE market_id = m.id AND timestamp > NOW() - INTERVAL '5 minutes') as recent_trades,
           (SELECT COUNT(*) FROM orderbook_snapshots WHERE market_id = m.id AND timestamp > NOW() - INTERVAL '5 minutes') as recent_orderbooks
    FROM markets m
    WHERE m.exchange = 'bybit'
    ORDER BY m.symbol
""")

print("=== Bybit Collector 狀態 ===\n")
for row in cur.fetchall():
    symbol, latest_ohlcv, recent_trades, recent_orderbooks = row
    print(f"{symbol}:")
    print(f"  最新 OHLCV: {latest_ohlcv}")
    print(f"  最近 5 分鐘 trades: {recent_trades} 筆")
    print(f"  最近 5 分鐘 orderbooks: {recent_orderbooks} 筆")
    print()

cur.close()
conn.close()
