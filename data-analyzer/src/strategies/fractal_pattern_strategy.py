"""
威廉分形與頭肩形態策略

策略邏輯：
1. 威廉分形突破策略：
   - 價格突破上分形（阻力位）→ 買入
   - 價格跌破下分形（支撐位）→ 賣出

2. 頭肩頂/頭肩底形態策略：
   - 識別到頭肩頂完成 → 賣出
   - 識別到頭肩底完成 → 買入
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict
from .strategy_base import StrategyBase, SignalType
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from features.technical_indicators import TechnicalIndicators


class FractalBreakoutStrategy(StrategyBase):
    """
    威廉分形突破策略

    當價格突破最近的分形點時產生信號：
    - 突破上分形（最近的阻力） → 做多
    - 跌破下分形（最近的支撐） → 做空
    """

    def __init__(
        self,
        name: str = "Fractal_Breakout",
        params: Optional[Dict] = None
    ):
        default_params = {
            'fractal_period': 2,  # 威廉分形週期
            'lookback_fractals': 3,  # 回溯幾個分形點
            'breakout_threshold': 0.001  # 突破閾值（0.1%）
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成分形突破信號

        Args:
            data: 包含 OHLCV 的 DataFrame

        Returns:
            交易信號序列
        """
        # 確保已計算分形
        if 'fractal_up' not in data.columns:
            data = TechnicalIndicators.identify_williams_fractal(
                data,
                period=self.params['fractal_period']
            )

        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        threshold = self.params['breakout_threshold']
        lookback = self.params['lookback_fractals']

        # 找出所有分形點
        up_fractals_idx = data[data['fractal_up']].index.tolist()
        down_fractals_idx = data[data['fractal_down']].index.tolist()

        for i in range(len(data)):
            current_idx = data.index[i]
            current_high = data['high'].iloc[i]
            current_low = data['low'].iloc[i]
            current_close = data['close'].iloc[i]

            # 找最近的上分形（阻力位）
            recent_up_fractals = [
                idx for idx in up_fractals_idx
                if idx < current_idx
            ][-lookback:] if up_fractals_idx else []

            if recent_up_fractals:
                # 取最高的上分形作為阻力
                resistance_level = data.loc[recent_up_fractals, 'high'].max()

                # 突破阻力 → 買入
                if current_close > resistance_level * (1 + threshold):
                    signals.iloc[i] = SignalType.LONG.value

            # 找最近的下分形（支撐位）
            recent_down_fractals = [
                idx for idx in down_fractals_idx
                if idx < current_idx
            ][-lookback:] if down_fractals_idx else []

            if recent_down_fractals:
                # 取最低的下分形作為支撐
                support_level = data.loc[recent_down_fractals, 'low'].min()

                # 跌破支撐 → 賣出
                if current_close < support_level * (1 - threshold):
                    signals.iloc[i] = SignalType.SHORT.value

        return signals

    def get_required_features(self) -> list:
        return ['high', 'low', 'close', 'fractal_up', 'fractal_down']


class HeadShouldersStrategy(StrategyBase):
    """
    頭肩頂/頭肩底形態策略

    識別頭肩形態完成後產生信號：
    - 頭肩頂完成 → 看跌，做空
    - 頭肩底完成 → 看漲，做多
    """

    def __init__(
        self,
        name: str = "Head_Shoulders",
        params: Optional[Dict] = None
    ):
        default_params = {
            'fractal_period': 2,
            'tolerance': 0.02,  # 左右肩容忍度（2%）
            'neckline_break_threshold': 0.005,  # 頸線突破閾值（0.5%）
            'confirm_bars': 2  # 確認K線數
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成頭肩形態信號

        Args:
            data: 包含 OHLCV 的 DataFrame

        Returns:
            交易信號序列
        """
        # 確保已識別分形和頭肩形態
        if 'fractal_up' not in data.columns:
            data = TechnicalIndicators.identify_williams_fractal(
                data,
                period=self.params['fractal_period']
            )

        if 'head_shoulders_top' not in data.columns:
            data = TechnicalIndicators.identify_head_shoulders(
                data,
                tolerance=self.params['tolerance']
            )

        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        threshold = self.params['neckline_break_threshold']
        confirm_bars = self.params['confirm_bars']

        # 找出頭肩頂形態位置
        hs_top_idx = data[data['head_shoulders_top']].index.tolist()

        for head_idx in hs_top_idx:
            # 找到頭部位置後，計算頸線
            # 頸線 = 左肩和右肩之間的支撐線（簡化為頭部後最低點）
            head_pos = data.index.get_loc(head_idx)

            # 檢查後續價格是否跌破頸線
            for i in range(head_pos + 1, min(head_pos + 20, len(data))):
                current_idx = data.index[i]
                current_close = data['close'].iloc[i]

                # 簡化：頸線為頭部價格的某個百分比
                neckline = data['low'].iloc[head_pos] * 0.98

                # 跌破頸線 → 確認頭肩頂，做空
                if current_close < neckline * (1 - threshold):
                    # 等待確認
                    if i + confirm_bars < len(data):
                        signals.iloc[i + confirm_bars] = SignalType.SHORT.value
                    break

        # 找出頭肩底形態位置
        hs_bottom_idx = data[data['head_shoulders_bottom']].index.tolist()

        for head_idx in hs_bottom_idx:
            head_pos = data.index.get_loc(head_idx)

            # 檢查後續價格是否突破頸線
            for i in range(head_pos + 1, min(head_pos + 20, len(data))):
                current_idx = data.index[i]
                current_close = data['close'].iloc[i]

                # 頸線為頭部價格的某個百分比
                neckline = data['high'].iloc[head_pos] * 1.02

                # 突破頸線 → 確認頭肩底，做多
                if current_close > neckline * (1 + threshold):
                    if i + confirm_bars < len(data):
                        signals.iloc[i + confirm_bars] = SignalType.LONG.value
                    break

        return signals

    def get_required_features(self) -> list:
        return [
            'high', 'low', 'close',
            'fractal_up', 'fractal_down',
            'head_shoulders_top', 'head_shoulders_bottom'
        ]


class CombinedFractalMAStrategy(StrategyBase):
    """
    結合威廉分形與移動平均線的趨勢策略

    邏輯：
    - 價格在 MA 之上 + 突破上分形 → 做多
    - 價格在 MA 之下 + 跌破下分形 → 做空
    """

    def __init__(
        self,
        name: str = "Fractal_MA_Combined",
        params: Optional[Dict] = None
    ):
        default_params = {
            'fractal_period': 2,
            'ma_period': 20,  # 使用 20 日均線作為趨勢過濾
            'ma_type': 'sma',  # 'sma' 或 'ema'
            'breakout_threshold': 0.001
        }

        if params:
            default_params.update(params)

        super().__init__(name, default_params)

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成結合分形與 MA 的信號

        Args:
            data: 包含 OHLCV 的 DataFrame

        Returns:
            交易信號序列
        """
        # 確保已計算分形和 MA
        if 'fractal_up' not in data.columns:
            data = TechnicalIndicators.identify_williams_fractal(
                data,
                period=self.params['fractal_period']
            )

        ma_col = f"ma_{self.params['ma_period']}"
        if ma_col not in data.columns:
            data = TechnicalIndicators.calculate_moving_averages(
                data,
                periods=[self.params['ma_period']],
                ma_type=self.params['ma_type']
            )

        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        threshold = self.params['breakout_threshold']

        up_fractals_idx = data[data['fractal_up']].index.tolist()
        down_fractals_idx = data[data['fractal_down']].index.tolist()

        for i in range(len(data)):
            current_idx = data.index[i]
            current_close = data['close'].iloc[i]
            current_ma = data[ma_col].iloc[i]

            if pd.isna(current_ma):
                continue

            # 趨勢向上（價格 > MA）
            if current_close > current_ma:
                # 找最近的上分形
                recent_up = [idx for idx in up_fractals_idx if idx < current_idx]
                if recent_up:
                    resistance = data.loc[recent_up[-1], 'high']
                    # 突破阻力 → 做多
                    if current_close > resistance * (1 + threshold):
                        signals.iloc[i] = SignalType.LONG.value

            # 趨勢向下（價格 < MA）
            elif current_close < current_ma:
                # 找最近的下分形
                recent_down = [idx for idx in down_fractals_idx if idx < current_idx]
                if recent_down:
                    support = data.loc[recent_down[-1], 'low']
                    # 跌破支撐 → 做空
                    if current_close < support * (1 - threshold):
                        signals.iloc[i] = SignalType.SHORT.value

        return signals

    def get_required_features(self) -> list:
        ma_col = f"ma_{self.params['ma_period']}"
        return ['high', 'low', 'close', 'fractal_up', 'fractal_down', ma_col]
