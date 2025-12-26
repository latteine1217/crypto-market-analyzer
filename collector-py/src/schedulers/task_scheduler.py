"""
任務排程器
封裝 APScheduler，提供統一的任務排程介面
"""
from typing import Callable, Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger


class TaskScheduler:
    """
    任務排程器

    封裝 APScheduler，提供統一介面管理定時任務
    """

    def __init__(self, blocking: bool = True, timezone: str = 'UTC'):
        """
        初始化排程器

        Args:
            blocking: 是否使用阻塞式排程器
            timezone: 時區設定
        """
        if blocking:
            self.scheduler = BlockingScheduler(timezone=timezone)
        else:
            self.scheduler = BackgroundScheduler(timezone=timezone)

        logger.info(
            f"TaskScheduler initialized "
            f"(blocking={blocking}, timezone={timezone})"
        )

    def add_interval_job(
        self,
        func: Callable,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        job_id: Optional[str] = None,
        **kwargs
    ):
        """
        添加間隔執行任務

        Args:
            func: 要執行的函數
            seconds: 間隔秒數
            minutes: 間隔分鐘數
            hours: 間隔小時數
            job_id: 任務 ID
            **kwargs: 其他 APScheduler 參數
        """
        self.scheduler.add_job(
            func,
            'interval',
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            id=job_id,
            **kwargs
        )
        logger.info(f"Added interval job: {job_id or func.__name__}")

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,
        job_id: Optional[str] = None,
        **kwargs
    ):
        """
        添加 cron 任務

        Args:
            func: 要執行的函數
            cron_expression: cron 表達式（如 "*/5 * * * *"）
            job_id: 任務 ID
            **kwargs: 其他 APScheduler 參數
        """
        # 解析 cron 表達式
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError("Invalid cron expression")

        minute, hour, day, month, day_of_week = parts

        self.scheduler.add_job(
            func,
            'cron',
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id=job_id,
            **kwargs
        )
        logger.info(f"Added cron job: {job_id or func.__name__}")

    def start(self):
        """啟動排程器"""
        logger.info("Starting scheduler...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
            self.shutdown()

    def shutdown(self):
        """關閉排程器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shutdown")

    def get_jobs(self):
        """獲取所有任務"""
        return self.scheduler.get_jobs()
