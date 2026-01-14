# Crypto Dashboard TypeScript

全新的 TypeScript + Next.js 版本 Crypto Market Dashboard

## 快速開始

### 前置需求
- Node.js 18+
- npm 或 yarn
- 已運行的 PostgreSQL (TimescaleDB) 和 Redis

### 安裝與啟動

#### 1. API Server

```bash
cd api-server
cp .env.example .env
# 編輯 .env 配置資料庫連接

npm install
npm run dev  # 開發模式運行在 http://localhost:8080
```

#### 2. Dashboard Frontend

```bash
cd dashboard-ts
cp .env.example .env
# 設置 NEXT_PUBLIC_API_URL=http://localhost:8080

npm install
npm run dev  # 開發模式運行在 http://localhost:3000
```

### 生產環境部署

```bash
# API Server
cd api-server
npm run build
npm start

# Dashboard
cd dashboard-ts
npm run build
npm start
```

## 功能特性

- ✅ **Market Overview**: 所有市場即時價格與 24h 變化
- ✅ **Technical Analysis**: K 線圖 + 技術指標 (MACD, MA, RSI, Fractals)
- ✅ **Liquidity Analysis**: 訂單簿深度視覺化
- ✅ **Multi-Exchange Support**: Binance, Bybit, OKX
- ✅ **Real-time Updates**: 5 秒自動刷新
- ✅ **Redis Caching**: 高效能資料快取
- ✅ **Responsive Design**: 適配各種螢幕尺寸

## 技術棧

**Frontend**:
- Next.js 14 (App Router)
- React 18
- TypeScript
- TanStack Query (React Query)
- Recharts
- Tailwind CSS

**Backend**:
- Express.js
- TypeScript
- PostgreSQL (pg)
- Redis (ioredis)
- Winston (logging)

## API Endpoints

### Markets
- `GET /api/markets` - 取得所有市場列表
- `GET /api/markets/prices` - 取得所有市場最新價格

### OHLCV
- `GET /api/ohlcv/:exchange/:symbol` - 取得 OHLCV 資料
- `GET /api/ohlcv/:exchange/:symbol/summary` - 取得市場摘要

### Orderbook
- `GET /api/orderbook/:exchange/:symbol` - 取得訂單簿快照
- `GET /api/orderbook/:exchange/:symbol/latest` - 取得最新訂單簿

## 開發指南

### 新增頁面

```typescript
// dashboard-ts/src/app/newpage/page.tsx
'use client'

export default function NewPage() {
  return <div>New Page Content</div>
}
```

### 新增 API Endpoint

```typescript
// api-server/src/routes/newroute.ts
import { Router } from 'express';

const router = Router();

router.get('/', async (req, res) => {
  res.json({ data: 'Hello' });
});

export { router as newRoutes };
```

## 環境變數

### API Server (.env)
```
PORT=8080
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto_pass
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Dashboard (.env)
```
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## 下一步計劃

- [ ] WebSocket 即時資料流整合
- [ ] 更多技術指標 (Bollinger Bands, Ichimoku)
- [ ] 自訂告警設定
- [ ] 使用者偏好設定
- [ ] 效能優化 (Server Components, ISR)

## 授權

MIT License
