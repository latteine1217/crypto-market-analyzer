"""
完整特徵集 LSTM 訓練腳本
添加 lag 和 rolling 特徵以匹配 XGBoost
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


class ImprovedLSTMModel(nn.Module):
    """改進的 LSTM 模型架構"""

    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(ImprovedLSTMModel, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        # 添加批次歸一化
        self.batch_norm = nn.BatchNorm1d(hidden_size)

        # 全連接層
        self.fc1 = nn.Linear(hidden_size, hidden_size // 2)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_size // 2, 1)

    def forward(self, x):
        # LSTM 前向傳播
        lstm_out, _ = self.lstm(x)

        # 取最後一個時間步的輸出
        last_output = lstm_out[:, -1, :]

        # 批次歸一化
        last_output = self.batch_norm(last_output)

        # 全連接層
        out = self.fc1(last_output)
        out = self.relu(out)
        out = self.dropout(out)
        predictions = self.fc2(out)

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


def create_lag_features(data, lag_periods=[1, 2, 3, 5, 10, 20]):
    """創建滯後特徵"""
    features = pd.DataFrame(index=data.index)

    for lag in lag_periods:
        features[f'lag_{lag}'] = data.shift(lag)

    return features


def create_rolling_features(data, windows=[5, 10, 20, 50]):
    """創建滾動窗口特徵"""
    features = pd.DataFrame(index=data.index)

    for window in windows:
        features[f'rolling_mean_{window}'] = data.rolling(window).mean()
        features[f'rolling_std_{window}'] = data.rolling(window).std()
        features[f'rolling_min_{window}'] = data.rolling(window).min()
        features[f'rolling_max_{window}'] = data.rolling(window).max()

    return features


def create_return_features(data, periods=[1, 5, 10, 20]):
    """創建報酬率特徵"""
    features = pd.DataFrame(index=data.index)

    for period in periods:
        features[f'return_{period}'] = data.pct_change(period)

    return features


def create_all_features(df):
    """創建完整的特徵集"""
    logger.info("創建完整特徵集...")

    from src.features.technical_indicators import TechnicalIndicators
    from src.features.price_features import PriceFeatures
    from src.features.volume_features import VolumeFeatures

    # 1. 基於 close 價格的時間序列特徵
    close_price = df['close']
    lag_features = create_lag_features(close_price)
    rolling_features = create_rolling_features(close_price)
    return_features = create_return_features(close_price)

    logger.info(f"  時間序列特徵: lag={lag_features.shape[1]}, rolling={rolling_features.shape[1]}, return={return_features.shape[1]}")

    # 2. 技術指標特徵
    tech_indicators = TechnicalIndicators()
    price_features_obj = PriceFeatures()
    volume_features = VolumeFeatures()

    tech_feat = tech_indicators.calculate_all(df)
    price_feat = price_features_obj.calculate_all(df)
    volume_feat = volume_features.calculate_all(df)

    # 移除重複的 OHLCV 列
    tech_cols = [col for col in tech_feat.columns
                if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    price_cols = [col for col in price_feat.columns
                 if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
    volume_cols = [col for col in volume_feat.columns
                  if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]

    logger.info(f"  技術指標特徵: tech={len(tech_cols)}, price={len(price_cols)}, volume={len(volume_cols)}")

    # 3. 合併所有特徵
    features = pd.concat([
        lag_features,
        rolling_features,
        return_features,
        tech_feat[tech_cols],
        price_feat[price_cols],
        volume_feat[volume_cols]
    ], axis=1)

    # 前向填充並刪除 NaN
    features = features.ffill().dropna()

    # 確保只保留數值型列
    numeric_columns = features.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) < len(features.columns):
        non_numeric = set(features.columns) - set(numeric_columns)
        logger.warning(f"移除非數值列: {non_numeric}")
        features = features[numeric_columns]

    logger.info(f"合併後特徵總數: {features.shape[1]}")
    logger.info(f"特徵列表前 20: {list(features.columns[:20])}")

    return features


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


def train_model(model, train_loader, val_loader, num_epochs=100, learning_rate=0.001, device='cpu'):
    """訓練模型"""
    logger.info(f"開始訓練（設備: {device}）...")

    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # 學習率調度器
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5
    )

    train_losses = []
    val_losses = []
    best_val_loss = float('inf')
    patience = 15
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

            # 梯度裁剪
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

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

        # 學習率調度
        scheduler.step(avg_val_loss)

        if (epoch + 1) % 5 == 0 or epoch == 0:
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


def save_results(model, metrics, predictions, actuals, train_losses, val_losses, config, num_features):
    """保存結果"""
    logger.info("保存結果...")

    # 創建輸出目錄
    output_dir = Path('results/lstm_full_features_btc_1h')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存模型
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': config,
        'num_features': num_features
    }, output_dir / 'lstm_model.pth')

    # 保存指標
    with open(output_dir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # 保存配置
    config_with_features = config.copy()
    config_with_features['num_features'] = num_features
    with open(output_dir / 'config.json', 'w') as f:
        json.dump(config_with_features, f, indent=2)

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
    axes[0, 0].plot(actuals[:300], label='Actual', alpha=0.7, linewidth=1.5)
    axes[0, 0].plot(predictions[:300], label='Predicted', alpha=0.7, linewidth=1.5)
    axes[0, 0].set_title('Actual vs Predicted Prices (First 300 samples)')
    axes[0, 0].set_xlabel('Sample')
    axes[0, 0].set_ylabel('Price (USDT)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # 誤差分布
    errors = actuals - predictions
    axes[0, 1].hist(errors, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
    axes[0, 1].set_title(f'Prediction Error Distribution\nMean: {errors.mean():.2f}, Std: {errors.std():.2f}')
    axes[0, 1].set_xlabel('Error (USDT)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', linewidth=1)
    axes[0, 1].grid(True, alpha=0.3)

    # 訓練歷史
    axes[1, 0].plot(train_losses, label='Train Loss', linewidth=1.5)
    axes[1, 0].plot(val_losses, label='Val Loss', linewidth=1.5)
    axes[1, 0].set_title('Training History')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('Loss')
    axes[1, 0].set_yscale('log')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)

    # 散點圖
    axes[1, 1].scatter(actuals, predictions, alpha=0.3, s=10)
    axes[1, 1].plot([actuals.min(), actuals.max()],
                    [actuals.min(), actuals.max()],
                    'r--', linewidth=2, label='Perfect Prediction')
    axes[1, 1].set_title(f'Predicted vs Actual Scatter\nR² = {metrics["R2"]:.6f}')
    axes[1, 1].set_xlabel('Actual Price (USDT)')
    axes[1, 1].set_ylabel('Predicted Price (USDT)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'lstm_evaluation.png', dpi=150, bbox_inches='tight')
    logger.info(f"結果已保存至 {output_dir}")

    # 生成評估報告
    generate_report(metrics, config_with_features, output_dir)


def generate_report(metrics, config, output_dir):
    """生成評估報告"""
    report = f"""# LSTM 模型評估報告（完整特徵集）

**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 模型配置

- **特徵數量**: {config['num_features']} 個
- **序列長度**: {config['sequence_length']}
- **隱藏層大小**: {config['hidden_size']}
- **LSTM 層數**: {config['num_layers']}
- **Dropout**: {config['dropout']}
- **批次大小**: {config['batch_size']}
- **最大訓練輪數**: {config['num_epochs']}
- **初始學習率**: {config['learning_rate']}
- **設備**: {config['device']}

## 2. 數據分割

- **訓練集**: {config['train_split'] * 100:.0f}%
- **驗證集**: {config['val_split'] * 100:.0f}%
- **測試集**: {config['test_split'] * 100:.0f}%

## 3. 測試集性能

| 指標 | 數值 | 說明 |
|------|------|------|
| RMSE | {metrics['RMSE']:.2f} | 均方根誤差 |
| MAE | {metrics['MAE']:.2f} | 平均絕對誤差 |
| R² | {metrics['R2']:.6f} | 決定係數 |
| MAPE | {metrics['MAPE']:.3f}% | 平均絕對百分比誤差 |
| 方向準確率 | {metrics['Direction_Accuracy']:.2f}% | 漲跌方向預測準確率 |

## 4. 模型特點

### ✅ 改進點

1. **完整特徵集**:
   - 添加了 lag 特徵（1, 2, 3, 5, 10, 20 期）
   - 添加了 rolling 特徵（5, 10, 20, 50 期的 mean, std, min, max）
   - 添加了 return 特徵（1, 5, 10, 20 期報酬率）
   - 保留所有技術指標、價格和成交量特徵

2. **模型架構改進**:
   - 增加隱藏層大小 (32 → {config['hidden_size']})
   - 增加 LSTM 層數 (1 → {config['num_layers']})
   - 添加批次歸一化
   - 添加額外的全連接層
   - 使用 dropout 防止過擬合

3. **訓練策略**:
   - 學習率自適應調整 (ReduceLROnPlateau)
   - 梯度裁剪防止梯度爆炸
   - Early stopping 防止過擬合

## 5. 結論

{"### ✅ 模型表現優秀" if metrics['R2'] > 0.99 else "### ⚠️ 模型需要改進"}

{"模型在測試集上表現出色，R² 超過 0.99，預測準確度高。" if metrics['R2'] > 0.99 else "模型在測試集上表現一般，需要進一步優化。"}

**與簡化版 LSTM 比較**: 查看 model_comparison 目錄中的對比報告。
"""

    with open(output_dir / 'evaluation_report.md', 'w', encoding='utf-8') as f:
        f.write(report)


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始 LSTM 模型訓練（完整特徵集）")
    logger.info("=" * 80)

    # 1. 載入數據
    df = load_data_from_db()

    # 2. 創建完整特徵集
    features = create_all_features(df)

    # 配置（在知道特徵數量後設置）
    config = {
        'sequence_length': 30,
        'hidden_size': 64,
        'num_layers': 2,
        'dropout': 0.2,
        'batch_size': 32,
        'num_epochs': 100,
        'learning_rate': 0.001,
        'train_split': 0.7,
        'val_split': 0.15,
        'test_split': 0.15,
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
    num_features = features.shape[1]
    model = ImprovedLSTMModel(
        input_size=num_features,
        hidden_size=config['hidden_size'],
        num_layers=config['num_layers'],
        dropout=config['dropout']
    )

    logger.info(f"模型架構:\n{model}")
    logger.info(f"模型參數數量: {sum(p.numel() for p in model.parameters()):,}")

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
    save_results(model, metrics, predictions, actuals, train_losses, val_losses, config, num_features)

    logger.info("=" * 80)
    logger.info("LSTM 訓練完成！")
    logger.info("=" * 80)
    logger.info(f"\n性能總結:")
    logger.info(f"  RMSE: {metrics['RMSE']:.2f} USDT")
    logger.info(f"  MAE: {metrics['MAE']:.2f} USDT")
    logger.info(f"  R²: {metrics['R2']:.6f}")
    logger.info(f"  MAPE: {metrics['MAPE']:.3f}%")
    logger.info(f"  方向準確率: {metrics['Direction_Accuracy']:.2f}%")


if __name__ == '__main__':
    main()
