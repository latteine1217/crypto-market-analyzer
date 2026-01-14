"""
Symbol 格式統一工具
處理不同交易所的 symbol 格式轉換
"""
from typing import Tuple


def parse_symbol(symbol: str) -> Tuple[str, str]:
    """
    解析 symbol 成 base 和 quote asset
    支援格式:
    - BTC/USDT  (CCXT 標準格式)
    - BTCUSDT   (交易所原生格式)
    
    Args:
        symbol: 交易對符號
        
    Returns:
        (base_asset, quote_asset)
        
    Raises:
        ValueError: 無法解析的 symbol 格式
    """
    # 移除可能的空白
    symbol = symbol.strip()
    
    # 格式 1: BTC/USDT (CCXT 標準)
    if '/' in symbol:
        parts = symbol.split('/')
        return parts[0], parts[1]
    
    # 格式 2: BTCUSDT (交易所原生)
    # 嘗試常見的 quote assets: USDT, USDC, USD, BUSD, BTC, ETH, BNB
    quote_assets = ['USDT', 'USDC', 'BUSD', 'USD', 'BTC', 'ETH', 'BNB', 'DAI', 'TUSD']
    
    for quote in quote_assets:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            if len(base) > 0:
                return base, quote
    
    # 無法解析，返回錯誤標記
    raise ValueError(
        f"Unable to parse symbol: {symbol}. "
        f"Supported formats: BTC/USDT or BTCUSDT"
    )


def normalize_symbol(symbol: str) -> str:
    """
    標準化 symbol 為交易所原生格式 (無斜線)
    BTC/USDT → BTCUSDT
    BTCUSDT → BTCUSDT
    
    Args:
        symbol: 交易對符號
        
    Returns:
        標準化後的 symbol (無斜線)
    """
    return symbol.replace('/', '')


def to_ccxt_format(symbol: str) -> str:
    """
    標準化 symbol 為 CCXT 格式 (有斜線)
    BTCUSDT → BTC/USDT
    BTC/USDT → BTC/USDT
    
    Args:
        symbol: 交易對符號
        
    Returns:
        標準化後的 symbol (CCXT 格式)
    """
    if '/' in symbol:
        return symbol
    
    base, quote = parse_symbol(symbol)
    return f"{base}/{quote}"


def is_valid_symbol(symbol: str) -> bool:
    """
    驗證 symbol 格式是否正確
    
    Args:
        symbol: 交易對符號
        
    Returns:
        是否為有效的 symbol
    """
    try:
        parse_symbol(symbol)
        return True
    except ValueError:
        return False
