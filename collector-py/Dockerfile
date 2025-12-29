FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements 並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製源碼
COPY src/ ./src/
COPY scripts/ ./scripts/

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import psycopg2; conn = psycopg2.connect('dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD} host=${POSTGRES_HOST}'); conn.close()" || exit 1

# 預設啟動命令（可在 docker-compose 中覆蓋）
CMD ["python", "-m", "src.main"]
