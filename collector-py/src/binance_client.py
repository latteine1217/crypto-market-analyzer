"""
Binance數據抓取客戶端
使用ccxt庫統一交易所API介面
"""
import ccxt
from typing import List, Dict, Optional
from datetime import datetime, timezone
from loguru import logger

from config import settings


class BinanceClient:
    """Binance交易所數據抓取客戶端"""

    def __init__(self):
        """初始化Binance客戶端"""
        # 初始化ccxt交易所實例
        self.exchange = ccxt.binance({
            'apiKey': settings.binance_api_key or None,
            'secret': settings.binance_api_secret or None,
            'enableRateLimit': True,  # 啟用API速率限制保護
            'options': {
                'defaultType': 'spot',  # 現貨市場
            }
        })
        logger.info("Binance client initialized")

    def fetch_ohlcv(
        self,
        symbol: str = "BTC/USDT",
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: int = 1000
    ) -> List[List]:
        """
        抓取OHLCV K線數據

        Args:
            symbol: 交易對符號，例如 "BTC/USDT"
            timeframe: 時間週期 (1m, 5m, 15m, 1h, 4h, 1d)
            since: 起始時間戳（毫秒），None表示最近的數據
            limit: 返回條數，最大1000

        Returns:
            [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            logger.info(
                f"Fetched {len(ohlcv)} {timeframe} candles for {symbol}"
            )
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    def fetch_recent_trades(
        self,
        symbol: str = "BTC/USDT",
        since: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        抓取最近成交記錄

        Args:
            symbol: 交易對符號
            since: 起始時間戳（毫秒）
            limit: 返回條數

        Returns:
            List of trade dicts with keys: id, timestamp, price, amount, side, etc.
        """
        try:
            trades = self.exchange.fetch_trades(
                symbol=symbol,
                since=since,
                limit=limit
            )
            logger.info(f"Fetched {len(trades)} trades for {symbol}")
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}")
            raise

    def fetch_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 100
    ) -> Dict:
        """
        抓取訂單簿快照

        Args:
            symbol: 交易對符號
            limit: 深度層數（每邊的檔位數）

        Returns:
            {
                'bids': [[price, amount], ...],
                'asks': [[price, amount], ...],
                'timestamp': ...,
                'datetime': ...
            }
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=limit)
            logger.info(
                f"Fetched order book for {symbol}: "
                f"{len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks"
            )
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise

    def get_market_info(self, symbol: str = "BTC/USDT") -> Dict:
        """
        獲取市場基礎資訊

        Args:
            symbol: 交易對符號

        Returns:
            市場資訊字典
        """
        try:
            self.exchange.load_markets()
            market = self.exchange.market(symbol)
            return {
                'symbol': market['symbol'],
                'base': market['base'],
                'quote': market['quote'],
                'active': market['active'],
                'type': market['type'],
            }
        except Exception as e:
            logger.error(f"Error fetching market info for {symbol}: {e}")
            raise

    @staticmethod
    def timestamp_to_datetime(ts_ms: int) -> datetime:
        """
        將毫秒時間戳轉換為UTC datetime

        Args:
            ts_ms: 毫秒時間戳

        Returns:
            UTC datetime對象
        """
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
