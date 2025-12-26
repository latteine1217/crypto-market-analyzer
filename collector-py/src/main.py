"""
主程式：定期抓取多個交易所數據並存入資料庫
支援：Binance、OKX
支援多交易對：BTC/USDT、ETH/USDT、BTC/ETH
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from typing import Dict, List

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from connectors.binance_rest import BinanceRESTConnector
from connectors.okx_rest import OKXRESTConnector
from loaders.db_loader import DatabaseLoader


# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)


class MultiExchangeCollector:
    """多交易所加密市場數據收集器"""

    def __init__(self):
        """初始化收集器"""
        # 初始化資料庫連接
        self.db = DatabaseLoader()

        # 初始化各交易所連接器
        self.connectors = {
            'binance': BinanceRESTConnector(
                api_key=settings.binance_api_key,
                api_secret=settings.binance_api_secret
            ),
            'okx': OKXRESTConnector()
        }

        # 定義要收集的交易對（按交易所分組）
        self.collection_config = {
            'binance': {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'ETH/BTC'],
                'timeframes': ['1m'],
                'collect_trades': True,
                'collect_orderbook': True
            },
            'okx': {
                'symbols': ['BTC/USDT', 'ETH/USDT', 'ETH/BTC'],
                'timeframes': ['1m'],
                'collect_trades': True,
                'collect_orderbook': True
            }
        }

        logger.info("MultiExchangeCollector initialized")
        logger.info(f"Exchanges: {list(self.connectors.keys())}")
        logger.info(f"Total symbols to collect: {sum(len(cfg['symbols']) for cfg in self.collection_config.values())}")

    def collect_ohlcv(
        self,
        exchange_name: str,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 1000
    ):
        """
        抓取並儲存 OHLCV 數據

        Args:
            exchange_name: 交易所名稱
            symbol: 交易對
            timeframe: 時間週期
            limit: 抓取條數
        """
        try:
            logger.info(f"=== Collecting {exchange_name.upper()} {symbol} {timeframe} OHLCV ===")

            # 取得 market_id
            market_id = self.db.get_market_id(exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
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

            # 取得對應的連接器
            connector = self.connectors.get(exchange_name)
            if not connector:
                logger.error(f"Connector not found for {exchange_name}")
                return

            # 抓取數據
            ohlcv = connector.fetch_ohlcv(
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
            logger.error(f"Error in collect_ohlcv for {exchange_name}/{symbol}: {e}")

    def collect_trades(
        self,
        exchange_name: str,
        symbol: str,
        limit: int = 1000
    ):
        """
        抓取並儲存交易數據

        Args:
            exchange_name: 交易所名稱
            symbol: 交易對
            limit: 抓取條數
        """
        try:
            logger.info(f"=== Collecting {exchange_name.upper()} {symbol} Trades ===")

            # 取得 market_id
            market_id = self.db.get_market_id(exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
                return

            # 取得對應的連接器
            connector = self.connectors.get(exchange_name)
            if not connector:
                logger.error(f"Connector not found for {exchange_name}")
                return

            # 抓取最近的交易
            trades = connector.fetch_trades(symbol=symbol, limit=limit)

            if not trades:
                logger.warning("No trades fetched")
                return

            # 寫入資料庫
            count = self.db.insert_trades_batch(market_id, trades)
            logger.success(f"Successfully saved {count} trades to database")

        except Exception as e:
            logger.error(f"Error in collect_trades for {exchange_name}/{symbol}: {e}")

    def collect_orderbook(
        self,
        exchange_name: str,
        symbol: str,
        limit: int = 20
    ):
        """
        抓取並儲存訂單簿快照

        Args:
            exchange_name: 交易所名稱
            symbol: 交易對
            limit: 訂單簿深度（每邊的檔位數）
        """
        try:
            logger.info(f"=== Collecting {exchange_name.upper()} {symbol} Order Book ===")

            # 取得 market_id
            market_id = self.db.get_market_id(exchange_name, symbol)
            if not market_id:
                logger.error(f"Failed to get market_id for {exchange_name}/{symbol}")
                return

            # 取得對應的連接器
            connector = self.connectors.get(exchange_name)
            if not connector:
                logger.error(f"Connector not found for {exchange_name}")
                return

            # 抓取訂單簿
            orderbook = connector.fetch_order_book(symbol=symbol, limit=limit)

            if not orderbook:
                logger.warning("No orderbook data fetched")
                return

            # 準備數據格式
            orderbook_data = [{
                'timestamp': orderbook.get('timestamp', int(datetime.now().timestamp() * 1000)),
                'bids': orderbook['bids'],
                'asks': orderbook['asks']
            }]

            # 寫入資料庫
            count = self.db.insert_orderbook_batch(market_id, orderbook_data)
            logger.success(f"Successfully saved orderbook snapshot to database")

        except Exception as e:
            logger.error(f"Error in collect_orderbook for {exchange_name}/{symbol}: {e}")

    def run_once(self):
        """執行一次完整的數據收集"""
        logger.info("=" * 80)
        logger.info(f"Data collection started at {datetime.now()}")
        logger.info("=" * 80)

        # 遍歷每個交易所
        for exchange_name, config in self.collection_config.items():
            logger.info(f"\n>>> Processing {exchange_name.upper()} <<<")

            symbols = config['symbols']
            timeframes = config['timeframes']
            collect_trades = config.get('collect_trades', False)
            collect_orderbook = config.get('collect_orderbook', False)

            # 遍歷每個交易對
            for symbol in symbols:
                # 收集 OHLCV
                for timeframe in timeframes:
                    self.collect_ohlcv(exchange_name, symbol, timeframe)

                # 收集交易數據
                if collect_trades:
                    self.collect_trades(exchange_name, symbol)

                # 收集訂單簿快照
                if collect_orderbook:
                    self.collect_orderbook(exchange_name, symbol)

        logger.info("=" * 80)
        logger.info("Data collection completed")
        logger.info("=" * 80 + "\n")

    def start_scheduler(self):
        """啟動定時任務"""
        scheduler = BlockingScheduler()

        # 每 60 秒執行一次
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
    collector = MultiExchangeCollector()

    # 先執行一次
    collector.run_once()

    # 啟動定時任務
    collector.start_scheduler()


if __name__ == "__main__":
    main()
