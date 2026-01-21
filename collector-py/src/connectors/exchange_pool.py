"""
CCXT Exchange 連接池 - 單例模式

職責：
- 為 Bybit 交易所維護唯一的 CCXT 實例
- 提供線程安全的實例獲取方法
- 避免重複載入市場資訊
- 大幅降低記憶體使用

使用方式：
    pool = ExchangePool()
    bybit = pool.get_exchange('bybit', api_key='xxx', api_secret='xxx')
"""
import ccxt
from typing import Dict, Optional
from threading import Lock
from loguru import logger


class ExchangePool:
    """
    CCXT Exchange 連接池（單例模式）
    
    設計原則：
    - 每個交易所僅建立一個 CCXT 實例
    - 所有 Collector 共享同一實例
    - 線程安全
    - 預先載入市場資訊，避免重複查詢
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """單例模式實作"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._exchanges = {}
                    cls._instance._init_lock = Lock()
                    logger.info("ExchangePool initialized (Singleton)")
        return cls._instance
    
    def get_exchange(
        self, 
        exchange_name: str, 
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        market_type: str = 'spot'
    ) -> ccxt.Exchange:
        """
        獲取或建立 CCXT Exchange 實例（共享實例）
        
        Args:
            exchange_name: 交易所名稱 (bybit)
            api_key: API Key (可選，公開數據不需要)
            api_secret: API Secret (可選)
            passphrase: Passphrase (可選)
            market_type: 市場類型 ('spot', 'future', 'swap')
            
        Returns:
            CCXT Exchange 實例（全局共享）
            
        Raises:
            ValueError: 不支援的交易所
        """
        if exchange_name.lower() != 'bybit':
            raise ValueError(f"Only 'bybit' is supported. Unsupported exchange: {exchange_name}")
        
        # 使用 exchange_name + market_type 作為 key，區分不同市場類型
        exchange_key = f"{exchange_name.lower()}_{market_type}"
        
        # 雙重檢查鎖定（Double-Checked Locking）
        if exchange_key not in self._exchanges:
            with self._init_lock:
                if exchange_key not in self._exchanges:
                    logger.info(f"Creating shared CCXT instance for {exchange_name} ({market_type})")
                    self._exchanges[exchange_key] = self._create_exchange(
                        exchange_name, api_key, api_secret, passphrase, market_type
                    )
                else:
                    logger.debug(f"Reusing existing CCXT instance for {exchange_name} ({market_type})")
        else:
            logger.debug(f"Reusing existing CCXT instance for {exchange_name} ({market_type})")
        
        return self._exchanges[exchange_key]
    
    def _create_exchange(
        self,
        exchange_name: str,
        api_key: Optional[str],
        api_secret: Optional[str],
        passphrase: Optional[str],
        market_type: str = 'spot'
    ) -> ccxt.Exchange:
        """
        建立 CCXT Exchange 實例
        
        Args:
            exchange_name: 交易所名稱
            api_key: API Key
            api_secret: API Secret
            passphrase: Passphrase (OKX)
            market_type: 市場類型 ('spot', 'future', 'swap')
            
        Returns:
            已初始化的 CCXT Exchange 實例
            
        Raises:
            ValueError: 不支援的交易所
        """
        # 基礎配置
        config = {
            'enableRateLimit': True,  # 啟用速率限制
            'timeout': 30000,         # 30 秒超時
            'options': {
                'defaultType': market_type  # 設定市場類型
            }
        }
        
        # 添加認證資訊（如果提供）
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret
            if passphrase:  # OKX 需要 passphrase
                config['password'] = passphrase
        
        # 交易所映射
        exchange_map = {
            'bybit': ccxt.bybit
        }
        
        if exchange_name not in exchange_map:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        # 建立實例
        exchange = exchange_map[exchange_name](config)
        
        # 預先載入市場資訊（只載入一次）
        try:
            exchange.load_markets()
            logger.info(
                f"Loaded {len(exchange.markets)} markets for {exchange_name} ({market_type}) "
                f"(Memory optimization: shared instance)"
            )
        except Exception as e:
            logger.warning(f"Failed to preload markets for {exchange_name} ({market_type}): {e}")
        
        return exchange
    
    def get_loaded_exchanges(self) -> Dict[str, ccxt.Exchange]:
        """
        取得所有已載入的交易所實例
        
        Returns:
            Dict[exchange_name, exchange_instance]
        """
        return self._exchanges.copy()
    
    def is_loaded(self, exchange_name: str) -> bool:
        """
        檢查交易所是否已載入
        
        Args:
            exchange_name: 交易所名稱
            
        Returns:
            True if loaded, False otherwise
        """
        return exchange_name.lower() in self._exchanges
    
    def get_stats(self) -> Dict[str, any]:
        """
        取得連接池統計資訊
        
        Returns:
            {
                'total_exchanges': int,
                'exchanges': List[str],
                'estimated_memory_saved': str  # 估計節省的記憶體
            }
        """
        num_exchanges = len(self._exchanges)
        
        # 估算記憶體節省
        # 假設每個 CCXT 實例約 60 MB
        estimated_old_usage = 3 * 60  # MB (假設原本有3個實例)
        estimated_new_usage = num_exchanges * 60  # MB
        estimated_saved = estimated_old_usage - estimated_new_usage
        
        return {
            'total_exchanges': num_exchanges,
            'exchanges': list(self._exchanges.keys()),
            'estimated_memory_saved_mb': estimated_saved,
            'optimization_ratio': f"{(estimated_saved / estimated_old_usage * 100):.1f}%"
        }


# ===========================
# 全局便捷函數
# ===========================

def get_shared_exchange(
    exchange_name: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    passphrase: Optional[str] = None,
    market_type: str = 'spot'
) -> ccxt.Exchange:
    """
    全局便捷函數：獲取共享的 CCXT Exchange 實例
    
    這是 ExchangePool().get_exchange() 的快捷方式
    
    Args:
        exchange_name: 交易所名稱
        api_key: API Key
        api_secret: API Secret
        passphrase: Passphrase (OKX)
        market_type: 市場類型 ('spot', 'future', 'swap')
        
    Returns:
        CCXT Exchange 實例（全局共享）
        
    Example:
        >>> bybit = get_shared_exchange('bybit', market_type='spot')
        >>> bybit_future = get_shared_exchange('bybit', market_type='linear')
    """
    return ExchangePool().get_exchange(exchange_name, api_key, api_secret, passphrase, market_type)
