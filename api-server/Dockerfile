FROM node:20-alpine AS builder

WORKDIR /app

# 安裝所有依賴（包含 devDependencies）用於構建
COPY package*.json ./
RUN npm ci

# 複製源碼並編譯
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

EXPOSE 8080

CMD ["npm", "start"]
