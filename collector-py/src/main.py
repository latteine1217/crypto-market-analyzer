"""
主程式：配置驅動的資料收集系統 (模組化重構版)
職責：
- 系統初始化
- 定時任務排程管理
"""
import sys
from pathlib import Path
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from config_loader import ConfigLoader
from loaders.db_loader import DatabaseLoader
from validators.data_validator import DataValidator
from metrics_exporter import start_metrics_server
from orchestrator import CollectorOrchestrator
from monitors.signal_monitor import SignalMonitor

# 導入任務模組
from tasks.ohlcv_tasks import collect_ohlcv_task
from tasks.derivative_tasks import run_funding_rate_task, run_open_interest_task
from tasks.external_tasks import (
    run_rich_list_task, 
    run_whale_task,
    run_events_task,
    run_fear_greed_task,
    run_etf_flows_task,
    run_etf_freshness_task
)
from tasks.maintenance_tasks import (
    run_quality_check_task, run_backfill_task, run_cvd_calibration_task
)

# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)

class ConfigDrivenCollector:
    def __init__(self):
        # 1. 初始化基礎設施
        metrics_port = int(settings.metrics_port) if hasattr(settings, 'metrics_port') else 8000
        self.metrics = start_metrics_server(port=metrics_port)
        self.db = DatabaseLoader()
        self.validator = DataValidator()
        
        # 2. 載入配置
        self.config_loader = ConfigLoader()
        self.configs = self.config_loader.load_all_collector_configs()
        
        # 3. 初始化資源協調器 (Resource Hub)
        self.orchestrator = CollectorOrchestrator(
            collector_configs=self.configs,
            db_loader=self.db,
            validator=self.validator,
            metrics=self.metrics
        )
        self.signal_monitor = SignalMonitor()
        logger.info("System initialized and ready.")

    def run_collection_cycle(self):
        """執行 OHLCV 收集循環"""
        for config in self.configs:
            if config.data_type == 'ohlcv' and config.mode.periodic.enabled:
                collect_ohlcv_task(self.orchestrator, config)

    def get_target_symbols(self):
        """從連接器獲取所有活躍的 USDT 線性合約"""
        try:
            bybit = self.orchestrator.connectors.get('bybit')
            if bybit:
                return bybit.get_markets()
        except Exception as e:
            logger.error(f"Failed to fetch dynamic symbols: {e}")
        return ['BTCUSDT', 'ETHUSDT']

    def start_scheduler(self):
        """啟動定時任務排程"""
        # 配置排程器，設定寬鬆的 misfire 容忍度
        job_defaults = {
            'coalesce': True,  # 將多個錯過的執行合併為一次
            'max_instances': 1,  # 同一任務同時只能有一個實例在執行
            'misfire_grace_time': 3600  # 錯過執行窗口後 1 小時內仍可執行
        }
        scheduler = BlockingScheduler(job_defaults=job_defaults)
        etf_tz = ZoneInfo("America/New_York") if ZoneInfo else None

        # 資料收集任務
        scheduler.add_job(self.run_collection_cycle, 'interval', seconds=settings.collector_interval_seconds, id='ohlcv_collect')
        scheduler.add_job(lambda: run_whale_task(self.orchestrator), 'interval', minutes=10, id='whale_collect')
        
        # 衍生品：每 5 分鐘抓取全市場數據（包含預測資金費率與 OI）
        scheduler.add_job(
            lambda: run_open_interest_task(self.orchestrator, self.get_target_symbols()), 
            'interval', minutes=5, id='oi_collect'
        )
        scheduler.add_job(
            lambda: run_funding_rate_task(self.orchestrator, self.get_target_symbols()), 
            'interval', minutes=5, id='funding_collect'
        )
        
        # 外部數據任務（增加更長的容忍時間）
        scheduler.add_job(
            lambda: run_rich_list_task(self.orchestrator), 
            'cron', hour=0, minute=15, 
            id='rich_list_collect',
            misfire_grace_time=7200  # Rich List: 2 小時容忍窗口
        )
        scheduler.add_job(lambda: run_events_task(self.orchestrator), 'cron', hour='*/6', minute=0, id='events_collect')  # 每 6 小時執行
        
        # Phase 1: Macro Indicators 任務
        scheduler.add_job(lambda: run_fear_greed_task(self.orchestrator), 'interval', hours=6, id='fear_greed_collect')  # 每 6 小時
        scheduler.add_job(
            lambda: run_etf_flows_task(self.orchestrator), 
            'cron', hour=17, minute=15, timezone=etf_tz,
            id='etf_flows_collect',
            misfire_grace_time=7200  # ETF: 2 小時容忍窗口
        )
        scheduler.add_job(
            lambda: run_etf_freshness_task(self.orchestrator),
            'interval', hours=1,
            id='etf_freshness_check'
        )
        
        # 維護任務
        scheduler.add_job(self.signal_monitor.scan, 'interval', minutes=5, id='signal_scan')
        scheduler.add_job(lambda: run_quality_check_task(self.orchestrator), 'interval', minutes=10, id='quality_check')
        scheduler.add_job(lambda: run_cvd_calibration_task(self.orchestrator), 'interval', minutes=15, id='cvd_calibration')
        scheduler.add_job(lambda: run_backfill_task(self.orchestrator), 'interval', minutes=5, id='backfill')

        logger.info(f"Scheduler started with {len(scheduler.get_jobs())} jobs.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.cleanup()

    def cleanup(self):
        self.metrics.set_running_status(False)
        self.db.close()
        logger.info("Cleanup completed.")

def main():
    collector = ConfigDrivenCollector()
    # 獲取初始市場清單
    symbols = collector.get_target_symbols()
    
    # 啟動前先執行一次關鍵任務
    collector.run_collection_cycle()
    run_whale_task(collector.orchestrator)
    run_open_interest_task(collector.orchestrator, symbols)
    run_funding_rate_task(collector.orchestrator, symbols)
    collector.signal_monitor.scan()
    
    collector.start_scheduler()

if __name__ == "__main__":
    main()
