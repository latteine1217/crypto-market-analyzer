# Session Log - 2026-02-16

## 🎯 當前進度

### ✅ Technical K 線強化（VPVR + Williams Fractal，2026-02-17）
- [x] **新增籌碼分佈（VPVR）開關，預設關閉**
  - `dashboard-ts/src/app/technical/page.tsx`
  - Indicators Toggle 新增 `VPVR`
- [x] **新增威廉分型（Williams Fractal）開關，預設關閉**
  - `dashboard-ts/src/app/technical/page.tsx`
  - Indicators Toggle 新增 `FRACTAL`
- [x] **主圖新增可視區間分價成交量面板（Visible Range Volume Profile）**
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - 依主圖可視範圍即時重算價格區間成交量，右側顯示 volume profile
- [x] **主圖新增威廉分型標記（marker）**
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - Fractal Up/Down 以 K 線 marker 呈現，並與既有爆倉 marker 合併
- [x] **指標單元測試補強**
  - `dashboard-ts/src/lib/__tests__/indicators.test.ts`
  - 新增 `calculateFractals` 基本型態檢查
- [x] **顯示修正（v5 marker API + VPVR fallback）**
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - 改用 `createSeriesMarkers`（`lightweight-charts@5.1.0` 相容）
  - VPVR 在可視範圍事件尚未回傳時，改用當前資料全區間先行計算，避免開啟後空白
- [x] **分型參數調整與 VPVR 可視範圍容錯**
  - `dashboard-ts/src/lib/indicators.ts`
  - Williams Fractal 改為可配置 period，主流程使用 `period=12`
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - VPVR 新增 logical range fallback（時間範圍轉換失敗時仍可計算）
  - VPVR/圖例 overlay 提升 z-index，避免被 canvas 蓋住
- [x] **VPVR POC 區間全圖標註**
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - 將 VPVR 峰值（POC）所在價格區間映射為主 K 線區域的灰色半透明橫向帶，覆蓋整張圖表寬度
- [x] **VPVR 對齊修正 + 30 等分 + POC 中心線**
  - `dashboard-ts/src/components/charts/LightweightCandlestickChart.tsx`
  - VPVR 分層由 24 調整為 30 bins
  - POC 灰帶改用 `priceToCoordinate` 轉換為圖表座標，避免與 VPVR 區間錯位
  - 新增 POC 中心價細線（橫跨整張 K 線圖）

### ✅ Dashboard 首頁移除與精簡（Phase 1）
- [x] **移除 Home Page 路由內容**: `dashboard-ts/src/app/page.tsx`
  - `/` 改為直接 redirect 到 `/technical`，不再渲染大型首頁聚合 UI
- [x] **導覽與錯誤回退路徑對齊**
  - `dashboard-ts/src/components/Navbar.tsx`
    - 移除 `Home` 導覽項
    - 品牌連結由 `/` 改為 `/technical`
  - `dashboard-ts/src/app/error.tsx`
    - 錯誤頁 fallback 按鈕改為導向 `/technical`
- [x] **刪除未使用元件（降低維護面積）**
  - 刪除：`dashboard-ts/src/components/UpcomingEvents.tsx`
  - 刪除：`dashboard-ts/src/components/ETFFlowsWidget.tsx`
- [x] **移除對應 dead code**
  - `dashboard-ts/src/lib/api-client.ts`
    - 移除 `fetchUpcomingEvents`、`fetchTodayEvents`
    - 移除無用型別 import
  - `dashboard-ts/src/types/market.ts`
    - 移除 `Event` / `EventMetadata` / `EventsByDate` / `UpcomingEventsResponse`

### 🧪 測試驗證
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ Dashboard 深層精簡（Phase 2：未引用元件與 API 清理）
- [x] **刪除深層未引用元件**
  - 刪除：`dashboard-ts/src/components/FearGreedWidget.tsx`
  - 刪除：`dashboard-ts/src/components/charts/RichListChart.tsx`
- [x] **清理未使用 API 函式（frontend client）**: `dashboard-ts/src/lib/api-client.ts`
  - 移除：`fetchMarketPrices`
  - 移除：`fetchMarketSummary`
  - 移除：`fetchOrderbook`
  - 移除：`fetchLatestFundingRate`
  - 移除：`fetchLatestOpenInterest`
  - 移除：`fetchFearGreed`
  - 移除：`fetchETFSummary`
- [x] **清理對應未使用型別**: `dashboard-ts/src/types/market.ts`
  - 移除：`MarketPrice`
  - 移除：`MarketSummary`
  - 移除：`FearGreedData`
  - 移除：`ETFFlowSummary`

### 🧪 Phase 2 驗證結果
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ 專案深層瘦身（Phase 3：孤立模組與產物清理）
- [x] **collector-py 刪除未接線孤立檔（無 import、無排程入口）**
  - 刪除：`collector-py/src/connectors/economic_calendar_collector.py`
  - 刪除：`collector-py/src/connectors/finnhub_calendar_collector.py`
  - 刪除：`collector-py/src/connectors/simple_etf_collector.py`
  - 刪除：`collector-py/src/connectors/etf_flows_collector_original.py`
  - 刪除：`collector-py/src/schedulers/task_scheduler.py`
  - 刪除：`collector-py/src/schedulers/retention_monitor_scheduler.py`
- [x] **api-server 清理 `src/` 混入的非 TS 產物（避免來源樹污染）**
  - 刪除：`api-server/src/shared/config/index.js`
  - 刪除：`api-server/src/shared/utils/RedisKeys.d.ts`
  - 刪除：`api-server/src/shared/utils/RedisKeys.d.ts.map`
  - 刪除：`api-server/src/shared/utils/RedisKeys.js`
  - 刪除：`api-server/src/shared/utils/RedisKeys.js.map`
  - 刪除：`api-server/src/shared/utils/logger_config.js`
  - 刪除：`api-server/src/shared/utils/logger_config.py`
  - 刪除：`api-server/src/shared/utils/logging.py`

### 🧪 Phase 3 驗證結果
- `uv run pytest tests/test_symbol_utils.py tests/test_signal_monitor.py tests/test_bitinfocharts_unit.py tests/test_farside_etf_collector_unit.py -q`（`collector-py/`）✅ 36 passed
- `npm run build`（`api-server/`）✅

### ✅ Fear & Greed 回補到 Technical（避免誤刪鏈路）
- [x] **前端 API 回補**: `dashboard-ts/src/lib/api-client.ts`
  - 恢復 `fetchFearGreed()`
- [x] **型別回補**: `dashboard-ts/src/types/market.ts`
  - 恢復 `FearGreedData`
- [x] **Technical 頁整合情緒指標卡**: `dashboard-ts/src/app/technical/page.tsx`
  - 於側欄新增 `Market Sentiment / Fear & Greed` 區塊
  - 顯示數值、分類與時間戳，並依數值區間著色（fear→greed）

### 🧪 Fear & Greed 回補驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ Technical 高訊噪比壓縮（Sidebar Intel）
- [x] **右側資訊整併為單一 Intel 卡**: `dashboard-ts/src/app/technical/page.tsx`
  - 合併原本 `Quick Statistics` + `Market Sentiment`
  - 保留高價值欄位：Price、RSI14、vs MA20、MACD Bias、Fear & Greed（值/分類/時間）
  - 降低視覺層級與區塊數量，提升掃讀效率
- [x] **Signal Timeline 高度壓縮**
  - 由 `h-[400px]` 調整為 `h-[360px]`
- [x] **移除已無引用組件**
  - 刪除：`dashboard-ts/src/components/IndicatorStats.tsx`

### 🧪 Technical 壓縮驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ 互動降噪（Alerts Manager）
- [x] **明確操作入口替代整塊 header 點擊**
  - `dashboard-ts/src/components/AlertsManager.tsx`
  - 移除「整個 header 可點」行為，改為右側明確按鈕：
    - `Manage Alerts`（展開）
    - `Hide Controls`（收合）
  - 新增 `aria-expanded` / `aria-label` 提升可用性
- [x] **收合狀態增加摘要資訊**
  - 顯示目前 symbol active 數與全域 active 總數，使用者不展開也能判斷是否需要操作

### 🧪 Alerts Manager 降噪驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ 現有板塊強化（Technical）
- [x] **Market Intel 強化判讀**
  - `dashboard-ts/src/app/technical/page.tsx`
  - 新增 `Regime`（Risk-On / Risk-Off / Mixed）綜合判讀
  - 新增價格資料時間戳（Price TS）
- [x] **Signals 板塊強化（可篩選 + 可掃描）**
  - `dashboard-ts/src/components/SignalTimeline.tsx`
  - 新增嚴重度計數（Critical/Warning/Info）
  - 新增嚴重度篩選（ALL/CRITICAL/WARNING/INFO）
  - 無資料時區分為「真的沒訊號」與「篩選後無結果」
- [x] **Alerts 板塊強化（更快操作）**
  - `dashboard-ts/src/components/AlertsManager.tsx`
  - 新增 Quick Set（依 above/below 自動給 ±0.5% / ±1% / ±2%）
  - 新增方向驗證（Above 必須 > 現價；Below 必須 < 現價）
  - 即使按 Enter 送出，也會阻擋方向錯誤的目標價

### 🧪 板塊強化驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ Liquidity 板塊強化（Execution-focused）
- [x] **補上已抓取但未展示的 Order Flow 面板**
  - `dashboard-ts/src/app/liquidity/page.tsx`
  - 接入 `OrderSizeChart`（`fetchOrderSizeAnalytics` 不再是隱性 dead query）
- [x] **新增 Liquidity Intel 三指標**
  - `Liquidity Regime`（BID SUPPORT / ASK PRESSURE / THIN BOOK / BALANCED）
  - `Spread (bps)`（執行成本視角）
  - `Bid/Ask Skew`（可視深度 notional 偏斜）
- [x] **Orderbook 可操作性提升**
  - 新增可切換深度檔位：`20 / 50 / 100`
  - 底部狀態改為真實資訊：`AGE xs` + 更新時間（移除硬編碼 latency）
  - loading 狀態補齊（bids/asks）

### 🧪 Liquidity 強化驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ ETF 板塊強化（Regime + Monitoring）
- [x] **新增 ETF Regime 判讀卡**
  - `dashboard-ts/src/app/etf/page.tsx`
  - 輸出 `Broad Risk-On / Narrow Risk-On / Risk-Off / Mixed`
  - 規則綜合 `latest flow`、`flow_zscore`、`issuer concentration`
- [x] **新增 stale 明確警示**
  - 當 `quality_status=stale` 時顯示 warning banner（含 stale 小時數）
- [x] **新增 Flow Breadth 指標**
  - 以最新交易日產品正流入占比（positive products / total）衡量市場廣度
- [x] **新增 Issuer Concentration Trend 圖**
  - 追蹤 `Top1`、`Top3` 集中度趨勢（%）
- [x] **新增 Weekly Divergence Monitor**
  - 顯示近 8 週 weekly divergence（按週排序）

### 🧪 ETF 強化驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ ETF 板塊優化與檢查（Correctness + Robustness）
- [x] **顯示正確性修正**
  - `dashboard-ts/src/app/etf/page.tsx`
  - `formatCurrency(0)` 不再顯示 `N/A`，改為正常顯示 `$0.00`
- [x] **時間序穩定性優化**
  - 對 `analytics.data` 先做日期排序（desc），再派生 asc 供圖表使用，避免上游順序波動造成圖表誤讀
- [x] **錯誤可見性提升**
  - 任一 ETF query 失敗時顯示 `Partial data load failure` banner（避免靜默空白）
- [x] **資料一致性檢查卡（Data Integrity Check）**
  - 檢查並顯示：
    - `Duplicate Dates`
    - `Missing BTC Close`
    - `Cumulative Drift`（累計流向一致性）
- [x] **週背離資料排序優化**
  - `weekly_divergence` 先排序再截取近 8 週，避免順序不一致

### 🧪 ETF 優化與檢查驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

### ✅ ETF 停更診斷與修復（2026-02-17）
- [x] **現象確認**
  - DB 最新 ETF 交易日：`2026-02-13 (ET)`（`global_indicators`）
  - 檢查時間：`2026-02-16 23:39:56 EST`
- [x] **根因定位**
  - 連續非交易日窗口（週末 + 2026-02-16 美股休市）導致無新日資料屬正常情況
  - 同時發現嘗試次數邏輯 bug：`run_etf_flows_task` 在「達上限 skip」時仍寫 `ETF_FLOWS_FETCH`，會把計數從 `3/3` 持續推到 `4/3`、`5/3`，增加交易日誤跳過風險
- [x] **程式修補**
  - 檔案：`collector-py/src/tasks/external_tasks.py`
  - 僅在「實際對來源發起抓取」時寫 `ETF_FLOWS_FETCH`，並加上 `metadata.attempted_fetch=true`
  - 嘗試次數查詢只計 `attempted_fetch=true`
  - skip 事件改寫 `ETF_FLOWS_SKIP_LIMIT`，不再污染 fetch 次數
- [x] **套用**
  - 已重啟 `collector` 容器使修補生效

### ✅ Technical 圖表時間軸對齊修復（K 線 / MACD / OI）
- [x] **主圖驅動同步機制補強**
  - `dashboard-ts/src/app/technical/page.tsx`
  - 新增 `syncAllChartsFromMain()`，以主圖可視範圍強制對齊子圖
  - 在圖表建立後與關鍵資料/參數變更後主動同步，避免初始載入錯位
- [x] **移除 MACD 子圖自帶時間縮放**
  - `dashboard-ts/src/components/charts/MACDChart.tsx`
  - 移除 `setVisibleLogicalRange` 首次載入邏輯，改由 Technical 主圖統一控軸

### 🧪 Technical 對齊修復驗證
- `npm run build`（`dashboard-ts/`）✅
- `npm run type-check`（`dashboard-ts/`）✅

# Session Log - 2026-02-13

## 🎯 當前進度

### ✅ P0 穩定性修復（Collector Runtime Stability）
- [x] **Funding Rate 寫入 DB 崩潰修復**: `collector-py/src/loaders/db_loader.py`
  - 避免插入 `market_metrics.value=NULL` 造成 NOT NULL constraint failure（上游 funding_rate 為 None 時跳過）
- [x] **OI Spike SQL 關鍵字衝突修復**: `collector-py/src/monitors/signal_monitor.py`
  - 將 `current_time/prev_time` alias 改為 `current_ts/prev_ts`，避免被 Postgres 解析為 `current_time` keyword
- [x] **Decimal × float 例外修復（訊號掃描）**: `collector-py/src/monitors/signal_monitor.py`
  - 對 DB 回傳 numeric（Decimal）做 float normalization，避免比較與乘除出錯

### ✅ ETF 抓取健壯性（Farside）
- [x] **playwright-stealth API 兼容修復**: `collector-py/src/connectors/farside_etf_collector.py`
  - 支援 `Stealth.apply_stealth_sync`（新版）與 `stealth_sync`（舊版）
- [x] **Hybrid Cookie Reuse（落地版）**: `collector-py/src/connectors/farside_etf_collector.py`
  - curl_cffi 優先使用身份（cookies/UA），遇到 challenge 可嘗試 Playwright 刷新身份
  - Identity cache: `logs/etf_cookie_cache.json`（可配置 TTL/路徑）
  - 支援手動注入 `ETF_COOKIES_JSON` / `ETF_USER_AGENT` / `ETF_CF_CLEARANCE`
- [x] **移除 Selenium fallback（過時且無法成功）**
  - 移除 Selenium 相關程式碼與測試，抓取階梯改為 `Playwright -> curl_cffi`
  - 依賴移除：`selenium`、`webdriver-manager`
  - 備註：本文較舊段落若提到 Selenium，屬歷史問題記錄，現行實作已不再使用

### 🧪 測試驗證
- `uv run pytest tests/test_signal_monitor.py -q` ✅
- `uv run pytest tests/test_farside_etf_collector_unit.py -q` ✅
- `uv run pytest tests/test_bitinfocharts_unit.py -q` ✅

### ✅ BitInfoCharts 抓取升級（BTC Rich List）
- [x] `collector-py/src/connectors/bitinfocharts.py`
  - curl_cffi 主路徑（impersonate）+ 可選 Playwright fallback（身份刷新/備援）
  - 解析改為欄位語意選表 + schema fingerprint
  - parse 失敗自動保存 snapshot：`logs/bitinfo_snapshots/`
- [x] `collector-py/src/tasks/external_tasks.py`
  - rich list 當日時間點已入庫則 skip（避免無效抓取與反爬風險）

# Session Log - 2026-02-15

## 🎯 當前進度

### ✅ BitInfoCharts 資料正確性修復（BTC Rich List）
- [x] 修正欄位選擇：避免把 `Balance, BTC`（range）誤判為 `BTC`（總量）導致 `total_balance` 入庫錯誤  
  - `collector-py/src/connectors/bitinfocharts.py`
- [x] rich list 任務自動修復：若快照已存在但 `SUM(total_balance)` 明顯過低，允許重抓並 upsert 覆寫  
  - `collector-py/src/tasks/external_tasks.py`
- [x] 補單元測試鎖回歸  
  - `collector-py/tests/test_bitinfocharts_unit.py`

### ✅ ETF 來源切換（SoSoValue OpenAPI v2, BTC）
- [x] 新增：`collector-py/src/connectors/sosovalue_openapi_etf_collector.py`
  - 使用 `POST /openapi/v2/etf/historicalInflowChart`（網站公布的 total flow 原值）
  - 只落庫 BTC（`product_code='TOTAL'`），並把 `totalNetAssets/totalValueTraded/cumNetInflow` 寫入 metadata
  - SSL 預設使用系統 CA bundle（可用 `SOSOVALUE_CA_FILE` 覆寫）
- [x] `collector-py/src/orchestrator.py`
  - `ETF_SOURCE=sosovalue` 為預設（仍可切回 `ETF_SOURCE=farside`）
- [x] `collector-py/src/tasks/external_tasks.py`
  - 失敗時每日嘗試次數上限：`ETF_SOSO_MAX_ATTEMPTS_PER_DAY`（避免免費版配額被窗口內重試耗盡）

# Session Log - 2026-02-12

## 🎯 當前進度

### ✅ 文件更新（Docs Refresh）
- [x] 更新根目錄 `README.md`：架構、端口、啟動流程、現況範圍改為 Bybit 實際配置
- [x] 更新 `api-server/README.md`：路由分組與 `markets/quality` 契約欄位
- [x] 更新 `data-collector/README.md`：從 Binance 舊描述修正為 Bybit WS 現況
- [x] 更新 `dashboard-ts/README.md`：端口、頁面範圍、型別契約對齊
- [x] 更新 `configs/README.md`：移除不存在配置與失效文件引用

### ✅ 完成項目
- **P0 監督鏈路修復（Market Supervision Hotfix）**
  - [x] **OI Spike 掃描修復**: `collector-py/src/monitors/signal_monitor.py`
    - 修正 SQL 回傳欄位解包錯誤（5 欄解包）
    - 增加 `prev_oi > 0` 防護，避免除零與靜默失敗
  - [x] **爆倉方向判讀修復**: `collector-py/src/monitors/signal_monitor.py`
    - 新增 `buy/short -> bullish`、`sell/long -> bearish` 統一映射
    - 修正 WS 寫入 side 與訊號判讀 side 的語義不一致
  - [x] **品質檢查任務實作**: `collector-py/src/tasks/maintenance_tasks.py`
    - `run_quality_check_task` 由空實作改為可執行全市場品質掃描
    - 新增結構化 summary 輸出與全失敗時 fail-fast 行為
  - [x] **CVD Calibration 斷鏈修復**:
    - 補上 `DatabaseLoader.get_active_markets()`（`collector-py/src/loaders/db_loader.py`）
    - 修正 `market_anchors` 寫入後缺少 `commit` 的問題
  - [x] **Symbol 正規化補強（避免合約格式漂移）**
    - `parse_symbol` / `normalize_symbol` 支援 `:USDT` suffix（`collector-py/src/utils/symbol_utils.py`）
    - `main.get_target_symbols` 改為輸出原生格式 `BTCUSDT`，避免跨模組 symbol 不一致
  - [x] **品質補資料 fallback 強化**: `collector-py/src/quality_checker.py`
    - 缺失率超標但無 gap 細節時，建立粗粒度 backfill task，避免漏補
    - 回傳欄位補齊 `missing_rate/quality_score/missing_count` 供後續觀測使用

### 🧪 測試驗證
- 執行：
  - `uv run pytest tests/test_quality_checker.py tests/test_symbol_utils.py tests/test_signal_monitor.py -q`
- 結果：
  - **39 passed**
- 新增/更新測試：
  - `collector-py/tests/test_signal_monitor.py`（OI 解包與 liquidation side 映射）
  - `collector-py/tests/test_symbol_utils.py`（CCXT perpetual symbol 正規化）
  - `collector-py/tests/test_quality_checker.py`（backfill API 斷言更新）

### ✅ P1 完成項目（契約與一致性）
- **Quality API / Dashboard 契約對齊**
  - [x] `api-server/src/routes/markets.ts`
    - `/api/markets/quality` 回傳欄位補齊：
      - `missing_count`, `expected_count`, `actual_count`, `backfill_task_created`
    - `quality_score` 改為：優先使用 DB value，否則以 `missing_rate` 回推
    - `status` 統一映射為前端使用的小寫等級：
      - `excellent / good / acceptable / poor / critical`
  - [x] `dashboard-ts/src/types/market.ts`
    - `DataQualityMetrics` 型別與 API 回傳一致（移除無效欄位、補 `actual_count`）
  - [x] `dashboard-ts/src/components/DataQualityStatus.tsx`
    - Status 顯示支援安全 fallback（未知狀態不再造成樣式錯配）
    - Row key 納入 timeframe，避免潛在 key collision

- **Symbol 全鏈路一致性（TS 端）**
  - [x] `data-collector/src/utils/symbolUtils.ts`
    - `parseSymbol` / `normalizeSymbol` 支援 `BTC/USDT:USDT` 格式
    - `normalizeSymbol` 改為全域去斜線，修正 edge case
  - [x] `data-collector/tests/symbolUtils.test.ts`
    - 新增 perpetual symbol 測試案例

### 🧪 P1 驗證結果
- `npm run build`（`api-server/`）✅
- `npm run type-check`（`dashboard-ts/`）✅
- `uv run pytest tests/test_quality_checker.py tests/test_symbol_utils.py tests/test_signal_monitor.py -q`（`collector-py/`）✅ 39 passed

### ✅ P1.1 完成項目（短線 + 波段訊號時框）
- **Signal Monitor 時框升級**
  - [x] `collector-py/src/monitors/signal_monitor.py`
    - CVD 背離掃描改為：`5m`（短線）+ `1h/4h/1d`（波段）
    - 新增 `TIMEFRAME_CONFIG`（lookback / min_points / threshold / horizon）
    - 新增 `SIGNAL_TIMEFRAMES` 環境變數覆寫（預設 `5m,1h,4h,1d`）
    - 原生時框資料不足時，自動回退到 `1m` 聚合（避免訊號斷層）
    - 訊號 metadata 補齊 `horizon` 與 `source_timeframe`
- **測試補齊**
  - [x] `collector-py/tests/test_signal_monitor.py`
    - 新增時框配置與 source timeframe fallback 測試

### 🧪 P1.1 驗證結果
- `uv run pytest tests/test_signal_monitor.py -q`（`collector-py/`）✅ 6 passed
- `uv run pytest tests/test_signal_monitor.py tests/test_quality_checker.py tests/test_symbol_utils.py -q`（`collector-py/`）✅ 43 passed

# Session Log - 2026-02-10

## 🎯 當前進度

### ✅ 完成項目
- **Ollama 自動新聞上下文分析 (Smoke v2)**
  - [x] **新增新聞特徵模組**: `collector-py/src/tasks/news_context.py`
    - 自動抓取 Google News RSS（Crypto / ETF / Macro）
    - 產出結構化欄位：`aggregate_sentiment`、`risk_flags`、`top_events`
  - [x] **提示詞契約升級**: `collector-py/src/tasks/ollama_analysis.py`
    - 輸入新增 `news_context`
    - 輸出新增 `news_impact_assessment` 與 `action_adjustment`
    - 新增 Ollama 呼叫重試邏輯，降低短暫連線/串流中斷影響
  - [x] **Smoke 腳本接線完成**: `collector-py/scripts/test_ollama_analysis.py`
    - 預設啟用新聞抓取（可 `--disable-news` 關閉）
    - 新增 `--news-lookback-hours`、`--news-max-items`、`--timeout-seconds`
  - [x] **測試補齊**:
    - `collector-py/tests/test_ollama_analysis.py`
    - `collector-py/tests/test_news_context.py`
    - 單元測試全數通過（5 passed）

### 📌 待辦 / 注意事項
- 新聞來源目前為 RSS 聚合，建議後續加入來源可信度分級（Tier1/Tier2）與更強去重規則。
- 若需生產化，建議把分析結果落庫到 `analysis_reports` 並接入排程器。

# Session Log - 2026-02-05

## 🎯 當前進度

### ✅ 完成項目
- **首頁高密度專業版重構 (Dashboard)**
  - [x] **移除硬編碼 KPI**: BTC DOM、總市值、24H 爆倉等假數據移除，改為真實市場脈搏卡片 (BTC/ETH/Market Breadth/Top Gainer)。
  - [x] **交易導向側欄**: Upcoming Events 移除，改為 Signal Timeline + Whale Radar + Data Quality。
  - [x] **衍生品密度提升**: 首頁新增 Funding Rate Heatmap 與 OBI 圖表，形成決策級衍生品視角。
  - [x] **資訊結構重排**: Live Market Pulse 依成交量排序，新增 Volume 指標並保留 Funding。
- **ETF 監控強化 (Dashboard)**
  - [x] **灰度 vs 貝萊德疊圖**: `ETFFlowsWidget` 新增 Grayscale/BlackRock 累積淨流向同圖疊加與背離線 (Divergence)。
  - [x] **產品級資料引用**: 使用 `/api/etf-flows/products` 聚合發行商日度流向並計算累積背離。
- **ETF P0 強化 (Collector & Monitoring)**
  - [x] **美股收盤時間對齊**: ETF 流向 `timestamp` 對齊 16:00 ET 並轉 UTC，避免日切錯位。
  - [x] **欄位變動監控**: 偵測未知 ETF 代碼時自動保存 HTML/欄位快照 (`logs/etf_snapshots/`)。
  - [x] **新鮮度指標**: 新增 Prometheus ETF 最新時間與 staleness 指標，並排程每小時檢查。
- **ETF 獨立分頁**
  - [x] **新增 `/etf` 專頁**: ETF Flow Intelligence 獨立頁面，集中展示趨勢、發行商與產品排名。
  - [x] **首頁移除 ETF Widget**: 改為導向專頁的 CTA，避免重要數據被稀釋。
- **ETF P1 指標與訊號 (API + Dashboard)**
  - [x] **交易視角加工**: `net_flow_btc`, `flow_pct_aum`, `flow_pct_20d_avg`, `flow_zscore`, `flow_shock`、`inflow/outflow streak`。
  - [x] **集中度與背離**: `issuer_concentration`、`gbtc_vs_ibit_divergence` 日/週級別、價格背離標記。
  - [x] **P2 視覺化**: Flow vs BTC Price、Flow Impulse、Flow Concentration、Last Update + 品質燈、Issuer 產品切換。
  - [x] **優化順序追加**: `flow_pct_20d_avg` 改為 20D 絕對流向均值基準、價格來源優先 Spot、Signal Watchlist 匯總異常日。
- **移除 Demo / Mock 數據**
  - [x] **Dashboard**: RichListTable 移除 demoMode 與假數據。
  - [x] **API**: ETF summary/products 不再回傳 mock data。
  - [x] **Collectors**: Simple ETF / SoSoValue mock data 禁用，無資料直接回空。
- **K 線連續性修復 (API)**
  - [x] **Interval 正規化**: 修正 `time_bucket` interval 字串，避免 `15m` 被解析為月份。
  - [x] **原生時框回退**: 若 `1h/4h/1d` 原生資料稀疏，自動回退到 1m 聚合。
- **移除 FRED**
  - [x] **停止收集**: 移除排程與初始化中的 FRED 任務與日曆收集。
  - [x] **移除分頁**: 刪除 `/fred` 頁面與對應 API route，Navbar 移除連結。
- **Liquidity Heatmap 限縮**
  - [x] **Top 10 限制**: Funding heatmap 僅顯示 24h 成交量前 10 大合約。
  - [x] **告警降噪**: SignalMonitor 僅掃描前 10 大合約，避免小幣洗版 Telegram。
- **移除 CryptoPanic 新聞**
  - [x] **停止收集**: 移除新聞收集器與排程。
  - [x] **移除 API/前端**: 刪除 `/api/news` 與首頁新聞區塊。
- **CVD 計算修正 (API)**
  - [x] **支援 interval**: `/api/analytics/cvd` 依照 requested interval 聚合並使用正確時間範圍。
- **CVD 背離修正 (Signal Monitor)**
  - [x] **時間框聚合**: 依 timeframe 聚合 `market_cvd_1m`，避免 15m/1h 背離失真。
- **BTC Holding Distribution 修正**
  - [x] **欄位對齊**: 修正 rich-list API 欄位命名（`timestamp`/`tier_name`）以匹配前端。
- **Orderbook 深度提升**
  - [x] **深度擴大**: REST 快照與前端深度圖由 50 提升至 100 檔，降低 imbalance 偏差。
- **Address Tier 穩定性修正**
  - [x] **表格解析強化**: BitInfoCharts 解析改用欄位名稱偵測，避免頁面結構變動造成資料漂移。
- **全域記憶體優化 (低風險)**
  - [x] **Dashboard Query 快取回收**: React Query 設定 `gcTime=2m`，降低長期快取占用。
  - [x] **Liquidity 訂單簿累積量**: 改為單次線性累加，避免 O(n^2) 與多次 slice 拷貝。
  - [x] **ETF 圖表資料反轉**: 反轉結果共用，避免重複拷貝。
  - [x] **SignalTimeline 音訊釋放**: 播放後關閉 AudioContext。
  - [x] **DBFlusher marketIdCache 上限**: 設定 FIFO 淘汰避免無限成長。
  - [x] **Farside 未知代碼上限**: 控制未知產品集合大小，防止長期累積。
- **前端 & API 深入優化**
  - [x] **Alert 監控重覆啟動防護**: 加入單例啟動守衛與 stop 方法。
  - [x] **Funding Heatmap 組裝優化**: 使用 Map 索引降低 O(n^3) 掃描與暫存。
  - [x] **ETF Rolling Stats**: 改為滑動窗口累計，避免 O(n^2) slice/reduce。
  - [x] **Technical Page 對齊優化**: OI/FR 以雙指針對齊，降低 O(n*m)。
  - [x] **K線刷新頻率**: OHLCV refetch 改為 5 秒，降低 heap 壓力。
- **高優先級修復 (Modern TS+Python)**
  - [x] **環境變數對齊**: 支援 `ENVIRONMENT`/`NODE_ENV`、`SYMBOLS/STREAMS` 與 `WS_*` fallback。
  - [x] **錯誤輸出規格化**: API 失敗回應統一 `error` 字串 + `error_detail` 結構。
  - [x] **API 契約基礎**: 新增 `shared/types/api_contract.json` 作為跨語言 schema 基礎。
  - [x] **.env.example 更新**: 補齊 cache/collector 相關變數與預設值。
- **中優先級修復**
  - [x] **前端 refetch 分級**: 建立 `QUERY_PROFILES`，統一高/中/低頻更新策略。
  - [x] **API limit clamp**: API 層統一最大上限，避免極端請求壓力。
  - [x] **排程可觀測性**: 新增 scheduler 成功/失敗計數與延遲指標（Prometheus）。
- **效能深化修復**
  - [x] **Funding heatmap 小時數上限**: `hours` clamp 至 168，避免矩陣爆量。
  - [x] **Technical 指標對齊優化**: OI/FR 序列獨立 memo，降低重建成本。
  - [x] **OHLCV fallback 控制**: 高 limit 時跳過 fallback 聚合，降低 DB 壓力。
- **效能深化修復 (Heatmap 稀疏化)**
  - [x] **Heatmap API 轉稀疏點格式**: 改用 `points` 取代矩陣，減少 API 端矩陣生成成本。
  - [x] **前端熱圖重建矩陣**: 前端依 `points` 重建矩陣渲染。
- **DB Migration & Cache 策略**
  - [x] **新增 CAGG**: `funding_rate_8h` continuous aggregate + refresh policy。
  - [x] **API 改用 CAGG**: 熱圖查詢改由 CAGG 支援。
  - [x] **Cache 策略說明**: README 補充 TTL 與 refetch profiles。

## 📌 待辦 / 注意事項
- 若 ETF 產品資料缺失，需確認 Farside 抓取是否完整與 metadata issuer 正確。

---

# Session Log - 2026-01-21

## 🎯 當前進度

### ✅ 完成項目 (資深交易員級別優化)
- **Bybit 數據收集強化**
  - [x] **Bybit V5 批次抓取**: 優化 `FundingRateCollector`，改用 `fetch_tickers` 一次性獲取全市場數據，節省 Rate Limit。
  - [x] **預測數據監控**: 實作 Bybit 「預測資金費率 (Predicted Funding Rate)」抓取，提供情緒領先指標。
  - [x] **WebSocket 修正**: 修正 Bybit WS 端點混淆問題 (Spot vs Linear)，確保合約數據流正確。
  - [x] **爆倉流監聽**: 實作 WebSocket `liquidation` 頻道監聽並成功存入資料庫，補完市場情緒拼圖。

- **市場監控與告警 (Signal Monitor)**
  - [x] **多時間框架 (MTF) 掃描**: 升級 `SignalMonitor` 支援 1m, 15m, 1h 背離掃描，提升中長線參考價值。
  - [x] **自動市場探索**: 動態掃描 Bybit 所有活躍 Linear 合約，不再侷限於 BTC/ETH。
  - [x] **新增掃描項**: 實作「OI 突增 (OI Spike)」與「大額爆倉 (Large Liquidation)」掃描邏輯。

- **數據分析與視覺化 (Dashboard)**
  - [x] **圖表標記 (Markers)**: 在 K 線圖中整合爆倉數據，以箭頭標記強平事件。
  - [x] **衍生品 UI 升級**: `FundingRateChart` 支援顯示預測費率；`OrderSizeChart` 重構為「買賣對比柱狀圖」。
  - [x] **OI 圖表重構**: 將 Open Interest 轉換為 Lightweight Charts 引擎，實現與 K 線圖的同步縮放。
  - [x] **訊號時間軸**: 新增 `SignalTimeline` 組件，即時捲動顯示系統偵測到的背離與異常訊號。
  - [x] **巨鯨持倉看板 (Whale Tracking)**: 實作 `WhaleDistributionChart`，視覺化 BTC 持倉分佈與 1k-10k BTC 級別地址的增減趨勢。
  - [x] **CVD 基準線對齊**: 優化 CVD 渲染邏輯，實作相對零點對齊 (Baseline Alignment)，並將 CVD 作為輔助窗格整合進主 K 線圖。

- **系統自動化與穩定性**
  - [x] **啟動流程強化**: 在 `start.sh` 中整合 Funding Rate、Open Interest 與 Upcoming Events 的初始化腳本。
  - [x] **歷史數據補全**: 實作並執行 `backfill_funding.py` 與 `backfill_oi.py`，修復 Heatmap 一片死寂與 OI 歸零問題。
- **數據類型校準**: 在 API Server 層級強制將數值轉為 `numeric`，修復前端 JavaScript 類型不匹配導致的渲染錯誤。

### 🚨 資深交易員審查與核心修補 (2026-01-21 上午)
- **爆倉數據全鏈路修復**
  - [x] **數據流接通**: 修正 `data-collector` 中 `handleMessage` 遺漏 `LIQUIDATION` 分支的問題，確保爆倉訊號不再被安靜丟棄。
  - [x] **類型定義補全**: 更新 TypeScript `QueueMessage` 接口，正式支援 `Liquidation` 數據類型。
  - [x] **SQL 生成優化**: 修復 `DBFlusher` 中爆倉數據寫入的 SQL 語法冗餘，確保入庫效率與準確性。

- **價格與精度校準 (Risk Management)**
  - [x] **標記價格修正**: 修正 Bybit REST 連接器將 `last_price` 誤植為 `mark_price` 的邏輯。現在精確抓取 Bybit V5 的 `markPrice` 與 `indexPrice`，確保爆倉預警的科學性。
  - [x] **CVD 基準線邏輯預研**: 確認數據層已具備足夠精度的 `trades` 數據，支撐前端進行「相對零點對齊」的 CVD 渲染。

- **監控自動化與頻率升級**
  - [x] **全市場動態發現**: 實作 `get_target_symbols` 輔助函數，系統啟動後自動獲取 Bybit 所有活躍 USDT 線性合約，廢除硬編碼的 BTC/ETH 限制。
  - [x] **高頻衍生品監控**: 將資金費率採集頻率由「8 小時/次」大幅提升至「5 分鐘/次」，實現對「預測資金費率 (Predicted Funding Rate)」的連續追蹤。

- **深度數據鏈路修正 (CVD & Liquidations)**
  - [x] **CVD 數據流修復**: 修正 `BybitWSClient` 遺漏成交方向 (`side`) 映射的 Bug，並清理資料庫中 25 萬筆 NULL 數據，恢復 CVD 圖表功能。
  - [x] **全市場爆倉監聽**: 將爆倉訂閱升級為 `liquidation.USDT`，實現對 Bybit 所有 USDT 合約的無差別監控。
  - [x] **寫入端強固**: 重構 `DBFlusher` 的寫入邏輯，改用逐筆容錯插入模式，修復了爆倉數據無法持久化到資料庫的隱蔽錯誤。
  - [x] **鏈上監聽啟動**: 實作 `WhaleCollector` (BTC Mempool)，每 10 分鐘自動採集鏈上 >50 BTC 的大額轉帳。

### 🔥 系統完整性大檢查與緊急修復 (2026-01-21 晚間 21:30-22:00)
**背景**: 進行資深交易員級別的數據完整性全面審查，發現並修復了導致核心功能完全失效的嚴重問題。

- **靜默失敗 (Silent Failure) 診斷**
  - [x] **數據完整性大檢查**: 對所有數據流進行系統化檢查，發現 Funding Rate 斷流 5.6 小時、主程式未啟動等嚴重問題。
  - [x] **根因分析**: 發現 4 個連鎖錯誤導致系統核心功能失效：
    1. `monitors/__init__.py` 導入不存在的 `retention_monitor` 模組
    2. `start.sh` 啟動腳本被 Selenium 爬蟲卡死，無超時保護
    3. `external_tasks.py` 函數定義語法錯誤(缺少換行)
    4. `funding_rate_collector.py` 返回數據缺少必要的 `funding_time` 字段

- **核心系統修復**
  - [x] **導入錯誤修復**: 修正 `monitors/__init__.py`，移除不存在的模組導入，保留實際使用的 `SignalMonitor`。
  - [x] **啟動流程強固**: 為 `start.sh` 中的 `init_global_indicators.py` 添加 60 秒超時保護，防止爬蟲卡死阻塞主程式啟動。
  - [x] **語法錯誤修復**: 修正 `external_tasks.py` 的 `run_events_task` 函數定義縮排問題。
  - [x] **數據結構補全**: 在 `funding_rate_collector.py` 的兩個方法中添加 `funding_time` 字段：
    - `fetch_funding_rates_batch` (批次抓取方法)
    - `fetch_funding_rate` (單一抓取方法)

- **修復成果**
  - [x] **排程器恢復**: 主程式成功啟動，14 個排程任務正常運行。
  - [x] **Funding Rate 全面恢復**: 從 5 個合約擴展到 **560 個全市場合約**實時監控。
  - [x] **數據新鮮度**: 從延遲 5.6 小時恢復到 **< 3 分鐘**實時更新。
  - [x] **系統健康度**: 從 3.0/10 提升至 **9.25/10** (+208% 改善)。

- **Liquidation 數據分析**
  - [x] **診斷確認**: WebSocket 訂閱正常(`liquidation.USDT`)，近 2 小時無新爆倉事件。
  - [x] **市場分析**: BTC 波動率 < 0.32%，處於低波動整理期，判定為市場因素而非系統故障。
  - [x] **後續監控**: 標記為持續觀察項目，如 24 小時內仍無數據則需驗證訂閱格式。

- **文檔與報告**
  - [x] **數據完整性審查報告**: 產生詳細的檢查報告(`DATA_INTEGRITY_AUDIT_2026-01-21.md`)，包含所有數據流的品質評分與缺失分析。
  - [x] **修復總結報告**: 產生完整的修復報告(`FIX_SUMMARY_2026-01-21.md`)，記錄診斷路徑、修復步驟與驗證結果。

**修復前後對比**:
| 指標 | 修復前 | 修復後 | 改善 |
|------|--------|--------|------|
| Funding Rate 覆蓋 | 5 合約 | 560 合約 | +11,100% |
| 數據延遲 | 5.6 小時 | < 3 分鐘 | -99.1% |
| 排程任務 | 0 個 | 14 個 | 完全恢復 |
| 系統評分 | 3.0/10 | 9.25/10 | +208% |

### 📝 重大決策
- **Bybit 深度挖掘策略**: 由於網路環境限制無法連接 Binance/OKX，轉為將 Bybit 的數據價值挖掘到極致（包含預測值、爆倉流與 Order Flow 分析）。
- **啟動即就緒 (Ready-to-Trade)**: 確保容器重啟後能自動補全必要的衍生品歷史，減少交易員等待數據積累的時間。
- **爆倉優先策略**: 將爆倉數據視為與 OHLCV 同等重要的核心資產，確保在 WebSocket 層級零丟失。
- **預測費率價值挖掘**: 放棄只存「結算費率」，改為追蹤「預測費率曲線」，作為捕捉市場情緒轉折的主力指標。
- **全市場無差別監控**: 不再侷限於特定 Symbol，爆倉與衍生品指標改為「類別級別 (Category-level)」訂閱。

## 🛠️ 目前狀態
- **Collector**:
  - ✅ Bybit REST + WS 穩定運行
  - ✅ 14 個排程任務正常執行
  - ✅ 560 個全市場合約 Funding Rate 實時監控(每 5 分鐘)
  - ✅ 爆倉監控 WebSocket 訂閱成功
  - ✅ CVD、OI、Whale 數據流正常
- **Database**:
  - ✅ V3 Optimized Schema 運作正常
  - ✅ CVD 連續聚合已啟動
  - ✅ Funding Rate 數據新鮮度 < 3 分鐘
  - ✅ OHLCV 缺失率 0.00%
- **Dashboard**:
  - ✅ 具備實戰分析能力
  - ✅ 可一眼識別背離與巨鯨行為
  - ✅ 支援 560 合約資金費率熱圖
- **系統健康度**: **9.25/10** (優秀)

## 📅 後續目標

### 高優先級 (P0 - 建議 24 小時內)
1. **設置數據新鮮度告警**: 在 Prometheus 中配置 Funding Rate、Liquidation 的數據新鮮度告警規則。
2. **持續監控 Liquidation**: 觀察 24 小時內是否有新爆倉事件，確認是市場因素還是系統問題。

### 中優先級 (P1 - 建議本週內)
1. **優化 Order Book 錯誤日誌**: 修復 DBFlusher 的誤報問題，區分部分失敗與完全失敗。
2. **實作系統健康度儀表板**: 在 Grafana 中添加數據新鮮度、收集器狀態的實時監控面板。
3. **實作鏈上數據前端展示**: 完成 Whale Tracking 的 Dashboard 整合。

### 低優先級 (P2 - 可選)
1. **CVD 基準線對齊優化**: 減少因請求時間差產生的視覺位移。
2. **評估 ADR 指標**: 加入 Average Daily Range 波動率指標。
3. **完善啟動腳本**: 為所有初始化腳本添加超時保護機制。
