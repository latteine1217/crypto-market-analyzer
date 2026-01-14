"""
主程式 V3：配置驅動的資料收集系統（重構版）
重構策略：
- CollectorOrchestrator: 負責資料收集協調
- ConfigDrivenCollector: 負責系統初始化、排程、監控
遵循單一職責原則，降低複雜度
"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from config_loader import ConfigLoader
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from schedulers.backfill_scheduler import BackfillScheduler
from quality_checker import DataQualityChecker
from metrics_exporter import start_metrics_server
from monitors.retention_monitor import RetentionMonitor
from orchestrator import CollectorOrchestrator


# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)


class ConfigDrivenCollector:
    """
    配置驅動的資料收集器（重構版）
    
    職責：
    - 系統初始化（資料庫、Metrics、配置載入）
    - 任務排程管理
    - 品質檢查與補資料協調
    - 系統監控與清理
    """

    def __init__(self):
        """初始化收集器"""
        # 啟動 Prometheus Metrics Server
        metrics_port = int(settings.metrics_port) if hasattr(settings, 'metrics_port') else 8000
        self.metrics = start_metrics_server(port=metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")

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

        # 初始化 Retention Monitor
        db_config = {
            'host': settings.postgres_host,
            'port': settings.postgres_port,
            'database': settings.postgres_db,
            'user': settings.postgres_user,
            'password': settings.postgres_password
        }
        self.retention_monitor = RetentionMonitor(db_config, metrics=self.metrics)

        # 初始化 CollectorOrchestrator（負責資料收集）
        self.orchestrator = CollectorOrchestrator(
            collector_configs=self.collector_configs,
            db_loader=self.db,
            validator=self.validator,
            metrics=self.metrics
        )

        logger.info(f"ConfigDrivenCollector initialized with {len(self.collector_configs)} configs")

    def run_collection_cycle(self):
        """執行資料收集循環（委託給 orchestrator）"""
        self.orchestrator.run_collection_cycle()

    def run_funding_rate_collection(self):
        """執行資金費率收集（委託給 orchestrator）"""
        self.orchestrator.run_funding_rate_collection()

    def run_open_interest_collection(self):
        """執行未平倉合約收集（委託給 orchestrator）"""
        self.orchestrator.run_open_interest_collection()

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

        # 更新品質 metrics
        for result in results:
            if 'exchange' in result and 'symbol' in result:
                score = result.get('score', 0)
                missing_rate = result.get('missing_rate', 0)
                timeframe = result.get('timeframe', '1m')

                self.metrics.update_data_quality(
                    exchange=result['exchange'],
                    symbol=result['symbol'],
                    timeframe=timeframe,
                    score=score,
                    missing_rate=missing_rate
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

        # 更新待處理任務數
        self.metrics.update_backfill_stats(pending=len(tasks) if tasks else 0)

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

                # 從資料庫取得 market 資訊
                market_info = self.db.get_market_info(market_id)
                if not market_info:
                    raise ValueError(f"Market ID {market_id} not found")
                
                exchange_name = market_info['exchange']
                symbol = market_info['symbol']

                # 找到對應的配置
                config = next(
                    (cfg for cfg in self.collector_configs 
                     if cfg.exchange.name == exchange_name),
                    None
                )
                
                if not config:
                    raise ValueError(f"No config found for exchange {exchange_name}")

                # 取得連接器
                connector = self.orchestrator.connectors.get(exchange_name)
                if not connector:
                    raise ValueError(f"Connector not found for {exchange_name}")

                # 執行補資料
                since = int(start_time.timestamp() * 1000)
                until = int(end_time.timestamp() * 1000)
                
                all_data = []
                current_since = since
                
                while current_since < until:
                    ohlcv = connector.fetch_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                        since=current_since,
                        limit=1000
                    )
                    
                    if not ohlcv:
                        break
                    
                    all_data.extend(ohlcv)
                    
                    # 更新起始時間為最後一筆資料的時間
                    last_ts = ohlcv[-1][0]
                    if last_ts <= current_since:
                        break
                    current_since = last_ts + 1

                # 寫入資料庫
                if all_data:
                    inserted_count = self.db.insert_ohlcv_batch(
                        market_id=market_id,
                        timeframe=timeframe,
                        ohlcv_data=all_data
                    )
                    
                    logger.info(f"Backfill completed: inserted {inserted_count} candles")
                    
                    # 更新任務狀態為 completed
                    self.backfill_scheduler.update_task_status(task_id, 'completed')
                    self.metrics.update_backfill_stats(completed=1)
                else:
                    logger.warning("No data fetched for backfill task")
                    self.backfill_scheduler.update_task_status(task_id, 'failed')
                    self.metrics.update_backfill_stats(failed=1)

            except Exception as e:
                logger.error(f"Backfill task #{task_id} failed: {e}")
                self.backfill_scheduler.update_task_status(task_id, 'failed')
                self.metrics.update_backfill_stats(failed=1)

        logger.info("=" * 80 + "\n")

    def run_retention_check_cycle(self):
        """執行資料保留策略檢查"""
        logger.info("=== Starting Retention Check Cycle ===")
        
        try:
            report = self.retention_monitor.check_retention_policy()
            
            if report.get('actions_taken'):
                logger.info(f"Retention policy applied: {report['actions_taken']} rows affected")
            else:
                logger.info("No retention actions needed")
        
        except Exception as e:
            logger.error(f"Retention check failed: {e}")
        
        logger.info("=== Retention Check Cycle Completed ===")

    def monitor_db_connections(self):
        """監控資料庫連接狀況"""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    # 查詢資料庫連接池狀況
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE state = 'active') as active,
                            COUNT(*) FILTER (WHERE state = 'idle') as idle,
                            COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                    """)
                    result = cur.fetchone()
                    
                    if result:
                        total, active, idle, idle_in_transaction = result
                        usage_rate = (active / total * 100) if total > 0 else 0
                        
                        logger.info(
                            f"DB pool status: {total} total ({active} active, {idle} idle, "
                            f"{idle_in_transaction} idle_in_transaction), usage: {usage_rate:.1f}%"
                        )
        except Exception as e:
            logger.error(f"DB connection monitoring failed: {e}")

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

        # 資料庫連接監控與清理（每 15 分鐘）
        scheduler.add_job(
            self.monitor_db_connections,
            'interval',
            minutes=15,
            id='db_connection_monitor'
        )

        # 資料保留策略監控（每 5 分鐘）
        scheduler.add_job(
            self.run_retention_check_cycle,
            'interval',
            minutes=5,
            id='retention_policy_check'
        )

        # 資金費率收集（每 8 小時，與交易所結算時間對齊：00:00, 08:00, 16:00 UTC）
        scheduler.add_job(
            self.run_funding_rate_collection,
            'cron',
            hour='0,8,16',
            minute=5,
            id='funding_rate_collection'
        )

        # 未平倉量收集（每 5 分鐘）
        scheduler.add_job(
            self.run_open_interest_collection,
            'interval',
            minutes=5,
            id='open_interest_collection'
        )

        logger.info("Scheduler started with following jobs:")
        logger.info(f"  - collect_crypto_data: every {settings.collector_interval_seconds}s")
        logger.info("  - quality_check: every 10 minutes")
        logger.info("  - backfill_tasks: every 5 minutes")
        logger.info("  - db_connection_monitor: every 15 minutes")
        logger.info("  - retention_policy_check: every 5 minutes")
        logger.info("  - funding_rate_collection: at 00:05, 08:05, 16:05 UTC")
        logger.info("  - open_interest_collection: every 5 minutes")
        logger.info("Press Ctrl+C to exit")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        # 設定停止狀態
        self.metrics.set_running_status(False)

        self.db.close()
        self.backfill_scheduler.close()
        self.quality_checker.close()
        self.retention_monitor.disconnect()
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
