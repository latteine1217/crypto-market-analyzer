# Configuration Guide

本目錄存放系統與 collector 配置，採配置驅動模式。

## 目錄結構

- `app.yml`
  - 全域配置（資料庫、Redis、系統預設）
- `collector/`
  - 個別收集任務配置（目前為 Bybit）
  - 目前檔案：
    - `bybit_btcusdt_1m.yml`
    - `bybit_btcusdt_1h.yml`
    - `bybit_ethusdt_1m.yml`
    - `bybit_ethusdt_1h.yml`

## 配置原則

1. 支援環境變數替換：`${VAR}` / `${VAR:default}`
2. `app.yml` 放全域與基礎設施設定
3. `collector/*.yml` 放任務粒度設定（symbol/timeframe/request/validation）
4. 敏感資料（API keys）不寫入 repo，改用 `.env`

## 新增收集任務

在 `collector/` 新增一個 `.yml` 後，重啟 `collector` 服務即可載入新任務。

```bash
docker-compose restart collector
```

## 檢查載入結果

```bash
docker-compose logs -f collector
```

---

最後更新：2026-02-13
