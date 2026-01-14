# Crypto Market Dashboard - Development Log

> **Purpose**: Record project progress, key decisions, change history, and todo list.
> **Maintainer**: Development Team
> **Last Updated**: 2026-01-15

---

## 🛣️ Feature Roadmap (1 Month)

| Feature | File(s) | Est. Hours | Priority | Status |
|---------|---------|------------|----------|--------|
| Multi-Timeframe Switching | `technical/page.tsx` | 3h | High | 🚀 In Progress |
| Depth Chart | `DepthChart.tsx` | 4h | Medium | ⏳ Pending |
| Price Alerts | New `alerts` module | 6h | Medium | ⏳ Pending |
| Bollinger Bands | `indicators.ts` | 2h | Low | ⏳ Pending |
| Responsive Optimization | All pages | 3h | Low | ⏳ Pending |

---

## 📅 Current Session (2026-01-15)

### Status
- **Project Version**: v2.3.0 (Focused Markets & Quality Monitoring)
- **Current Phase**: Quality Assurance & UI Integration

### Today's Progress

#### ✅ Completed Tasks

**Task 19: Docker & Build System Integration (Docker 與構建系統整合)** 🐳
- **目標**: 確保 WebSocket Collector 能在 Docker 容器中正確編譯並引用外部 `shared` 代碼。
- **執行項目**:
  - **tsconfig 優化**: 調整 `data-collector/tsconfig.json` 的 `rootDir` 與 `include`，支援引用 `../shared/utils/RedisKeys.ts`。
  - **Dockerfile 重構**: 
    - 提升 Build Context 至專案根目錄。
    - 修復編譯時的目錄結構，確保生產環境 `dist/` 路徑正確。
    - 將 `npm ci` 降級為 `npm install` 以解決鎖檔不一致問題。
  - **Docker Compose 更新**: 同步 `ws-collector` 的掛載路徑與 Build Context。
  - **程式碼修正**: 
    - 在 `config/index.ts` 中補上 `exchange` 屬性。
    - 修復 `OKXWSClient.ts` 的編譯器警告與 `RedisQueue.ts` 的屬性存取錯誤。
- **結果**: 
  - ✅ `ws-collector` 映像構建成功。
  - ✅ 解決跨目錄依賴問題。
  - ✅ Prometheus 與 Redis 服務配置已同步。

**Task 18: Redis Optimization & Key Standardization (Redis 優化與 Key 規範化)** 🚀
- **目標**: 統一跨服務的 Redis Key 命名，優化快取效能，降低資料庫負擔。
- **執行項目**:
  - **統一 Key 管理**: 建立 `shared/utils/RedisKeys.ts`，集中管理所有 Redis Key 模式（支援 Versioning `v2`）。
  - **Collector 優化**:
    - 重構 `RedisQueue.ts`，為所有佇列加入 1 小時 TTL，防止記憶體無限增長。
    - 在訂單簿快照 Key 中加入 `exchange` 欄位，解決多交易所 Key 衝突問題。
    - 使用 Redis Pipeline 優化 `getAllQueueSizes` 效能。
  - **API Server 優化**:
    - 更新 `CacheService` 以整合 `RedisKeys` 並支援 Hash 操作。
    - 重構 `/api/orderbook/:exchange/:symbol/latest` 路由，實作 **Redis-First** 策略，優先讀取 Collector 寫入的即時快照。
- **結果**: 
  - ✅ 實現跨服務 Key 一致性。
  - ✅ 降低 `/latest` 訂單簿請求的延遲（由 DB 查詢轉為 Redis 內存讀取）。
  - ✅ 提升系統健壯性，防止 Redis 記憶體溢出。

**Task 17: Refactor Data Collector Registry (數據收集器重構 - 註冊表模式)** 🛠️
- **目標**: 使用映射表 (Registry) 動態加載交易所客戶端，提升擴展性與程式碼整潔度。
- **執行項目**:
  - **型別修正**: 在 `data-collector/src/types/index.ts` 中修復 `IWSClient` 介面，匯入 `EventEmitter` 並完善定義。
  - **建立註冊表**: 新增 `data-collector/src/ExchangeRegistry.ts`，實作交易所客戶端的自動註冊與動態實例化。
  - **主程式重構**: 修改 `data-collector/src/index.ts`，移除手動的 `if/else` 客戶端建立邏輯，改用 `ExchangeRegistry.createClient`。
  - **介面一致性**: 確保 `BinanceWSClient`, `BybitWSClient`, `OKXWSClient` 均符合 `IWSClient` 介面。
- **結果**: 
  - ✅ 程式碼邏輯更簡潔，支援「不修改主程式」即可新增交易所。
  - ✅ 提升 TypeScript 型別安全性。
  - ✅ 降低不同交易所實作間的耦合度。

**Task 16: Market Cleanup & Quality Dashboard (市場清理與品質面板)** 🎯
- **目標**: 專注核心市場 (BTC/ETH)，實現資料品質指標視覺化。
- **執行項目**:
  - **市場清理**: 從 `markets` 表中刪除非 BTCUSDT/ETHUSDT 的所有記錄，清理了 7 個市場。
  - **API 擴展**: 在 API Server 新增 `/api/markets/quality` 端點。
  - **品質面板**: 建立 `DataQualityStatus` 元件，即時監控 K 線缺失率與品質評分。
  - **UI 整合**: 將品質面板整合至 Dashboard 首頁，並更新系統統計數據。
- **結果**: 
  - ✅ 系統僅追蹤 6 個核心市場。
  - ✅ 實現「資料缺失率 ≤ 0.1%」的視覺化驗收。

**Task 15: Technical Debt Resolution (技術債清理)** 🛠️
...

**Task 14: Documentation & File Organization (文件與檔案整理)** 🧹
- **目標**: 整理專案根目錄、`docs/` 與 `scripts/` 中的過時檔案與報告，保持專案結構清晰。
- **執行項目**:
  - 建立 `docs/archive/reports/` 與 `scripts/archive/` 目錄。
  - 將已完成的任務報告 (e.g., `DOCKER_INTEGRATION_REPORT.md`, `DASHBOARD_TS_COMPLETION_REPORT.md`) 移動至 archive。
  - 將一次性遷移腳本 (e.g., `migration_004.sh`) 移動至 archive。
  - 將 `unused-modules-20260115.tar.gz` 移動至 `.archived/`。
- **結果**: 
  - ✅ `docs/` 目錄僅保留核心文檔 (`PROJECT_STATUS_REPORT`, `SESSION_LOG` 等)。
  - ✅ `scripts/` 目錄更專注於日常運維腳本。
  - ✅ 專案根目錄更加整潔。

**Task 13: Critical Fixes & Code Cleanup (關鍵修復與代碼清理)** 🎯
- **目標**: 修復高風險問題 (P0)，提升類型安全與記憶體管理，清理未使用的依賴
- **解決方案**:
  1. **API 請求頻率限制**:
     - 修改 `Providers.tsx`，將 `staleTime` 從 30s 延長至 60s，並關閉 `refetchOnWindowFocus`。
     - 顯著降低背景與切換視窗時的無效請求，減輕後端壓力。
  2. **記憶體洩漏修復**:
     - 修正 `LightweightCandlestickChart.tsx` 中的 `useEffect` 清理邏輯。
     - 確保組件卸載時，`chart.remove()` 被正確調用且 Refs 被置空。
  3. **TypeScript 類型安全**:
     - 全面清除圖表組件 (`MACDChart`, `FundingRateChart`, `OpenInterestChart`, `LightweightCandlestickChart`) 中的 `any` 類型。
     - 引入 `lightweight-charts` 的完整類型定義 (`ISeriesApi`, `UTCTimestamp`, `HistogramData` 等)。
  4. **代碼與依賴清理**:
     - 移除未使用的 `recharts` 與 `zustand` 套件，減少 Bundle Size。
     - 修復 `indicators.ts` 中 RSI 計算在 Edge Case (無變動) 下的精度問題。
     - 新增 `indicators.test.ts` 單元測試，確保核心算法正確性。
- **結果**: 
  - ✅ 消除所有 `any` 濫用，建置通過類型檢查。
  - ✅ 通過指標單元測試 (6/6 tests passed)。
  - ✅ Bundle Size 進一步優化。

**Task 12: Performance Optimization (效能優化)** 🎯
...

**Task 11: Fix Open Interest Data Collection** 🎯
...
- **Issue**: Open Interest charts were empty because `open_interest_usd` was missing (NULL) in the database.
- **Root Cause**: Binance API (via CCXT) was not returning `openInterestValue` or `price` in `fetch_open_interest`, which prevented `open_interest_usd` calculation.
- **Solution**: 
  - Modified `collector-py/src/connectors/open_interest_collector.py` to fallback to fetching the ticker price if `open_interest_usd` is missing, allowing calculation of USD value (`OI * Price`).
  - Modified `collector-py/src/main.py` to trigger `run_open_interest_collection` immediately at startup for faster verification and robustness.
- **Result**: 
  - ✅ Database now populates `open_interest_usd` correctly.
  - ✅ Dashboard charts should now display Open Interest data.

**Task 10: Robustness Improvements (健壯性提升)** 🎯
- **目標**: 提高系統穩定性，避免白屏，增強錯誤處理與自動化測試
- **解決方案**:
  1. **Error Boundary**: 
     - 新增 `dashboard-ts/src/app/error.tsx` 作為 Next.js 全域錯誤頁面
     - 驗證並測試 `src/components/ErrorBoundary.tsx`
  2. **API 錯誤處理**:
     - 在 `src/lib/api-client.ts` 新增 Axios 攔截器 (Interceptors)
     - 實作統一的日誌紀錄與錯誤訊息處理機制
  3. **單元測試 (Unit Tests)**:
     - 配置 `vitest` 測試環境與 `@testing-library/react`
     - 新增 `api-client.test.ts` 與 `ErrorBoundary.test.tsx`
     - 整合測試執行腳本 `npm test`
- **結果**: 
  - ✅ 測試通過 (3 tests passed)
  - ✅ 錯誤頁面與攔截器運作正常
  - ✅ 系統穩定性提升，大幅降低崩潰白屏機率

---

## 📅 Previous Session (2026-01-14)

### Status
- **Project Version**: v2.0.0 (TypeScript Migration + Docker Integration Complete)
- **System Status**: ✅ All services running in Docker (8/8 containers healthy)
- **Current Phase**: Production-Ready Deployment

### Progress Highlights

#### ✅ Completed Tasks

**Task 6: Docker 整合與容器化部署** 🎯
- **結果**: 
  - ✅ API Server 映像構建成功 (~110MB)
  - ✅ Dashboard 映像構建成功 (~320MB)
  - ✅ 所有容器正常啟動並通過健康檢查
  - ✅ 建立自動化測試腳本 `test-docker-services.sh`
  - ✅ 建立完整文檔 `docs/DOCKER_INTEGRATION_REPORT.md`

**Task 5: TypeScript Dashboard Migration - Bug Fixes & Service Startup** 🎯
- **結果**: 
  - ✅ API Server 成功啟動並運行在 port 8080
  - ✅ Dashboard 成功啟動並運行在 port 3001
  - ✅ 所有核心 API 端點測試通過

...
