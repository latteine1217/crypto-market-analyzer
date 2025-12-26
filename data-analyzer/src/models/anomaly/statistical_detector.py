"""
統計方法異常檢測模組

使用統計方法（Z-score, MAD）檢測時間序列異常。
輕量級、可解釋性強，適合快速異常偵測。
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ZScoreDetector:
    """
    Z-Score 異常檢測器

    使用標準差方法檢測異常值：
    - Z-score = (x - mean) / std
    - |Z-score| > threshold 視為異常
    """

    def __init__(
        self,
        threshold: float = 3.0,
        window: Optional[int] = None
    ):
        """
        初始化 Z-Score 檢測器

        Args:
            threshold: Z-score 閾值（通常 2-4）
            window: 滾動窗口大小（None 為使用全局統計）
        """
        self.threshold = threshold
        self.window = window

        # 全局統計量（如果使用全局模式）
        self.mean = None
        self.std = None

        self.model_name = f"ZScore_t{threshold}_w{window if window else 'global'}"

    def fit(
        self,
        prices: pd.Series,
        return_based: bool = True
    ) -> 'ZScoreDetector':
        """
        計算統計量（訓練）

        Args:
            prices: 價格序列
            return_based: 是否使用報酬率（推薦）

        Returns:
            self
        """
        logger.info(f"訓練 {self.model_name}")

        # 計算報酬率或使用原始價格
        if return_based:
            data = prices.pct_change().dropna()
        else:
            data = prices.dropna()

        # 如果不使用滾動窗口，計算全局統計量
        if self.window is None:
            self.mean = data.mean()
            self.std = data.std()
            logger.info(f"全局統計: mean={self.mean:.6f}, std={self.std:.6f}")
        else:
            logger.info(f"使用滾動窗口: {self.window}")

        return self

    def predict(
        self,
        prices: pd.Series,
        return_based: bool = True
    ) -> pd.DataFrame:
        """
        檢測異常

        Args:
            prices: 價格序列
            return_based: 是否使用報酬率

        Returns:
            包含異常標記和 Z-score 的 DataFrame
        """
        # 計算報酬率或使用原始價格
        if return_based:
            data = prices.pct_change()
        else:
            data = prices.copy()

        results = pd.DataFrame(index=data.index)
        results['price'] = prices

        # 計算 Z-score
        if self.window is None:
            # 全局統計
            if self.mean is None or self.std is None:
                raise ValueError("模型尚未訓練，請先調用 fit() 方法")
            z_scores = (data - self.mean) / self.std
        else:
            # 滾動統計
            rolling_mean = data.rolling(self.window).mean()
            rolling_std = data.rolling(self.window).std()
            z_scores = (data - rolling_mean) / rolling_std

        results['z_score'] = z_scores
        results['abs_z_score'] = np.abs(z_scores)
        results['anomaly'] = results['abs_z_score'] > self.threshold

        # 移除 NaN
        results = results.dropna()

        return results

    def get_anomaly_statistics(
        self,
        results: pd.DataFrame
    ) -> Dict[str, float]:
        """
        計算異常統計資訊

        Args:
            results: predict() 返回的結果

        Returns:
            統計資訊字典
        """
        total_samples = len(results)
        n_anomalies = results['anomaly'].sum()
        anomaly_ratio = n_anomalies / total_samples * 100

        stats = {
            'total_samples': total_samples,
            'n_anomalies': int(n_anomalies),
            'anomaly_ratio': anomaly_ratio,
            'mean_z_score': results['z_score'].mean(),
            'max_abs_z_score': results['abs_z_score'].max(),
            'threshold': self.threshold
        }

        # 異常樣本的 Z-score 統計
        if n_anomalies > 0:
            anomaly_z_scores = results.loc[results['anomaly'], 'abs_z_score']
            stats['anomaly_mean_z_score'] = anomaly_z_scores.mean()
            stats['anomaly_max_z_score'] = anomaly_z_scores.max()

        return stats


class MADDetector:
    """
    MAD (Median Absolute Deviation) 異常檢測器

    比 Z-Score 更 robust，對離群值不敏感：
    - MAD = median(|x - median(x)|)
    - Modified Z-score = 0.6745 * (x - median) / MAD
    """

    def __init__(
        self,
        threshold: float = 3.5,
        window: Optional[int] = None
    ):
        """
        初始化 MAD 檢測器

        Args:
            threshold: Modified Z-score 閾值（通常 3.5）
            window: 滾動窗口大小（None 為使用全局統計）
        """
        self.threshold = threshold
        self.window = window

        # 全局統計量
        self.median = None
        self.mad = None

        self.model_name = f"MAD_t{threshold}_w{window if window else 'global'}"

    def _calculate_mad(self, data: pd.Series) -> Tuple[float, float]:
        """
        計算 MAD

        Args:
            data: 資料序列

        Returns:
            (median, mad)
        """
        median = data.median()
        mad = np.median(np.abs(data - median))
        return median, mad

    def fit(
        self,
        prices: pd.Series,
        return_based: bool = True
    ) -> 'MADDetector':
        """
        計算統計量（訓練）

        Args:
            prices: 價格序列
            return_based: 是否使用報酬率

        Returns:
            self
        """
        logger.info(f"訓練 {self.model_name}")

        # 計算報酬率或使用原始價格
        if return_based:
            data = prices.pct_change().dropna()
        else:
            data = prices.dropna()

        # 如果不使用滾動窗口，計算全局統計量
        if self.window is None:
            self.median, self.mad = self._calculate_mad(data)
            logger.info(f"全局統計: median={self.median:.6f}, MAD={self.mad:.6f}")
        else:
            logger.info(f"使用滾動窗口: {self.window}")

        return self

    def predict(
        self,
        prices: pd.Series,
        return_based: bool = True
    ) -> pd.DataFrame:
        """
        檢測異常

        Args:
            prices: 價格序列
            return_based: 是否使用報酬率

        Returns:
            包含異常標記和 Modified Z-score 的 DataFrame
        """
        # 計算報酬率或使用原始價格
        if return_based:
            data = prices.pct_change()
        else:
            data = prices.copy()

        results = pd.DataFrame(index=data.index)
        results['price'] = prices

        # 計算 Modified Z-score
        if self.window is None:
            # 全局統計
            if self.median is None or self.mad is None:
                raise ValueError("模型尚未訓練，請先調用 fit() 方法")

            # Modified Z-score = 0.6745 * (x - median) / MAD
            modified_z_scores = 0.6745 * (data - self.median) / (self.mad + 1e-10)
        else:
            # 滾動統計
            rolling_median = data.rolling(self.window).median()
            rolling_mad = data.rolling(self.window).apply(
                lambda x: np.median(np.abs(x - np.median(x))),
                raw=True
            )
            modified_z_scores = 0.6745 * (data - rolling_median) / (rolling_mad + 1e-10)

        results['modified_z_score'] = modified_z_scores
        results['abs_modified_z_score'] = np.abs(modified_z_scores)
        results['anomaly'] = results['abs_modified_z_score'] > self.threshold

        # 移除 NaN
        results = results.dropna()

        return results

    def get_anomaly_statistics(
        self,
        results: pd.DataFrame
    ) -> Dict[str, float]:
        """
        計算異常統計資訊

        Args:
            results: predict() 返回的結果

        Returns:
            統計資訊字典
        """
        total_samples = len(results)
        n_anomalies = results['anomaly'].sum()
        anomaly_ratio = n_anomalies / total_samples * 100

        stats = {
            'total_samples': total_samples,
            'n_anomalies': int(n_anomalies),
            'anomaly_ratio': anomaly_ratio,
            'mean_modified_z_score': results['modified_z_score'].mean(),
            'max_abs_modified_z_score': results['abs_modified_z_score'].max(),
            'threshold': self.threshold
        }

        # 異常樣本的統計
        if n_anomalies > 0:
            anomaly_scores = results.loc[results['anomaly'], 'abs_modified_z_score']
            stats['anomaly_mean_score'] = anomaly_scores.mean()
            stats['anomaly_max_score'] = anomaly_scores.max()

        return stats


class CompositeDetector:
    """
    組合檢測器

    結合多個檢測器的結果，提高檢測準確性
    """

    def __init__(
        self,
        detectors: list,
        voting_strategy: str = 'any'
    ):
        """
        初始化組合檢測器

        Args:
            detectors: 檢測器列表
            voting_strategy: 投票策略 ('any', 'majority', 'all')
        """
        self.detectors = detectors
        self.voting_strategy = voting_strategy

    def predict(
        self,
        prices: pd.Series,
        **kwargs
    ) -> pd.DataFrame:
        """
        使用所有檢測器進行檢測並組合結果

        Args:
            prices: 價格序列
            **kwargs: 傳遞給檢測器的參數

        Returns:
            組合檢測結果
        """
        all_results = []

        for i, detector in enumerate(self.detectors):
            result = detector.predict(prices, **kwargs)
            result = result.rename(columns={'anomaly': f'anomaly_{i}'})
            all_results.append(result[['price', f'anomaly_{i}']])

        # 合併所有結果
        combined = pd.concat(all_results, axis=1)
        combined = combined.loc[:, ~combined.columns.duplicated()]  # 移除重複的 price 列

        # 根據投票策略決定最終異常
        anomaly_cols = [col for col in combined.columns if col.startswith('anomaly_')]

        if self.voting_strategy == 'any':
            combined['anomaly'] = combined[anomaly_cols].any(axis=1)
        elif self.voting_strategy == 'all':
            combined['anomaly'] = combined[anomaly_cols].all(axis=1)
        elif self.voting_strategy == 'majority':
            combined['anomaly'] = combined[anomaly_cols].sum(axis=1) > len(anomaly_cols) / 2
        else:
            raise ValueError(f"Unknown voting strategy: {self.voting_strategy}")

        combined['n_detectors_flagged'] = combined[anomaly_cols].sum(axis=1)

        return combined
