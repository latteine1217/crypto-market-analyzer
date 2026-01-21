"""
OHLCV 任務模組
負責協調各交易所的 OHLCV 資料抓取與寫入
"""
from typing import List
from datetime import timedelta
from loguru import logger
import time

from config_loader import CollectorConfig
from error_handler import retry_with_backoff, RetryConfig, ErrorClassifier, global_failure_tracker

def collect_ohlcv_task(orchestrator, config: CollectorConfig):
    """
    執行單一配置的 OHLCV 抓取任務
    """
    exchange_name = config.exchange.name
    symbol = f"{config.symbol.base}/{config.symbol.quote}"
    timeframe = config.timeframe

    logger.info(f"=== Collecting {exchange_name.upper()} {symbol} {timeframe} OHLCV ===")

    try:
        # 取得 market_id
        market_id = orchestrator.db.get_market_id(exchange_name, symbol)
        if not market_id:
            logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
            return

        # 檢查最新數據時間
        latest_time = orchestrator.db.get_latest_ohlcv_time(market_id, timeframe)
        since = None
        if latest_time:
            lookback_minutes = config.mode.periodic.lookback_minutes
            since_time = latest_time - timedelta(minutes=lookback_minutes)
            since = int(since_time.timestamp() * 1000)

        # 取得連接器
        connector = orchestrator.connectors.get(exchange_name)
        if not connector:
            logger.error(f"Connector not found for {exchange_name}")
            return

        # 使用重試機制
        retry_config = RetryConfig(
            max_retries=config.request.max_retries,
            initial_delay=config.request.retry_delay,
            backoff_factor=config.request.backoff_factor
        )

        @retry_with_backoff(config=retry_config, exchange_name=exchange_name, endpoint='fetch_ohlcv')
        def fetch_with_retry():
            start_time = time.time()
            try:
                result = connector.fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since, limit=1000)
                orchestrator.metrics.record_api_request(exchange=exchange_name, endpoint='fetch_ohlcv', status='success', duration=time.time() - start_time)
                return result
            except Exception as e:
                orchestrator.metrics.record_api_request(exchange=exchange_name, endpoint='fetch_ohlcv', status='failed', duration=time.time() - start_time)
                error_type = ErrorClassifier.classify_exception(e)
                orchestrator.metrics.record_api_error(exchange=exchange_name, endpoint='fetch_ohlcv', error_type=error_type)
                raise

        ohlcv = fetch_with_retry()
        if not ohlcv:
            return

        # 驗證
        if config.validation.enabled:
            validation_result = orchestrator.validator.validate_ohlcv_batch(ohlcv, timeframe)
            if not validation_result['valid']:
                logger.warning(f"Validation failed for {exchange_name} {symbol}")
                if config.error_handling.on_validation_error == 'skip_and_log':
                    return

        # 寫入
        count = orchestrator.db.insert_ohlcv_batch(market_id, timeframe, ohlcv)
        orchestrator.metrics.record_ohlcv_collection(exchange=exchange_name, symbol=symbol, timeframe=timeframe, count=count)
        
        # 重置失敗計數
        failure_key = f"{exchange_name}:{symbol}:{timeframe}"
        global_failure_tracker.record_success(failure_key)
        orchestrator.metrics.update_consecutive_failures(exchange=exchange_name, symbol=symbol, timeframe=timeframe, count=0)

    except Exception as e:
        logger.error(f"Error in collect_ohlcv for {exchange_name}/{symbol}: {e}")
        failure_key = f"{exchange_name}:{symbol}:{timeframe}"
        count = global_failure_tracker.record_failure(failure_key)
        orchestrator.metrics.update_consecutive_failures(exchange=exchange_name, symbol=symbol, timeframe=timeframe, count=count)
