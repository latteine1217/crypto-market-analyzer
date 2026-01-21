# Crypto Market Dashboard

**Version**: v3.0.0 (Optimized V3 Architecture)
**Focus**: High Efficiency + Minimalist Architecture + Data Consolidation

以 Bybit 交易所資料收集與可視化為核心的加密貨幣市場監控平台。從 Bybit 即時收集市場數據、衍生品指標與全球宏觀指標，透過 V3 優化架構整合存入 TimescaleDB，並提供流暢的 Next.js 分析介面。

## 🎯 核心特性

### 🚀 V3 架構優化 (v3.0+)
- **資料高度整合**: 廢除碎片化表結構，將宏觀 (FRED)、情緒 (FearGreed)、ETF 數據統合成 `global_indicators` 泛用指標表。
- **高效查詢**: 減少多表 Join，API 回傳延遲降低 50% 以上。
- **系統精簡**: 移除重型監控棧 (Grafana/Prometheus)，系統資源消耗降低 60%，實現「輕量化運行」。
- **TimescaleDB 壓縮**: 全面啟用列式壓縮與自動數據保留政策 (Retention Policies)。

### 📊 資料收集與管理
- **交易所支援**: Bybit (REST + WebSocket)。
- **原生格式化**: Symbol 全面採用 `BTCUSDT` 格式，移除了陳舊的格式轉換邏輯。
- **衍生品監控**: 即時追蹤 Funding Rate、Open Interest 及 Long/Short Ratio。
- **全球指標**: 整合 FRED 美國經濟數據、恐懼貪婪指數與 BTC/ETH ETF 資金流向。

## 🏗️ 系統架構

```
┌──────────────────────────────────────────────────────────────┐
│                        Data Sources                           │
│              Bybit API        FRED/SoSo                       │
└────────────┬─────────────────────────────┬───────────────────┘
             │                             │
        REST API                      WebSocket
             │                             │
             ▼                             ▼
    ┌────────────────┐          ┌────────────────┐
    │ Python         │          │ TypeScript     │
    │ REST Collector │          │ WS Collector   │
    └────────┬───────┘          └────────┬───────┘
             │                           │
             │    ┌───────────────┐      │
             └───▶│ Redis Cache   │◀─────┘
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ TimescaleDB   │
                  │ (V3 Schema)   │
                  └───────┬───────┘
                          │
              ┌───────────┴────────────────┐
              ▼                            ▼
         ┌──────────┐                ┌──────────┐
         │API Server│◀───────────────┤Dashboard │
         │(Express) │                │(Next.js) │
         └──────────┘                └──────────┘
            :8080                        :3001
```

## 📁 專案結構

```
crypto-market-dashboard/
├── collector-py/              # Python REST API 收集器 (宏觀、情緒、指標)
├── data-collector/            # TypeScript WebSocket 收集器 (價格、成交)
├── api-server/                # TypeScript API Server (後端資料匯聚)
├── dashboard-ts/              # Next.js Dashboard (現代化前端介面)
├── database/                  # 📚 V3 優化 Schema 與 Migrations
├── shared/                    # 共享工具與類型定義 (TS/Py)
├── scripts/                   # 核心維運工具 (狀態檢查、資料驗證)
└── docs/                      # 📚 開發日誌、技術債與專案報告
```

## 🚀 快速開始

### 前置需求
- Docker & Docker Compose
- 可用端口: 80, 5432, 6379, 8080, 3001

### 1. 啟動服務

```bash
# 複製環境變數範本
cp .env.example .env

# 啟動系統 (自動執行 V3 初始化)
docker-compose up -d
```

### 2. 管理命令 (Makefile)

```bash
make status             # 查看服務狀態
make logs-collector     # 查看收集器日誌
make db-shell           # 進入資料庫 Psql
make db-check-rich-list # 檢查巨鯨數據
```

## 🧪 驗證與運維

```bash
# 驗證資料收集完整性
python scripts/verify_data.py

# 檢查各交易所最新 K 線時間
./scripts/collector_status.sh
```

---

**最後更新**: 2026-01-16  
**專案版本**: v3.0.0  
**維護者**: Development Team
