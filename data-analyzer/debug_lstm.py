"""
LSTM 問題診斷腳本
"""

import numpy as np
import pandas as pd
import torch
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_lstm():
    """測試基本 LSTM 功能"""
    logger.info("=" * 60)
    logger.info("測試 1: 基本 LSTM 創建")
    logger.info("=" * 60)

    try:
        import torch.nn as nn

        # 創建簡單的 LSTM
        lstm = nn.LSTM(input_size=1, hidden_size=10, num_layers=1, batch_first=True)
        logger.info("✓ LSTM 模型創建成功")

        # 測試前向傳播
        x = torch.randn(32, 10, 1)  # batch_size=32, seq_len=10, features=1
        output, (h, c) = lstm(x)
        logger.info(f"✓ LSTM 前向傳播成功, 輸出形狀: {output.shape}")

        return True
    except Exception as e:
        logger.error(f"✗ 基本 LSTM 測試失敗: {e}")
        return False


def test_data_loading():
    """測試數據載入"""
    logger.info("=" * 60)
    logger.info("測試 2: 數據載入")
    logger.info("=" * 60)

    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            database='crypto_db',
            user='crypto',
            password='crypto_pass'
        )

        query = """
            SELECT o.close
            FROM ohlcv o
            JOIN markets m ON o.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = 'bybit'
                AND m.symbol = 'BTC/USDT'
                AND o.timeframe = '1h'
            ORDER BY o.open_time
            LIMIT 1000
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        logger.info(f"✓ 數據載入成功: {len(df)} 筆")
        logger.info(f"  數據範圍: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
        logger.info(f"  是否有 NaN: {df['close'].isna().any()}")
        logger.info(f"  是否有 Inf: {np.isinf(df['close'].values).any()}")

        return df

    except Exception as e:
        logger.error(f"✗ 數據載入失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_sequence_creation(df, sequence_length=30):
    """測試序列創建"""
    logger.info("=" * 60)
    logger.info(f"測試 3: 序列創建 (sequence_length={sequence_length})")
    logger.info("=" * 60)

    try:
        data = df['close'].values

        # 標準化
        from sklearn.preprocessing import MinMaxScaler
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(data.reshape(-1, 1))

        logger.info(f"✓ 數據標準化成功")
        logger.info(f"  標準化後範圍: {scaled_data.min():.4f} ~ {scaled_data.max():.4f}")

        # 創建序列
        X, y = [], []
        for i in range(len(scaled_data) - sequence_length):
            X.append(scaled_data[i:i + sequence_length])
            y.append(scaled_data[i + sequence_length])

        X = np.array(X)
        y = np.array(y)

        logger.info(f"✓ 序列創建成功")
        logger.info(f"  X 形狀: {X.shape}")
        logger.info(f"  y 形狀: {y.shape}")
        logger.info(f"  是否有 NaN in X: {np.isnan(X).any()}")
        logger.info(f"  是否有 NaN in y: {np.isnan(y).any()}")

        return X, y, scaler

    except Exception as e:
        logger.error(f"✗ 序列創建失敗: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def test_dataloader(X, y, batch_size=32):
    """測試 DataLoader"""
    logger.info("=" * 60)
    logger.info(f"測試 4: DataLoader (batch_size={batch_size})")
    logger.info("=" * 60)

    try:
        from torch.utils.data import DataLoader, TensorDataset

        # 轉換為 Tensor
        logger.info("  轉換為 PyTorch Tensor...")
        X_tensor = torch.FloatTensor(X)
        y_tensor = torch.FloatTensor(y)

        logger.info(f"  X_tensor 形狀: {X_tensor.shape}")
        logger.info(f"  y_tensor 形狀: {y_tensor.shape}")

        # 創建 Dataset
        logger.info("  創建 TensorDataset...")
        dataset = TensorDataset(X_tensor, y_tensor)

        # 創建 DataLoader
        logger.info("  創建 DataLoader...")
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        logger.info(f"✓ DataLoader 創建成功")
        logger.info(f"  批次數量: {len(dataloader)}")

        # 測試迭代
        logger.info("  測試迭代第一個批次...")
        for X_batch, y_batch in dataloader:
            logger.info(f"✓ 成功獲取批次: X={X_batch.shape}, y={y_batch.shape}")
            break

        return dataloader

    except Exception as e:
        logger.error(f"✗ DataLoader 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_simple_training(dataloader):
    """測試簡單訓練循環"""
    logger.info("=" * 60)
    logger.info("測試 5: 簡單訓練循環")
    logger.info("=" * 60)

    try:
        import torch.nn as nn
        import torch.optim as optim

        # 創建模型
        logger.info("  創建 LSTM 模型...")
        model = nn.LSTM(input_size=1, hidden_size=16, num_layers=1, batch_first=True)
        fc = nn.Linear(16, 1)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(list(model.parameters()) + list(fc.parameters()), lr=0.001)

        logger.info("✓ 模型創建成功")

        # 訓練 3 個 epoch
        logger.info("  開始訓練...")
        model.train()
        fc.train()

        for epoch in range(3):
            total_loss = 0
            batch_count = 0

            for X_batch, y_batch in dataloader:
                # 前向傳播
                lstm_out, _ = model(X_batch)
                last_output = lstm_out[:, -1, :]
                predictions = fc(last_output)

                # 計算損失
                loss = criterion(predictions, y_batch)

                # 反向傳播
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                total_loss += loss.item()
                batch_count += 1

            avg_loss = total_loss / batch_count
            logger.info(f"  Epoch {epoch + 1}/3 - Loss: {avg_loss:.6f}")

        logger.info("✓ 訓練循環成功完成")
        return True

    except Exception as e:
        logger.error(f"✗ 訓練循環失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函數"""
    logger.info("開始 LSTM 診斷測試")
    logger.info("")

    # 測試 1: 基本 LSTM
    if not test_basic_lstm():
        logger.error("基本 LSTM 測試失敗，停止後續測試")
        return

    logger.info("")

    # 測試 2: 數據載入
    df = test_data_loading()
    if df is None:
        logger.error("數據載入失敗，停止後續測試")
        return

    logger.info("")

    # 測試 3: 序列創建
    X, y, scaler = test_sequence_creation(df, sequence_length=30)
    if X is None:
        logger.error("序列創建失敗，停止後續測試")
        return

    logger.info("")

    # 測試 4: DataLoader
    dataloader = test_dataloader(X, y, batch_size=32)
    if dataloader is None:
        logger.error("DataLoader 創建失敗，停止後續測試")
        return

    logger.info("")

    # 測試 5: 訓練循環
    if not test_simple_training(dataloader):
        logger.error("訓練循環失敗")
        return

    logger.info("")
    logger.info("=" * 60)
    logger.info("所有測試通過！LSTM 基本功能正常")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
