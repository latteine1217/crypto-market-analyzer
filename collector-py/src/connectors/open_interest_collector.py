"""
Open Interest (未平倉量) 收集器
支援從 Bybit 收集永續合約未平倉量

優化記憶體：使用 ExchangePool 共享 CCXT 實例
"""
import ccxt
from typing import Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

from utils.symbol_utils import to_ccxt_format, normalize_symbol
from connectors.exchange_pool import ExchangePool


class OpenInterestCollector:
    """
    未平倉量收集器
    
    記憶體優化：
    - 使用 ExchangePool 共享 CCXT 實例
    - 避免每個 Collector 重複建立實例
    - 預期減少 60-80 MB 記憶體使用
    """
    
    def __init__(self, exchange_name: str, api_key: str = None, api_secret: str = None):
        """
        初始化 Open Interest 收集器
        
        Args:
            exchange_name: 交易所名稱 (bybit)
            api_key: API Key (可選，讀取公開數據不需要)
            api_secret: API Secret (可選)
        """
        self.exchange_name = exchange_name.lower()
        
        # 根據交易所選擇正確的 market type
        # Bybit: linear
        market_type_map = {
            'bybit': 'linear'
        }
        self.market_type = market_type_map.get(self.exchange_name, 'linear')
        
        # ✅ 使用 ExchangePool 共享實例（記憶體優化）
        # 🔧 使用正確的 market type（未平倉量僅支援合約市場）
        self.exchange = ExchangePool().get_exchange(
            exchange_name=self.exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            market_type=self.market_type
        )
        
        logger.info(
            f"Initialized {self.exchange_name} open interest collector "
            f"(using shared CCXT instance)"
        )
    
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
            # 轉為 CCXT 永續合約格式（例如: BTC/USDT:USDT）
            ccxt_symbol = to_ccxt_format(symbol, market_type=self.market_type)
            
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
            ccxt_symbol = to_ccxt_format(symbol, market_type=self.market_type)
            
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
