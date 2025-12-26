"""
XGBoost 價格預測模型

使用 XGBoost (eXtreme Gradient Boosting) 進行時間序列預測。
XGBoost 是基於梯度提升決策樹的模型，特別適合結構化特徵與非線性關係學習。
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb
import logging
import joblib

logger = logging.getLogger(__name__)


class XGBoostForecast:
    """
    XGBoost 價格預測器

    主要功能：
    - 時間序列資料 + 技術指標特徵處理
    - XGBoost 模型訓練
    - 價格預測
    - 模型評估與保存
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: int = 1,
        gamma: float = 0,
        reg_alpha: float = 0,
        reg_lambda: float = 1,
        random_state: int = 42,
        n_jobs: int = -1,
        early_stopping_rounds: Optional[int] = 10
    ):
        """
        初始化 XGBoost 預測器

        Args:
            n_estimators: 樹的數量
            max_depth: 樹的最大深度
            learning_rate: 學習率
            subsample: 樣本採樣比例
            colsample_bytree: 特徵採樣比例
            min_child_weight: 最小子節點權重
            gamma: 分裂所需最小損失減少
            reg_alpha: L1 正則化係數
            reg_lambda: L2 正則化係數
            random_state: 隨機種子
            n_jobs: 並行數 (-1 為使用所有核心)
            early_stopping_rounds: 早停輪數
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.min_child_weight = min_child_weight
        self.gamma = gamma
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.early_stopping_rounds = early_stopping_rounds

        # 標準化器
        self.scaler = StandardScaler()

        # 模型
        self.model = None

        # 特徵名稱
        self.feature_names = None

        # 訓練歷史
        self.eval_results = {}

        self.model_name = f"XGBoost_n{n_estimators}_d{max_depth}_lr{learning_rate}"

    def _create_lag_features(
        self,
        data: pd.Series,
        lag_periods: List[int] = [1, 2, 3, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        創建滯後特徵

        Args:
            data: 價格序列
            lag_periods: 滯後週期列表

        Returns:
            包含滯後特徵的 DataFrame
        """
        features = pd.DataFrame(index=data.index)

        for lag in lag_periods:
            features[f'lag_{lag}'] = data.shift(lag)

        return features

    def _create_rolling_features(
        self,
        data: pd.Series,
        windows: List[int] = [5, 10, 20]
    ) -> pd.DataFrame:
        """
        創建滾動窗口特徵

        Args:
            data: 價格序列
            windows: 窗口大小列表

        Returns:
            包含滾動特徵的 DataFrame
        """
        features = pd.DataFrame(index=data.index)

        for window in windows:
            features[f'rolling_mean_{window}'] = data.rolling(window).mean()
            features[f'rolling_std_{window}'] = data.rolling(window).std()
            features[f'rolling_min_{window}'] = data.rolling(window).min()
            features[f'rolling_max_{window}'] = data.rolling(window).max()

        return features

    def _create_return_features(
        self,
        data: pd.Series,
        periods: List[int] = [1, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        創建報酬率特徵

        Args:
            data: 價格序列
            periods: 報酬週期列表

        Returns:
            包含報酬特徵的 DataFrame
        """
        features = pd.DataFrame(index=data.index)

        for period in periods:
            features[f'return_{period}'] = data.pct_change(period)

        return features

    def _prepare_features(
        self,
        y: pd.Series,
        external_features: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        準備所有特徵

        Args:
            y: 目標序列（價格）
            external_features: 外部特徵（技術指標等）

        Returns:
            完整特徵 DataFrame
        """
        # 時間序列特徵
        lag_features = self._create_lag_features(y)
        rolling_features = self._create_rolling_features(y)
        return_features = self._create_return_features(y)

        # 合併所有特徵
        features = pd.concat([
            lag_features,
            rolling_features,
            return_features
        ], axis=1)

        # 添加外部特徵（如技術指標）
        if external_features is not None:
            features = pd.concat([features, external_features], axis=1)

        return features

    def fit(
        self,
        y_train: pd.Series,
        external_features: Optional[pd.DataFrame] = None,
        val_ratio: float = 0.2,
        verbose: bool = True
    ) -> 'XGBoostForecast':
        """
        訓練 XGBoost 模型

        Args:
            y_train: 訓練資料（價格序列）
            external_features: 外部特徵（技術指標等）
            val_ratio: 驗證集比例
            verbose: 是否顯示訓練進度

        Returns:
            self
        """
        logger.info(f"開始訓練 {self.model_name}")

        # 準備特徵
        X = self._prepare_features(y_train, external_features)
        y = y_train.copy()

        # 對齊索引（移除 NaN）
        valid_idx = X.notna().all(axis=1) & y.notna()
        X = X[valid_idx]
        y = y[valid_idx]

        # 保存特徵名稱
        self.feature_names = X.columns.tolist()

        # 分割訓練集與驗證集
        split_idx = int(len(X) * (1 - val_ratio))
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train_split, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        # 標準化特徵
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)

        # 初始化模型
        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            min_child_weight=self.min_child_weight,
            gamma=self.gamma,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            objective='reg:squarederror'
        )

        # 訓練模型（新版 XGBoost API）
        eval_set = [(X_train_scaled, y_train_split), (X_val_scaled, y_val)]

        if self.early_stopping_rounds is not None:
            self.model.set_params(early_stopping_rounds=self.early_stopping_rounds)

        self.model.fit(
            X_train_scaled,
            y_train_split,
            eval_set=eval_set,
            verbose=verbose
        )

        # 保存評估結果
        self.eval_results = self.model.evals_result()

        logger.info(f"訓練完成，最佳迭代: {self.model.best_iteration}")
        logger.info(f"訓練集大小: {len(X_train)}, 驗證集大小: {len(X_val)}")

        return self

    def predict(
        self,
        y: pd.Series,
        external_features: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        進行預測

        Args:
            y: 歷史資料
            external_features: 外部特徵

        Returns:
            預測值陣列
        """
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 fit() 方法")

        # 準備特徵
        X = self._prepare_features(y, external_features)

        # 移除 NaN
        valid_idx = X.notna().all(axis=1)
        X_valid = X[valid_idx]

        # 標準化
        X_scaled = self.scaler.transform(X_valid)

        # 預測
        predictions = self.model.predict(X_scaled)

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
        # 對齊長度
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true.iloc[-min_len:].values
        y_pred = y_pred[-min_len:]

        # 計算指標
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        # MAPE（避免除零）
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

        # 方向準確率
        if len(y_true) > 1:
            true_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            direction_accuracy = np.mean(true_direction == pred_direction) * 100
        else:
            direction_accuracy = 0.0

        metrics = {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape,
            'direction_accuracy': direction_accuracy
        }

        return metrics

    def get_feature_importance(
        self,
        importance_type: str = 'gain'
    ) -> pd.DataFrame:
        """
        獲取特徵重要性

        Args:
            importance_type: 重要性類型 ('gain', 'weight', 'cover')

        Returns:
            特徵重要性 DataFrame
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")

        importance = self.model.get_booster().get_score(
            importance_type=importance_type
        )

        # 轉換為 DataFrame
        importance_df = pd.DataFrame({
            'feature': list(importance.keys()),
            'importance': list(importance.values())
        }).sort_values('importance', ascending=False)

        return importance_df

    def save_model(self, path: str):
        """
        保存模型

        Args:
            path: 保存路徑
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'config': {
                'n_estimators': self.n_estimators,
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'subsample': self.subsample,
                'colsample_bytree': self.colsample_bytree
            },
            'eval_results': self.eval_results
        }

        joblib.dump(model_data, path)
        logger.info(f"模型已保存至 {path}")

    def load_model(self, path: str):
        """
        載入模型

        Args:
            path: 模型路徑
        """
        model_data = joblib.load(path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']

        config = model_data['config']
        self.n_estimators = config['n_estimators']
        self.max_depth = config['max_depth']
        self.learning_rate = config['learning_rate']
        self.subsample = config['subsample']
        self.colsample_bytree = config['colsample_bytree']

        self.eval_results = model_data.get('eval_results', {})

        logger.info(f"模型已從 {path} 載入")

    def get_training_history(self) -> pd.DataFrame:
        """
        獲取訓練歷史

        Returns:
            包含訓練和驗證損失的 DataFrame
        """
        if not self.eval_results:
            return pd.DataFrame()

        history = {
            'iteration': range(len(self.eval_results['validation_0']['rmse'])),
            'train_rmse': self.eval_results['validation_0']['rmse'],
            'val_rmse': self.eval_results['validation_1']['rmse']
        }

        return pd.DataFrame(history)
