#!/bin/bash
# Docker 環境快速啟動腳本
# Phase 6: 部署與自動化

set -e

echo "======================================"
echo "Crypto Market Analyzer - Docker 啟動"
echo "======================================"

# 檢查 .env 檔案
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 檔案，從 .env.example 複製..."
    cp .env.example .env
    echo "✅ .env 已建立，請編輯 .env 設定必要參數後再次執行此腳本"
    echo ""
    echo "必要設定："
    echo "  - POSTGRES_PASSWORD（資料庫密碼）"
    echo "  - SMTP_* 配置（用於報表與告警）"
    echo ""
    exit 1
fi

echo "✅ 環境變數檔案存在"

# 檢查 Docker
echo ""
echo "檢查 Docker 環境..."
if ! command -v docker &> /dev/null; then
    echo "❌ 未安裝 Docker，請先安裝 Docker Desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 未安裝 docker-compose，請先安裝"
    exit 1
fi

echo "✅ Docker 版本：$(docker --version)"
echo "✅ Docker Compose 版本：$(docker-compose --version)"

# 詢問啟動模式
echo ""
echo "請選擇啟動模式："
echo "  1. 基礎服務（DB + Redis）"
echo "  2. 資料收集（基礎 + Collector + WS-Collector）"
echo "  3. 完整服務（包含監控 + 報表）"
echo "  4. 僅監控（Prometheus + Grafana + Alertmanager）"
echo "  5. 全部服務"
read -p "請輸入選項 [1-5] (預設: 3): " mode
mode=${mode:-3}

case $mode in
    1)
        services="db redis"
        ;;
    2)
        services="db redis collector ws-collector"
        ;;
    3)
        services="db redis collector ws-collector analyzer report-scheduler prometheus grafana alertmanager"
        ;;
    4)
        services="prometheus grafana alertmanager node-exporter postgres-exporter redis-exporter"
        ;;
    5)
        services=""
        ;;
    *)
        echo "❌ 無效選項"
        exit 1
        ;;
esac

# 啟動服務
echo ""
echo "======================================"
echo "正在啟動服務..."
echo "======================================"

if [ -z "$services" ]; then
    docker-compose up -d
else
    docker-compose up -d $services
fi

# 等待服務啟動
echo ""
echo "等待服務啟動..."
sleep 10

# 檢查服務狀態
echo ""
echo "======================================"
echo "服務狀態"
echo "======================================"
docker-compose ps

# 顯示存取資訊
echo ""
echo "======================================"
echo "服務存取資訊"
echo "======================================"

if docker-compose ps | grep -q "crypto_timescaledb"; then
    echo "📊 TimescaleDB: localhost:5432"
    echo "   - Database: crypto_db"
    echo "   - User: crypto"
fi

if docker-compose ps | grep -q "crypto_redis"; then
    echo "🔴 Redis: localhost:6379"
fi

if docker-compose ps | grep -q "crypto_jupyter"; then
    echo "📓 Jupyter Lab: http://localhost:8888"
fi

if docker-compose ps | grep -q "crypto_prometheus"; then
    echo "📈 Prometheus: http://localhost:9090"
fi

if docker-compose ps | grep -q "crypto_grafana"; then
    echo "📊 Grafana: http://localhost:3000"
    echo "   - 預設帳號: admin / admin"
fi

if docker-compose ps | grep -q "crypto_alertmanager"; then
    echo "🚨 Alertmanager: http://localhost:9093"
fi

echo ""
echo "======================================"
echo "常用指令"
echo "======================================"
echo "查看所有服務狀態："
echo "  docker-compose ps"
echo ""
echo "查看服務日誌："
echo "  docker-compose logs -f [service_name]"
echo ""
echo "停止所有服務："
echo "  docker-compose down"
echo ""
echo "重啟特定服務："
echo "  docker-compose restart [service_name]"
echo ""
echo "進入容器："
echo "  docker exec -it [container_name] bash"
echo ""

echo "✅ 啟動完成！"
