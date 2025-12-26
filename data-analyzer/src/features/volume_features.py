"""
成交量特徵工程模組

功能：
1. 成交量統計特徵
2. 成交量動量特徵
3. 價量關係特徵
4. 訂單流特徵（基於 trades 資料）
"""
import pandas as pd
import numpy as np
from typing import Optional, List


class VolumeFeatures:
    """成交量特徵計算器"""

    @staticmethod
    def calculate_volume_stats(
        df: pd.DataFrame,
        volume_col: str = 'volume',
        windows: List[int] = [10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算成交量統計特徵

        Args:
            df: 包含成交量資料的 DataFrame
            volume_col: 成交量欄位名稱
            windows: 滾動窗口大小列表

        Returns:
            包含成交量統計特徵的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 平均成交量
            result[f'volume_ma_{window}'] = result[volume_col].rolling(
                window=window
            ).mean()

            # 成交量標準差
            result[f'volume_std_{window}'] = result[volume_col].rolling(
                window=window
            ).std()

            # 成交量相對強度（當前成交量 / 平均成交量）
            result[f'volume_ratio_{window}'] = (
                result[volume_col] / result[f'volume_ma_{window}']
            )

        return result

    @staticmethod
    def calculate_volume_momentum(
        df: pd.DataFrame,
        volume_col: str = 'volume',
        periods: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        計算成交量動量指標

        Args:
            df: 包含成交量資料的 DataFrame
            volume_col: 成交量欄位名稱
            periods: 動量計算週期

        Returns:
            包含成交量動量的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 成交量變化率
            result[f'volume_change_{period}'] = result[volume_col].pct_change(
                period
            )

            # 成交量動量
            result[f'volume_momentum_{period}'] = (
                result[volume_col] / result[volume_col].shift(period) - 1
            )

        return result

    @staticmethod
    def calculate_obv(
        df: pd.DataFrame,
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> pd.DataFrame:
        """
        計算 OBV (On-Balance Volume) 指標

        OBV 根據價格漲跌累積成交量：
        - 收盤價上漲：OBV += volume
        - 收盤價下跌：OBV -= volume

        Args:
            df: 包含價格和成交量的 DataFrame
            close_col: 收盤價欄位名稱
            volume_col: 成交量欄位名稱

        Returns:
            包含 OBV 的 DataFrame
        """
        result = df.copy()

        # 計算價格變化
        price_change = result[close_col].diff()

        # OBV 計算
        obv = (np.sign(price_change) * result[volume_col]).fillna(0).cumsum()
        result['obv'] = obv

        # OBV 變化率
        result['obv_change'] = result['obv'].pct_change()

        return result

    @staticmethod
    def calculate_vwap(
        df: pd.DataFrame,
        price_col: str = 'close',
        volume_col: str = 'volume',
        windows: List[int] = [10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算 VWAP (Volume Weighted Average Price)

        VWAP = Σ(價格 × 成交量) / Σ(成交量)

        Args:
            df: 包含價格和成交量的 DataFrame
            price_col: 價格欄位名稱
            volume_col: 成交量欄位名稱
            windows: 滾動窗口大小列表

        Returns:
            包含 VWAP 的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 計算滾動 VWAP
            pv = (result[price_col] * result[volume_col]).rolling(
                window=window
            ).sum()
            v = result[volume_col].rolling(window=window).sum()

            result[f'vwap_{window}'] = pv / v

            # 價格偏離 VWAP 的程度
            result[f'price_vwap_diff_{window}'] = (
                (result[price_col] - result[f'vwap_{window}']) /
                result[f'vwap_{window}']
            )

        return result

    @staticmethod
    def calculate_price_volume_correlation(
        df: pd.DataFrame,
        price_col: str = 'close',
        volume_col: str = 'volume',
        windows: List[int] = [10, 20, 50]
    ) -> pd.DataFrame:
        """
        計算價量相關性

        Args:
            df: 包含價格和成交量的 DataFrame
            price_col: 價格欄位名稱
            volume_col: 成交量欄位名稱
            windows: 滾動窗口大小列表

        Returns:
            包含價量相關性的 DataFrame
        """
        result = df.copy()

        for window in windows:
            # 滾動相關係數
            result[f'pv_corr_{window}'] = result[price_col].rolling(
                window=window
            ).corr(result[volume_col])

        return result

    @staticmethod
    def calculate_volume_profile(
        df: pd.DataFrame,
        volume_col: str = 'volume',
        window: int = 20
    ) -> pd.DataFrame:
        """
        計算成交量分布特徵

        Args:
            df: 包含成交量資料的 DataFrame
            volume_col: 成交量欄位名稱
            window: 滾動窗口大小

        Returns:
            包含成交量分布特徵的 DataFrame
        """
        result = df.copy()

        # 成交量百分位數
        result[f'volume_percentile_{window}'] = result[volume_col].rolling(
            window=window
        ).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )

        # 異常大成交量標記（超過均值 + 2倍標準差）
        volume_ma = result[volume_col].rolling(window=window).mean()
        volume_std = result[volume_col].rolling(window=window).std()
        result[f'volume_spike_{window}'] = (
            result[volume_col] > (volume_ma + 2 * volume_std)
        ).astype(int)

        return result

    @staticmethod
    def add_all_volume_features(
        df: pd.DataFrame,
        close_col: str = 'close',
        volume_col: str = 'volume'
    ) -> pd.DataFrame:
        """
        一次性加入所有成交量特徵

        Args:
            df: 原始 OHLCV 資料
            close_col: 收盤價欄位名稱
            volume_col: 成交量欄位名稱

        Returns:
            包含所有成交量特徵的 DataFrame
        """
        result = df.copy()

        # 成交量統計
        result = VolumeFeatures.calculate_volume_stats(result, volume_col)

        # 成交量動量
        result = VolumeFeatures.calculate_volume_momentum(result, volume_col)

        # OBV
        result = VolumeFeatures.calculate_obv(result, close_col, volume_col)

        # VWAP
        result = VolumeFeatures.calculate_vwap(result, close_col, volume_col)

        # 價量相關性
        result = VolumeFeatures.calculate_price_volume_correlation(
            result, close_col, volume_col
        )

        # 成交量分布
        result = VolumeFeatures.calculate_volume_profile(result, volume_col)

        return result


class OrderFlowFeatures:
    """
    訂單流特徵（基於 trades 資料）

    需要更細粒度的 trades 資料
    """

    @staticmethod
    def aggregate_trades_to_bars(
        trades_df: pd.DataFrame,
        freq: str = '1min',
        timestamp_col: str = 'timestamp',
        price_col: str = 'price',
        quantity_col: str = 'quantity',
        is_buyer_maker_col: str = 'is_buyer_maker'
    ) -> pd.DataFrame:
        """
        將 trades 聚合為時間條

        Args:
            trades_df: Trades 資料
            freq: 聚合頻率（如 '1min', '5min'）
            timestamp_col: 時間戳欄位
            price_col: 價格欄位
            quantity_col: 數量欄位
            is_buyer_maker_col: 買方是否為 maker

        Returns:
            聚合後的 DataFrame
        """
        df = trades_df.copy()
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.set_index(timestamp_col)

        # 聚合為 OHLC
        ohlc = df[price_col].resample(freq).ohlc()
        ohlc.columns = ['open', 'high', 'low', 'close']

        # 總成交量
        volume = df[quantity_col].resample(freq).sum()

        # 買單成交量（taker買入）
        buy_volume = df[~df[is_buyer_maker_col]][quantity_col].resample(
            freq
        ).sum()

        # 賣單成交量（taker賣出）
        sell_volume = df[df[is_buyer_maker_col]][quantity_col].resample(
            freq
        ).sum()

        # 合併
        result = pd.concat([ohlc, volume, buy_volume, sell_volume], axis=1)
        result.columns = list(ohlc.columns) + [
            'volume', 'buy_volume', 'sell_volume'
        ]

        # 計算買賣壓力
        result['buy_sell_ratio'] = result['buy_volume'] / (
            result['sell_volume'] + 1e-10
        )
        result['net_volume'] = result['buy_volume'] - result['sell_volume']

        return result.reset_index()
