#!/bin/bash

# ============================================
# Collector 啟動腳本
# 用途：啟動資料收集服務
# ============================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COLLECTOR_DIR="$PROJECT_ROOT/collector-py"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Crypto Market Data Collector ===${NC}"

# 檢查環境
if [ ! -f "$COLLECTOR_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "${YELLOW}Copying from .env.example...${NC}"
    cp "$COLLECTOR_DIR/.env.example" "$COLLECTOR_DIR/.env"
    echo -e "${RED}Please edit .env file with your configuration${NC}"
    exit 1
fi

# 檢查虛擬環境
if [ ! -d "$COLLECTOR_DIR/venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv "$COLLECTOR_DIR/venv"
    echo -e "${GREEN}Virtual environment created${NC}"
fi

# 啟動虛擬環境
echo -e "${GREEN}Activating virtual environment...${NC}"
source "$COLLECTOR_DIR/venv/bin/activate"

# 安裝依賴
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -q -r "$COLLECTOR_DIR/requirements.txt"

# 運行 collector
echo -e "${GREEN}Starting collector...${NC}"
cd "$COLLECTOR_DIR"
python src/main.py

# 清理
deactivate
echo -e "${GREEN}=== Collector stopped ===${NC}"
