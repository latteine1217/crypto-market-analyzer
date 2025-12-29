#!/usr/bin/env python3
"""
資料保留策略監控服務啟動腳本
"""
import sys
import os
import signal
from pathlib import Path

# 添加專案根目錄到 Python path
project_root = Path(__file__).parent.parent
collector_src = project_root / 'collector-py' / 'src'
sys.path.insert(0, str(collector_src))

from loguru import logger
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 配置日誌
logger.remove()  # 移除預設 handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=os.getenv('LOG_LEVEL', 'INFO')
)
logger.add(
    project_root / "logs" / "retention_monitor.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
)

from metrics_exporter import start_metrics_server
from schedulers.retention_monitor_scheduler import create_retention_monitor_scheduler


def signal_handler(signum, frame):
    """處理終止訊號"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """主函數"""
    logger.info("=" * 60)
    logger.info("Starting Retention Policy Monitor Service")
    logger.info("=" * 60)
    
    try:
        # 啟動 Prometheus metrics server（使用獨立端口 8002）
        metrics_port = int(os.getenv('RETENTION_MONITOR_METRICS_PORT', 8002))
        metrics = start_metrics_server(port=metrics_port)
        logger.info(f"Metrics server started on port {metrics_port}")
        
        # 創建並啟動監控排程器
        check_interval = int(os.getenv('RETENTION_CHECK_INTERVAL_MINUTES', 30))
        scheduler = create_retention_monitor_scheduler(check_interval_minutes=check_interval)
        scheduler.start()
        
        # 註冊訊號處理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Retention monitor service is running. Press Ctrl+C to stop.")
        
        # 保持程式運行
        signal.pause()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Retention monitor service stopped")


if __name__ == '__main__':
    main()
