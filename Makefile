# Crypto Market Dashboard - 快速命令集
.PHONY: help test-rich-list test-all status logs up down restart rebuild clean

help: ## 顯示可用命令
	@echo "可用命令："
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === 測試命令 ===
test-rich-list: ## 執行 Rich List 完整驗收測試
	@echo "執行 Rich List 驗收測試..."
	@./scripts/test_rich_list_complete.sh

test-frontend-parsing: ## 測試前端 rank_group 解析邏輯
	@echo "測試前端解析邏輯..."
	@node ./scripts/test_frontend_parsing.js

test-all: ## 執行所有測試
	@echo "執行所有測試..."
	@./scripts/test_rich_list_complete.sh
	@node ./scripts/test_frontend_parsing.js

# === Docker 管理 ===
# 初始化全球指標資料 (修復 Dashboard 空白問題)
init-indicators:
	@echo "Initializing Global Indicators (Fear&Greed)..."
	docker-compose exec -T collector python /app/scripts/init_global_indicators.py

status: ## 查看容器狀態
	@docker-compose ps

logs: ## 查看所有容器日誌（最近 50 行）
	@docker-compose logs --tail=50

logs-collector: ## 查看 Collector 日誌
	@docker-compose logs -f collector

logs-api: ## 查看 API Server 日誌
	@docker-compose logs -f api-server

logs-dashboard: ## 查看 Dashboard 日誌
	@docker-compose logs -f dashboard-ts

up: ## 啟動所有服務
	@docker-compose up -d
	@echo "等待服務啟動..."
	@sleep 5
	@docker-compose ps

down: ## 停止所有服務
	@docker-compose down

restart: ## 重啟所有服務
	@docker-compose restart
	@echo "等待服務重啟..."
	@sleep 3
	@docker-compose ps

restart-api: ## 重啟 API Server
	@docker-compose restart api-server
	@echo "API Server 已重啟"

restart-collector: ## 重啟 Collector
	@docker-compose restart collector
	@echo "Collector 已重啟"

rebuild: ## 重新建置並啟動所有服務
	@docker-compose down
	@docker-compose build --no-cache
	@docker-compose up -d
	@echo "等待服務啟動..."
	@sleep 10
	@docker-compose ps

# === 資料庫管理 ===
db-shell: ## 進入 PostgreSQL Shell
	@docker exec -it crypto_timescaledb psql -U crypto -d crypto_db

db-check-rich-list: ## 檢查 Rich List 資料 (V3 Schema)
	@docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "\
	SELECT DATE(time) as date, COUNT(*) as records, \
	ROUND(SUM(total_balance)::numeric, 0) as total_btc \
	FROM address_tier_snapshots \
	GROUP BY DATE(time) ORDER BY date DESC LIMIT 5;"

db-check-fear-greed: ## 檢查 Fear & Greed Index 資料 (V3 Schema)
	@docker exec crypto_timescaledb psql -U crypto -d crypto_db -c "\
	SELECT time, value, classification \
	FROM global_indicators \
	WHERE name = 'fear_greed' \
	ORDER BY time DESC LIMIT 10;"

# === API 測試 ===
api-test-rich-list: ## 測試 Rich List API
	@curl -s "http://localhost/api/blockchain/BTC/rich-list?days=30" | jq '.data | group_by(.snapshot_date) | map({date: .[0].snapshot_date, count: length})'

api-test-fear-greed: ## 測試 Fear & Greed API
	@curl -s "http://localhost/api/fear-greed/latest" | jq '.'

# === 清理 ===
clean: ## 清理未使用的 Docker 資源
	@docker system prune -f
	@echo "Docker 資源已清理"

clean-all: ## 清理所有 Docker 資源（包含 Volume）
	@docker-compose down -v
	@docker system prune -af --volumes
	@echo "所有 Docker 資源已清理（包含資料庫！）"
