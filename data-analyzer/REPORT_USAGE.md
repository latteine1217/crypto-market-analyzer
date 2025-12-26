# Report Agent 使用指南

## 概述

Report Agent 是階段 5 的核心功能，負責整合資料品質摘要、回測結果和模型訓練結果，生成結構化的 HTML 和 PDF 報表。

## 功能特點

✅ **資料整合**
- 從 TimescaleDB 讀取資料品質摘要
- 從檔案系統讀取回測結果
- 統一資料格式供報表使用

✅ **雙層報表**
- **Overview**：給非技術人員，圖表 + 簡潔摘要
- **Detail**：給 quant/engineer，完整數據 + 技術細節

✅ **多種報表類型**
- 綜合報表（日報/週報/月報）
- 單一回測報表
- 資料品質報表

✅ **多種輸出格式**
- HTML（適合瀏覽器/Dashboard）
- PDF（適合寄送/存檔，需安裝 weasyprint）
- JSON（結構化資料）

## 安裝依賴

```bash
# 基礎功能（HTML 報表）
pip install -r requirements.txt

# PDF 功能（可選）
pip install weasyprint
```

## 快速開始

### 1. 生成綜合報表（日報）

```python
from reports import ReportAgent

# 初始化 Report Agent
agent = ReportAgent(
    output_dir="reports",
    db_config={
        'host': 'localhost',
        'port': 5432,
        'database': 'crypto_market',
        'user': 'postgres',
        'password': ''
    }
)

# 生成日報
result = agent.generate_comprehensive_report(
    report_type='daily',                        # 'daily', 'weekly', 'monthly'
    markets=['BTC/USDT', 'ETH/USDT'],          # 市場列表
    strategies=['RSI', 'MA_Cross'],             # 策略列表
    formats=['html', 'pdf']                     # 輸出格式
)

print(f"報表已生成：{result['output_paths']}")

agent.close()
```

### 2. 為單一回測生成報表

```python
from backtesting.engine import BacktestEngine
from strategies.rsi_strategy import RSIStrategy
from reports import ReportAgent

# 執行回測
engine = BacktestEngine(initial_capital=10000)
strategy = RSIStrategy()
results = engine.run(data=market_data, strategy=strategy)

# 生成報表
agent = ReportAgent(output_dir="reports")
paths = agent.generate_backtest_report(
    backtest_results=results,
    strategy_name='RSI',
    market_data=market_data,
    formats=['html', 'pdf']
)

print(f"回測報表：{paths}")
```

### 3. 生成資料品質報表

```python
from reports import ReportAgent

agent = ReportAgent(output_dir="reports")

# 過去 24 小時的品質報告
paths = agent.generate_quality_report(
    markets=['BTC/USDT'],
    hours=24,
    formats=['html']
)

print(f"品質報表：{paths}")
```

## 輸出結構

```
reports/
├── daily/                          # 日報目錄
│   ├── data/
│   │   └── daily_20241226.json    # JSON 資料
│   ├── daily_overview_20241226.html
│   ├── daily_detail_20241226.html
│   ├── daily_overview_20241226.pdf
│   └── daily_detail_20241226.pdf
│
├── weekly/                         # 週報目錄
│   └── ...
│
├── monthly/                        # 月報目錄
│   └── ...
│
├── backtests/                      # 回測報表
│   ├── RSI_report.html
│   ├── RSI_results.json
│   └── ...
│
└── quality/                        # 品質報表
    ├── quality_20241226_1400.html
    └── quality_20241226_1400.json
```

## 報表內容說明

### Overview 報表（給非技術人）

**包含內容：**
- 📊 關鍵指標卡片
  - 最佳策略 & 收益率
  - 資料品質平均分數
  - 品質異常數
  - 測試策略數
- 💼 策略績效比較表
  - 總收益、Sharpe Ratio、最大回撤、勝率、交易次數
- 📋 資料品質摘要表
  - Symbol、Exchange、品質分數、狀態、缺失數

**特點：**
- 視覺化優先，圖表清晰
- 簡潔明瞭的指標
- 適合管理層查看

### Detail 報表（給 quant/engineer）

**包含內容：**
- 📝 完整 Metadata
- 📊 詳細回測結果（JSON 格式）
- 🔍 詳細品質資料（JSON 格式）
- 所有技術細節

**特點：**
- 完整的技術資訊
- JSON 格式的原始資料
- 可追溯所有計算

## 排程自動化

### 使用 cron 定期生成報表

```bash
# 每天 01:00 生成日報
0 1 * * * cd /path/to/project && python scripts/generate_daily_report.py

# 每週日 02:00 生成週報
0 2 * * 0 cd /path/to/project && python scripts/generate_weekly_report.py

# 每月 1 號 03:00 生成月報
0 3 1 * * cd /path/to/project && python scripts/generate_monthly_report.py
```

### 使用 Python APScheduler

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from reports import ReportAgent

def generate_daily_report():
    agent = ReportAgent(output_dir="reports")
    agent.generate_comprehensive_report(
        report_type='daily',
        formats=['html', 'pdf']
    )
    agent.close()

scheduler = BlockingScheduler()
scheduler.add_job(generate_daily_report, 'cron', hour=1)  # 每天 01:00
scheduler.start()
```

## 測試

運行測試腳本：

```bash
cd data-analyzer
python test_report_agent.py
```

測試項目：
1. 綜合報表生成（日報）
2. 從現有回測結果生成報表
3. 資料品質報表

## 注意事項

1. **資料庫連接**：確保 TimescaleDB 運行中
2. **PDF 生成**：需安裝 weasyprint（可選）
3. **檔案權限**：確保輸出目錄有寫入權限
4. **回測結果**：確保回測已執行並有結果檔案

## 故障排除

### PDF 生成失敗

**問題**：`WeasyPrint 未安裝`

**解決**：
```bash
pip install weasyprint
```

如果仍然失敗，系統會自動退回到 HTML 模式。

### 資料庫連接失敗

**問題**：`資料庫連接失敗`

**解決**：
1. 檢查 TimescaleDB 是否運行：`docker ps`
2. 檢查資料庫配置是否正確
3. 檢查網路連接

### 無回測結果

**問題**：`收集到 0 個策略的回測結果`

**解決**：
1. 先執行回測：`python tests/test_backtest.py`
2. 確認回測結果目錄：`results/backtest_reports/`

## 進階使用

### 自訂資料收集器

```python
from reports.data_collector import ReportDataCollector

collector = ReportDataCollector(db_config={...})

# 自訂時間範圍
quality_data = collector.collect_quality_summary(
    start_date=datetime(2024, 12, 1),
    end_date=datetime(2024, 12, 26),
    markets=['BTC/USDT']
)

# 獲取統計摘要
stats = collector.get_quality_statistics(
    start_date=datetime(2024, 12, 1),
    end_date=datetime(2024, 12, 26)
)

print(f"平均品質分數：{stats['avg_quality_score']}")
```

### 自訂 HTML 模板

HTML 模板內建在 `html_generator.py` 中，可以通過繼承 `HTMLReportGenerator` 來自訂樣式。

## 版本資訊

- **版本**：1.0.0
- **狀態**：階段 5 完成
- **更新日期**：2024-12-26
