"""
移動平均預測模型（Baseline）

這是最簡單的預測模型，作為其他模型的 baseline。
使用移動平均線來預測未來價格。
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


class MovingAverageForecast:
    """
    移動平均預測器

    預測方法：使用過去 N 期的平均值作為未來的預測值
    """

    def __init__(self, window: int = 20):
        """
        初始化預測器

        Args:
            window: 移動平均窗口大小
        """
        self.window = window
        self.model_name = f"MA_{window}"

    def fit(self, y_train: pd.Series) -> 'MovingAverageForecast':
        """
        訓練模型（移動平均不需要訓練，這裡僅為保持 API 一致性）

        Args:
            y_train: 訓練資料

        Returns:
            self
        """
        # 移動平均模型不需要訓練
        return self

    def predict(self, y: pd.Series, steps: int = 1) -> np.ndarray:
        """
        進行預測

        Args:
            y: 歷史資料
            steps: 預測步數

        Returns:
            預測值陣列
        """
        # 使用滾動窗口計算預測值
        predictions = y.rolling(window=self.window).mean().values

        # 移除前面的 NaN 值
        predictions = predictions[self.window-1:]

        return predictions

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        評估模型性能

        Args:
            y_true: 真實值
            y_pred: 預測值

        Returns:
            評估指標字典
        """
        # 確保長度一致
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true.iloc[-min_len:]
        y_pred = y_pred[-min_len:]

        metrics = {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred),
            'mape': np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        }

        return metrics


class ExponentialMovingAverageForecast:
    """
    指數移動平均預測器

    相比簡單移動平均，給予近期資料更高的權重
    """

    def __init__(self, span: int = 20):
        """
        初始化預測器

        Args:
            span: EMA 的 span 參數
        """
        self.span = span
        self.model_name = f"EMA_{span}"

    def fit(self, y_train: pd.Series) -> 'ExponentialMovingAverageForecast':
        """訓練模型"""
        return self

    def predict(self, y: pd.Series, steps: int = 1) -> np.ndarray:
        """
        進行預測

        Args:
            y: 歷史資料
            steps: 預測步數

        Returns:
            預測值陣列
        """
        # 計算 EMA
        ema = y.ewm(span=self.span, adjust=False).mean()

        return ema.values

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """評估模型性能"""
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true.iloc[-min_len:]
        y_pred = y_pred[-min_len:]

        metrics = {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred),
            'mape': np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        }

        return metrics


class NaiveForecast:
    """
    樸素預測器（最簡單的 baseline）

    預測方法：使用最後一個觀測值作為預測值
    """

    def __init__(self):
        self.model_name = "Naive"

    def fit(self, y_train: pd.Series) -> 'NaiveForecast':
        """訓練模型"""
        return self

    def predict(self, y: pd.Series, steps: int = 1) -> np.ndarray:
        """
        進行預測

        Args:
            y: 歷史資料
            steps: 預測步數

        Returns:
            預測值陣列
        """
        # 每個預測都是前一個值
        predictions = []
        for i in range(1, len(y)):
            predictions.append(y.iloc[i - 1])

        return np.array(predictions)

    def evaluate(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """評估模型性能"""
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true.iloc[-min_len:]
        y_pred = y_pred[-min_len:]

        metrics = {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred),
            'mape': np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        }

        return metrics


def compare_baseline_models(
    y: pd.Series,
    train_ratio: float = 0.8,
    windows: List[int] = [10, 20, 50]
) -> pd.DataFrame:
    """
    比較不同 baseline 模型的性能

    Args:
        y: 時間序列資料
        train_ratio: 訓練集比例
        windows: 移動平均窗口大小列表

    Returns:
        包含各模型評估指標的 DataFrame
    """
    # 分割訓練和測試集
    split_idx = int(len(y) * train_ratio)
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    results = []

    # 樸素預測
    naive_model = NaiveForecast()
    naive_model.fit(y_train)
    naive_pred = naive_model.predict(y_test)
    naive_metrics = naive_model.evaluate(y_test, naive_pred)
    naive_metrics['model'] = 'Naive'
    results.append(naive_metrics)

    # 不同窗口的 MA
    for window in windows:
        ma_model = MovingAverageForecast(window=window)
        ma_model.fit(y_train)
        ma_pred = ma_model.predict(y_test)
        ma_metrics = ma_model.evaluate(y_test, ma_pred)
        ma_metrics['model'] = f'MA_{window}'
        results.append(ma_metrics)

    # 不同 span 的 EMA
    for span in windows:
        ema_model = ExponentialMovingAverageForecast(span=span)
        ema_model.fit(y_train)
        ema_pred = ema_model.predict(y_test)
        ema_metrics = ema_model.evaluate(y_test, ema_pred)
        ema_metrics['model'] = f'EMA_{span}'
        results.append(ema_metrics)

    # 轉換為 DataFrame
    results_df = pd.DataFrame(results)
    results_df = results_df[[
        'model', 'mse', 'rmse', 'mae', 'r2', 'mape'
    ]].sort_values('rmse')

    return results_df
