"""
測試 Bybit 資料收集
執行一次完整的資料收集流程
"""
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.main import MultiExchangeCollector
from loguru import logger

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Bybit 資料收集測試")
    logger.info("=" * 80)

    # 建立收集器
    collector = MultiExchangeCollector()

    # 執行一次資料收集
    collector.run_once()

    # 清理資源
    collector.cleanup()

    logger.info("=" * 80)
    logger.info("✅ 測試完成！")
    logger.info("=" * 80)
