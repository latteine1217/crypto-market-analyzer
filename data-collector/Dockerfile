# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# 複製 package files (從 context 根目錄開始)
COPY data-collector/package*.json ./data-collector/

# 安裝所有依賴
RUN cd data-collector && npm install

# 複製 TypeScript 配置、源碼與共享代碼
COPY data-collector/tsconfig.json ./data-collector/
COPY data-collector/src/ ./data-collector/src/
COPY shared/utils/RedisKeys.ts ./shared/utils/RedisKeys.ts

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
RUN npm install --only=production

# 從 builder stage 複製編譯好的 dist 目錄
# 結構會是 dist/data-collector/src/... 及 dist/shared/...
# 我們將它們分別放到正確的位置
COPY --from=builder /app/data-collector/dist/data-collector/src ./dist/src
COPY --from=builder /app/data-collector/dist/shared ./dist/shared

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV NODE_ENV=production

# 健康檢查 - 檢查 metrics 端口是否回應
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8001}/metrics || exit 1

# 啟動應用 - 指向正確的 entry point
CMD ["node", "dist/src/index.js"]
