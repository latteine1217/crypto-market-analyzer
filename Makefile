.PHONY: help setup start stop restart logs clean test

help:
	@echo "=========================================="
	@echo "Crypto Market Analyzer - Commands"
	@echo "=========================================="
	@echo "make setup      - 初始化專案（建立.env檔案）"
	@echo "make start      - 啟動所有服務"
	@echo "make stop       - 停止所有服務"
	@echo "make restart    - 重啟所有服務"
	@echo "make logs       - 查看服務日誌"
	@echo "make clean      - 清理Docker資源"
	@echo "make db-shell   - 進入資料庫shell"
	@echo "make collector  - 執行數據收集器"
	@echo "make jupyter    - 啟動Jupyter Lab"
	@echo "=========================================="

setup:
	@echo "Setting up project..."
	@cp collector-py/.env.example collector-py/.env
	@echo "✓ Created collector-py/.env"
	@echo "Please edit .env file if needed"

start:
	@echo "Starting services..."
	docker-compose up -d db redis
	@echo "Waiting for database to be ready..."
	@sleep 10
	@echo "✓ Database and Redis are running"
	@echo "Run 'make collector' to start data collection"
	@echo "Run 'make jupyter' to start Jupyter Lab"

stop:
	@echo "Stopping services..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	@echo "✓ All containers and volumes removed"

db-shell:
	docker exec -it crypto_timescaledb psql -U crypto -d crypto_db

collector:
	@echo "Starting data collector..."
	cd collector-py && python src/main.py

jupyter:
	@echo "Starting Jupyter Lab..."
	docker-compose up -d jupyter
	@echo "✓ Jupyter Lab is running at http://localhost:8888"

install-collector:
	@echo "Installing collector dependencies..."
	cd collector-py && pip install -r requirements.txt
	@echo "✓ Collector dependencies installed"

install-analyzer:
	@echo "Installing analyzer dependencies..."
	cd data-analyzer && pip install -r requirements.txt
	@echo "✓ Analyzer dependencies installed"
