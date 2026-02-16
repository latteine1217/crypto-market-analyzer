# 使用 uv 的多階段構建
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# 啟用字節碼編譯
ENV UV_COMPILE_BYTECODE=1
# 從 uv.lock 進行同步，確保依賴一致
ENV UV_LINK_MODE=copy

# 複製依賴定義檔
COPY pyproject.toml uv.lock ./

# 安裝依賴 (不含專案本身，僅安裝依賴到系統或 venv)
# 使用 --system 安裝到系統環境，避免多層 venv 複雜度，適合容器
RUN uv pip install --system --no-cache .

# ==========================================
# Runtime Image
# ==========================================
FROM python:3.11-slim-bookworm

WORKDIR /app

# 安裝系統依賴（包含 Chromium 與 ChromeDriver）
# 為了穩定性，建議明確指定版本，但在此使用 default apt 源
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    wget \
    gnupg \
    unzip \
    # Chromium dependencies
    chromium \
    chromium-driver \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    libgtk-3-0 \
    libgbm1 \
    ca-certificates \
    tzdata \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 從 Builder 階段複製已安裝的 Python 套件
# 注意：因為我們在 builder 用了 --system，所以直接複製 site-packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 複製源碼
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/
COPY shared/ ./shared/

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import psycopg2; conn = psycopg2.connect('dbname=${POSTGRES_DB} user=${POSTGRES_USER} password=${POSTGRES_PASSWORD} host=${POSTGRES_HOST}'); conn.close()" || exit 1

# 賦予腳本執行權限
RUN chmod +x /app/scripts/start.sh

# 預設啟動命令 (使用啟動腳本自動初始化)
CMD ["/app/scripts/start.sh"]
