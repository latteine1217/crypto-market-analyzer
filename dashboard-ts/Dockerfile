FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine

WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./
# 只在 public 目錄存在時複製
RUN mkdir -p ./public

ENV PORT=3001
EXPOSE 3001

CMD ["npm", "start"]
