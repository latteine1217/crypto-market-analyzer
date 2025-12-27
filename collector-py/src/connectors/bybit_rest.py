"""
Bybit REST API Connector
替代 Binance 的交易所連接器
"""
import ccxt
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class BybitClient:
    """Bybit REST API 客戶端"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        初始化 Bybit 客戶端

        Args:
            api_key: API Key（選用，僅讀取公開資料時不需要）
            api_secret: API Secret（選用）
        """
        config = {
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',  # 使用現貨市場
            }
        }

        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        self.exchange = ccxt.bybit(config)
        logger.info(f"Bybit 客戶端初始化成功 (Rate Limit: {self.exchange.rateLimit}ms)")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1m',
        since: Optional[int] = None,
        limit: int = 1000
    ) -> List[List]:
        """
        獲取 OHLCV K 線資料

        Args:
            symbol: 交易對 (例如: 'BTC/USDT')
            timeframe: 時間週期 ('1m', '5m', '15m', '1h', '4h', '1d')
            since: 起始時間戳（毫秒）
            limit: 返回筆數（最大 1000）

        Returns:
            OHLCV 資料列表 [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )

            # 檢查是否有數據
            if not ohlcv:
                logger.warning(f"⚠️ {symbol} {timeframe} 無可用數據")
                return []

            logger.debug(
                f"✓ 獲取 {symbol} {timeframe} K線: {len(ohlcv)} 條 "
                f"({datetime.fromtimestamp(ohlcv[0][0]/1000)} ~ "
                f"{datetime.fromtimestamp(ohlcv[-1][0]/1000)})"
            )

            return ohlcv

        except Exception as e:
            logger.error(f"❌ 獲取 OHLCV 失敗: {symbol} {timeframe} - {e}")
            raise

    def fetch_trades(
        self,
        symbol: str,
        since: Optional[int] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        獲取最近成交記錄

        Args:
            symbol: 交易對
            since: 起始時間戳（毫秒）
            limit: 返回筆數

        Returns:
            成交記錄列表
        """
        try:
            trades = self.exchange.fetch_trades(
                symbol=symbol,
                since=since,
                limit=limit
            )

            logger.debug(f"✓ 獲取 {symbol} 成交記錄: {len(trades)} 筆")
            return trades

        except Exception as e:
            logger.error(f"❌ 獲取成交記錄失敗: {symbol} - {e}")
            raise

    def fetch_order_book(
        self,
        symbol: str,
        limit: int = 100
    ) -> Dict:
        """
        獲取訂單簿

        Args:
            symbol: 交易對
            limit: 深度檔位數

        Returns:
            訂單簿資料 {'bids': [[price, amount], ...], 'asks': [...]}
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=limit)

            logger.debug(
                f"✓ 獲取 {symbol} 訂單簿: "
                f"買盤 {len(orderbook['bids'])} 檔, "
                f"賣盤 {len(orderbook['asks'])} 檔"
            )

            return orderbook

        except Exception as e:
            logger.error(f"❌ 獲取訂單簿失敗: {symbol} - {e}")
            raise

    def fetch_ticker(self, symbol: str) -> Dict:
        """
        獲取 24h ticker 資料

        Args:
            symbol: 交易對

        Returns:
            Ticker 資料
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            logger.debug(f"✓ 獲取 {symbol} ticker: ${ticker['last']:.2f}")
            return ticker

        except Exception as e:
            logger.error(f"❌ 獲取 ticker 失敗: {symbol} - {e}")
            raise

    def load_markets(self) -> Dict:
        """載入所有市場資訊"""
        try:
            markets = self.exchange.load_markets()
            logger.info(f"✓ 載入 {len(markets)} 個交易對")
            return markets

        except Exception as e:
            logger.error(f"❌ 載入市場資訊失敗: {e}")
            raise

    def get_exchange_name(self) -> str:
        """獲取交易所名稱"""
        return 'bybit'

    def get_markets(self) -> List[str]:
        """獲取所有 USDT 交易對"""
        try:
            markets = self.exchange.load_markets()

            # 過濾出現貨 USDT 交易對
            usdt_markets = [
                symbol for symbol in markets.keys()
                if symbol.endswith('/USDT') and markets[symbol].get('spot', False)
            ]

            logger.info(f"✓ 找到 {len(usdt_markets)} 個 USDT 現貨交易對")
            return sorted(usdt_markets)

        except Exception as e:
            logger.error(f"❌ 獲取市場列表失敗: {e}")
            raise


# 測試範例
if __name__ == "__main__":
    client = BybitClient()

    # 測試獲取 K 線
    print("\n測試獲取 BTC/USDT 1m K線...")
    ohlcv = client.fetch_ohlcv('BTC/USDT', '1m', limit=5)
    for candle in ohlcv:
        timestamp = datetime.fromtimestamp(candle[0] / 1000)
        print(f"{timestamp} | O:{candle[1]} H:{candle[2]} L:{candle[3]} C:{candle[4]} V:{candle[5]}")

    # 測試獲取 ticker
    print("\n測試獲取 ticker...")
    ticker = client.fetch_ticker('BTC/USDT')
    print(f"BTC/USDT: ${ticker['last']:,.2f}")
    print(f"24h 變化: {ticker['percentage']:.2f}%")

    # 測試獲取市場列表
    print("\n測試獲取市場列表...")
    markets = client.get_markets()
    print(f"前 10 個交易對: {markets[:10]}")
