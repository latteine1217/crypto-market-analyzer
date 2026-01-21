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

### 🚨 資深交易員審查與核心修補 (2026-01-21)
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

### 📝 重大決策
- **Bybit 深度挖掘策略**: 由於網路環境限制無法連接 Binance/OKX，轉為將 Bybit 的數據價值挖掘到極致（包含預測值、爆倉流與 Order Flow 分析）。
- **啟動即就緒 (Ready-to-Trade)**: 確保容器重啟後能自動補全必要的衍生品歷史，減少交易員等待數據積累的時間。
- **爆倉優先策略**: 將爆倉數據視為與 OHLCV 同等重要的核心資產，確保在 WebSocket 層級零丟失。
- **預測費率價值挖掘**: 放棄只存「結算費率」，改為追蹤「預測費率曲線」，作為捕捉市場情緒轉折的主力指標。
- **全市場無差別監控**: 不再侷限於特定 Symbol，爆倉與衍生品指標改為「類別級別 (Category-level)」訂閱。

## 🛠️ 目前狀態
- **Collector**: Bybit REST + WS 穩定運行，包含爆倉監控。
- **Database**: V3 Optimized Schema 運作正常，CVD 連續聚合已啟動。
- **Dashboard**: 具備實戰分析能力，可一眼識別背離與巨鯨行為。

## 📅 後續目標
1. 實作鏈上數據 (Whale Tracking) 的前端展示看板。
2. 進行 CVD 基準線對齊優化，減少因請求時間差產生的視覺位移。
3. 評估加入 ADR (Average Daily Range) 波動率指標。
