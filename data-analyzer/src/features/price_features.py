"""
價格特徵計算模組

職責：
- 計算價格相關的基礎特徵
- 報酬率（Returns）
- 價格變化（Price Changes）
- 價格趨勢特徵
"""
import numpy as np
import pandas as pd
from typing import Optional


class PriceFeatures:
    """價格特徵計算器"""

    @staticmethod
    def calculate_returns(
        df: pd.DataFrame,
        price_col: str = 'close',
        periods: list = [1, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算不同週期的報酬率

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            periods: 計算報酬率的週期列表

        Returns:
            包含報酬率特徵的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 簡單報酬率 (Simple Return)
            result[f'return_{period}'] = result[price_col].pct_change(period)

            # 對數報酬率 (Log Return)
            result[f'log_return_{period}'] = np.log(
                result[price_col] / result[price_col].shift(period)
            )

        return result

    @staticmethod
    def calculate_price_changes(
        df: pd.DataFrame,
        periods: list = [1, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算價格變化特徵

        Args:
            df: OHLCV DataFrame
            periods: 計算價格變化的週期列表

        Returns:
            包含價格變化特徵的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 價格變化量
            result[f'price_change_{period}'] = result['close'] - result['close'].shift(period)

            # 價格變化率
            result[f'price_change_pct_{period}'] = (
                (result['close'] - result['close'].shift(period)) / result['close'].shift(period) * 100
            )

        return result

    @staticmethod
    def calculate_high_low_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        計算高低價相關特徵

        Args:
            df: OHLCV DataFrame

        Returns:
            包含高低價特徵的 DataFrame
        """
        result = df.copy()

        # High-Low 價差
        result['high_low_diff'] = result['high'] - result['low']

        # High-Low 價差百分比
        result['high_low_pct'] = (
            (result['high'] - result['low']) / result['low'] * 100
        )

        # Close 相對於 High-Low 範圍的位置 (0-1)
        result['close_position'] = (
            (result['close'] - result['low']) / (result['high'] - result['low'])
        )

        # Open-Close 關係
        result['open_close_diff'] = result['close'] - result['open']
        result['open_close_pct'] = (
            (result['close'] - result['open']) / result['open'] * 100
        )

        # 是否收漲（1）或收跌（0）
        result['is_up'] = (result['close'] > result['open']).astype(int)

        return result

    @staticmethod
    def calculate_price_momentum(
        df: pd.DataFrame,
        price_col: str = 'close',
        periods: list = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算價格動量指標

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            periods: 計算動量的週期列表

        Returns:
            包含動量特徵的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 動量 (Momentum) = 當前價格 - N期前價格
            result[f'momentum_{period}'] = (
                result[price_col] - result[price_col].shift(period)
            )

            # 動量比率 (Momentum Ratio)
            result[f'momentum_ratio_{period}'] = (
                result[price_col] / result[price_col].shift(period)
            )

            # 價格變化率 (Rate of Change, ROC)
            result[f'roc_{period}'] = (
                (result[price_col] - result[price_col].shift(period)) /
                result[price_col].shift(period) * 100
            )

        return result

    @staticmethod
    def calculate_price_position(
        df: pd.DataFrame,
        price_col: str = 'close',
        windows: list = [20, 50, 100]
    ) -> pd.DataFrame:
        """
        計算價格相對位置（價格在歷史範圍中的位置）

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            windows: 計算範圍的視窗大小列表

        Returns:
            包含價格位置特徵的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 滾動最高價
            rolling_high = result[price_col].rolling(window=window).max()
            # 滾動最低價
            rolling_low = result[price_col].rolling(window=window).min()

            # 價格在範圍中的位置 (0-1)
            # 1 表示在最高點，0 表示在最低點
            result[f'price_position_{window}'] = (
                (result[price_col] - rolling_low) / (rolling_high - rolling_low)
            )

            # 距離最高點的百分比
            result[f'dist_from_high_{window}'] = (
                (rolling_high - result[price_col]) / rolling_high * 100
            )

            # 距離最低點的百分比
            result[f'dist_from_low_{window}'] = (
                (result[price_col] - rolling_low) / rolling_low * 100
            )

        return result

    @classmethod
    def calculate_all(
        cls,
        df: pd.DataFrame,
        return_periods: list = [1, 5, 10, 20],
        momentum_periods: list = [5, 10, 20],
        position_windows: list = [20, 50, 100]
    ) -> pd.DataFrame:
        """
        計算所有價格特徵

        Args:
            df: OHLCV DataFrame
            return_periods: 報酬率計算週期
            momentum_periods: 動量計算週期
            position_windows: 價格位置計算視窗

        Returns:
            包含所有價格特徵的 DataFrame
        """
        result = df.copy()

        # 計算各類價格特徵
        result = cls.calculate_returns(result, periods=return_periods)
        result = cls.calculate_price_changes(result, periods=return_periods)
        result = cls.calculate_high_low_features(result)
        result = cls.calculate_price_momentum(result, periods=momentum_periods)
        result = cls.calculate_price_position(result, windows=position_windows)

        return result
