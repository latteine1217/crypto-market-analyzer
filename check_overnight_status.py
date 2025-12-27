#!/usr/bin/env python
"""檢查一晚數據收集狀況"""
import psycopg2
from datetime import datetime, timezone, timedelta

conn = psycopg2.connect(
    host="localhost", port=5432,
    database="crypto_db", user="crypto", password="crypto_pass"
)
cur = conn.cursor()

now_utc = datetime.now(tz=timezone.utc)
last_night = now_utc - timedelta(hours=11)

print("=" * 80)
print("📊 一晚數據收集統計報告")
print("=" * 80)
print(f"當前時間: {now_utc}")
print(f"收集起始: ~{last_night} (約 11 小時前)")
print()

# Bybit OHLCV 統計
print("=== Bybit OHLCV (1m K線) ===")
cur.execute("""
    SELECT m.symbol,
           COUNT(*) as total,
           MIN(open_time) as earliest,
           MAX(open_time) as latest,
           (SELECT COUNT(*) FROM ohlcv o2
            WHERE o2.market_id = m.id AND o2.timeframe = '1m'
            AND o2.open_time >= %s) as last_11h
    FROM markets m
    JOIN exchanges e ON m.exchange_id = e.id
    LEFT JOIN ohlcv o ON m.id = o.market_id AND o.timeframe = '1m'
    WHERE e.name = 'bybit'
    GROUP BY m.id, m.symbol
    ORDER BY m.symbol
""", (last_night,))

for row in cur.fetchall():
    symbol, total, earliest, latest, last_11h = row
    if latest:
        time_ago = (now_utc - latest).total_seconds() / 60
        status = "✅" if time_ago < 5 else "⚠️"
    else:
        time_ago = float("inf")
        status = "❌"

    print(f"{status} {symbol}:")
    print(f"   總數據: {total:,} 條")
    print(f"   最早: {earliest}")
    print(f"   最新: {latest} ({time_ago:.1f} 分鐘前)")
    print(f"   過去 11 小時: {last_11h:,} 條 (預期 ~660)")
    completion = (last_11h / 660 * 100) if last_11h else 0
    print(f"   完成度: {completion:.1f}%")
    print()

# Trades 統計
print("=== Bybit Trades ===")
cur.execute("""
    SELECT m.symbol,
           COUNT(*) as total,
           MIN(timestamp) as earliest,
           MAX(timestamp) as latest,
           (SELECT COUNT(*) FROM trades t2
            WHERE t2.market_id = m.id
            AND t2.timestamp >= %s) as last_11h
    FROM markets m
    JOIN exchanges e ON m.exchange_id = e.id
    LEFT JOIN trades t ON m.id = t.market_id
    WHERE e.name = 'bybit'
    GROUP BY m.id, m.symbol
    ORDER BY m.symbol
""", (last_night,))

for row in cur.fetchall():
    symbol, total, earliest, latest, last_11h = row
    print(f"{symbol}:")
    print(f"   總數據: {total:,} 筆")
    print(f"   過去 11 小時: {last_11h:,} 筆 (預期 ~39,600)")
    completion = (last_11h / 39600 * 100) if last_11h else 0
    print(f"   完成度: {completion:.1f}%")
    print()

# OrderBook 統計
print("=== Bybit OrderBook Snapshots ===")
cur.execute("""
    SELECT m.symbol,
           COUNT(*) as total,
           (SELECT COUNT(*) FROM orderbook_snapshots o2
            WHERE o2.market_id = m.id
            AND o2.timestamp >= %s) as last_11h
    FROM markets m
    JOIN exchanges e ON m.exchange_id = e.id
    LEFT JOIN orderbook_snapshots o ON m.id = o.market_id
    WHERE e.name = 'bybit'
    GROUP BY m.id, m.symbol
    ORDER BY m.symbol
""", (last_night,))

for row in cur.fetchall():
    symbol, total, last_11h = row
    print(f"{symbol}: {total:,} 條 (過去 11h: {last_11h:,}, 預期 ~660)")
    completion = (last_11h / 660 * 100) if last_11h else 0
    print(f"   完成度: {completion:.1f}%")

print()
print("=" * 80)

# 檢查數據連續性
print("\n=== 數據連續性檢查 ===")
cur.execute("""
    SELECT m.symbol,
           COUNT(*) as gaps
    FROM markets m
    JOIN exchanges e ON m.exchange_id = e.id
    JOIN LATERAL (
        SELECT o1.open_time, o2.open_time as next_time
        FROM ohlcv o1
        LEFT JOIN ohlcv o2 ON o2.market_id = o1.market_id
            AND o2.timeframe = o1.timeframe
            AND o2.open_time = o1.open_time + INTERVAL '1 minute'
        WHERE o1.market_id = m.id
            AND o1.timeframe = '1m'
            AND o1.open_time >= %s
            AND o2.open_time IS NULL
    ) gaps ON true
    WHERE e.name = 'bybit'
    GROUP BY m.symbol
    ORDER BY m.symbol
""", (last_night,))

print("過去 11 小時的數據缺口:")
for row in cur.fetchall():
    symbol, gaps = row
    status = "✅" if gaps == 1 else "⚠️"  # 只有最後一條可能沒有 next
    print(f"{status} {symbol}: {gaps} 個缺口")

cur.close()
conn.close()
