"""
主程式：定期抓取Binance數據並存入資料庫
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler

# 添加src到Python路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from binance_client import BinanceClient
from loaders.db_loader import DatabaseLoader


# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)


class CryptoDataCollector:
    """加密市場數據收集器"""

    def __init__(self):
        """初始化收集器"""
        self.binance = BinanceClient()
        self.db = DatabaseLoader()
        self.exchange_name = "binance"
        logger.info("CryptoDataCollector initialized")

    def collect_ohlcv(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1m",
        limit: int = 1000
    ):
        """
        抓取並儲存OHLCV數據

        Args:
            symbol: 交易對
            timeframe: 時間週期
            limit: 抓取條數
        """
        try:
            logger.info(f"=== Collecting {symbol} {timeframe} OHLCV ===")

            # 取得market_id
            market_id = self.db.get_market_id(self.exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {symbol}")
                return

            # 檢查最新數據時間
            latest_time = self.db.get_latest_ohlcv_time(market_id, timeframe)
            if latest_time:
                logger.info(f"Latest data in DB: {latest_time}")
                # 從最新時間後開始抓取
                since = int((latest_time + timedelta(minutes=1)).timestamp() * 1000)
            else:
                logger.info("No existing data, fetching recent candles")
                since = None

            # 抓取數據
            ohlcv = self.binance.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )

            if not ohlcv:
                logger.warning("No new data fetched")
                return

            # 寫入資料庫
            count = self.db.insert_ohlcv_batch(market_id, timeframe, ohlcv)
            logger.success(f"Successfully saved {count} candles to database")

        except Exception as e:
            logger.error(f"Error in collect_ohlcv: {e}")

    def collect_trades(self, symbol: str = "BTC/USDT", limit: int = 1000):
        """
        抓取並儲存交易數據

        Args:
            symbol: 交易對
            limit: 抓取條數
        """
        try:
            logger.info(f"=== Collecting {symbol} Trades ===")

            market_id = self.db.get_market_id(self.exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {symbol}")
                return

            # 抓取最近的交易
            trades = self.binance.fetch_recent_trades(symbol=symbol, limit=limit)

            if not trades:
                logger.warning("No trades fetched")
                return

            # 寫入資料庫
            count = self.db.insert_trades_batch(market_id, trades)
            logger.success(f"Successfully saved {count} trades to database")

        except Exception as e:
            logger.error(f"Error in collect_trades: {e}")

    def run_once(self):
        """執行一次完整的數據收集"""
        logger.info("========================================")
        logger.info(f"Data collection started at {datetime.now()}")
        logger.info("========================================")

        # 收集OHLCV（可以添加多個交易對和時間週期）
        symbols = ["BTC/USDT"]
        timeframes = ["1m"]

        for symbol in symbols:
            for timeframe in timeframes:
                self.collect_ohlcv(symbol, timeframe)

            # 收集交易數據
            self.collect_trades(symbol)

        logger.info("========================================")
        logger.info("Data collection completed")
        logger.info("========================================\n")

    def start_scheduler(self):
        """啟動定時任務"""
        scheduler = BlockingScheduler()

        # 每60秒執行一次
        scheduler.add_job(
            self.run_once,
            'interval',
            seconds=settings.collector_interval_seconds,
            id='collect_crypto_data'
        )

        logger.info(
            f"Scheduler started. Running every {settings.collector_interval_seconds} seconds"
        )
        logger.info("Press Ctrl+C to exit")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        self.db.close()
        logger.info("Resources cleaned up")


def main():
    """主函數"""
    collector = CryptoDataCollector()

    # 先執行一次
    collector.run_once()

    # 啟動定時任務
    collector.start_scheduler()


if __name__ == "__main__":
    main()
