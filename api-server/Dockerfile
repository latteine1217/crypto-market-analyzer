FROM node:20-alpine AS builder

WORKDIR /app

# 安裝依賴
COPY package*.json ./
RUN npm install

# 複製所有代碼 (已包含 src/shared_copy)
COPY src ./src
COPY tsconfig.json ./

# 編譯
RUN npm run build

FROM node:20-alpine

WORKDIR /app

# 複製產物與依賴
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

EXPOSE 8080

CMD ["node", "dist/index.js"]
