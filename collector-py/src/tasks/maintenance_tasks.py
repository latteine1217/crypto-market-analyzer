"""
維護任務模組
負責品質檢查、補資料、資料保留政策與 DB 監控
"""
from loguru import logger
from error_handler import retry_with_backoff, RetryConfig
from utils.symbol_utils import to_ccxt_format

def run_quality_check_task(orchestrator):
    """品質檢查任務"""
    results = orchestrator.quality_checker.check_all_active_markets(timeframe="1m", lookback_hours=1, create_backfill_tasks=True)
    for result in results:
        if 'exchange' in result and 'symbol' in result:
            orchestrator.metrics.update_data_quality(
                exchange=result['exchange'], symbol=result['symbol'], 
                timeframe=result.get('timeframe', '1m'), score=result.get('score', 0), 
                missing_rate=result.get('missing_rate', 0)
            )
    logger.info(f"Quality check completed: {len(results)} markets checked")

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
