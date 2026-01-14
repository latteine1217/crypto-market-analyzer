# 資料級觀測性增強設計（Data-Level Observability）

**任務 ID**: design-improvements-003  
**建立日期**: 2025-12-30  
**狀態**: 設計中  
**優先級**: 高

---

## 問題描述

### 現況
- Prometheus 指標齊全（108+ metrics），但偏「服務級」
- 對資料「缺失率、延遲、品質分數」的**跨層追蹤**不足
- 缺少統一 KPI 橫跨交易所/時間框架/資料層
- 無法快速回答：「最近 24 小時哪些資料有問題？」

### 影響
- 資料品質問題發現慢（被動等告警）
- 跨交易所資料對比困難
- Root cause 分析需手動查詢多個系統
- 無法自動生成「資料健康度報告」

---

## 設計目標

### 核心原則
1. **Physics Gate 優先**：監控指標需包含量綱正確性檢查
2. **觀測性優先**：資料問題需可追溯到具體時間/交易所/交易對
3. **不破壞 Userspace**：新增 metrics，不修改現有資料流

### 驗收標準
- [ ] 可在 Grafana 查詢「任意交易對過去 7 天的缺失率」
- [ ] 有統一「資料健康度分數」（0-100）
- [ ] 品質問題可追溯到 exchange/symbol/timeframe/timestamp
- [ ] 新增 <20 個 data-quality metrics

---

## 實施方案

### Phase 9A: Data Quality Metrics Exporter（2 天）

#### 新增 metrics（在 quality_checker.py）

```python
# collector-py/src/quality_checker.py

from prometheus_client import Gauge, Counter, Histogram

# ===== 資料缺失率 metrics =====
data_missing_rate = Gauge(
    'data_missing_rate',
    'Data missing rate (0-1)',
    ['exchange', 'symbol', 'timeframe', 'data_type']  # data_type: ohlcv/trades/orderbook
)

# ===== 資料品質分數 metrics =====
data_quality_score = Gauge(
    'data_quality_score',
    'Overall data quality score (0-100)',
    ['exchange', 'symbol', 'timeframe']
)

# ===== 資料延遲 metrics =====
data_latency_seconds = Gauge(
    'data_latency_seconds',
    'Data latency (now - latest_timestamp)',
    ['exchange', 'symbol', 'timeframe']
)

# ===== 異常值檢測 metrics =====
data_anomaly_count = Counter(
    'data_anomaly_total',
    'Total anomalies detected',
    ['exchange', 'symbol', 'anomaly_type']  # price_jump/volume_spike/timestamp_gap
)

# ===== 跨交易所價差 metrics =====
cross_exchange_price_diff = Gauge(
    'cross_exchange_price_diff_percent',
    'Price difference between exchanges (%)',
    ['symbol', 'exchange_a', 'exchange_b']
)
```

#### 實作 Data Health Score

```python
class DataHealthScorer:
    """資料健康度評分（0-100）"""
    
    @staticmethod
    def compute_score(exchange: str, symbol: str, timeframe: str, lookback_hours: int = 24) -> float:
        """
        綜合評分邏輯：
        - 缺失率 (40%)：缺失越少分數越高
        - 品質分數 (30%)：來自 quality_checker
        - 延遲 (20%)：越新鮮分數越高
        - 異常數量 (10%)：異常越少分數越高
        """
        # 1. 缺失率（40 分）
        missing_rate = get_missing_rate(exchange, symbol, timeframe, lookback_hours)
        missing_score = max(0, 40 * (1 - missing_rate))
        
        # 2. 品質分數（30 分）
        avg_quality = get_avg_quality_score(exchange, symbol, timeframe, lookback_hours)
        quality_score = 30 * (avg_quality / 100)
        
        # 3. 延遲分數（20 分）
        latency_minutes = get_data_latency_minutes(exchange, symbol, timeframe)
        latency_score = max(0, 20 * (1 - latency_minutes / 60))  # 超過 60 分鐘得 0 分
        
        # 4. 異常數量（10 分）
        anomaly_count = get_anomaly_count(exchange, symbol, lookback_hours)
        anomaly_score = max(0, 10 * (1 - anomaly_count / 100))  # 超過 100 個得 0 分
        
        return missing_score + quality_score + latency_score + anomaly_score
```

---

### Phase 9B: Cross-Exchange Monitoring（1 天）

```python
# 新增跨交易所價差監控
def monitor_cross_exchange_spread():
    """監控同一交易對在不同交易所的價差"""
    exchanges = ['binance', 'bybit', 'okx']
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    for symbol in symbols:
        prices = {}
        for exchange in exchanges:
            latest_price = get_latest_price(exchange, symbol)
            if latest_price:
                prices[exchange] = latest_price
        
        # 計算兩兩價差
        for ex_a, ex_b in itertools.combinations(prices.keys(), 2):
            diff_pct = abs(prices[ex_a] - prices[ex_b]) / prices[ex_a] * 100
            cross_exchange_price_diff.labels(
                symbol=symbol, 
                exchange_a=ex_a, 
                exchange_b=ex_b
            ).set(diff_pct)
```

---

### Phase 9C: Grafana Data Health Dashboard（1 天）

創建 `monitoring/grafana/dashboards/data_health.json`：

**Panels 設計**：
1. **Overall Health Heatmap**：各交易對的健康度分數（顏色：綠 >90, 黃 70-90, 紅 <70）
2. **Missing Rate by Exchange**：各交易所的缺失率趨勢
3. **Data Latency**：最新資料的延遲時間
4. **Anomaly Timeline**：異常事件時間線
5. **Cross-Exchange Spread**：交易所間價差監控
6. **Top 10 Unhealthy Pairs**：健康度最差的交易對列表

---

### Phase 9D: Automated Data Health Report（2 天）

```python
# scripts/generate_data_health_report.py

def generate_daily_data_health_report():
    """每日自動生成資料健康度報告"""
    
    report = {
        "date": datetime.now().date(),
        "overall_health": compute_overall_health(),
        "by_exchange": {},
        "top_issues": []
    }
    
    for exchange in ['binance', 'bybit', 'okx']:
        exchange_health = DataHealthScorer.compute_exchange_health(exchange)
        report["by_exchange"][exchange] = {
            "score": exchange_health,
            "missing_rate": get_exchange_missing_rate(exchange),
            "anomaly_count": get_exchange_anomaly_count(exchange)
        }
    
    # 找出 Top 10 問題
    report["top_issues"] = get_top_issues(limit=10)
    
    # 生成 HTML 報告
    html = render_health_report_html(report)
    save_report(html, f"reports/data_health_{datetime.now().date()}.html")
    
    # 如果健康度 <70，發送告警郵件
    if report["overall_health"] < 70:
        send_alert_email("Data Health Alert", html)
```

---

## 驗收標準

- [ ] Grafana 可查詢任意交易對過去 N 天的缺失率/品質/延遲
- [ ] 每日自動生成資料健康度報告（HTML）
- [ ] 跨交易所價差超過 5% 自動告警
- [ ] 資料健康度 <70 自動發送郵件

---

**時間估算**: 6 天  
**狀態**: 設計完成，待審查
