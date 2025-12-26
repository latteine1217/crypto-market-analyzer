"""
RSI 反轉策略

職責：
- 使用 RSI 指標判斷超買超賣
- 在超賣時買入，超買時賣出
"""
import pandas as pd
from typing import Optional
from loguru import logger

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting.strategy import StrategyBase, Signal


class RSIStrategy(StrategyBase):
    """RSI 反轉策略"""

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        **params
    ):
        """
        初始化 RSI 策略

        Args:
            rsi_period: RSI 週期
            oversold_threshold: 超賣閾值
            overbought_threshold: 超買閾值
        """
        super().__init__(
            name="RSI_Reversal",
            rsi_period=rsi_period,
            oversold_threshold=oversold_threshold,
            overbought_threshold=overbought_threshold,
            **params
        )
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold

    def initialize(self):
        """初始化"""
        logger.info(
            f"RSI 策略初始化：週期 {self.rsi_period}, "
            f"超賣 < {self.oversold_threshold}, "
            f"超買 > {self.overbought_threshold}"
        )

    def on_data(
        self,
        timestamp: pd.Timestamp,
        data: pd.Series,
        features: Optional[pd.Series] = None
    ) -> Optional[Signal]:
        """
        RSI 策略邏輯：
        - RSI < oversold_threshold：買入
        - RSI > overbought_threshold：賣出
        """
        if features is None:
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='hold',
                reason="無特徵資料"
            )

        # 取得 RSI
        rsi_key = f'rsi_{self.rsi_period}'
        if rsi_key not in features:
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='hold',
                reason=f"無 {rsi_key} 資料"
            )

        rsi = features[rsi_key]

        if pd.isna(rsi):
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='hold',
                reason="RSI 為 NaN"
            )

        # 超賣：買入
        if rsi < self.oversold_threshold and self.current_position <= 0:
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='buy',
                confidence=min((self.oversold_threshold - rsi) / self.oversold_threshold, 1.0),
                reason=f"RSI 超賣 ({rsi:.2f} < {self.oversold_threshold})"
            )

        # 超買：賣出
        if rsi > self.overbought_threshold and self.current_position > 0:
            return Signal(
                timestamp=timestamp,
                symbol=data.get('symbol', 'UNKNOWN'),
                action='sell',
                confidence=min((rsi - self.overbought_threshold) / (100 - self.overbought_threshold), 1.0),
                reason=f"RSI 超買 ({rsi:.2f} > {self.overbought_threshold})"
            )

        # 持有
        return Signal(
            timestamp=timestamp,
            symbol=data.get('symbol', 'UNKNOWN'),
            action='hold',
            reason=f"RSI 中性 ({rsi:.2f})"
        )

    def finalize(self):
        """結束"""
        logger.info(f"RSI 策略完成，共產生 {len(self.signals_history)} 個信號")
