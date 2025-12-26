"""
MACD 交叉策略

策略邏輯：
1. 金叉（MACD 上穿 Signal）→ 買入 (LONG)
2. 死叉（MACD 下穿 Signal）→ 賣出 (SHORT/EXIT)
3. 可選：結合 MACD Histogram 的趨勢強度過濾
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from .strategy_base import StrategyBase, SignalType
import sys
from pathlib import Path

# 添加 features 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
from features.technical_indicators import TechnicalIndicators


class MACDStrategy(StrategyBase):
    """
    MACD 交叉策略

    參數：
        fast_period: 快線週期（預設 12）
        slow_period: 慢線週期（預設 26）
        signal_period: 信號線週期（預設 9）
        use_histogram_filter: 是否使用柱狀圖過濾（預設 False）
        histogram_threshold: 柱狀圖閾值（預設 0）
    """

    def __init__(
        self,
        name: str = "MACD_Cross",
        params: Optional[Dict] = None
    ):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'use_histogram_filter': False,
            'histogram_threshold': 0.0
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成 MACD 交易信號

        Args:
            data: 包含 OHLCV 的 DataFrame

        Returns:
            交易信號序列
        """
        # 確保資料已計算 MACD，若無則計算
        if 'macd' not in data.columns:
            data = TechnicalIndicators.calculate_macd(
                data,
                fast_period=self.params['fast_period'],
                slow_period=self.params['slow_period'],
                signal_period=self.params['signal_period']
            )

        # 初始化信號序列
        signals = pd.Series(SignalType.HOLD.value, index=data.index)

        # 計算交叉點
        # 金叉：MACD 從下方穿越 Signal（前一期 MACD < Signal，當期 MACD > Signal）
        macd = data['macd']
        signal = data['macd_signal']

        # 避免使用未來資訊：只用 shift(1) 比較前一期
        prev_macd = macd.shift(1)
        prev_signal = signal.shift(1)

        # 金叉條件（買入）
        golden_cross = (prev_macd < prev_signal) & (macd > signal)

        # 死叉條件（賣出）
        death_cross = (prev_macd > prev_signal) & (macd < signal)

        # 可選：使用柱狀圖過濾弱信號
        if self.params['use_histogram_filter']:
            histogram = data['macd_histogram']
            threshold = self.params['histogram_threshold']

            # 金叉時，柱狀圖需為正且大於閾值
            golden_cross = golden_cross & (histogram > threshold)

            # 死叉時，柱狀圖需為負且小於負閾值
            death_cross = death_cross & (histogram < -threshold)

        # 設定信號
        signals[golden_cross] = SignalType.LONG.value
        signals[death_cross] = SignalType.SHORT.value

        return signals

    def get_required_features(self) -> list:
        """獲取所需特徵"""
        return ['close', 'macd', 'macd_signal', 'macd_histogram']

    def validate_params(self) -> bool:
        """驗證參數有效性"""
        required_keys = ['fast_period', 'slow_period', 'signal_period']

        for key in required_keys:
            if key not in self.params:
                return False

            if not isinstance(self.params[key], int) or self.params[key] <= 0:
                return False

        # 快線週期必須小於慢線週期
        if self.params['fast_period'] >= self.params['slow_period']:
            return False

        return True


class MACDDivergenceStrategy(StrategyBase):
    """
    MACD 背離策略

    識別價格與 MACD 的背離：
    - 牛背離（Bullish Divergence）：價格創新低，但 MACD 未創新低 → 買入
    - 熊背離（Bearish Divergence）：價格創新高，但 MACD 未創新高 → 賣出
    """

    def __init__(
        self,
        name: str = "MACD_Divergence",
        params: Optional[Dict] = None
    ):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'lookback_period': 10,  # 檢查背離的回溯期
            'divergence_threshold': 0.01  # 背離閾值
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成 MACD 背離信號

        Args:
            data: 包含 OHLCV 的 DataFrame

        Returns:
            交易信號序列
        """
        # 確保資料已計算 MACD
        if 'macd' not in data.columns:
            data = TechnicalIndicators.calculate_macd(
                data,
                fast_period=self.params['fast_period'],
                slow_period=self.params['slow_period'],
                signal_period=self.params['signal_period']
            )

        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        lookback = self.params['lookback_period']
        threshold = self.params['divergence_threshold']

        # 需要足夠的歷史資料
        if len(data) < lookback + 1:
            return signals

        for i in range(lookback, len(data)):
            current_idx = data.index[i]
            window_data = data.iloc[i - lookback:i + 1]

            current_price = data['close'].iloc[i]
            current_macd = data['macd'].iloc[i]

            # 檢查牛背離（價格新低，MACD 未新低）
            price_low = window_data['close'].min()
            macd_low = window_data['macd'].min()

            if (current_price == price_low and
                current_macd > macd_low * (1 + threshold)):
                signals.iloc[i] = SignalType.LONG.value

            # 檢查熊背離（價格新高，MACD 未新高）
            price_high = window_data['close'].max()
            macd_high = window_data['macd'].max()

            if (current_price == price_high and
                current_macd < macd_high * (1 - threshold)):
                signals.iloc[i] = SignalType.SHORT.value

        return signals

    def get_required_features(self) -> list:
        return ['close', 'macd', 'macd_signal']
