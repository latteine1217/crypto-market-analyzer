
import os

exchanges = [
    {
        'name': 'bybit',
        'api_endpoint': 'https://api.bybit.com',
        'rate_limit_per_min': 120,
        'rate_limit_per_sec': 5,
        'symbol_map': {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT'}
    }
]

timeframes = [
    {'tf': '5m', 'schedule': '*/5 * * * *', 'lookback': 30, 'desc': '5分鐘'},
    {'tf': '15m', 'schedule': '*/15 * * * *', 'lookback': 60, 'desc': '15分鐘'},
    {'tf': '4h', 'schedule': '5 */4 * * *', 'lookback': 720, 'desc': '4小時'},
    {'tf': '1d', 'schedule': '10 0 * * *', 'lookback': 2880, 'desc': '1日'}
]

assets = ['BTC', 'ETH']

template = """# ============================================
# {exchange_cap} {base}/USDT {desc} K線 Collector 配置
# ============================================

# 基本資訊
name: {name}
description: "{exchange_cap} {base}/USDT {desc} K線資料收集"

# 交易所配置
exchange:
  name: {exchange}
  api_endpoint: {api_endpoint}
  api_key: ${{{exchange_upper}_API_KEY}}
  api_secret: ${{{exchange_upper}_API_SECRET}}

# 交易對配置
symbol:
  base: {base}
  quote: USDT
  exchange_symbol: {exchange_symbol}

# 資料類型配置
data_type: ohlcv
timeframe: {tf}

# 收集模式
mode:
  # 歷史資料補齊
  historical:
    enabled: true
    start_date: "2024-01-01T00:00:00Z"
    end_date: null
    batch_size: 1000

  # 定期批次更新
  periodic:
    enabled: true
    schedule: "{schedule}"
    lookback_minutes: {lookback}

  # WebSocket 實時
  realtime:
    enabled: false

# API 請求配置
request:
  timeout: 30
  max_retries: 3
  retry_delay: 5
  backoff_factor: 2

# 速率限制
rate_limit:
  requests_per_minute: {rpm}
  requests_per_second: {rps}
  weight_per_request: 1
  max_weight: {rpm}

# 資料驗證
validation:
  enabled: true
  checks:
    - timestamp_order
    - no_duplicates
    - price_range
    - volume_positive

# 儲存配置
storage:
  target: timescaledb
  table: ohlcv
  conflict_strategy: upsert
  batch_insert: true
  batch_size: 100

# 錯誤處理
error_handling:
  on_api_error: retry
  on_validation_error: skip_and_log
  on_storage_error: retry
  max_consecutive_failures: 10

# 監控與日誌
monitoring:
  log_every_n_batches: 1
  metrics:
    - rows_inserted
    - api_calls
    - api_errors
    - validation_failures
"""

config_dir = 'configs/collector'

for exc in exchanges:
    for asset in assets:
        for tf in timeframes:
            exchange_symbol = exc['symbol_map'][asset]
            filename = f"{exc['name']}_{asset.lower()}usdt_{tf['tf']}.yml"
            filepath = os.path.join(config_dir, filename)
            
            content = template.format(
                exchange_cap=exc['name'].capitalize(),
                exchange=exc['name'],
                exchange_upper=exc['name'].upper(),
                api_endpoint=exc['api_endpoint'],
                base=asset,
                desc=tf['desc'],
                name=filename.replace('.yml', ''),
                exchange_symbol=exchange_symbol,
                tf=tf['tf'],
                schedule=tf['schedule'],
                lookback=tf['lookback'],
                rpm=exc['rate_limit_per_min'],
                rps=exc['rate_limit_per_sec']
            )
            
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Created {filename}")

