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
- **Project Version**: v2.2.0 (Performance & UX Optimized)
- **Current Phase**: Performance Refinement & UI/UX Enhancement

### Today's Progress

#### ✅ Completed Tasks

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
