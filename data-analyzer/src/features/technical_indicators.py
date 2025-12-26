"""
技術指標計算模組

職責：
- 計算常用技術指標
- MA（移動平均線）
- EMA（指數移動平均）
- RSI（相對強弱指標）
- MACD（異同移動平均線）
- Bollinger Bands（布林通道）
- ATR（平均真實波幅）
"""
import numpy as np
import pandas as pd
from typing import Tuple


class TechnicalIndicators:
    """技術指標計算器"""

    @staticmethod
    def calculate_sma(
        df: pd.DataFrame,
        price_col: str = 'close',
        windows: list = [5, 10, 20, 50, 100, 200]
    ) -> pd.DataFrame:
        """
        計算簡單移動平均線 (Simple Moving Average, SMA)

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            windows: MA 視窗大小列表

        Returns:
            包含 SMA 的 DataFrame
        """
        result = df.copy()

        for window in windows:
            result[f'sma_{window}'] = result[price_col].rolling(window=window).mean()

        return result

    @staticmethod
    def calculate_ema(
        df: pd.DataFrame,
        price_col: str = 'close',
        spans: list = [5, 10, 20, 50, 100, 200]
    ) -> pd.DataFrame:
        """
        計算指數移動平均線 (Exponential Moving Average, EMA)

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            spans: EMA 週期列表

        Returns:
            包含 EMA 的 DataFrame
        """
        result = df.copy()

        for span in spans:
            result[f'ema_{span}'] = result[price_col].ewm(span=span, adjust=False).mean()

        return result

    @staticmethod
    def calculate_rsi(
        df: pd.DataFrame,
        price_col: str = 'close',
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """
        計算相對強弱指標 (Relative Strength Index, RSI)

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            periods: RSI 計算週期列表

        Returns:
            包含 RSI 的 DataFrame
        """
        result = df.copy()

        for period in periods:
            # 計算價格變化
            delta = result[price_col].diff()

            # 分離漲跌
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # 計算平均漲跌幅
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # 計算 RS 和 RSI
            rs = avg_gain / avg_loss
            result[f'rsi_{period}'] = 100 - (100 / (1 + rs))

        return result

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        price_col: str = 'close',
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> pd.DataFrame:
        """
        計算 MACD (Moving Average Convergence Divergence)

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            fast_period: 快線週期
            slow_period: 慢線週期
            signal_period: 訊號線週期

        Returns:
            包含 MACD 相關指標的 DataFrame
        """
        result = df.copy()

        # 計算快線和慢線
        ema_fast = result[price_col].ewm(span=fast_period, adjust=False).mean()
        ema_slow = result[price_col].ewm(span=slow_period, adjust=False).mean()

        # MACD 線
        result['macd'] = ema_fast - ema_slow

        # 訊號線
        result['macd_signal'] = result['macd'].ewm(span=signal_period, adjust=False).mean()

        # MACD 柱狀圖
        result['macd_hist'] = result['macd'] - result['macd_signal']

        return result

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        price_col: str = 'close',
        window: int = 20,
        num_std: float = 2.0
    ) -> pd.DataFrame:
        """
        計算布林通道 (Bollinger Bands)

        Args:
            df: OHLCV DataFrame
            price_col: 價格欄位名稱
            window: 移動平均視窗
            num_std: 標準差倍數

        Returns:
            包含布林通道的 DataFrame
        """
        result = df.copy()

        # 中軌（移動平均）
        result[f'bb_middle_{window}'] = result[price_col].rolling(window=window).mean()

        # 標準差
        rolling_std = result[price_col].rolling(window=window).std()

        # 上軌和下軌
        result[f'bb_upper_{window}'] = result[f'bb_middle_{window}'] + (rolling_std * num_std)
        result[f'bb_lower_{window}'] = result[f'bb_middle_{window}'] - (rolling_std * num_std)

        # 布林通道寬度（標準化）
        result[f'bb_width_{window}'] = (
            (result[f'bb_upper_{window}'] - result[f'bb_lower_{window}']) /
            result[f'bb_middle_{window}']
        )

        # 價格在布林通道中的位置 (0-1)
        result[f'bb_position_{window}'] = (
            (result[price_col] - result[f'bb_lower_{window}']) /
            (result[f'bb_upper_{window}'] - result[f'bb_lower_{window}'])
        )

        return result

    @staticmethod
    def calculate_atr(
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        計算平均真實波幅 (Average True Range, ATR)

        Args:
            df: OHLCV DataFrame
            period: ATR 計算週期

        Returns:
            包含 ATR 的 DataFrame
        """
        result = df.copy()

        # 計算真實波幅 (True Range)
        high_low = result['high'] - result['low']
        high_close = abs(result['high'] - result['close'].shift())
        low_close = abs(result['low'] - result['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # 計算 ATR（使用 EMA）
        result[f'atr_{period}'] = true_range.ewm(span=period, adjust=False).mean()

        # ATR 百分比（相對於價格）
        result[f'atr_pct_{period}'] = result[f'atr_{period}'] / result['close'] * 100

        return result

    @staticmethod
    def calculate_stochastic(
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> pd.DataFrame:
        """
        計算隨機指標 (Stochastic Oscillator)

        Args:
            df: OHLCV DataFrame
            k_period: %K 週期
            d_period: %D 週期（%K 的移動平均）

        Returns:
            包含 Stochastic 的 DataFrame
        """
        result = df.copy()

        # 計算最高價和最低價
        low_min = result['low'].rolling(window=k_period).min()
        high_max = result['high'].rolling(window=k_period).max()

        # %K
        result['stoch_k'] = 100 * (result['close'] - low_min) / (high_max - low_min)

        # %D（%K 的移動平均）
        result['stoch_d'] = result['stoch_k'].rolling(window=d_period).mean()

        return result

    @staticmethod
    def calculate_adx(
        df: pd.DataFrame,
        period: int = 14
    ) -> pd.DataFrame:
        """
        計算平均趨向指標 (Average Directional Index, ADX)

        Args:
            df: OHLCV DataFrame
            period: ADX 計算週期

        Returns:
            包含 ADX 的 DataFrame
        """
        result = df.copy()

        # 計算價格變動
        high_diff = result['high'].diff()
        low_diff = -result['low'].diff()

        # 正向和負向移動
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # 計算 ATR（真實波幅）
        high_low = result['high'] - result['low']
        high_close = abs(result['high'] - result['close'].shift())
        low_close = abs(result['low'] - result['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # 平滑化
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        # 計算 DX 和 ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        result[f'adx_{period}'] = dx.ewm(span=period, adjust=False).mean()

        result[f'plus_di_{period}'] = plus_di
        result[f'minus_di_{period}'] = minus_di

        return result

    @classmethod
    def calculate_all(
        cls,
        df: pd.DataFrame,
        sma_windows: list = [5, 10, 20, 50],
        ema_spans: list = [5, 10, 20, 50],
        rsi_periods: list = [14],
        bb_window: int = 20,
        atr_period: int = 14
    ) -> pd.DataFrame:
        """
        計算所有技術指標

        Args:
            df: OHLCV DataFrame
            sma_windows: SMA 視窗列表
            ema_spans: EMA 週期列表
            rsi_periods: RSI 週期列表
            bb_window: 布林通道視窗
            atr_period: ATR 週期

        Returns:
            包含所有技術指標的 DataFrame
        """
        result = df.copy()

        # 移動平均線
        result = cls.calculate_sma(result, windows=sma_windows)
        result = cls.calculate_ema(result, spans=ema_spans)

        # 動量指標
        result = cls.calculate_rsi(result, periods=rsi_periods)
        result = cls.calculate_macd(result)

        # 波動性指標
        result = cls.calculate_bollinger_bands(result, window=bb_window)
        result = cls.calculate_atr(result, period=atr_period)

        # 趨勢指標
        result = cls.calculate_stochastic(result)
        result = cls.calculate_adx(result)

        return result
