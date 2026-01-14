#!/bin/bash
# 測試 BTC 地址分層追蹤 cron 任務
#
# 這個腳本模擬 cron 環境來測試任務是否正常執行

set -e

PROJECT_DIR="/Users/latteine/Documents/coding/finance"
LOG_FILE="$PROJECT_DIR/logs/address_tiers/test_run.log"

echo "=========================================="
echo "測試 BTC 地址分層追蹤 Cron 任務"
echo "=========================================="
echo ""

# 1. 檢查環境
echo "📝 檢查環境..."
echo "  工作目錄: $PROJECT_DIR"
echo "  Python: $(which python3)"
echo "  Python 版本: $(python3 --version)"
echo ""

# 2. 模擬 cron 環境執行
echo "🚀 執行收集任務（模擬 cron 環境）..."
echo "  日誌輸出: $LOG_FILE"
echo ""

cd "$PROJECT_DIR" && python3 collector-py/collect_address_tiers.py > "$LOG_FILE" 2>&1

# 3. 檢查執行結果
if [ $? -eq 0 ]; then
    echo "✅ 任務執行成功！"
    echo ""
    echo "最後 20 行日誌:"
    echo "─────────────────────────────────────"
    tail -20 "$LOG_FILE"
    echo "─────────────────────────────────────"
else
    echo "❌ 任務執行失敗"
    echo ""
    echo "錯誤日誌:"
    tail -50 "$LOG_FILE"
    exit 1
fi

# 4. 驗證資料庫
echo ""
echo "📊 驗證資料庫資料..."
docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "
    SELECT 
        COUNT(*) as total_records,
        MAX(snapshot_date)::date as latest_date
    FROM address_tier_snapshots 
    WHERE blockchain_id = 1;
"

echo ""
echo "=========================================="
echo "✅ 測試完成"
echo "=========================================="
echo ""
echo "下一步:"
echo "  • 等待明天 00:05 自動執行"
echo "  • 或手動觸發: cd $PROJECT_DIR && python3 collector-py/collect_address_tiers.py"
echo "  • 查看 cron 日誌: tail -f $PROJECT_DIR/logs/address_tiers/cron.log"
echo ""
