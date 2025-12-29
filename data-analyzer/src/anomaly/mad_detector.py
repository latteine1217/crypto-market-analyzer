"""
MAD (Median Absolute Deviation) 異常檢測
使用 MAD 方法進行時序資料異常檢測，比標準差更穩健
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, List, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MADDetector:
    """
    MAD (Median Absolute Deviation) 異常檢測器

    MAD 是一種穩健的統計量，相比標準差對離群值不敏感
    計算公式：MAD = median(|X_i - median(X)|)
    異常判定：|X_i - median(X)| > threshold * MAD
    """

    def __init__(
        self,
        threshold: float = 3.0,
        window_size: int = 100,
        min_samples: int = 30
    ):
        """
        初始化 MAD 檢測器

        Args:
            threshold: 異常閾值（倍數），通常取 2-3
            window_size: 滑動窗口大小
            min_samples: 最小樣本數，少於此數量不進行檢測
        """
        self.threshold = threshold
        self.window_size = window_size
        self.min_samples = min_samples

        logger.info(
            f"MAD Detector initialized: threshold={threshold}, "
            f"window_size={window_size}, min_samples={min_samples}"
        )

    def calculate_mad(self, data: np.ndarray) -> float:
        """
        計算 MAD (Median Absolute Deviation)

        Args:
            data: 一維數據陣列

        Returns:
            MAD 值
        """
        if len(data) < self.min_samples:
            logger.warning(f"樣本數不足 ({len(data)} < {self.min_samples})，返回 0")
            return 0.0

        median = np.median(data)
        mad = np.median(np.abs(data - median))

        return mad

    def detect_anomalies(
        self,
        data: pd.Series,
        return_scores: bool = False
    ) -> Tuple[pd.Series, Optional[pd.Series]]:
        """
        檢測時序資料中的異常點

        Args:
            data: 時序資料（pandas Series）
            return_scores: 是否返回異常分數

        Returns:
            is_anomaly: 布林序列，True 表示異常
            scores: 異常分數（可選），值越大越異常
        """
        if len(data) < self.min_samples:
            logger.warning(f"資料量不足 ({len(data)} < {self.min_samples})，無法檢測異常")
            return pd.Series(False, index=data.index), None

        # 使用滑動窗口計算 MAD
        is_anomaly = pd.Series(False, index=data.index)
        scores = pd.Series(0.0, index=data.index) if return_scores else None

        for i in range(len(data)):
            # 取當前點前面的窗口資料
            start_idx = max(0, i - self.window_size)
            window_data = data.iloc[start_idx:i+1].values

            if len(window_data) < self.min_samples:
                continue

            # 計算 MAD
            median = np.median(window_data)
            mad = self.calculate_mad(window_data)

            # 避免除以零
            if mad == 0:
                mad = np.std(window_data)  # 退化為標準差
                if mad == 0:
                    continue

            # 計算當前點與中位數的偏差
            current_value = data.iloc[i]
            deviation = abs(current_value - median)

            # 異常分數
            score = deviation / mad

            # 判斷是否異常
            if score > self.threshold:
                is_anomaly.iloc[i] = True
                logger.debug(
                    f"檢測到異常: index={data.index[i]}, "
                    f"value={current_value:.2f}, score={score:.2f}"
                )

            if return_scores:
                scores.iloc[i] = score

        anomaly_count = is_anomaly.sum()
        anomaly_rate = anomaly_count / len(data) * 100
        logger.info(
            f"異常檢測完成: 共 {len(data)} 筆資料, "
            f"發現 {anomaly_count} 個異常點 ({anomaly_rate:.2f}%)"
        )

        return is_anomaly, scores

    def detect_price_anomalies(
        self,
        df: pd.DataFrame,
        price_column: str = 'close',
        volume_column: Optional[str] = 'volume'
    ) -> pd.DataFrame:
        """
        檢測價格異常，可同時考慮成交量

        Args:
            df: 包含價格資料的 DataFrame
            price_column: 價格欄位名稱
            volume_column: 成交量欄位名稱（可選）

        Returns:
            包含異常檢測結果的 DataFrame
        """
        result = df.copy()

        # 計算價格變化率
        result['price_change_pct'] = result[price_column].pct_change() * 100

        # 檢測價格變化率異常
        is_anomaly, scores = self.detect_anomalies(
            result['price_change_pct'].fillna(0),
            return_scores=True
        )

        result['is_price_anomaly'] = is_anomaly
        result['anomaly_score'] = scores

        # 如果有成交量，也檢測成交量異常
        if volume_column and volume_column in df.columns:
            vol_anomaly, vol_scores = self.detect_anomalies(
                result[volume_column],
                return_scores=True
            )

            result['is_volume_anomaly'] = vol_anomaly
            result['volume_anomaly_score'] = vol_scores

            # 綜合判斷：價格和成交量都異常時，標記為高風險異常
            result['is_high_risk_anomaly'] = (
                result['is_price_anomaly'] & result['is_volume_anomaly']
            )

        return result

    def get_anomaly_summary(self, df: pd.DataFrame) -> Dict:
        """
        獲取異常檢測摘要統計

        Args:
            df: 包含異常檢測結果的 DataFrame

        Returns:
            異常統計字典
        """
        total_points = len(df)
        price_anomalies = df['is_price_anomaly'].sum() if 'is_price_anomaly' in df else 0
        volume_anomalies = df['is_volume_anomaly'].sum() if 'is_volume_anomaly' in df else 0
        high_risk_anomalies = df['is_high_risk_anomaly'].sum() if 'is_high_risk_anomaly' in df else 0

        summary = {
            'total_points': total_points,
            'price_anomalies': int(price_anomalies),
            'price_anomaly_rate': float(price_anomalies / total_points * 100),
            'volume_anomalies': int(volume_anomalies),
            'volume_anomaly_rate': float(volume_anomalies / total_points * 100),
            'high_risk_anomalies': int(high_risk_anomalies),
            'high_risk_anomaly_rate': float(high_risk_anomalies / total_points * 100),
            'detector_config': {
                'threshold': self.threshold,
                'window_size': self.window_size,
                'min_samples': self.min_samples
            }
        }

        return summary


class RealtimeMADDetector:
    """
    即時 MAD 異常檢測器
    適用於流式資料處理
    """

    def __init__(
        self,
        threshold: float = 3.0,
        window_size: int = 100,
        symbols: List[str] = None
    ):
        """
        初始化即時檢測器

        Args:
            threshold: 異常閾值
            window_size: 滑動窗口大小
            symbols: 要監控的交易對列表
        """
        self.threshold = threshold
        self.window_size = window_size
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT']

        # 為每個交易對維護一個資料緩衝區
        self.buffers = {symbol: [] for symbol in self.symbols}

        # 統計資訊
        self.stats = {
            symbol: {
                'total_checked': 0,
                'anomalies_detected': 0,
                'last_anomaly_time': None,
                'current_mad': 0.0,
                'current_median': 0.0
            }
            for symbol in self.symbols
        }

        logger.info(f"Realtime MAD Detector initialized for symbols: {self.symbols}")

    def add_data_point(
        self,
        symbol: str,
        value: float,
        timestamp: datetime = None
    ) -> Tuple[bool, float]:
        """
        添加新資料點並檢測是否異常

        Args:
            symbol: 交易對符號
            value: 價格或其他指標值
            timestamp: 時間戳（可選）

        Returns:
            is_anomaly: 是否為異常
            score: 異常分數
        """
        if symbol not in self.buffers:
            logger.warning(f"未監控的交易對: {symbol}")
            return False, 0.0

        timestamp = timestamp or datetime.now()

        # 添加到緩衝區
        self.buffers[symbol].append({
            'timestamp': timestamp,
            'value': value
        })

        # 保持緩衝區大小
        if len(self.buffers[symbol]) > self.window_size:
            self.buffers[symbol].pop(0)

        # 檢測異常
        buffer_values = np.array([d['value'] for d in self.buffers[symbol]])

        if len(buffer_values) < 30:  # 最小樣本數
            return False, 0.0

        median = np.median(buffer_values)
        mad = np.median(np.abs(buffer_values - median))

        # 更新統計
        self.stats[symbol]['current_median'] = float(median)
        self.stats[symbol]['current_mad'] = float(mad)
        self.stats[symbol]['total_checked'] += 1

        if mad == 0:
            mad = np.std(buffer_values)
            if mad == 0:
                return False, 0.0

        deviation = abs(value - median)
        score = deviation / mad

        is_anomaly = score > self.threshold

        if is_anomaly:
            self.stats[symbol]['anomalies_detected'] += 1
            self.stats[symbol]['last_anomaly_time'] = timestamp.isoformat()

            logger.warning(
                f"異常檢測: {symbol} at {timestamp}, "
                f"value={value:.2f}, median={median:.2f}, "
                f"MAD={mad:.4f}, score={score:.2f}"
            )

        return is_anomaly, float(score)

    def get_stats(self) -> Dict:
        """獲取所有交易對的統計資訊"""
        return self.stats

    def reset_buffer(self, symbol: str = None):
        """重置緩衝區"""
        if symbol:
            if symbol in self.buffers:
                self.buffers[symbol] = []
                logger.info(f"重置 {symbol} 的緩衝區")
        else:
            for sym in self.symbols:
                self.buffers[sym] = []
            logger.info("重置所有緩衝區")
