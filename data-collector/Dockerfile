# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# 複製 package files
COPY package*.json ./

# 安裝所有依賴（包括 devDependencies）
RUN npm ci

# 複製 TypeScript 配置與源碼
COPY tsconfig.json ./
COPY src/ ./src/

# 編譯 TypeScript
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# 安裝系統依賴
RUN apk add --no-cache \
    postgresql-client \
    curl

# 複製 package files
COPY package*.json ./

# 只安裝生產依賴
RUN npm ci --only=production

# 從 builder stage 複製編譯好的 dist 目錄
COPY --from=builder /app/dist ./dist

# 建立日誌目錄
RUN mkdir -p /app/logs

# 設定環境變數
ENV NODE_ENV=production

# 健康檢查 - 檢查 metrics 端口是否回應
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${METRICS_PORT:-8001}/metrics || exit 1

# 啟動應用
CMD ["npm", "start"]
