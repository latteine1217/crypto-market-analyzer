"""
LSTM 價格預測模型測試腳本

測試功能：
1. 從資料庫載入數據
2. 訓練 LSTM 模型
3. 評估模型性能
4. 與 baseline 模型比較
5. 保存模型和結果
"""

import sys
import os
import logging
from pathlib import Path
import yaml
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import psycopg2
from datetime import datetime, timedelta

# 添加專案路徑
sys.path.append(str(Path(__file__).parent))

from src.models.ml.lstm_forecast import LSTMForecast
from src.models.baseline.ma_forecast import (
    MovingAverageForecast,
    ExponentialMovingAverageForecast,
    NaiveForecast
)

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data_from_db(
    market_id: int = 1,
    lookback_days: int = 30
) -> pd.DataFrame:
    """
    從資料庫載入數據

    Args:
        market_id: 市場 ID
        lookback_days: 回溯天數

    Returns:
        包含 OHLCV 資料的 DataFrame
    """
    logger.info(f"從資料庫載入最近 {lookback_days} 天的資料...")

    # 資料庫連線配置
    conn_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', 5432),
        'database': os.getenv('POSTGRES_DB', 'crypto_db'),
        'user': os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass')
    }

    # 連接資料庫
    conn = psycopg2.connect(**conn_params)

    # 查詢資料
    query = """
    SELECT
        open_time,
        open,
        high,
        low,
        close,
        volume,
        quote_volume,
        trade_count
    FROM ohlcv
    WHERE market_id = %s
    AND timeframe = '1m'
    AND open_time >= NOW() - INTERVAL '%s days'
    ORDER BY open_time ASC
    """

    df = pd.read_sql_query(
        query,
        conn,
        params=(market_id, lookback_days)
    )

    conn.close()

    logger.info(f"載入 {len(df)} 筆資料")
    logger.info(f"時間範圍: {df['open_time'].min()} 到 {df['open_time'].max()}")

    return df


def train_and_evaluate_lstm(
    df: pd.DataFrame,
    config: dict
) -> dict:
    """
    訓練並評估 LSTM 模型

    Args:
        df: 訓練資料
        config: 模型配置

    Returns:
        包含模型和評估結果的字典
    """
    logger.info("=" * 50)
    logger.info("開始訓練 LSTM 模型")
    logger.info("=" * 50)

    # 準備資料
    prices = df['close']

    # 分割資料
    train_ratio = config['data']['split']['train_ratio']
    test_ratio = config['data']['split']['test_ratio']
    val_ratio = 1 - train_ratio - test_ratio

    train_size = int(len(prices) * train_ratio)
    test_size = int(len(prices) * test_ratio)

    train_data = prices.iloc[:train_size]
    test_data = prices.iloc[train_size:]

    logger.info(f"訓練集大小: {len(train_data)}")
    logger.info(f"測試集大小: {len(test_data)}")

    # 初始化 LSTM 模型
    model_config = config['model']
    training_config = config['training']

    lstm_model = LSTMForecast(
        sequence_length=model_config['sequence_length'],
        hidden_size=model_config['hidden_size'],
        num_layers=model_config['num_layers'],
        dropout=model_config['dropout'],
        learning_rate=model_config['learning_rate'],
        batch_size=training_config['batch_size'],
        epochs=training_config['epochs'],
        device=model_config.get('device')
    )

    # 訓練模型
    lstm_model.fit(
        train_data,
        val_ratio=training_config['val_ratio'],
        early_stopping_patience=training_config['early_stopping']['patience'],
        verbose=training_config['verbose']
    )

    # 預測
    predictions = lstm_model.predict(test_data)

    # 評估
    # 對齊長度（因為序列生成會減少樣本數）
    y_true = test_data.iloc[lstm_model.sequence_length:]
    metrics = lstm_model.evaluate(y_true, predictions)

    logger.info("\n" + "=" * 50)
    logger.info("LSTM 模型評估結果")
    logger.info("=" * 50)
    for metric_name, metric_value in metrics.items():
        logger.info(f"{metric_name}: {metric_value:.6f}")

    return {
        'model': lstm_model,
        'predictions': predictions,
        'y_true': y_true,
        'metrics': metrics
    }


def train_baseline_models(
    df: pd.DataFrame,
    train_ratio: float = 0.7
) -> dict:
    """
    訓練 baseline 模型用於比較

    Args:
        df: 訓練資料
        train_ratio: 訓練集比例

    Returns:
        包含各 baseline 模型結果的字典
    """
    logger.info("\n" + "=" * 50)
    logger.info("訓練 Baseline 模型")
    logger.info("=" * 50)

    prices = df['close']

    train_size = int(len(prices) * train_ratio)
    train_data = prices.iloc[:train_size]
    test_data = prices.iloc[train_size:]

    baseline_results = {}

    # Naive 模型
    naive = NaiveForecast()
    naive.fit(train_data)
    naive_pred = naive.predict(test_data)
    naive_metrics = naive.evaluate(test_data, naive_pred)
    baseline_results['Naive'] = naive_metrics

    # MA 模型
    for window in [10, 20, 50]:
        ma = MovingAverageForecast(window=window)
        ma.fit(train_data)
        ma_pred = ma.predict(test_data)
        ma_metrics = ma.evaluate(test_data, ma_pred)
        baseline_results[f'MA_{window}'] = ma_metrics

    # EMA 模型
    for span in [10, 20]:
        ema = ExponentialMovingAverageForecast(span=span)
        ema.fit(train_data)
        ema_pred = ema.predict(test_data)
        ema_metrics = ema.evaluate(test_data, ema_pred)
        baseline_results[f'EMA_{span}'] = ema_metrics

    return baseline_results


def compare_models(
    lstm_metrics: dict,
    baseline_results: dict
) -> pd.DataFrame:
    """
    比較 LSTM 與 baseline 模型

    Args:
        lstm_metrics: LSTM 模型指標
        baseline_results: Baseline 模型指標字典

    Returns:
        比較結果 DataFrame
    """
    logger.info("\n" + "=" * 50)
    logger.info("模型比較結果")
    logger.info("=" * 50)

    # 整理結果
    all_results = {'LSTM': lstm_metrics}
    all_results.update(baseline_results)

    # 轉換為 DataFrame
    df_results = pd.DataFrame(all_results).T
    df_results = df_results[['rmse', 'mae', 'r2', 'mape']].round(4)
    df_results = df_results.sort_values('rmse')

    logger.info("\n" + df_results.to_string())

    return df_results


def plot_results(
    y_true: pd.Series,
    lstm_predictions: np.ndarray,
    lstm_model: LSTMForecast,
    output_dir: str
):
    """
    繪製結果圖表

    Args:
        y_true: 真實值
        lstm_predictions: LSTM 預測值
        lstm_model: LSTM 模型實例
        output_dir: 輸出目錄
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. 實際 vs 預測
    plt.figure(figsize=(15, 6))
    plt.plot(y_true.values, label='實際價格', alpha=0.7)
    plt.plot(lstm_predictions, label='LSTM 預測', alpha=0.7)
    plt.title('LSTM 價格預測 - 實際 vs 預測', fontsize=14)
    plt.xlabel('時間步')
    plt.ylabel('價格')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/actual_vs_predicted.png', dpi=300)
    logger.info(f"已保存: {output_dir}/actual_vs_predicted.png")
    plt.close()

    # 2. 訓練歷史
    history = lstm_model.get_training_history()
    plt.figure(figsize=(12, 5))
    plt.plot(history['epoch'], history['train_loss'], label='訓練損失')
    plt.plot(history['epoch'], history['val_loss'], label='驗證損失')
    plt.title('LSTM 訓練歷史', fontsize=14)
    plt.xlabel('Epoch')
    plt.ylabel('損失 (MSE)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/training_history.png', dpi=300)
    logger.info(f"已保存: {output_dir}/training_history.png")
    plt.close()

    # 3. 殘差分析
    residuals = y_true.values - lstm_predictions
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.scatter(lstm_predictions, residuals, alpha=0.5)
    plt.axhline(y=0, color='r', linestyle='--')
    plt.title('殘差 vs 預測值')
    plt.xlabel('預測值')
    plt.ylabel('殘差')
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.hist(residuals, bins=50, edgecolor='black')
    plt.title('殘差分布')
    plt.xlabel('殘差')
    plt.ylabel('頻率')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/residuals.png', dpi=300)
    logger.info(f"已保存: {output_dir}/residuals.png")
    plt.close()


def main():
    """主函數"""
    # 載入配置
    config_path = Path(__file__).parent.parent / 'configs' / 'models' / 'lstm_price_forecast_pytorch.yml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    logger.info("開始 LSTM 模型測試")
    logger.info(f"配置: {config['experiment']['name']}")

    # 1. 載入數據
    df = load_data_from_db(
        market_id=config['data']['source']['market_id'],
        lookback_days=config['data']['source']['lookback_days']
    )

    if len(df) < 1000:
        logger.error(f"資料量不足 ({len(df)} 筆)，建議至少 1000 筆")
        return

    # 2. 訓練 LSTM 模型
    lstm_result = train_and_evaluate_lstm(df, config)

    # 3. 訓練 baseline 模型
    baseline_results = train_baseline_models(
        df,
        train_ratio=config['data']['split']['train_ratio']
    )

    # 4. 比較模型
    comparison_df = compare_models(
        lstm_result['metrics'],
        baseline_results
    )

    # 5. 繪製結果
    output_dir = Path(config['output']['results_dir'])
    plot_results(
        lstm_result['y_true'],
        lstm_result['predictions'],
        lstm_result['model'],
        str(output_dir)
    )

    # 6. 保存結果
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存模型
    model_path = Path(config['output']['model_dir']) / config['output']['model_filename']
    model_path.parent.mkdir(parents=True, exist_ok=True)
    lstm_result['model'].save_model(str(model_path))

    # 保存指標
    metrics_path = output_dir / config['output']['metrics_file']
    comparison_df.to_csv(metrics_path.with_suffix('.csv'))
    logger.info(f"已保存指標: {metrics_path.with_suffix('.csv')}")

    # 保存訓練歷史
    history_path = output_dir / config['output']['training_history_file']
    lstm_result['model'].get_training_history().to_csv(history_path, index=False)
    logger.info(f"已保存訓練歷史: {history_path}")

    logger.info("\n" + "=" * 50)
    logger.info("測試完成！")
    logger.info("=" * 50)
    logger.info(f"結果保存於: {output_dir}")


if __name__ == '__main__':
    main()
