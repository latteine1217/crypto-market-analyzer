# 任務簡述：報表增強 - K線圖與巨鯨動向

**任務 ID**: `report-enhancement-001`  
**建立時間**: 2025-12-30  
**優先級**: 高  
**預估時間**: 4-6 小時  

---

## 📋 任務目標

在現有報表系統中加入以下視覺化內容：
1. **K 線圖**：顯示價格走勢、成交量
2. **巨鯨動向分析**：大額交易列表、流入流出統計、異常告警
3. **市場深度**：訂單簿分布圖
4. **交易量分析**：時間序列熱力圖

---

## 📥 輸入資料來源

| 資料類型 | 資料表 | 查詢方法 |
|---------|--------|---------|
| K 線資料 | `ohlcv`、`ohlcv_1h`、`ohlcv_1d` | 時間範圍查詢 |
| 巨鯨交易 | `whale_transactions` | JOIN `whale_addresses` |
| 訂單簿 | `orderbook_snapshots` | 最新快照 |
| 交易資料 | `trades` | 聚合統計 |

---

## 🎯 驗收指標

### 功能性指標
- [ ] K 線圖包含：開高低收、成交量柱狀圖
- [ ] 巨鯨動向包含：交易列表、流入流出統計、異常標記
- [ ] 支援多時間粒度：5m/15m/1h/1d
- [ ] 圖表具備互動功能：縮放、懸停提示、時間範圍選擇

### 品質指標
- [ ] 圖表生成時間 < 3 秒 (100 筆資料)
- [ ] HTML 檔案大小 < 5 MB (含圖表)
- [ ] 瀏覽器相容性：Chrome/Firefox/Safari
- [ ] PDF 生成正常 (圖表不失真)

### 可用性指標
- [ ] Overview 報表包含核心圖表 (1-2 張)
- [ ] Detail 報表包含完整圖表 (5-8 張)
- [ ] 圖表具備標題、軸標籤、圖例
- [ ] 配色符合專業財報風格

---

## 📁 影響檔案

### 需要修改
1. `data-analyzer/src/reports/data_collector.py` - 新增資料查詢方法
2. `data-analyzer/src/reports/html_generator.py` - 新增圖表生成方法
3. `data-analyzer/src/reports/report_agent.py` - 整合新功能

### 需要新增
4. `data-analyzer/src/reports/chart_generator.py` - 圖表生成核心模組
5. `data-analyzer/requirements.txt` - 新增 `plotly` 依賴

### 需要測試
6. `data-analyzer/test_enhanced_report.py` - 測試腳本

---

## ⏱️ 時間盒

- **階段 1**：資料收集器擴展 (1.5h)
- **階段 2**：圖表生成器實作 (2h)
- **階段 3**：HTML 生成器整合 (1.5h)
- **階段 4**：測試與調整 (1h)

**總計**：約 6 小時

---

## 🔗 相關文件

- `data-analyzer/REPORT_USAGE.md` - 報表系統使用指南
- `database/schemas/01_init.sql` - 資料庫 schema
- `database/schemas/02_blockchain_whale_tracking.sql` - 巨鯨資料 schema
- `docs/SESSION_LOG.md` - 專案進度日誌

---

## 📝 實作筆記

### 設計決策
1. **圖表庫選擇**：Plotly (互動式、Python 原生、PDF 友好)
2. **資料快取**：查詢結果暫存於記憶體，避免重複查詢
3. **圖表樣式**：專業財報風格 (深色背景、對比色)
4. **錯誤處理**：資料缺失時顯示友善訊息，不中斷報表生成

### 技術挑戰
- Plotly 生成的 HTML 較大 → 使用 `include_plotlyjs='cdn'` 減小體積
- PDF 中嵌入互動圖表 → 轉換為靜態圖片後嵌入
- 大量資料效能 → 限制查詢筆數 (最多 1000 筆) + 採樣顯示

### 測試策略
1. 單元測試：測試各查詢方法資料正確性
2. 整合測試：生成完整報表並驗證圖表
3. 視覺測試：人工檢查圖表美觀度與可讀性
4. 效能測試：測量生成時間與檔案大小

---

**建立者**: 主 Agent  
**狀態**: 規劃完成，待實作
