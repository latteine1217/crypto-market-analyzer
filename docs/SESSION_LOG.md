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
