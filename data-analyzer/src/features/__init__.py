"""
特徵工程模組

此模組負責從原始 OHLCV 資料計算各種特徵：
- 價格特徵：報酬率、價格變化、趨勢
- 技術指標：MA, EMA, RSI, MACD, Bollinger Bands
- 成交量特徵：成交量變化、成交量比率
- 波動率特徵：歷史波動率、ATR
"""

from .price_features import PriceFeatures
from .technical_indicators import TechnicalIndicators
from .volume_features import VolumeFeatures
from .volatility_features import VolatilityFeatures

__all__ = [
    'PriceFeatures',
    'TechnicalIndicators',
    'VolumeFeatures',
    'VolatilityFeatures',
]
