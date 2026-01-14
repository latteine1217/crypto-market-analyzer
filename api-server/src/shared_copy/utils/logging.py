"""
統一日誌配置工具
提供全專案一致的日誌格式與設定
"""
import sys
from pathlib import Path
from loguru import logger
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
):
    """
    配置統一的日誌系統

    Args:
        log_level: 日誌級別 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日誌檔案路徑（可選）
        rotation: 檔案輪轉大小
        retention: 保留時間
    """
    # 移除預設 handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True
    )

    # File handler（如果指定）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            level=log_level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} - "
                "{message}"
            ),
            rotation=rotation,
            retention=retention,
            compression="zip"
        )

    logger.info(f"Logging configured (level={log_level})")


def get_logger(name: str):
    """
    獲取指定名稱的 logger

    Args:
        name: logger 名稱（通常是模組名）

    Returns:
        logger 實例
    """
    return logger.bind(name=name)
