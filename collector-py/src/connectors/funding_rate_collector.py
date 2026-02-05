"""
Funding Rate 收集器
支援從 Bybit 收集永續合約資金費率

優化記憶體：使用 ExchangePool 共享 CCXT 實例
"""
import ccxt
from typing import Dict, List, Optional
from datetime import datetime, timezone
from loguru import logger

from utils.symbol_utils import to_ccxt_format, normalize_symbol
from connectors.exchange_pool import ExchangePool


class FundingRateCollector:
    """
    資金費率收集器
    
    記憶體優化：
    - 使用 ExchangePool 共享 CCXT 實例
    - 避免每個 Collector 重複建立實例
    - 預期減少 60-80 MB 記憶體使用
    """
    
    def __init__(self, exchange_name: str, api_key: str = None, api_secret: str = None):
        """
        初始化 Funding Rate 收集器
        
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
        # 🔧 使用正確的 market type（資金費率僅支援合約市場）
        self.exchange = ExchangePool().get_exchange(
            exchange_name=self.exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            market_type=self.market_type
        )
        
        logger.info(
            f"Initialized {self.exchange_name} funding rate collector "
            f"(using shared CCXT instance)"
        )
    
    def fetch_funding_rate(self, symbol: str) -> Optional[Dict]:
        """
        抓取當前資金費率
        """
        try:
            # 轉為 CCXT 永續合約格式
            ccxt_symbol = to_ccxt_format(symbol, market_type=self.market_type)
            
            # Bybit V5 getTickers 其實包含了所有需要的資訊
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            info = ticker.get('info', {})
            
            # 解析結果
            result = {
                'symbol': normalize_symbol(symbol),
                'funding_rate': float(info.get('fundingRate', 0)) if info.get('fundingRate') else None,
                'predicted_funding_rate': float(info.get('predictedFundingRate', 0)) if info.get('predictedFundingRate') else None,
                'funding_time': datetime.now(tz=timezone.utc),  # 當前採集時間
                'next_funding_time': None,
                'funding_interval': None,
                'mark_price': float(ticker.get('markPrice')) if ticker.get('markPrice') else None,
                'index_price': float(ticker.get('last')) if ticker.get('last') else None,
            }
            
            # 處理下一次結算時間
            next_funding_time_ms = info.get('nextFundingTime')
            if next_funding_time_ms:
                result['next_funding_time'] = datetime.fromtimestamp(
                    int(next_funding_time_ms) / 1000,
                    tz=timezone.utc
                )
            
            # Bybit 預設通常是 8 小時，但我們可以從 API 獲取更準確的資訊（如果有的話）
            # 這裡計算每日費率：Bybit V5 預設 interval 可以在某些 endpoint 查到，
            # 若無則根據 next_funding_time 推算
            result['funding_rate_daily'] = (result['funding_rate'] * 3) if result['funding_rate'] is not None else 0
            
            logger.debug(f"Fetched funding rate for {symbol}: {result['funding_rate']}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            raise

    def fetch_funding_rates_batch(self, symbols: List[str]) -> List[Dict]:
        """
        精準批次抓取 (Bybit V5 優化版)
        """
        if self.exchange_name != 'bybit':
            # 非 Bybit 交易所維持原有的循環模式
            return self._fetch_funding_rates_sequential(symbols)

        try:
            # Bybit V5: fetch_tickers('linear') 可以一次拿到所有合約數據
            # 這是最省 Rate Limit 的做法
            tickers = self.exchange.fetch_tickers(params={'category': 'linear'})
            
            results = []
            normalized_targets = [normalize_symbol(s) for s in symbols]
            
            for symbol_key, ticker in tickers.items():
                norm_symbol = normalize_symbol(symbol_key)
                if norm_symbol in normalized_targets:
                    info = ticker.get('info', {})
                    funding_rate = float(info.get('fundingRate', 0)) if info.get('fundingRate') else None
                    
                    # Bybit V5: ticker['info'] contains accurate markPrice and indexPrice
                    mark_price = float(info.get('markPrice')) if info.get('markPrice') else float(ticker.get('last', 0))
                    index_price = float(info.get('indexPrice')) if info.get('indexPrice') else float(ticker.get('last', 0))

                    res = {
                        'symbol': norm_symbol,
                        'funding_time': datetime.now(tz=timezone.utc),  # 當前採集時間
                        'funding_rate': funding_rate,
                        'predicted_funding_rate': float(info.get('predictedFundingRate', 0)) if info.get('predictedFundingRate') else None,
                        'funding_rate_daily': (funding_rate * 3) if funding_rate is not None else 0,
                        'next_funding_time': None,
                        'mark_price': mark_price,
                        'index_price': index_price
                    }
                    
                    next_time = info.get('nextFundingTime')
                    if next_time:
                        res['next_funding_time'] = datetime.fromtimestamp(int(next_time)/1000, tz=timezone.utc)
                    
                    results.append(res)
            
            logger.info(f"Batch fetched {len(results)} funding rates from Bybit V5 Tickers")
            return results
        except Exception as e:
            logger.error(f"Bybit batch fetch failed: {e}. Falling back to sequential.")
            return self._fetch_funding_rates_sequential(symbols)

    def fetch_funding_rate_history(
        self,
        symbol: str,
        since: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        抓取歷史資金費率
        """
        try:
            ccxt_symbol = to_ccxt_format(symbol, market_type=self.market_type)
            
            # 檢查交易所是否支援歷史資金費率
            if not self.exchange.has['fetchFundingRateHistory']:
                logger.warning(f"{self.exchange_name} does not support fetchFundingRateHistory")
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
                
                # 計算每日資金費率 (這部分可再優化，目前維持固定 x3)
                if item['funding_rate'] is not None:
                    item['funding_rate_daily'] = item['funding_rate'] * 3
                
                results.append(item)
            
            logger.info(f"Fetched {len(results)} historical funding rates for {symbol}")
            return results
        except Exception as e:
            logger.error(f"Failed to fetch funding rate history for {symbol}: {e}")
            raise

    def _fetch_funding_rates_sequential(self, symbols: List[str]) -> List[Dict]:
        """原有的循環抓取邏輯作為備援"""
        results = []
        for symbol in symbols:
            try:
                data = self.fetch_funding_rate(symbol)
                if data: results.append(data)
            except: continue
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
