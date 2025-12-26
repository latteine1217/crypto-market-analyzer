"""
Binance REST API 連接器
職責：正確完整地從 Binance 取得資料，不做策略計算
"""
import ccxt
from typing import List, Dict, Optional
from datetime import datetime, timezone
from loguru import logger


class BinanceRESTConnector:
    """
    Binance 交易所 REST API 連接器

    規則：
    1. 只負責資料抓取，不做策略計算
    2. 所有請求必須有超時設定、重試機制、速率限制
    3. 對於缺失區段，只做標記，不填補虛假數據
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        timeout: int = 30,
        enable_rate_limit: bool = True
    ):
        """
        初始化 Binance REST 連接器

        Args:
            api_key: API 金鑰（可選，公開數據不需要）
            api_secret: API 密鑰（可選）
            timeout: 請求超時時間（秒）
            enable_rate_limit: 是否啟用速率限制保護
        """
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': enable_rate_limit,
            'timeout': timeout * 1000,  # ccxt 使用毫秒
            'options': {
                'defaultType': 'spot',
            }
        })
        logger.info("BinanceRESTConnector initialized")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: int = 1000
    ) -> List[List]:
        """
        抓取 OHLCV K 線數據

        Args:
            symbol: 交易對符號，例如 "BTC/USDT"
            timeframe: 時間週期 (1m, 5m, 15m, 1h, 4h, 1d)
            since: 起始時間戳（毫秒），None 表示最近的數據
            limit: 返回條數，最大 1000

        Returns:
            [[timestamp, open, high, low, close, volume], ...]

        Raises:
            Exception: API 請求失敗時拋出
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            logger.info(
                f"[Binance] Fetched {len(ohlcv)} {timeframe} candles "
                f"for {symbol}"
            )
            return ohlcv

        except ccxt.NetworkError as e:
            logger.error(f"[Binance] Network error fetching OHLCV: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"[Binance] Exchange error fetching OHLCV: {e}")
            raise
        except Exception as e:
            logger.error(f"[Binance] Unexpected error fetching OHLCV: {e}")
            raise

    def fetch_trades(
        self,
        symbol: str,
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

        Raises:
            Exception: API 請求失敗時拋出
        """
        try:
            trades = self.exchange.fetch_trades(
                symbol=symbol,
                since=since,
                limit=limit
            )
            logger.info(f"[Binance] Fetched {len(trades)} trades for {symbol}")
            return trades

        except Exception as e:
            logger.error(f"[Binance] Error fetching trades: {e}")
            raise

    def fetch_order_book(
        self,
        symbol: str,
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
                'datetime': ...,
                'nonce': ...
            }

        Raises:
            Exception: API 請求失敗時拋出
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=limit)
            logger.info(
                f"[Binance] Fetched order book for {symbol}: "
                f"{len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks"
            )
            return orderbook

        except Exception as e:
            logger.error(f"[Binance] Error fetching order book: {e}")
            raise

    def fetch_ticker(self, symbol: str) -> Dict:
        """
        抓取即時行情

        Args:
            symbol: 交易對符號

        Returns:
            Ticker 資訊字典

        Raises:
            Exception: API 請求失敗時拋出
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            logger.debug(f"[Binance] Fetched ticker for {symbol}")
            return ticker

        except Exception as e:
            logger.error(f"[Binance] Error fetching ticker: {e}")
            raise

    def get_market_info(self, symbol: str) -> Dict:
        """
        獲取市場基礎資訊

        Args:
            symbol: 交易對符號

        Returns:
            {
                'symbol': str,
                'base': str,
                'quote': str,
                'active': bool,
                'type': str,
                'spot': bool,
                'limits': {...},
                'precision': {...}
            }

        Raises:
            Exception: 獲取失敗時拋出
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
                'spot': market.get('spot', False),
                'limits': market.get('limits', {}),
                'precision': market.get('precision', {})
            }

        except Exception as e:
            logger.error(f"[Binance] Error fetching market info: {e}")
            raise

    @staticmethod
    def timestamp_to_datetime(ts_ms: int) -> datetime:
        """
        將毫秒時間戳轉換為 UTC datetime

        Args:
            ts_ms: 毫秒時間戳

        Returns:
            UTC datetime 對象
        """
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

    @staticmethod
    def datetime_to_timestamp(dt: datetime) -> int:
        """
        將 datetime 轉換為毫秒時間戳

        Args:
            dt: datetime 對象

        Returns:
            毫秒時間戳
        """
        return int(dt.timestamp() * 1000)
