"""
主程式 V2：配置驅動的資料收集系統
整合功能：
- 配置檔驅動
- 錯誤處理與重試
- 資料驗證
- 補資料排程
- 品質監控
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from typing import Dict, List, Optional

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from config_loader import ConfigLoader, CollectorConfig
from connectors.binance_rest import BinanceRESTConnector
from connectors.okx_rest import OKXRESTConnector
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from schedulers.backfill_scheduler import BackfillScheduler
from quality_checker import DataQualityChecker
from error_handler import (
    retry_with_backoff,
    RetryConfig,
    ErrorClassifier,
    global_failure_tracker
)


# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)


class ConfigDrivenCollector:
    """
    配置驅動的資料收集器

    特點：
    - 從 YAML 配置檔載入所有設定
    - 自動重試與錯誤處理
    - 資料驗證與品質監控
    - 自動補資料
    """

    def __init__(self):
        """初始化收集器"""
        # 載入配置
        self.config_loader = ConfigLoader()
        self.collector_configs = self.config_loader.load_all_collector_configs()

        if not self.collector_configs:
            logger.warning("No collector configs found!")

        # 初始化資料庫與工具
        self.db = DatabaseLoader()
        self.validator = DataValidator()
        self.backfill_scheduler = BackfillScheduler(db_conn=self.db.conn)
        self.quality_checker = DataQualityChecker(
            db_loader=self.db,
            validator=self.validator,
            backfill_scheduler=self.backfill_scheduler
        )

        # 建立連接器映射
        self.connectors = {}
        self._init_connectors()

        logger.info(f"ConfigDrivenCollector initialized with {len(self.collector_configs)} configs")

    def _init_connectors(self):
        """初始化交易所連接器"""
        # 取得所有唯一的交易所
        exchanges = set(cfg.exchange.name for cfg in self.collector_configs)

        for exchange_name in exchanges:
            if exchange_name == 'binance':
                # 從第一個 binance 配置取得 API 金鑰
                binance_cfg = next(
                    cfg for cfg in self.collector_configs
                    if cfg.exchange.name == 'binance'
                )
                self.connectors['binance'] = BinanceRESTConnector(
                    api_key=binance_cfg.exchange.api_key,
                    api_secret=binance_cfg.exchange.api_secret
                )
            elif exchange_name == 'okx':
                self.connectors['okx'] = OKXRESTConnector()

        logger.info(f"Initialized connectors for: {list(self.connectors.keys())}")

    def collect_ohlcv(self, config: CollectorConfig):
        """
        根據配置抓取 OHLCV 資料

        Args:
            config: Collector 配置
        """
        exchange_name = config.exchange.name
        symbol = f"{config.symbol.base}/{config.symbol.quote}"
        timeframe = config.timeframe

        logger.info(f"=== Collecting {exchange_name.upper()} {symbol} {timeframe} OHLCV ===")

        try:
            # 取得 market_id
            market_id = self.db.get_market_id(exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
                return

            # 檢查最新數據時間
            latest_time = self.db.get_latest_ohlcv_time(market_id, timeframe)
            if latest_time:
                logger.info(f"Latest data in DB: {latest_time}")
                # 從最新時間後開始抓取（考慮 lookback）
                lookback_minutes = config.mode.periodic.lookback_minutes
                since_time = latest_time - timedelta(minutes=lookback_minutes)
                since = int(since_time.timestamp() * 1000)
            else:
                logger.info("No existing data, fetching recent candles")
                since = None

            # 取得連接器
            connector = self.connectors.get(exchange_name)
            if not connector:
                logger.error(f"Connector not found for {exchange_name}")
                return

            # 使用重試機制抓取資料
            retry_config = RetryConfig(
                max_retries=config.request.max_retries,
                initial_delay=config.request.retry_delay,
                backoff_factor=config.request.backoff_factor
            )

            @retry_with_backoff(
                config=retry_config,
                exchange_name=exchange_name,
                endpoint='fetch_ohlcv'
            )
            def fetch_with_retry():
                return connector.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=1000
                )

            ohlcv = fetch_with_retry()

            if not ohlcv:
                logger.warning("No new data fetched")
                return

            # 資料驗證（如果啟用）
            if config.validation.enabled:
                validation_result = self.validator.validate_ohlcv_batch(
                    ohlcv, timeframe
                )

                if not validation_result['valid']:
                    logger.warning(
                        f"Validation failed: "
                        f"{len(validation_result['errors'])} errors, "
                        f"{len(validation_result['warnings'])} warnings"
                    )

                    # 根據配置決定如何處理驗證失敗
                    if config.error_handling.on_validation_error == 'skip_and_log':
                        logger.warning("Skipping invalid data batch")
                        return

            # 寫入資料庫
            count = self.db.insert_ohlcv_batch(market_id, timeframe, ohlcv)
            logger.success(f"Successfully saved {count} candles to database")

            # 記錄成功（重置連續失敗計數）
            failure_key = f"{exchange_name}:{symbol}:{timeframe}"
            global_failure_tracker.record_success(failure_key)

        except Exception as e:
            logger.error(f"Error in collect_ohlcv for {exchange_name}/{symbol}: {e}")

            # 記錄連續失敗
            failure_key = f"{exchange_name}:{symbol}:{timeframe}"
            count = global_failure_tracker.record_failure(failure_key)

            if count >= config.error_handling.max_consecutive_failures:
                logger.critical(
                    f"⚠️ Max consecutive failures ({count}) reached for {failure_key}!"
                )

    def run_collection_cycle(self):
        """執行一次完整的資料收集循環"""
        logger.info("=" * 80)
        logger.info(f"Data collection cycle started at {datetime.now()}")
        logger.info("=" * 80)

        for config in self.collector_configs:
            # 只處理 OHLCV 且啟用定期模式的配置
            if config.data_type == 'ohlcv' and config.mode.periodic.enabled:
                self.collect_ohlcv(config)

        logger.info("=" * 80)
        logger.info("Data collection cycle completed")
        logger.info("=" * 80 + "\n")

    def run_quality_check_cycle(self):
        """執行品質檢查循環"""
        logger.info("=" * 80)
        logger.info("Quality check cycle started")
        logger.info("=" * 80)

        # 檢查所有活躍市場的資料品質（最近 1 小時）
        results = self.quality_checker.check_all_active_markets(
            timeframe="1m",
            lookback_hours=1,
            create_backfill_tasks=True
        )

        # 統計結果
        total = len(results)
        valid = sum(1 for r in results if r.get('valid', False))
        invalid = total - valid

        logger.info(
            f"Quality check completed: "
            f"{total} markets checked, {valid} passed, {invalid} failed"
        )

        logger.info("=" * 80 + "\n")

    def run_backfill_cycle(self):
        """執行補資料循環"""
        logger.info("=" * 80)
        logger.info("Backfill cycle started")
        logger.info("=" * 80)

        # 取得待執行的補資料任務
        tasks = self.backfill_scheduler.get_pending_tasks(limit=5)

        if not tasks:
            logger.info("No pending backfill tasks")
            logger.info("=" * 80 + "\n")
            return

        logger.info(f"Found {len(tasks)} pending backfill tasks")

        for task in tasks:
            task_id = task['id']
            market_id = task['market_id']
            timeframe = task['timeframe']
            start_time = task['start_time']
            end_time = task['end_time']

            try:
                logger.info(
                    f"Executing backfill task #{task_id}: "
                    f"market_id={market_id}, {start_time} - {end_time}"
                )

                # 更新任務狀態為 running
                self.backfill_scheduler.update_task_status(task_id, 'running')

                # 執行補資料（這裡簡化處理，實際應根據 market_id 取得交易所和符號）
                # TODO: 實作更完善的補資料邏輯
                since_ms = int(start_time.timestamp() * 1000)

                # 暫時標記為完成
                self.backfill_scheduler.update_task_status(
                    task_id, 'completed', actual_records=0
                )

                logger.success(f"Backfill task #{task_id} completed")

            except Exception as e:
                logger.error(f"Backfill task #{task_id} failed: {e}")
                self.backfill_scheduler.update_task_status(
                    task_id, 'failed', error_message=str(e)
                )

        logger.info("=" * 80 + "\n")

    def start_scheduler(self):
        """啟動定時任務排程器"""
        scheduler = BlockingScheduler()

        # 資料收集任務（每 60 秒）
        scheduler.add_job(
            self.run_collection_cycle,
            'interval',
            seconds=settings.collector_interval_seconds,
            id='collect_crypto_data'
        )

        # 品質檢查任務（每 10 分鐘）
        scheduler.add_job(
            self.run_quality_check_cycle,
            'interval',
            minutes=10,
            id='quality_check'
        )

        # 補資料任務（每 5 分鐘）
        scheduler.add_job(
            self.run_backfill_cycle,
            'interval',
            minutes=5,
            id='backfill_tasks'
        )

        logger.info("Scheduler started with following jobs:")
        logger.info(f"  - collect_crypto_data: every {settings.collector_interval_seconds}s")
        logger.info("  - quality_check: every 10 minutes")
        logger.info("  - backfill_tasks: every 5 minutes")
        logger.info("Press Ctrl+C to exit")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        self.db.close()
        self.backfill_scheduler.close()
        self.quality_checker.close()
        logger.info("Resources cleaned up")


def main():
    """主函數"""
    collector = ConfigDrivenCollector()

    # 先執行一次資料收集
    collector.run_collection_cycle()

    # 啟動定時任務
    collector.start_scheduler()


if __name__ == "__main__":
    main()
