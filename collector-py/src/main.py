"""
主程式：配置驅動的資料收集系統 (模組化重構版)
職責：
- 系統初始化
- 定時任務排程管理
"""
import sys
import time
from datetime import datetime
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
from utils.symbol_utils import normalize_symbol

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
        # 用於避免同一分鐘重複觸發同一個 cron 配置
        self._last_run_by_config = {}
        logger.info("System initialized and ready.")

    def run_collection_cycle(self):
        """執行 OHLCV 收集循環"""
        now = datetime.now()
        current_bucket = now.strftime("%Y-%m-%d %H:%M")

        for config in self.configs:
            if config.data_type != 'ohlcv' or not config.mode.periodic.enabled:
                continue

            schedule = (config.mode.periodic.schedule or "").strip()
            if schedule and not self._cron_matches_now(schedule, now):
                continue

            if self._last_run_by_config.get(config.name) == current_bucket:
                continue

            collect_ohlcv_task(self.orchestrator, config)
            self._last_run_by_config[config.name] = current_bucket

    @staticmethod
    def _cron_matches_now(schedule: str, now: datetime) -> bool:
        """
        檢查 5 欄位 cron 是否匹配現在時間。
        支援 *, */n, a, a-b, a,b,c, a-b/n。
        """
        parts = schedule.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron schedule format: {schedule}, fallback to always run")
            return True

        minute, hour, day, month, day_of_week = parts
        cron_weekday = (now.weekday() + 1) % 7  # Python: Monday=0, Cron: Sunday=0

        return (
            ConfigDrivenCollector._cron_field_matches(minute, now.minute, 0, 59) and
            ConfigDrivenCollector._cron_field_matches(hour, now.hour, 0, 23) and
            ConfigDrivenCollector._cron_field_matches(day, now.day, 1, 31) and
            ConfigDrivenCollector._cron_field_matches(month, now.month, 1, 12) and
            ConfigDrivenCollector._cron_field_matches(day_of_week, cron_weekday, 0, 7, is_day_of_week=True)
        )

    @staticmethod
    def _cron_field_matches(
        field: str,
        value: int,
        min_value: int,
        max_value: int,
        is_day_of_week: bool = False
    ) -> bool:
        for token in field.split(','):
            token = token.strip()
            if not token:
                continue
            if ConfigDrivenCollector._cron_token_matches(
                token, value, min_value, max_value, is_day_of_week
            ):
                return True
        return False

    @staticmethod
    def _normalize_cron_number(num: int, is_day_of_week: bool) -> int:
        if is_day_of_week and num == 7:
            return 0
        return num

    @staticmethod
    def _cron_token_matches(
        token: str,
        value: int,
        min_value: int,
        max_value: int,
        is_day_of_week: bool
    ) -> bool:
        if token == '*':
            return True

        step = 1
        range_part = token
        if '/' in token:
            range_part, step_part = token.split('/', 1)
            try:
                step = int(step_part)
            except ValueError:
                return False
            if step <= 0:
                return False

        if range_part == '*':
            start, end = min_value, max_value
        elif '-' in range_part:
            start_s, end_s = range_part.split('-', 1)
            try:
                start = int(start_s)
                end = int(end_s)
            except ValueError:
                return False
        else:
            try:
                target = int(range_part)
            except ValueError:
                return False
            target = ConfigDrivenCollector._normalize_cron_number(target, is_day_of_week)
            return value == target

        start = ConfigDrivenCollector._normalize_cron_number(start, is_day_of_week)
        end = ConfigDrivenCollector._normalize_cron_number(end, is_day_of_week)

        if start < min_value or end > max_value:
            return False
        if start > end:
            return False
        if value < start or value > end:
            return False

        return ((value - start) % step) == 0

    def get_target_symbols(self):
        """從連接器獲取所有活躍的 USDT 線性合約"""
        try:
            bybit = self.orchestrator.connectors.get('bybit')
            if bybit:
                raw_symbols = bybit.get_markets()
                # 統一使用原生格式（BTCUSDT），避免跨模組 symbol 不一致
                normalized = [
                    normalize_symbol(s).split(':', 1)[0]
                    for s in raw_symbols
                ]
                return sorted(set(normalized))
        except Exception as e:
            logger.error(f"Failed to fetch dynamic symbols: {e}")
        return ['BTCUSDT', 'ETHUSDT']

    def _wrap_job(self, job_id: str, func):
        """統一封裝排程任務，記錄成功/失敗與延遲"""
        def runner():
            start = time.monotonic()
            status = 'success'
            try:
                func()
            except Exception as e:
                status = 'failed'
                logger.error(f"Scheduler job failed: {job_id}", e)
                raise
            finally:
                duration = time.monotonic() - start
                self.metrics.record_scheduler_job(
                    job_id=job_id,
                    status=status,
                    duration_seconds=duration,
                    timestamp=time.time()
                )
        return runner

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
        scheduler.add_job(self._wrap_job('ohlcv_collect', self.run_collection_cycle), 'interval', seconds=settings.collector_interval_seconds, id='ohlcv_collect')
        scheduler.add_job(self._wrap_job('whale_collect', lambda: run_whale_task(self.orchestrator)), 'interval', minutes=10, id='whale_collect')
        
        # 衍生品：每 5 分鐘抓取全市場數據（包含預測資金費率與 OI）
        scheduler.add_job(
            self._wrap_job('oi_collect', lambda: run_open_interest_task(self.orchestrator, self.get_target_symbols())),
            'interval', minutes=5, id='oi_collect'
        )
        scheduler.add_job(
            self._wrap_job('funding_collect', lambda: run_funding_rate_task(self.orchestrator, self.get_target_symbols())),
            'interval', minutes=5, id='funding_collect'
        )
        
        # 外部數據任務（增加更長的容忍時間）
        scheduler.add_job(
            self._wrap_job('rich_list_collect', lambda: run_rich_list_task(self.orchestrator)),
            'cron', hour=0, minute=15,
            id='rich_list_collect',
            misfire_grace_time=7200  # Rich List: 2 小時容忍窗口
        )
        scheduler.add_job(
            self._wrap_job('events_collect', lambda: run_events_task(self.orchestrator)),
            'cron', hour='*/6', minute=0, id='events_collect'
        )  # 每 6 小時執行
        
        # Phase 1: Macro Indicators 任務
        scheduler.add_job(
            self._wrap_job('fear_greed_collect', lambda: run_fear_greed_task(self.orchestrator)),
            'interval', hours=6, id='fear_greed_collect'
        )  # 每 6 小時
        scheduler.add_job(
            self._wrap_job('etf_flows_collect', lambda: run_etf_flows_task(self.orchestrator)),
            'cron',
            day_of_week='mon-fri',
            hour='17-23',
            minute=5,
            timezone=etf_tz,
            id='etf_flows_collect',
            misfire_grace_time=7200  # ETF: 2 小時容忍窗口
        )
        scheduler.add_job(
            self._wrap_job('etf_freshness_check', lambda: run_etf_freshness_task(self.orchestrator)),
            'interval', hours=1,
            id='etf_freshness_check'
        )
        
        # 維護任務
        scheduler.add_job(self._wrap_job('signal_scan', self.signal_monitor.scan), 'interval', minutes=5, id='signal_scan')
        scheduler.add_job(self._wrap_job('quality_check', lambda: run_quality_check_task(self.orchestrator)), 'interval', minutes=10, id='quality_check')
        scheduler.add_job(self._wrap_job('cvd_calibration', lambda: run_cvd_calibration_task(self.orchestrator)), 'interval', minutes=15, id='cvd_calibration')
        scheduler.add_job(self._wrap_job('backfill', lambda: run_backfill_task(self.orchestrator)), 'interval', minutes=5, id='backfill')

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
