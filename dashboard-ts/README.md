# Crypto Dashboard (Next.js)

`dashboard-ts` 是交易監看前端，資料來源為 `api-server`。

## 功能範圍（目前）

- 市場總覽（Top 市值/成交量與衍生品摘要）
- 技術分析頁（K 線、CVD、OI、Funding）
- 流動性頁（Orderbook depth / OBI）
- ETF 頁（Flow / divergence / issuer concentration）
- 鏈上頁（whale / rich-list）
- 狀態頁（系統健康與資料品質）

## 啟動

```bash
npm install
npm run dev
```

預設埠：`3001`

生產模式：

```bash
npm run build
npm start
```

## 環境變數

```env
NEXT_PUBLIC_API_URL=/api
```

若本地直連 API（非 nginx）可改成：

```env
NEXT_PUBLIC_API_URL=http://localhost:8080/api
```

## 型別契約注意事項

- `DataQualityMetrics.status` 為小寫等級：
  - `excellent | good | acceptable | poor | critical`
- `DataQualityMetrics` 包含：
  - `missing_count`
  - `expected_count`
  - `actual_count`
  - `backfill_task_created`

## 驗證

```bash
npm run type-check
npm run build
```

---

最後更新：2026-02-13
