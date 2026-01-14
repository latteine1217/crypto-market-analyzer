"""
Open Interest (未平倉量) 收集器
支援從 Binance, Bybit, OKX 收集永續合約未平倉量
"""
import ccxt
from typing import Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

from utils.symbol_utils import to_ccxt_format, normalize_symbol


class OpenInterestCollector:
    """未平倉量收集器"""
    
    def __init__(self, exchange_name: str, api_key: str = None, api_secret: str = None):
        """
        初始化 Open Interest 收集器
        
        Args:
            exchange_name: 交易所名稱 (binance/bybit/okx)
            api_key: API Key (可選，讀取公開數據不需要)
            api_secret: API Secret (可選)
        """
        self.exchange_name = exchange_name.lower()
        self.exchange = self._init_exchange(api_key, api_secret)
        
    def _init_exchange(self, api_key: Optional[str], api_secret: Optional[str]) -> ccxt.Exchange:
        """
        初始化 CCXT exchange 實例
        
        Args:
            api_key: API Key
            api_secret: API Secret
            
        Returns:
            CCXT Exchange 實例
        """
        config = {
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'future',  # 永續合約市場
            }
        }
        
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret
        
        if self.exchange_name == 'binance':
            exchange = ccxt.binance(config)
        elif self.exchange_name == 'bybit':
            exchange = ccxt.bybit(config)
        elif self.exchange_name == 'okx':
            exchange = ccxt.okx(config)
        else:
            raise ValueError(f"Unsupported exchange: {self.exchange_name}")
        
        logger.info(f"Initialized {self.exchange_name} open interest collector")
        return exchange
    
    def fetch_open_interest(self, symbol: str) -> Optional[Dict]:
        """
        抓取當前未平倉量
        
        Args:
            symbol: 交易對符號 (原生格式: BTCUSDT 或 CCXT格式: BTC/USDT)
            
        Returns:
            {
                'symbol': 'BTCUSDT',
                'open_interest': 123456.78,  # 基礎貨幣數量
                'open_interest_usd': 6172839000.0,  # USD 價值
                'timestamp': datetime,
                'price': 50000.0
            }
            
        Raises:
            Exception: 抓取失敗
        """
        try:
            # 轉為 CCXT 格式
            ccxt_symbol = to_ccxt_format(symbol)
            
            # 抓取未平倉量
            oi_data = self.exchange.fetch_open_interest(ccxt_symbol)
            
            # 解析結果
            result = {
                'symbol': normalize_symbol(symbol),
                'open_interest': oi_data.get('openInterestAmount'),  # 基礎貨幣數量
                'open_interest_usd': oi_data.get('openInterestValue'),  # USD 價值
                'timestamp': None,
                'price': None,
            }
            
            # 處理時間戳
            if oi_data.get('timestamp'):
                result['timestamp'] = datetime.fromtimestamp(
                    oi_data['timestamp'] / 1000,
                    tz=timezone.utc
                )
            else:
                result['timestamp'] = datetime.now(tz=timezone.utc)
            
            # 如果缺少 USD 價值或價格，嘗試從 ticker 獲取價格並計算
            if result['open_interest'] and (not result['open_interest_usd'] or not result['price']):
                try:
                    ticker = self.exchange.fetch_ticker(ccxt_symbol)
                    current_price = ticker.get('last')
                    
                    if current_price:
                        if not result['price']:
                            result['price'] = current_price
                        
                        if not result['open_interest_usd']:
                            result['open_interest_usd'] = result['open_interest'] * current_price
                            logger.debug(f"Calculated OI USD for {symbol}: {result['open_interest_usd']} (Price: {current_price})")
                except Exception as e:
                    logger.warning(f"Failed to fetch ticker for {symbol} to calculate OI USD: {e}")

            # 如果有價格資訊，使用它
            # 否則從 openInterestValue / openInterestAmount 計算
            if oi_data.get('price'):
                result['price'] = oi_data['price']
            elif result['open_interest'] and result['open_interest_usd'] and not result['price']:
                result['price'] = result['open_interest_usd'] / result['open_interest']
            
            logger.debug(
                f"Fetched open interest for {symbol}: "
                f"OI={result['open_interest']}, "
                f"USD={result['open_interest_usd']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
            raise
    
    def fetch_open_interest_history(
        self,
        symbol: str,
        timeframe: str = '5m',
        since: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        抓取歷史未平倉量
        
        Args:
            symbol: 交易對符號
            timeframe: 時間週期 ('5m', '15m', '1h', '4h', '1d')
            since: 起始時間戳 (milliseconds)
            limit: 最多返回幾筆 (預設100)
            
        Returns:
            List of open interest records
            
        Raises:
            Exception: 抓取失敗
        """
        try:
            ccxt_symbol = to_ccxt_format(symbol)
            
            # 檢查交易所是否支援歷史未平倉量
            if not self.exchange.has.get('fetchOpenInterestHistory'):
                logger.warning(
                    f"{self.exchange_name} does not support fetchOpenInterestHistory"
                )
                return []
            
            # 抓取歷史未平倉量
            history = self.exchange.fetch_open_interest_history(
                ccxt_symbol,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            # 解析結果
            results = []
            for record in history:
                item = {
                    'symbol': normalize_symbol(symbol),
                    'open_interest': record.get('openInterestAmount'),
                    'open_interest_usd': record.get('openInterestValue'),
                    'timestamp': None,
                    'price': None,
                }
                
                # 處理時間戳
                if record.get('timestamp'):
                    item['timestamp'] = datetime.fromtimestamp(
                        record['timestamp'] / 1000,
                        tz=timezone.utc
                    )
                
                # 計算價格
                if record.get('price'):
                    item['price'] = record['price']
                elif item['open_interest'] and item['open_interest_usd']:
                    item['price'] = item['open_interest_usd'] / item['open_interest']
                
                results.append(item)
            
            logger.info(
                f"Fetched {len(results)} historical open interest records for {symbol}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch open interest history for {symbol}: {e}")
            raise
    
    def fetch_open_interest_batch(self, symbols: List[str]) -> List[Dict]:
        """
        批次抓取多個交易對的未平倉量
        
        Args:
            symbols: 交易對列表
            
        Returns:
            List of open interest records
        """
        results = []
        for symbol in symbols:
            try:
                oi_data = self.fetch_open_interest(symbol)
                if oi_data:
                    results.append(oi_data)
            except Exception as e:
                logger.error(f"Failed to fetch open interest for {symbol}: {e}")
                continue
        
        logger.info(
            f"Batch fetched {len(results)}/{len(symbols)} open interest from {self.exchange_name}"
        )
        return results
    
    def calculate_oi_change(
        self,
        current_oi: float,
        previous_oi: float
    ) -> Dict[str, float]:
        """
        計算未平倉量變化
        
        Args:
            current_oi: 當前未平倉量
            previous_oi: 先前未平倉量 (例如24小時前)
            
        Returns:
            {
                'change': absolute_change,
                'change_pct': percentage_change
            }
        """
        change = current_oi - previous_oi
        change_pct = (change / previous_oi * 100) if previous_oi > 0 else 0
        
        return {
            'change': change,
            'change_pct': change_pct
        }
    
    def get_available_symbols(self) -> List[str]:
        """
        取得交易所支援的永續合約交易對
        
        Returns:
            List of available perpetual symbols
        """
        try:
            # 載入市場資訊
            self.exchange.load_markets()
            
            # 篩選永續合約
            perpetual_symbols = []
            for symbol, market in self.exchange.markets.items():
                # 檢查是否為永續合約
                if market.get('type') == 'swap' or market.get('linear') or market.get('inverse'):
                    # 只選擇 USDT 結算的合約
                    if market.get('quote') == 'USDT':
                        perpetual_symbols.append(normalize_symbol(symbol))
            
            logger.info(
                f"Found {len(perpetual_symbols)} USDT perpetual symbols on {self.exchange_name}"
            )
            
            return perpetual_symbols
            
        except Exception as e:
            logger.error(f"Failed to get available symbols: {e}")
            return []
