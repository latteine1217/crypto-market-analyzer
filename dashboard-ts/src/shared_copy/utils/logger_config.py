"""
統一日誌配置模組

提供標準化的 JSON 格式日誌配置
- 日誌輪轉：每日或達到 500MB
- 保留期限：30 天
- 格式：JSON
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(
    service_name: str,
    log_dir: str = "logs",
    level: str = "INFO",
    rotation: str = "500 MB",
    retention: str = "30 days",
    json_format: bool = True
):
    """設定統一日誌配置

    Args:
        service_name: 服務名稱（如：collector, analyzer）
        log_dir: 日誌目錄
        level: 日誌等級
        rotation: 輪轉條件（"500 MB" 或 "1 day"）
        retention: 保留期限（"30 days"）
        json_format: 是否使用 JSON 格式
    """
    # 移除預設 handler
    logger.remove()

    # 確保日誌目錄存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # JSON 格式配置
    if json_format:
        log_format = (
            "{{\"timestamp\": \"{time:YYYY-MM-DD HH:mm:ss.SSS}\", "
            "\"level\": \"{level}\", "
            "\"service\": \"" + service_name + "\", "
            "\"module\": \"{name}\", "
            "\"function\": \"{function}\", "
            "\"line\": {line}, "
            "\"message\": \"{message}\"}}\n"
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 添加控制台 handler（人類可讀格式）
    logger.add(
        sys.stderr,
        format=log_format if not json_format else log_format,
        level=level,
        colorize=not json_format,
    )

    # 添加檔案 handler（JSON 格式，有輪轉）
    logger.add(
        log_path / f"{service_name}.log",
        format=log_format,
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",  # 壓縮舊日誌
        enqueue=True,  # 非同步寫入
        backtrace=True,  # 記錄完整 traceback
        diagnose=True,  # 記錄變數值
    )

    # 添加錯誤專用檔案 handler
    logger.add(
        log_path / f"{service_name}.error.log",
        format=log_format,
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"{service_name} 日誌系統初始化完成")
    logger.info(f"日誌目錄：{log_path.absolute()}")
    logger.info(f"日誌等級：{level}")
    logger.info(f"輪轉條件：{rotation}")
    logger.info(f"保留期限：{retention}")
    logger.info(f"JSON 格式：{json_format}")

    return logger


# 預設配置
def get_default_logger(service_name: str):
    """獲取預設配置的 logger

    Args:
        service_name: 服務名稱

    Returns:
        配置好的 logger
    """
    import os

    return setup_logger(
        service_name=service_name,
        log_dir=os.getenv("LOG_DIR", "logs"),
        level=os.getenv("LOG_LEVEL", "INFO"),
        rotation=os.getenv("LOG_ROTATION", "500 MB"),
        retention=os.getenv("LOG_RETENTION", "30 days"),
        json_format=os.getenv("LOG_JSON", "true").lower() == "true"
    )
