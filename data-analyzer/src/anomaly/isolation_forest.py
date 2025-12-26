"""
異常偵測模型 - Isolation Forest

功能：
1. 檢測價格異常跳動（Flash crash / Pump）
2. 檢測成交量異常
3. 檢測市場微觀結構異常
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


class PriceAnomalyDetector:
    """價格異常偵測器"""

    def __init__(
        self,
        contamination: float = 0.01,
        random_state: int = 42
    ):
        """
        初始化偵測器

        Args:
            contamination: 預期異常比例（0-0.5）
            random_state: 隨機種子
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        準備異常偵測特徵

        Args:
            df: OHLCV DataFrame

        Returns:
            特徵 DataFrame
        """
        features = pd.DataFrame(index=df.index)

        # 價格變化率
        features['return_1'] = df['close'].pct_change()
        features['return_5'] = df['close'].pct_change(5)
        features['return_15'] = df['close'].pct_change(15)

        # 價格波動度
        features['volatility_10'] = df['close'].pct_change().rolling(10).std()
        features['volatility_20'] = df['close'].pct_change().rolling(20).std()

        # 價格範圍
        features['price_range'] = (df['high'] - df['low']) / df['close']

        # 成交量異常
        features['volume_change'] = df['volume'].pct_change()
        features['volume_ratio_20'] = df['volume'] / df['volume'].rolling(20).mean()

        # 價格偏離移動平均
        ma_20 = df['close'].rolling(20).mean()
        features['price_ma_diff'] = (df['close'] - ma_20) / ma_20

        # 跳空
        features['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)

        return features.dropna()

    def fit(self, df: pd.DataFrame) -> 'PriceAnomalyDetector':
        """
        訓練異常偵測模型

        Args:
            df: OHLCV DataFrame

        Returns:
            self
        """
        # 準備特徵
        X = self.prepare_features(df)

        # 標準化
        X_scaled = self.scaler.fit_transform(X)

        # 訓練模型
        self.model.fit(X_scaled)
        self.is_fitted = True

        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """
        預測異常

        Args:
            df: OHLCV DataFrame

        Returns:
            異常標記 Series（1: 正常, -1: 異常）
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")

        # 準備特徵
        X = self.prepare_features(df)

        # 標準化
        X_scaled = self.scaler.transform(X)

        # 預測
        predictions = self.model.predict(X_scaled)

        return pd.Series(predictions, index=X.index, name='anomaly')

    def get_anomaly_scores(self, df: pd.DataFrame) -> pd.Series:
        """
        獲取異常分數（分數越低越異常）

        Args:
            df: OHLCV DataFrame

        Returns:
            異常分數 Series
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before getting scores")

        X = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        scores = self.model.score_samples(X_scaled)

        return pd.Series(scores, index=X.index, name='anomaly_score')

    def detect_flash_events(
        self,
        df: pd.DataFrame,
        threshold_pct: float = 0.05
    ) -> pd.DataFrame:
        """
        檢測閃崩/暴漲事件

        Args:
            df: OHLCV DataFrame
            threshold_pct: 閃崩/暴漲閾值（5% = 0.05）

        Returns:
            包含閃崩事件的 DataFrame
        """
        events = []

        # 計算單期報酬
        returns = df['close'].pct_change()

        # 檢測閃崩（急劇下跌）
        crash_mask = returns < -threshold_pct
        crashes = df[crash_mask].copy()
        crashes['event_type'] = 'flash_crash'
        crashes['return'] = returns[crash_mask]

        # 檢測暴漲（急劇上漲）
        pump_mask = returns > threshold_pct
        pumps = df[pump_mask].copy()
        pumps['event_type'] = 'pump'
        pumps['return'] = returns[pump_mask]

        # 合併事件
        events_df = pd.concat([crashes, pumps]).sort_index()

        return events_df


class StatisticalAnomalyDetector:
    """
    統計方法異常偵測

    使用 Z-score 和 IQR 方法
    """

    @staticmethod
    def detect_zscore_anomalies(
        series: pd.Series,
        window: int = 20,
        threshold: float = 3.0
    ) -> pd.Series:
        """
        使用 Z-score 方法檢測異常

        Args:
            series: 時間序列
            window: 滾動窗口
            threshold: Z-score 閾值（預設 3）

        Returns:
            異常標記 Series
        """
        # 計算滾動均值和標準差
        rolling_mean = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()

        # 計算 Z-score
        z_score = (series - rolling_mean) / (rolling_std + 1e-10)

        # 標記異常
        anomalies = (np.abs(z_score) > threshold).astype(int)

        return anomalies

    @staticmethod
    def detect_iqr_anomalies(
        series: pd.Series,
        window: int = 20,
        multiplier: float = 1.5
    ) -> pd.Series:
        """
        使用 IQR (Interquartile Range) 方法檢測異常

        Args:
            series: 時間序列
            window: 滾動窗口
            multiplier: IQR 倍數（預設 1.5）

        Returns:
            異常標記 Series
        """
        def detect_outliers(x):
            if len(x) < 4:
                return 0

            q1 = x.quantile(0.25)
            q3 = x.quantile(0.75)
            iqr = q3 - q1

            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr

            # 當前值是否異常
            current_value = x.iloc[-1]
            is_outlier = (current_value < lower_bound) or (current_value > upper_bound)

            return int(is_outlier)

        anomalies = series.rolling(window=window).apply(detect_outliers)

        return anomalies


def run_comprehensive_anomaly_detection(
    df: pd.DataFrame,
    methods: List[str] = ['isolation_forest', 'zscore', 'iqr']
) -> pd.DataFrame:
    """
    執行綜合異常偵測

    Args:
        df: OHLCV DataFrame
        methods: 要使用的方法列表

    Returns:
        包含所有異常偵測結果的 DataFrame
    """
    result = df.copy()

    # Isolation Forest
    if 'isolation_forest' in methods:
        detector = PriceAnomalyDetector(contamination=0.01)
        detector.fit(df)
        result['anomaly_if'] = detector.predict(df)
        result['anomaly_score_if'] = detector.get_anomaly_scores(df)

    # Z-score
    if 'zscore' in methods:
        returns = df['close'].pct_change()
        result['anomaly_zscore'] = StatisticalAnomalyDetector.detect_zscore_anomalies(
            returns, window=20, threshold=3.0
        )

    # IQR
    if 'iqr' in methods:
        returns = df['close'].pct_change()
        result['anomaly_iqr'] = StatisticalAnomalyDetector.detect_iqr_anomalies(
            returns, window=20, multiplier=1.5
        )

    # 綜合判斷（多數投票）
    anomaly_cols = [col for col in result.columns if col.startswith('anomaly_') and col != 'anomaly_score_if']
    if anomaly_cols:
        result['anomaly_consensus'] = (
            result[anomaly_cols].sum(axis=1) >= len(anomaly_cols) / 2
        ).astype(int)

    return result
