#!/bin/bash
# 檢查歷史資料回填進度

echo "=========================================="
echo "📊 歷史資料回填進度監控"
echo "=========================================="
echo ""

# 檢查背景程序
echo "🔍 執行中的回填任務："
ps aux | grep "backfill_historical_ohlcv.py" | grep -v grep | awk '{print "  PID " $2 ": " $11 " " $12 " " $13 " " $14 " " $15}'

if [ $? -ne 0 ]; then
    echo "  無執行中的回填任務"
fi

echo ""
echo "------------------------------------------"
echo "📋 最新日誌輸出："
echo "------------------------------------------"

# 顯示各個任務的最新進度
if [ -f logs/backfill_btc_1m_90d.log ]; then
    echo ""
    echo "🔵 BTC 1m (90天):"
    tail -n 3 logs/backfill_btc_1m_90d.log | sed 's/^/  /'
fi

if [ -f logs/backfill_btc_1h_365d.log ]; then
    echo ""
    echo "🟢 BTC 1h (365天):"
    tail -n 3 logs/backfill_btc_1h_365d.log | sed 's/^/  /'
fi

if [ -f logs/backfill_eth_1m_90d.log ]; then
    echo ""
    echo "🟡 ETH 1m (90天):"
    tail -n 3 logs/backfill_eth_1m_90d.log | sed 's/^/  /'
fi

echo ""
echo "------------------------------------------"
echo "💾 資料庫目前資料量："
echo "------------------------------------------"

# 查詢資料庫
python3 << 'PYTHON'
import psycopg2
from datetime import datetime

try:
    conn = psycopg2.connect(
        dbname='crypto_db',
        user='crypto',
        password='crypto_pass',
        host='localhost',
        port='5432'
    )
    cur = conn.cursor()

    # 按 symbol 和 timeframe 統計
    cur.execute("""
        SELECT
            m.symbol,
            o.timeframe,
            COUNT(*) as count,
            MIN(o.open_time) as first_time,
            MAX(o.open_time) as last_time
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.market_id
        GROUP BY m.symbol, o.timeframe
        ORDER BY m.symbol, o.timeframe
    """)

    results = cur.fetchall()

    if results:
        for symbol, tf, count, first_time, last_time in results:
            duration = last_time - first_time
            days = duration.total_seconds() / 86400
            print(f"\n  {symbol} ({tf}):")
            print(f"    筆數: {count:,}")
            print(f"    時間範圍: {first_time} ~ {last_time}")
            print(f"    涵蓋: {days:.1f} 天")
    else:
        print("\n  尚無資料")

    cur.close()
    conn.close()

except Exception as e:
    print(f"\n  ❌ 無法連接資料庫: {e}")

PYTHON

echo ""
echo "=========================================="
echo "💡 提示："
echo "  - 即時監控日誌: tail -f logs/backfill_btc_1m_90d.log"
echo "  - 停止所有回填: pkill -f backfill_historical_ohlcv"
echo "  - 重新執行此腳本: bash scripts/check_backfill_progress.sh"
echo "=========================================="
