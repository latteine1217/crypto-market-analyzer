#!/bin/bash
# 啟動配置驅動的 Collector V2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================="
echo "Crypto Data Collector V2"
echo "配置驅動 + 品質監控 + 自動補資料"
echo "================================="
echo ""

# 檢查資料庫是否運行
echo "[1/3] 檢查 TimescaleDB..."
if ! docker ps | grep -q crypto_timescaledb; then
    echo "❌ TimescaleDB 未運行！請先執行: docker-compose up -d"
    exit 1
fi
echo "✅ TimescaleDB 正在運行"

# 檢查 Python 依賴
echo ""
echo "[2/3] 檢查 Python 依賴..."
cd "$PROJECT_ROOT/collector-py"

if ! python3 -c "import ccxt, psycopg2, yaml, loguru" 2>/dev/null; then
    echo "❌ Python 依賴缺失！請執行: pip3 install -r requirements.txt"
    exit 1
fi
echo "✅ Python 依賴已安裝"

# 啟動 Collector
echo ""
echo "[3/3] 啟動 Collector V2..."
echo ""
cd "$PROJECT_ROOT/collector-py/src"

python3 main_v2.py

echo ""
echo "Collector 已停止"
