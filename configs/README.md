# Crypto Market Dashboard - Configuration Guide

本目錄存放所有系統配置檔，遵循「配置驅動」的設計原則。

## 📂 目錄結構

- `app.yml`: 全域系統配置（資料庫、Redis、監控、全域預設值）。
- `collector/`: 存放各交易對的收集任務配置。
  - `binance_btcusdt_1m.yml`: Binance BTC/USDT 配置。
  - `bybit_btcusdt_1m.yml`: Bybit BTC/USDT 配置。
  - `okx_btcusdt_1m.yml`: OKX BTC/USDT 配置。

## 🛠 配置原則

1. **環境變數替換**: 所有 YAML 檔案均支援 `${VAR_NAME}` 或 `${VAR_NAME:default_value}` 語法，會自動從環境變數或 `.env` 檔案中載入。
2. **單一職責**:
   - `app.yml` 負責「基礎設施」與「全域行為」。
   - `collector/*.yml` 負責「具體收集任務」的參數。
3. **版本控制**: 範例配置與通用設定應進入 Git，敏感資訊（API Keys）必須透過環境變數傳遞。

## 🚀 新增收集任務

若要新增一個收集任務，只需在 `collector/` 目錄下新增一個 `.yml` 檔案，系統重啟後會自動偵測並啟動對應的收集器。

---

**Last Updated**: 2026-01-15  
**Related Docs**: [PROJECT_STATUS_REPORT.md](../docs/PROJECT_STATUS_REPORT.md), [TECH_DEBT.md](../docs/TECH_DEBT.md)
