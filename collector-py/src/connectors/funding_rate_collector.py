"""
Funding Rate 收集器
支援從 Binance, Bybit, OKX 收集永續合約資金費率
"""
import ccxt
from typing import Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

from utils.symbol_utils import to_ccxt_format, normalize_symbol


class FundingRateCollector:
    """資金費率收集器"""
    
    def __init__(self, exchange_name: str, api_key: str = None, api_secret: str = None):
        """
        初始化 Funding Rate 收集器
        
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
        
        logger.info(f"Initialized {self.exchange_name} funding rate collector")
        return exchange
    
    def fetch_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        抓取當前資金費率
        
        Args:
            symbol: 交易對符號 (原生格式: BTCUSDT 或 CCXT格式: BTC/USDT)
            
        Returns:
            {
                'symbol': 'BTCUSDT',
                'funding_rate': 0.0001,
                'funding_rate_daily': 0.0003,
                'funding_time': datetime,
                'next_funding_time': datetime,
                'funding_interval': 28800,  # seconds
                'mark_price': 50000.0,
                'index_price': 49995.0
            }
            
        Raises:
            Exception: 抓取失敗
        """
        try:
            # 轉為 CCXT 格式
            ccxt_symbol = to_ccxt_format(symbol)
            
            # 抓取資金費率
            funding_data = self.exchange.fetch_funding_rate(ccxt_symbol)
            
            # 解析結果
            result = {
                'symbol': normalize_symbol(symbol),
                'funding_rate': funding_data.get('fundingRate'),
                'funding_time': None,
                'next_funding_time': None,
                'funding_interval': None,
                'mark_price': funding_data.get('markPrice'),
                'index_price': funding_data.get('indexPrice'),
            }
            
            # 處理時間戳
            if funding_data.get('fundingTimestamp'):
                result['funding_time'] = datetime.fromtimestamp(
                    funding_data['fundingTimestamp'] / 1000,
                    tz=timezone.utc
                )
            
            if funding_data.get('nextFundingTimestamp'):
                result['next_funding_time'] = datetime.fromtimestamp(
                    funding_data['nextFundingTimestamp'] / 1000,
                    tz=timezone.utc
                )
            
            # 計算 funding_interval (秒)
            if result['funding_time'] and result['next_funding_time']:
                result['funding_interval'] = int(
                    (result['next_funding_time'] - result['funding_time']).total_seconds()
                )
            
            # 計算每日資金費率 (假設一天3次結算)
            if result['funding_rate'] is not None:
                # 大多數交易所每8小時結算一次 (一天3次)
                result['funding_rate_daily'] = result['funding_rate'] * 3
            
            logger.debug(
                f"Fetched funding rate for {symbol}: "
                f"rate={result['funding_rate']}, "
                f"next_time={result['next_funding_time']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            raise
    
    def fetch_funding_rate_history(
        self,
        symbol: str,
        since: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        抓取歷史資金費率
        
        Args:
            symbol: 交易對符號
            since: 起始時間戳 (milliseconds)
            limit: 最多返回幾筆 (預設100)
            
        Returns:
            List of funding rate records
            
        Raises:
            Exception: 抓取失敗
        """
        try:
            ccxt_symbol = to_ccxt_format(symbol)
            
            # 檢查交易所是否支援歷史資金費率
            if not self.exchange.has['fetchFundingRateHistory']:
                logger.warning(
                    f"{self.exchange_name} does not support fetchFundingRateHistory"
                )
                return []
            
            # 抓取歷史資金費率
            history = self.exchange.fetch_funding_rate_history(
                ccxt_symbol,
                since=since,
                limit=limit
            )
            
            # 解析結果
            results = []
            for record in history:
                item = {
                    'symbol': normalize_symbol(symbol),
                    'funding_rate': record.get('fundingRate'),
                    'funding_time': None,
                    'mark_price': record.get('markPrice'),
                    'index_price': record.get('indexPrice'),
                }
                
                # 處理時間戳
                if record.get('timestamp'):
                    item['funding_time'] = datetime.fromtimestamp(
                        record['timestamp'] / 1000,
                        tz=timezone.utc
                    )
                
                # 計算每日資金費率
                if item['funding_rate'] is not None:
                    item['funding_rate_daily'] = item['funding_rate'] * 3
                
                results.append(item)
            
            logger.info(
                f"Fetched {len(results)} historical funding rates for {symbol}"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to fetch funding rate history for {symbol}: {e}")
            raise
    
    def fetch_funding_rates_batch(self, symbols: List[str]) -> List[Dict]:
        """
        批次抓取多個交易對的資金費率
        
        Args:
            symbols: 交易對列表
            
        Returns:
            List of funding rate records
        """
        results = []
        for symbol in symbols:
            try:
                funding_rate = self.fetch_funding_rate(symbol)
                if funding_rate:
                    results.append(funding_rate)
            except Exception as e:
                logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
                continue
        
        logger.info(
            f"Batch fetched {len(results)}/{len(symbols)} funding rates from {self.exchange_name}"
        )
        return results
    
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
