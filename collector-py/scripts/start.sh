#!/bin/bash
# set -e  <-- 暫時移除，以便捕捉錯誤

echo "=================================================="
echo "🚀 Crypto Collector Container Starting"
echo "=================================================="

# 確保 logs 目錄存在
mkdir -p /app/logs

# 1. 回填 Bybit 歷史數據 (1年) - 最優先任務
# 這能確保 DataValidator 在啟動時就有足夠的 K 線數據
echo "📊 [Startup] Backfilling Bybit historical data..."
python /app/scripts/backfill_history.py

# 2. 初始化全球指標 (Fear&Greed, FRED, ETF)
echo "🔄 [Startup] Initializing global indicators..."
python /app/scripts/init_global_indicators.py

# 2.5 初始化衍生品歷史 (Funding & OI)
echo "📈 [Startup] Backfilling Derivatives history (Funding & OI)..."
python /app/scripts/backfill_funding.py
python /app/scripts/backfill_oi.py

# 2.6 初始化事件日曆 (Upcoming Events)
echo "📅 [Startup] Initializing Market Events..."
python /app/scripts/init_events.py

# 3. 啟動主程式 (Orchestrator)
echo "🔥 [Startup] Starting main collector process..."
# 捕捉標準輸出和錯誤輸出
exec python -m src.main 2>&1 | tee /app/logs/collector.log
