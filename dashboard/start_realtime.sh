#!/bin/bash

# =============================================================================
# Crypto Market Analyzer Dashboard 啟動腳本
# 實時版本 - 支援 1-5 秒刷新間隔與 Redis 快取
# =============================================================================

set -e

echo "============================================"
echo "🚀 Crypto Market Analyzer Dashboard"
echo "    實時版本 v2.0"
echo "============================================"
echo ""

# 切換到 dashboard 目錄
cd "$(dirname "$0")"

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 檢查 Python 環境
echo "📦 檢查 Python 環境..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 找不到 Python 3${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 已安裝${NC}"

# 2. 檢查依賴
echo ""
echo "📚 檢查依賴套件..."
if ! python3 -c "import dash" &> /dev/null; then
    echo -e "${YELLOW}⚠️  缺少依賴，正在安裝...${NC}"
    pip3 install -r requirements.txt
else
    echo -e "${GREEN}✓ 依賴套件已安裝${NC}"
fi

# 3. 檢查 PostgreSQL
echo ""
echo "🗄️  檢查 PostgreSQL 連接..."
export POSTGRES_USER="${POSTGRES_USER:-crypto}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-crypto_pass}"
export POSTGRES_DB="${POSTGRES_DB:-crypto_db}"

if psql -h localhost -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL 連接成功${NC}"

    # 檢查資料表
    TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM ohlcv LIMIT 1;" 2>/dev/null || echo "0")
    echo "  - OHLCV 資料筆數: $TABLE_COUNT"
else
    echo -e "${YELLOW}⚠️  無法連接 PostgreSQL，請確保資料庫正在運行${NC}"
    echo "  提示: docker-compose up -d"
fi

# 4. 檢查 Redis（可選）
echo ""
echo "💾 檢查 Redis 連接（可選，用於快取）..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis 已啟用，將使用快取加速${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis 未運行，將不使用快取（仍可正常運行）${NC}"
        echo "  提示: 啟動 Redis 可減少資料庫查詢次數"
    fi
else
    echo -e "${YELLOW}⚠️  未安裝 Redis，將不使用快取（仍可正常運行）${NC}"
fi

# 5. 啟動 Dashboard
echo ""
echo "============================================"
echo "🎯 啟動 Dashboard..."
echo "============================================"
echo ""
echo -e "${GREEN}訪問地址: http://localhost:8050${NC}"
echo ""
echo "功能特色:"
echo "  ⚡ 實時刷新: 價格/訂單簿 1秒, 技術指標 5秒"
echo "  💾 Redis 快取: 減少 DB 查詢壓力"
echo "  📊 多層級刷新: 依組件重要性調整頻率"
echo ""
echo "按 Ctrl+C 停止..."
echo ""

# 啟動應用
python3 app.py
