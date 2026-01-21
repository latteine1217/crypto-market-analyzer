# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# 複製 package files (從 context 根目錄開始)
COPY data-collector/package*.json ./data-collector/

# 安裝所有依賴
# 注意：如果 package-lock.json 不存在或不同步，先用 install 生成
RUN cd data-collector && \
    if [ ! -f package-lock.json ]; then \
        echo "⚠️  package-lock.json not found, generating..."; \
        npm install; \
    else \
        npm ci || (echo "⚠️  npm ci failed, falling back to npm install" && npm install); \
    fi

# 複製 TypeScript 配置、源碼與共享代碼
COPY data-collector/tsconfig.json ./data-collector/
COPY data-collector/src/ ./data-collector/src/
COPY shared/ ./shared/

# 編譯 TypeScript
RUN cd data-collector && npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# 安裝系統依賴
RUN apk add --no-cache \
    postgresql-client \
    curl

# 複製 package files
COPY data-collector/package*.json ./

# 安裝生產依賴
# 使用與 builder stage 相同的策略確保成功
RUN if [ ! -f package-lock.json ]; then \
        npm install --omit=dev; \
    else \
        npm ci --omit=dev || npm install --omit=dev; \
    fi

# 從 builder stage 複製編譯好的 dist 目錄
# 結構會是 dist/data-collector/src/... 及 dist/shared/...
COPY --from=builder /app/data-collector/dist ./dist

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV NODE_ENV=production

# 健康檢查 - 檢查 metrics 端口是否回應
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8001}/metrics || exit 1

# 啟動應用 - 指向正確的 entry point
CMD ["node", "dist/index.js"]
