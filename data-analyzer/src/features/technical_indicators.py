"""
技術指標計算模組

實現常用技術指標：
- MACD (Moving Average Convergence Divergence)
- MA (Moving Average): 20, 60, 200
- Williams Fractal (威廉分形)
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional


class TechnicalIndicators:
    """技術指標計算器"""

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """
        計算指數移動平均線 (Exponential Moving Average)

        Args:
            series: 價格序列
            period: 週期

        Returns:
            EMA 序列
        """
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """
        計算簡單移動平均線 (Simple Moving Average)

        Args:
            series: 價格序列
            period: 週期

        Returns:
            SMA 序列
        """
        return series.rolling(window=period).mean()

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        計算 MACD 指標

        MACD = 快線EMA - 慢線EMA
        Signal = MACD的EMA
        Histogram = MACD - Signal

        Args:
            df: 包含價格資料的 DataFrame
            fast_period: 快線週期（預設 12）
            slow_period: 慢線週期（預設 26）
            signal_period: 信號線週期（預設 9）
            price_col: 價格欄位名稱

        Returns:
            包含 MACD、Signal、Histogram 的 DataFrame
        """
        result = df.copy()

        # 計算快線和慢線 EMA
        ema_fast = TechnicalIndicators.calculate_ema(df[price_col], fast_period)
        ema_slow = TechnicalIndicators.calculate_ema(df[price_col], slow_period)

        # 計算 MACD 線
        result['macd'] = ema_fast - ema_slow

        # 計算信號線
        result['macd_signal'] = TechnicalIndicators.calculate_ema(
            result['macd'], signal_period
        )

        # 計算柱狀圖
        result['macd_histogram'] = result['macd'] - result['macd_signal']

        return result

    @staticmethod
    def calculate_rsi(
        df: pd.DataFrame,
        period: int = 14,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        計算 RSI (Relative Strength Index) 指標

        RSI = 100 - (100 / (1 + RS))
        RS = 平均漲幅 / 平均跌幅

        Args:
            df: 包含價格資料的 DataFrame
            period: RSI 週期（預設 14）
            price_col: 價格欄位名稱

        Returns:
            包含 RSI 的 DataFrame
        """
        result = df.copy()

        # 計算價格變化
        delta = result[price_col].diff()

        # 分離漲跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 計算平均漲跌（使用 EMA）
        avg_gain = gain.ewm(span=period, adjust=False).mean()
        avg_loss = loss.ewm(span=period, adjust=False).mean()

        # 計算 RS 和 RSI
        rs = avg_gain / (avg_loss + 1e-10)
        result['rsi'] = 100 - (100 / (1 + rs))

        return result

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        num_std: float = 2.0,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        計算布林通道 (Bollinger Bands)

        中軌 = N 期 SMA
        上軌 = 中軌 + (標準差 × K)
        下軌 = 中軌 - (標準差 × K)

        Args:
            df: 包含價格資料的 DataFrame
            period: 週期（預設 20）
            num_std: 標準差倍數（預設 2）
            price_col: 價格欄位名稱

        Returns:
            包含布林通道的 DataFrame
        """
        result = df.copy()

        # 計算中軌（SMA）
        sma = result[price_col].rolling(window=period).mean()
        std = result[price_col].rolling(window=period).std()

        result['bb_middle'] = sma
        result['bb_upper'] = sma + (std * num_std)
        result['bb_lower'] = sma - (std * num_std)

        # 計算價格在布林通道中的位置（%B）
        result['bb_position'] = (
            (result[price_col] - result['bb_lower']) /
            (result['bb_upper'] - result['bb_lower'])
        )

        # 計算通道寬度（Bandwidth）
        result['bb_width'] = (
            (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
        )

        return result

    @staticmethod
    def calculate_moving_averages(
        df: pd.DataFrame,
        periods: list = [20, 60, 200],
        price_col: str = 'close',
        ma_type: str = 'sma'
    ) -> pd.DataFrame:
        """
        計算多條移動平均線

        Args:
            df: 包含價格資料的 DataFrame
            periods: 週期列表
            price_col: 價格欄位名稱
            ma_type: 移動平均類型 ('sma' 或 'ema')

        Returns:
            包含各週期 MA 的 DataFrame
        """
        result = df.copy()

        calc_func = (
            TechnicalIndicators.calculate_sma if ma_type == 'sma'
            else TechnicalIndicators.calculate_ema
        )

        for period in periods:
            col_name = f'ma_{period}'
            result[col_name] = calc_func(df[price_col], period)

        return result

    @staticmethod
    def identify_williams_fractal(
        df: pd.DataFrame,
        high_col: str = 'high',
        low_col: str = 'low',
        period: int = 2
    ) -> pd.DataFrame:
        """
        識別威廉分形 (Williams Fractal)

        分形定義：
        - 上分形（Fractal Up）：中間K線的高點是左右各N根K線中的最高點
        - 下分形（Fractal Down）：中間K線的低點是左右各N根K線中的最低點

        Args:
            df: 包含價格資料的 DataFrame
            high_col: 高點欄位名稱
            low_col: 低點欄位名稱
            period: 左右兩側的K線數量（預設 2，即標準威廉分形）

        Returns:
            包含 fractal_up 和 fractal_down 標記的 DataFrame
        """
        result = df.copy()
        n = len(df)

        # 初始化分形標記
        result['fractal_up'] = False
        result['fractal_down'] = False

        # 需要至少 2*period + 1 根K線才能判斷分形
        if n < 2 * period + 1:
            return result

        # 從 period 開始到 n-period 結束，檢查每個中心點
        for i in range(period, n - period):
            # 檢查上分形（局部高點）
            is_fractal_up = True
            center_high = df[high_col].iloc[i]

            for j in range(1, period + 1):
                # 檢查左側
                if df[high_col].iloc[i - j] >= center_high:
                    is_fractal_up = False
                    break
                # 檢查右側
                if df[high_col].iloc[i + j] >= center_high:
                    is_fractal_up = False
                    break

            if is_fractal_up:
                result.loc[result.index[i], 'fractal_up'] = True

            # 檢查下分形（局部低點）
            is_fractal_down = True
            center_low = df[low_col].iloc[i]

            for j in range(1, period + 1):
                # 檢查左側
                if df[low_col].iloc[i - j] <= center_low:
                    is_fractal_down = False
                    break
                # 檢查右側
                if df[low_col].iloc[i + j] <= center_low:
                    is_fractal_down = False
                    break

            if is_fractal_down:
                result.loc[result.index[i], 'fractal_down'] = True

        return result

    @staticmethod
    def identify_head_shoulders(
        df: pd.DataFrame,
        fractal_col_up: str = 'fractal_up',
        fractal_col_down: str = 'fractal_down',
        high_col: str = 'high',
        low_col: str = 'low',
        tolerance: float = 0.02
    ) -> pd.DataFrame:
        """
        基於威廉分形識別頭肩頂/頭肩底形態

        頭肩頂（Head and Shoulders Top）：
        - 三個上分形：左肩 < 頭部 > 右肩
        - 左肩和右肩高度相近（容忍度範圍內）

        頭肩底（Inverse Head and Shoulders）：
        - 三個下分形：左肩 > 頭部 < 右肩
        - 左肩和右肩深度相近

        Args:
            df: 包含分形標記的 DataFrame
            fractal_col_up: 上分形標記欄位
            fractal_col_down: 下分形標記欄位
            high_col: 高點欄位
            low_col: 低點欄位
            tolerance: 左右肩高度容忍度（預設 2%）

        Returns:
            包含 head_shoulders_top 和 head_shoulders_bottom 標記的 DataFrame
        """
        result = df.copy()
        result['head_shoulders_top'] = False
        result['head_shoulders_bottom'] = False

        # 找出所有上分形位置（潛在的頭肩頂）
        up_fractals = result[result[fractal_col_up]].index.tolist()

        # 至少需要 3 個分形
        if len(up_fractals) >= 3:
            for i in range(len(up_fractals) - 2):
                left_idx = up_fractals[i]
                head_idx = up_fractals[i + 1]
                right_idx = up_fractals[i + 2]

                left_high = result.loc[left_idx, high_col]
                head_high = result.loc[head_idx, high_col]
                right_high = result.loc[right_idx, high_col]

                # 檢查頭肩頂條件
                if (head_high > left_high and
                    head_high > right_high and
                    abs(left_high - right_high) / left_high <= tolerance):

                    # 標記頭部位置
                    result.loc[head_idx, 'head_shoulders_top'] = True

        # 找出所有下分形位置（潛在的頭肩底）
        down_fractals = result[result[fractal_col_down]].index.tolist()

        if len(down_fractals) >= 3:
            for i in range(len(down_fractals) - 2):
                left_idx = down_fractals[i]
                head_idx = down_fractals[i + 1]
                right_idx = down_fractals[i + 2]

                left_low = result.loc[left_idx, low_col]
                head_low = result.loc[head_idx, low_col]
                right_low = result.loc[right_idx, low_col]

                # 檢查頭肩底條件
                if (head_low < left_low and
                    head_low < right_low and
                    abs(left_low - right_low) / left_low <= tolerance):

                    # 標記頭部位置
                    result.loc[head_idx, 'head_shoulders_bottom'] = True

        return result

    @staticmethod
    def add_all_indicators(
        df: pd.DataFrame,
        macd_params: Optional[dict] = None,
        ma_periods: list = [20, 60, 200],
        fractal_period: int = 2,
        identify_patterns: bool = True
    ) -> pd.DataFrame:
        """
        一次性計算所有技術指標

        Args:
            df: 原始 OHLCV 資料
            macd_params: MACD 參數字典
            ma_periods: 移動平均線週期列表
            fractal_period: 威廉分形週期
            identify_patterns: 是否識別頭肩形態

        Returns:
            包含所有技術指標的 DataFrame
        """
        result = df.copy()

        # MACD
        if macd_params is None:
            macd_params = {'fast_period': 12, 'slow_period': 26, 'signal_period': 9}
        result = TechnicalIndicators.calculate_macd(result, **macd_params)

        # 移動平均線
        result = TechnicalIndicators.calculate_moving_averages(
            result, periods=ma_periods
        )

        # 威廉分形
        result = TechnicalIndicators.identify_williams_fractal(
            result, period=fractal_period
        )

        # 頭肩形態識別
        if identify_patterns:
            result = TechnicalIndicators.identify_head_shoulders(result)

        return result


def calculate_indicators_for_symbol(
    df: pd.DataFrame,
    symbol: str = None
) -> pd.DataFrame:
    """
    為特定交易對計算所有技術指標（便捷函數）

    Args:
        df: OHLCV 資料
        symbol: 交易對名稱（用於日誌）

    Returns:
        包含所有指標的 DataFrame
    """
    if symbol:
        print(f"正在計算 {symbol} 的技術指標...")

    result = TechnicalIndicators.add_all_indicators(df)

    if symbol:
        print(f"  - MACD: ✓")
        print(f"  - MA (20, 60, 200): ✓")
        print(f"  - Williams Fractal: ✓")
        print(f"  - 頭肩形態: ✓")

    return result
