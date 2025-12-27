"""
簡化版 LSTM 訓練腳本
使用最重要的特徵和診斷中證明有效的架構
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import psycopg2
import logging
import json
from pathlib import Path
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Top 15 most important features from XGBoost
TOP_FEATURES = [
    'ema_5', 'rolling_mean_5', 'rolling_max_5', 'lag_1', 'rolling_mean_10',
    'rolling_max_20', 'rolling_min_5', 'rolling_max_10', 'ema_10', 'rolling_min_20',
    'ema_20', 'rolling_min_10', 'ema_50', 'bb_middle_20', 'vwap_20'
]

class SimpleLSTMModel(nn.Module):
    """簡單的 LSTM 模型架構（基於診斷腳本）"""

    def __init__(self, input_size, hidden_size=32, num_layers=1):
        super(SimpleLSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.0 if num_layers == 1 else 0.2
        )

        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # LSTM 前向傳播
        lstm_out, _ = self.lstm(x)

        # 取最後一個時間步的輸出
        last_output = lstm_out[:, -1, :]

        # 全連接層預測
        predictions = self.fc(last_output)

        return predictions


def load_data_from_db():
    """從資料庫載入數據"""
    logger.info("從資料庫載入數據...")

    conn = psycopg2.connect(
        host='localhost',
        database='crypto_db',
        user='crypto',
        password='crypto_pass'
    )

    query = """
        SELECT o.open_time, o.open, o.high, o.low, o.close, o.volume, o.quote_volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = 'bybit'
            AND m.symbol = 'BTC/USDT'
            AND o.timeframe = '1h'
        ORDER BY o.open_time
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"載入 {len(df)} 筆數據")
    logger.info(f"時間範圍: {df['open_time'].min()} ~ {df['open_time'].max()}")

    return df


def create_features(df):
    """創建特徵（只創建 TOP_FEATURES）"""
    logger.info("創建特徵...")

    from src.features.technical_indicators import TechnicalIndicators
    from src.features.price_features import PriceFeatures
    from src.features.volume_features import VolumeFeatures

    # 創建所有特徵
    tech_indicators = TechnicalIndicators()
    price_features = PriceFeatures()
    volume_features = VolumeFeatures()

    tech_feat = tech_indicators.calculate_all(df)
    price_feat = price_features.calculate_all(df)
    volume_feat = volume_features.calculate_all(df)

    # 合併特徵（避免重複）
    tech_cols = [col for col in tech_feat.columns
                if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    price_cols = [col for col in price_feat.columns
                 if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    volume_cols = [col for col in volume_feat.columns
                  if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]

    features = pd.concat([
        tech_feat[tech_cols],
        price_feat[price_cols],
        volume_feat[volume_cols]
    ], axis=1)

    # 前向填充並刪除 NaN
    features = features.ffill().dropna()

    # 只保留 TOP_FEATURES
    available_features = [f for f in TOP_FEATURES if f in features.columns]
    logger.info(f"使用 {len(available_features)}/{len(TOP_FEATURES)} 個重要特徵")

    if len(available_features) < len(TOP_FEATURES):
        missing = set(TOP_FEATURES) - set(available_features)
        logger.warning(f"缺失特徵: {missing}")

    # 如果可用特徵太少，使用所有可用特徵
    if len(available_features) < 5:
        logger.warning(f"可用重要特徵太少({len(available_features)})，改用所有可用特徵")
        features_selected = features.copy()
        logger.info(f"使用所有 {len(features.columns)} 個特徵")
    else:
        features_selected = features[available_features].copy()

    return features_selected


def create_sequences(data, target, sequence_length=30):
    """創建 LSTM 序列"""
    logger.info(f"創建序列（序列長度={sequence_length}）...")

    X, y = [], []
    for i in range(len(data) - sequence_length):
        X.append(data[i:i + sequence_length])
        y.append(target[i + sequence_length])

    X = np.array(X)
    y = np.array(y)

    logger.info(f"序列創建完成: X shape={X.shape}, y shape={y.shape}")

    return X, y


def train_model(model, train_loader, val_loader, num_epochs=50, learning_rate=0.001, device='cpu'):
    """訓練模型"""
    logger.info(f"開始訓練（設備: {device}）...")

    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    train_losses = []
    val_losses = []
    best_val_loss = float('inf')
    patience = 10
    patience_counter = 0

    for epoch in range(num_epochs):
        # 訓練模式
        model.train()
        train_loss = 0.0
        train_batches = 0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            # 前向傳播
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)

            # 反向傳播
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_batches += 1

        avg_train_loss = train_loss / train_batches
        train_losses.append(avg_train_loss)

        # 驗證模式
        model.eval()
        val_loss = 0.0
        val_batches = 0

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch = X_batch.to(device)
                y_batch = y_batch.to(device)

                predictions = model(X_batch)
                loss = criterion(predictions, y_batch)

                val_loss += loss.item()
                val_batches += 1

        avg_val_loss = val_loss / val_batches
        val_losses.append(avg_val_loss)

        logger.info(f"Epoch {epoch + 1}/{num_epochs} - Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")

        # Early stopping
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break

    return train_losses, val_losses


def evaluate_model(model, test_loader, scaler_y, device='cpu'):
    """評估模型"""
    logger.info("評估模型...")

    model.eval()
    predictions = []
    actuals = []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)

            pred = model(X_batch)
            predictions.extend(pred.cpu().numpy())
            actuals.extend(y_batch.numpy())

    predictions = np.array(predictions).reshape(-1, 1)
    actuals = np.array(actuals).reshape(-1, 1)

    # 反標準化
    predictions_original = scaler_y.inverse_transform(predictions).flatten()
    actuals_original = scaler_y.inverse_transform(actuals).flatten()

    # 計算指標
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    rmse = np.sqrt(mean_squared_error(actuals_original, predictions_original))
    mae = mean_absolute_error(actuals_original, predictions_original)
    r2 = r2_score(actuals_original, predictions_original)
    mape = np.mean(np.abs((actuals_original - predictions_original) / actuals_original)) * 100

    # 方向準確率
    actual_direction = np.diff(actuals_original) > 0
    pred_direction = np.diff(predictions_original) > 0
    direction_accuracy = np.mean(actual_direction == pred_direction) * 100

    metrics = {
        'RMSE': rmse,
        'MAE': mae,
        'R2': r2,
        'MAPE': mape,
        'Direction_Accuracy': direction_accuracy
    }

    logger.info("測試集性能:")
    for metric, value in metrics.items():
        logger.info(f"  {metric}: {value:.4f}")

    return metrics, predictions_original, actuals_original


def save_results(model, metrics, predictions, actuals, train_losses, val_losses, config):
    """保存結果"""
    logger.info("保存結果...")

    # 創建輸出目錄
    output_dir = Path('results/lstm_btc_1h')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存模型
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': config
    }, output_dir / 'lstm_model.pth')

    # 保存指標
    with open(output_dir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # 保存預測結果
    results_df = pd.DataFrame({
        'actual': actuals,
        'predicted': predictions,
        'error': actuals - predictions
    })
    results_df.to_csv(output_dir / 'predictions.csv', index=False)

    # 繪製結果
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # 實際 vs 預測
    axes[0, 0].plot(actuals, label='Actual', alpha=0.7)
    axes[0, 0].plot(predictions, label='Predicted', alpha=0.7)
    axes[0, 0].set_title('Actual vs Predicted Prices')
    axes[0, 0].set_xlabel('Sample')
    axes[0, 0].set_ylabel('Price (USDT)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # 誤差分布
    errors = actuals - predictions
    axes[0, 1].hist(errors, bins=50, edgecolor='black', alpha=0.7)
    axes[0, 1].set_title('Prediction Error Distribution')
    axes[0, 1].set_xlabel('Error (USDT)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].grid(True, alpha=0.3)

    # 訓練歷史
    axes[1, 0].plot(train_losses, label='Train Loss')
    axes[1, 0].plot(val_losses, label='Val Loss')
    axes[1, 0].set_title('Training History')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('Loss')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # 散點圖
    axes[1, 1].scatter(actuals, predictions, alpha=0.5)
    axes[1, 1].plot([actuals.min(), actuals.max()],
                    [actuals.min(), actuals.max()],
                    'r--', linewidth=2)
    axes[1, 1].set_title('Predicted vs Actual Scatter')
    axes[1, 1].set_xlabel('Actual Price (USDT)')
    axes[1, 1].set_ylabel('Predicted Price (USDT)')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'lstm_evaluation.png', dpi=150, bbox_inches='tight')
    logger.info(f"結果已保存至 {output_dir}")


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始 LSTM 模型訓練（簡化版）")
    logger.info("=" * 80)

    # 1. 載入數據
    df = load_data_from_db()

    # 2. 創建特徵
    features = create_features(df)

    # 配置（在知道特徵數量後設置）
    config = {
        'sequence_length': 30,
        'hidden_size': 32,
        'num_layers': 1,
        'batch_size': 32,
        'num_epochs': 50,
        'learning_rate': 0.001,
        'train_split': 0.7,
        'val_split': 0.15,
        'test_split': 0.15,
        'num_features': features.shape[1],  # 使用實際特徵數量
        'device': 'cpu'
    }

    logger.info(f"配置: {json.dumps(config, indent=2)}")

    # 確保索引對齊
    df = df.loc[features.index]
    target = df['close'].values

    logger.info(f"特徵形狀: {features.shape}")
    logger.info(f"目標形狀: {target.shape}")

    # 3. 標準化
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()

    features_scaled = scaler_X.fit_transform(features)
    target_scaled = scaler_y.fit_transform(target.reshape(-1, 1)).flatten()

    # 4. 創建序列
    X, y = create_sequences(features_scaled, target_scaled, config['sequence_length'])

    # 5. 分割數據
    n_samples = len(X)
    train_size = int(n_samples * config['train_split'])
    val_size = int(n_samples * config['val_split'])

    X_train = X[:train_size]
    y_train = y[:train_size]

    X_val = X[train_size:train_size + val_size]
    y_val = y[train_size:train_size + val_size]

    X_test = X[train_size + val_size:]
    y_test = y[train_size + val_size:]

    logger.info(f"訓練集: {X_train.shape}, 驗證集: {X_val.shape}, 測試集: {X_test.shape}")

    # 6. 創建 DataLoader
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train).reshape(-1, 1)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val),
        torch.FloatTensor(y_val).reshape(-1, 1)
    )
    test_dataset = TensorDataset(
        torch.FloatTensor(X_test),
        torch.FloatTensor(y_test).reshape(-1, 1)
    )

    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=config['batch_size'], shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=config['batch_size'], shuffle=False)

    # 7. 創建模型
    model = SimpleLSTMModel(
        input_size=config['num_features'],
        hidden_size=config['hidden_size'],
        num_layers=config['num_layers']
    )

    logger.info(f"模型架構: {model}")

    # 8. 訓練模型
    train_losses, val_losses = train_model(
        model, train_loader, val_loader,
        num_epochs=config['num_epochs'],
        learning_rate=config['learning_rate'],
        device=config['device']
    )

    # 9. 評估模型
    metrics, predictions, actuals = evaluate_model(
        model, test_loader, scaler_y, device=config['device']
    )

    # 10. 保存結果
    save_results(model, metrics, predictions, actuals, train_losses, val_losses, config)

    logger.info("=" * 80)
    logger.info("LSTM 訓練完成！")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
