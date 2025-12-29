"""
資料保留策略監控排程器
定期執行資料保留策略監控檢查
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from typing import Dict, Any
import os

from monitors.retention_monitor import RetentionMonitor


class RetentionMonitorScheduler:
    """資料保留策略監控排程器"""
    
    def __init__(self, db_config: Dict[str, Any], check_interval_minutes: int = 30):
        """
        初始化排程器
        
        Args:
            db_config: 資料庫配置
            check_interval_minutes: 檢查間隔（分鐘）
        """
        self.db_config = db_config
        self.check_interval_minutes = check_interval_minutes
        self.scheduler = BackgroundScheduler(timezone='UTC')
        self.monitor = RetentionMonitor(db_config)
        
    def start(self):
        """啟動排程器"""
        try:
            # 添加定期檢查任務（每 N 分鐘執行一次）
            self.scheduler.add_job(
                func=self._run_check,
                trigger=IntervalTrigger(minutes=self.check_interval_minutes),
                id='retention_monitor_periodic',
                name='Retention Policy Monitor (Periodic)',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # 添加完整檢查任務（每小時執行一次）
            self.scheduler.add_job(
                func=self._run_full_check,
                trigger=CronTrigger(minute=5),  # 每小時的第5分鐘執行
                id='retention_monitor_hourly',
                name='Retention Policy Monitor (Hourly Full Check)',
                replace_existing=True,
                max_instances=1,
                coalesce=True
            )
            
            # 啟動排程器
            self.scheduler.start()
            logger.info(
                f"Retention monitor scheduler started "
                f"(check every {self.check_interval_minutes} minutes)"
            )
            
            # 立即執行一次檢查
            self._run_check()
            
        except Exception as e:
            logger.error(f"Failed to start retention monitor scheduler: {e}")
            raise
    
    def stop(self):
        """停止排程器"""
        try:
            self.scheduler.shutdown(wait=True)
            self.monitor.disconnect()
            logger.info("Retention monitor scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping retention monitor scheduler: {e}")
    
    def _run_check(self):
        """執行檢查（快速檢查）"""
        try:
            logger.info("Running retention policy check")
            self.monitor.check_all()
            logger.info("Retention policy check completed")
        except Exception as e:
            logger.error(f"Error during retention policy check: {e}", exc_info=True)
    
    def _run_full_check(self):
        """執行完整檢查（包含更詳細的分析）"""
        try:
            logger.info("Running full retention policy check")
            self.monitor.check_all()
            logger.info("Full retention policy check completed")
        except Exception as e:
            logger.error(f"Error during full retention policy check: {e}", exc_info=True)


def create_retention_monitor_scheduler(
    check_interval_minutes: int = 30
) -> RetentionMonitorScheduler:
    """
    創建資料保留監控排程器
    
    Args:
        check_interval_minutes: 檢查間隔（分鐘）
        
    Returns:
        RetentionMonitorScheduler 實例
    """
    # 從環境變數讀取資料庫配置
    # 支援多種環境變數名稱
    db_config = {
        'host': os.getenv('DB_HOST') or os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT') or os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('DB_NAME') or os.getenv('POSTGRES_DB', 'crypto_db'),
        'user': os.getenv('DB_USER') or os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('DB_PASSWORD') or os.getenv('POSTGRES_PASSWORD', '')
    }
    
    return RetentionMonitorScheduler(db_config, check_interval_minutes)
