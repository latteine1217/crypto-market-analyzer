#!/bin/bash
# 設定 BTC 地址分層追蹤自動化排程
# 
# 執行方式：
#   chmod +x scripts/setup_address_tier_cron.sh
#   ./scripts/setup_address_tier_cron.sh

set -e

PROJECT_DIR="/Users/latteine/Documents/coding/finance"
PYTHON_BIN="python3"
COLLECTOR_SCRIPT="$PROJECT_DIR/collector-py/collect_address_tiers.py"
LOG_DIR="$PROJECT_DIR/logs/address_tiers"
CRON_LOG="$LOG_DIR/cron.log"

echo "=========================================="
echo "BTC 地址分層追蹤 - Crontab 設定"
echo "=========================================="
echo ""

# 1. 檢查 Python 腳本是否存在
if [ ! -f "$COLLECTOR_SCRIPT" ]; then
    echo "❌ 錯誤: 找不到收集腳本"
    echo "   路徑: $COLLECTOR_SCRIPT"
    exit 1
fi
echo "✅ 收集腳本存在: $COLLECTOR_SCRIPT"

# 2. 建立日誌目錄
mkdir -p "$LOG_DIR"
echo "✅ 日誌目錄已建立: $LOG_DIR"

# 3. 測試腳本執行
echo ""
echo "📝 測試腳本執行..."
cd "$PROJECT_DIR"
if $PYTHON_BIN "$COLLECTOR_SCRIPT" 2>&1 | tail -5; then
    echo "✅ 腳本測試執行成功"
else
    echo "❌ 腳本測試執行失敗，請檢查錯誤訊息"
    exit 1
fi

# 4. 建立 crontab entry
echo ""
echo "📝 準備設定 crontab..."
echo ""
echo "建議的 crontab 排程："
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│ # BTC 地址分層追蹤（每天 00:05 執行）                   │"
echo "│ 5 0 * * * cd $PROJECT_DIR && $PYTHON_BIN $COLLECTOR_SCRIPT >> $CRON_LOG 2>&1"
echo "└─────────────────────────────────────────────────────────┘"
echo ""

# 5. 詢問是否自動設定
read -p "是否自動加入到 crontab? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 檢查是否已存在相同的 cron job
    if crontab -l 2>/dev/null | grep -q "collect_address_tiers.py"; then
        echo "⚠️  Crontab 中已存在地址分層收集任務"
        read -p "是否覆蓋現有設定? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ 已取消"
            exit 0
        fi
        # 移除舊的 entry
        crontab -l 2>/dev/null | grep -v "collect_address_tiers.py" | crontab -
        echo "✅ 已移除舊的 crontab 設定"
    fi
    
    # 加入新的 crontab entry
    (crontab -l 2>/dev/null; echo "# BTC 地址分層追蹤（每天 00:05 執行）"; echo "5 0 * * * cd $PROJECT_DIR && $PYTHON_BIN $COLLECTOR_SCRIPT >> $CRON_LOG 2>&1") | crontab -
    
    echo ""
    echo "✅ Crontab 設定成功！"
    echo ""
    echo "當前 crontab 列表："
    echo "─────────────────────────────────────"
    crontab -l | grep -A 1 "BTC 地址分層追蹤"
    echo "─────────────────────────────────────"
else
    echo ""
    echo "📝 手動設定方式："
    echo ""
    echo "1. 執行: crontab -e"
    echo "2. 加入以下行："
    echo ""
    echo "   # BTC 地址分層追蹤（每天 00:05 執行）"
    echo "   5 0 * * * cd $PROJECT_DIR && $PYTHON_BIN $COLLECTOR_SCRIPT >> $CRON_LOG 2>&1"
    echo ""
fi

echo ""
echo "=========================================="
echo "🎯 設定完成"
echo "=========================================="
echo ""
echo "排程資訊："
echo "  • 執行時間: 每天 00:05"
echo "  • 日誌位置: $CRON_LOG"
echo "  • 查看 cron: crontab -l"
echo "  • 移除 cron: crontab -e (手動刪除該行)"
echo ""
echo "測試方式："
echo "  • 手動執行: cd $PROJECT_DIR && $PYTHON_BIN $COLLECTOR_SCRIPT"
echo "  • 查看日誌: tail -f $CRON_LOG"
echo "  • 查看資料: psql -U crypto -d crypto_db -c 'SELECT * FROM address_tier_snapshots ORDER BY snapshot_date DESC LIMIT 10;'"
echo ""
