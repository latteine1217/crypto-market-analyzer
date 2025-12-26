"""
LSTM 價格預測模型

使用 Long Short-Term Memory (LSTM) 神經網絡進行時間序列預測。
LSTM 能夠學習時間序列中的長期依賴關係，適合金融市場價格預測。
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import logging

logger = logging.getLogger(__name__)


class LSTMModel(nn.Module):
    """
    LSTM 神經網絡模型

    架構：
    - LSTM 層（可多層堆疊）
    - Dropout 層（防止過擬合）
    - 全連接層（輸出預測值）
    """

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 50,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2
    ):
        """
        初始化 LSTM 模型

        Args:
            input_size: 輸入特徵數量
            hidden_size: LSTM 隱藏層大小
            num_layers: LSTM 層數
            output_size: 輸出大小（預測步數）
            dropout: Dropout 比例
        """
        super(LSTMModel, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # LSTM 層
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # Dropout 層
        self.dropout = nn.Dropout(dropout)

        # 全連接層
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        """
        前向傳播

        Args:
            x: 輸入張量 (batch_size, seq_length, input_size)

        Returns:
            預測值 (batch_size, output_size)
        """
        # LSTM 輸出: (batch_size, seq_length, hidden_size)
        lstm_out, _ = self.lstm(x)

        # 取最後一個時間步的輸出
        last_output = lstm_out[:, -1, :]

        # Dropout
        dropped = self.dropout(last_output)

        # 全連接層
        output = self.fc(dropped)

        return output


class LSTMForecast:
    """
    LSTM 價格預測器

    主要功能：
    - 時間序列資料預處理
    - LSTM 模型訓練
    - 價格預測
    - 模型評估與保存
    """

    def __init__(
        self,
        sequence_length: int = 60,
        hidden_size: int = 50,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        batch_size: int = 32,
        epochs: int = 50,
        device: Optional[str] = None
    ):
        """
        初始化 LSTM 預測器

        Args:
            sequence_length: 輸入序列長度（使用過去 N 個時間點預測）
            hidden_size: LSTM 隱藏層大小
            num_layers: LSTM 層數
            dropout: Dropout 比例
            learning_rate: 學習率
            batch_size: 批次大小
            epochs: 訓練輪數
            device: 計算設備 ('cpu', 'cuda', 'mps' 或 None 自動選擇)
        """
        self.sequence_length = sequence_length
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs

        # 自動選擇設備
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            elif torch.backends.mps.is_available():
                self.device = torch.device('mps')
            else:
                self.device = torch.device('cpu')
        else:
            self.device = torch.device(device)

        logger.info(f"使用設備: {self.device}")

        # 資料縮放器
        self.scaler = MinMaxScaler(feature_range=(0, 1))

        # 模型（延遲初始化）
        self.model = None

        # 訓練歷史
        self.train_losses = []
        self.val_losses = []

        self.model_name = f"LSTM_seq{sequence_length}_h{hidden_size}_l{num_layers}"

    def _create_sequences(
        self,
        data: np.ndarray,
        target: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        創建時間序列訓練樣本

        Args:
            data: 輸入資料 (n_samples, n_features)
            target: 目標資料 (n_samples,)，如果為 None 則使用 data 作為目標

        Returns:
            X: 序列特徵 (n_sequences, sequence_length, n_features)
            y: 目標值 (n_sequences,) 或 None
        """
        X, y = [], []

        if target is None:
            target = data[:, 0] if len(data.shape) > 1 else data

        for i in range(len(data) - self.sequence_length):
            # 輸入序列
            X.append(data[i:i + self.sequence_length])
            # 目標值（下一個時間點的價格）
            y.append(target[i + self.sequence_length])

        return np.array(X), np.array(y) if len(y) > 0 else None

    def _prepare_data(
        self,
        y: pd.Series,
        features: Optional[pd.DataFrame] = None,
        val_ratio: float = 0.2
    ) -> Tuple[DataLoader, DataLoader]:
        """
        準備訓練資料

        Args:
            y: 目標序列（價格）
            features: 額外特徵（可選）
            val_ratio: 驗證集比例

        Returns:
            train_loader: 訓練資料載入器
            val_loader: 驗證資料載入器
        """
        # 準備輸入資料
        if features is not None:
            # 合併價格與特徵
            data = np.column_stack([y.values.reshape(-1, 1), features.values])
        else:
            data = y.values.reshape(-1, 1)

        # 資料標準化
        scaled_data = self.scaler.fit_transform(data)

        # 創建序列
        X, y_target = self._create_sequences(scaled_data)

        # 分割訓練集與驗證集
        split_idx = int(len(X) * (1 - val_ratio))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y_target[:split_idx], y_target[split_idx:]

        # 轉換為 PyTorch 張量
        X_train_tensor = torch.FloatTensor(X_train).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1).to(self.device)
        X_val_tensor = torch.FloatTensor(X_val).to(self.device)
        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1).to(self.device)

        # 創建資料載入器
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        val_dataset = TensorDataset(X_val_tensor, y_val_tensor)

        train_loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.batch_size,
            shuffle=False
        )

        logger.info(f"訓練集大小: {len(X_train)}, 驗證集大小: {len(X_val)}")

        return train_loader, val_loader

    def fit(
        self,
        y_train: pd.Series,
        features: Optional[pd.DataFrame] = None,
        val_ratio: float = 0.2,
        early_stopping_patience: int = 10,
        verbose: bool = True
    ) -> 'LSTMForecast':
        """
        訓練 LSTM 模型

        Args:
            y_train: 訓練資料（價格序列）
            features: 額外特徵
            val_ratio: 驗證集比例
            early_stopping_patience: 早停耐心值
            verbose: 是否顯示訓練進度

        Returns:
            self
        """
        logger.info(f"開始訓練 {self.model_name}")

        # 準備資料
        train_loader, val_loader = self._prepare_data(
            y_train, features, val_ratio
        )

        # 初始化模型
        input_size = train_loader.dataset[0][0].shape[1]
        self.model = LSTMModel(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            output_size=1,
            dropout=self.dropout
        ).to(self.device)

        # 損失函數與優化器
        criterion = nn.MSELoss()
        optimizer = optim.Adam(
            self.model.parameters(),
            lr=self.learning_rate
        )

        # 早停機制
        best_val_loss = float('inf')
        patience_counter = 0

        # 訓練循環
        for epoch in range(self.epochs):
            # 訓練階段
            self.model.train()
            train_loss = 0.0
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)
            self.train_losses.append(avg_train_loss)

            # 驗證階段
            self.model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    outputs = self.model(X_batch)
                    loss = criterion(outputs, y_batch)
                    val_loss += loss.item()

            avg_val_loss = val_loss / len(val_loader)
            self.val_losses.append(avg_val_loss)

            # 顯示進度
            if verbose and (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch [{epoch+1}/{self.epochs}] - "
                    f"Train Loss: {avg_train_loss:.6f}, "
                    f"Val Loss: {avg_val_loss:.6f}"
                )

            # 早停檢查
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                patience_counter = 0
                # 保存最佳模型
                self.best_model_state = self.model.state_dict()
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    logger.info(f"早停於 epoch {epoch+1}")
                    break

        # 載入最佳模型
        if hasattr(self, 'best_model_state'):
            self.model.load_state_dict(self.best_model_state)

        logger.info("訓練完成")
        return self

    def predict(
        self,
        y: pd.Series,
        features: Optional[pd.DataFrame] = None,
        steps: int = 1
    ) -> np.ndarray:
        """
        進行預測

        Args:
            y: 歷史資料
            features: 額外特徵
            steps: 預測步數（目前僅支持 1）

        Returns:
            預測值陣列
        """
        if self.model is None:
            raise ValueError("模型尚未訓練，請先調用 fit() 方法")

        self.model.eval()

        # 準備輸入資料
        if features is not None:
            data = np.column_stack([y.values.reshape(-1, 1), features.values])
        else:
            data = y.values.reshape(-1, 1)

        # 資料標準化
        scaled_data = self.scaler.transform(data)

        # 創建序列
        X, _ = self._create_sequences(scaled_data)

        # 轉換為張量
        X_tensor = torch.FloatTensor(X).to(self.device)

        # 預測
        with torch.no_grad():
            predictions = self.model(X_tensor)

        # 反標準化
        predictions_np = predictions.cpu().numpy()

        # 創建虛擬資料用於反標準化（保持維度一致）
        dummy_data = np.zeros((len(predictions_np), data.shape[1]))
        dummy_data[:, 0] = predictions_np.flatten()
        predictions_unscaled = self.scaler.inverse_transform(dummy_data)[:, 0]

        return predictions_unscaled

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

        # 方向準確率（預測漲跌方向的準確率）
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

    def save_model(self, path: str):
        """
        保存模型

        Args:
            path: 保存路徑
        """
        if self.model is None:
            raise ValueError("模型尚未訓練")

        torch.save({
            'model_state_dict': self.model.state_dict(),
            'scaler': self.scaler,
            'config': {
                'sequence_length': self.sequence_length,
                'hidden_size': self.hidden_size,
                'num_layers': self.num_layers,
                'dropout': self.dropout
            },
            'train_losses': self.train_losses,
            'val_losses': self.val_losses
        }, path)

        logger.info(f"模型已保存至 {path}")

    def load_model(self, path: str):
        """
        載入模型

        Args:
            path: 模型路徑
        """
        checkpoint = torch.load(path, map_location=self.device)

        # 載入配置
        config = checkpoint['config']
        self.sequence_length = config['sequence_length']
        self.hidden_size = config['hidden_size']
        self.num_layers = config['num_layers']
        self.dropout = config['dropout']

        # 載入縮放器
        self.scaler = checkpoint['scaler']

        # 重建模型
        input_size = 1  # 預設值，實際使用時會根據輸入調整
        self.model = LSTMModel(
            input_size=input_size,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            output_size=1,
            dropout=self.dropout
        ).to(self.device)

        # 載入權重
        self.model.load_state_dict(checkpoint['model_state_dict'])

        # 載入訓練歷史
        self.train_losses = checkpoint.get('train_losses', [])
        self.val_losses = checkpoint.get('val_losses', [])

        logger.info(f"模型已從 {path} 載入")

    def get_training_history(self) -> pd.DataFrame:
        """
        獲取訓練歷史

        Returns:
            包含訓練和驗證損失的 DataFrame
        """
        return pd.DataFrame({
            'epoch': range(1, len(self.train_losses) + 1),
            'train_loss': self.train_losses,
            'val_loss': self.val_losses
        })
