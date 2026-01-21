"""
Liquidation Collector
收集各交易所的爆倉數據 (Liquidations)
"""
import os
import requests
from typing import List, Dict, Optional
from loguru import logger

from connectors.exchange_pool import ExchangePool
from loaders.db_loader import DatabaseLoader
from utils.symbol_utils import normalize_symbol

class LiquidationCollector:
    def __init__(self):
        self.pool = ExchangePool()
        self.loader = DatabaseLoader()
        self.session = requests.Session()
        
        # 偵測代理設定
        proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        if proxy:
            self.session.proxies = {'http': proxy, 'https': proxy}
            logger.info(f"LiquidationCollector using proxy: {proxy}")
            
        self.timeout = 15
        
    def _get_ccxt_symbol(self, exchange_name: str, symbol: str) -> str:
        """將通用 Symbol 轉換為交易所格式"""
        if exchange_name == 'bybit':
            return symbol.replace('/', '')
        return symbol

    def collect_bybit(self, symbol: str) -> List[Dict]:
        """
        Bybit V5 Liquidations
        REST 端點在某些地區不穩定，建議未來遷移至 WebSocket
        """
        target_symbol = self._get_ccxt_symbol('bybit', symbol)
        domains = ["https://api.bybit.com", "https://api.bytick.com"]
        
        for url_base in domains:
            url = f"{url_base}/v5/market/liquidation"
            params = {'category': 'linear', 'symbol': target_symbol, 'limit': 100}
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    liquidations = []
                    if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                        for item in data['result']['list']:
                            side = 'short' if item['side'] == 'Buy' else 'long'
                            qty = float(item['size'])
                            price = float(item['price'])
                            liquidations.append({
                                'time': int(item['time']),
                                'exchange': 'bybit',
                                'symbol': normalize_symbol(symbol),
                                'side': side,
                                'price': price,
                                'quantity': qty,
                                'value_usd': price * qty
                            })
                        return liquidations
            except Exception as e:
                logger.debug(f"[Bybit] Domain {url_base} failed: {e}")
                continue
        return []

    def run_collection(self, symbols: List[str] = ['BTC/USDT', 'ETH/USDT']):
        """
        執行收集任務
        """
        logger.info("Starting Liquidation Collection (Bybit only)...")
        all_data = []
        
        for symbol in symbols:
            # Bybit
            bybit_data = self.collect_bybit(symbol)
            if bybit_data:
                logger.info(f"Collected {len(bybit_data)} liquidations from Bybit for {symbol}")
                all_data.extend(bybit_data)
        
        # Insert to DB
        if all_data:
            count = self.loader.insert_liquidations_batch(all_data)
            logger.info(f"Inserted {count} total liquidation records.")
        else:
            logger.warning("No liquidation data collected.")

if __name__ == "__main__":
    collector = LiquidationCollector()
    collector.run_collection()