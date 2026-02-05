"""
維護任務模組
負責品質檢查、補資料、資料保留政策與 DB 監控
"""
from loguru import logger
from error_handler import retry_with_backoff, RetryConfig
from utils.symbol_utils import to_ccxt_format

import datetime

def run_quality_check_task(orchestrator):
    """品質檢查任務"""
    # ... existing code ...

def run_cvd_calibration_task(orchestrator):
    """CVD 校準任務：抓取 24h Volume 作為真值錨點，記錄漂移"""
    logger.info("Starting CVD calibration...")
    markets = orchestrator.db.get_active_markets()
    client = orchestrator.connectors.get('bybit')
    
    if not client:
        return

    for m in markets:
        market_id, symbol = m['id'], m['symbol']
        try:
            ccxt_symbol = to_ccxt_format(symbol, market_type='linear')
            ticker = client.fetch_ticker(ccxt_symbol)
            exchange_vol_24h = float(ticker.get('baseVolume', 0))
            
            if exchange_vol_24h <= 0: continue
            
            # 獲取本地 24h 累積成交量
            query = "SELECT SUM(amount) FROM trades WHERE market_id = %s AND time >= NOW() - INTERVAL '24 hours'"
            with orchestrator.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (market_id,))
                    local_vol_24h = float(cur.fetchone()[0] or 0)
            
            # 記錄錨點
            with orchestrator.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO market_anchors (market_id, time, anchor_type, value, system_cvd) VALUES (%s, NOW(), %s, %s, %s)",
                        (market_id, 'volume_24h', exchange_vol_24h, local_vol_24h)
                    )
            
            drift = (1 - (local_vol_24h / exchange_vol_24h)) * 100 if exchange_vol_24h > 0 else 0
            if abs(drift) > 5:
                logger.warning(f"⚠️ CVD Drift detected for {symbol}: {drift:.2f}%")
            else:
                logger.info(f"✅ {symbol} CVD drift is within healthy range: {drift:.2f}%")
                
        except Exception as e:
            logger.error(f"CVD calibration failed for {symbol}: {e}")

def run_backfill_task(orchestrator):
    """補資料任務"""
    tasks = orchestrator.backfill_scheduler.get_pending_tasks(limit=5)
    orchestrator.metrics.update_backfill_stats(pending=len(tasks) if tasks else 0)
    
    for task in tasks:
        task_id, market_id = task['id'], task['market_id']
        try:
            orchestrator.backfill_scheduler.update_task_status(task_id, 'running')
            market_info = orchestrator.db.get_market_info(market_id)
            exchange_name, symbol, timeframe = market_info['exchange'], market_info['symbol'], task['timeframe']
            
            connector = orchestrator.connectors.get(exchange_name)
            if not connector: 
                logger.warning(f"Connector not found for exchange: {exchange_name}")
                continue

            # ✅ 修正：轉換 symbol 為 CCXT 格式（OKX 需要 BTC/USDT 而非 BTCUSDT）
            try:
                ccxt_symbol = to_ccxt_format(symbol, market_type='linear')
                logger.debug(f"Symbol conversion: {symbol} → {ccxt_symbol} for {exchange_name}")
            except Exception as conv_err:
                logger.error(f"Symbol conversion failed for {symbol}: {conv_err}")
                orchestrator.backfill_scheduler.update_task_status(task_id, 'failed', error_message=f"Symbol conversion error: {conv_err}")
                continue

            # 補資料邏輯
            ohlcv = connector.fetch_ohlcv(symbol=ccxt_symbol, timeframe=timeframe, since=int(task['start_time'].timestamp() * 1000), limit=1000)
            if ohlcv:
                count = orchestrator.db.insert_ohlcv_batch(market_id, timeframe, ohlcv)
                orchestrator.backfill_scheduler.update_task_status(task_id, 'completed', actual_records=count)
                orchestrator.metrics.record_backfill_completion(status='success')
                logger.success(f"Backfill task #{task_id} completed: {count} records ({exchange_name} {symbol})")
            else:
                logger.warning(f"Backfill task #{task_id} returned no data")
                orchestrator.backfill_scheduler.update_task_status(task_id, 'completed', actual_records=0)
        except Exception as e:
            logger.error(f"Backfill task #{task_id} failed: {e}")
            orchestrator.backfill_scheduler.update_task_status(task_id, 'failed', error_message=str(e))
            orchestrator.metrics.record_backfill_completion(status='failed')
