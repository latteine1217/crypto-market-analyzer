"""
模型訓練與比較腳本

從數據庫載入 Bybit 數據，訓練 XGBoost 和 LSTM 模型，並比較性能。
"""

import os
import sys
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import logging
import json
from pathlib import Path

# 添加 src 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.ml.xgboost_forecast import XGBoostForecast
from models.ml.lstm_forecast import LSTMForecast
from features.technical_indicators import TechnicalIndicators
from features.price_features import PriceFeatures
from features.volume_features import VolumeFeatures

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelComparison:
    """
    模型訓練與比較工具
    """

    def __init__(
        self,
        exchange: str = 'bybit',
        symbol: str = 'BTC/USDT',
        timeframe: str = '1h',
        output_dir: str = 'results/model_comparison'
    ):
        """
        初始化

        Args:
            exchange: 交易所名稱
            symbol: 交易對
            timeframe: 時間週期
            output_dir: 輸出目錄
        """
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.output_dir = output_dir

        # 創建輸出目錄
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 數據庫連接
        self.conn = psycopg2.connect(
            host='localhost',
            database='crypto_db',
            user='crypto',
            password='crypto_pass'
        )

        # 數據
        self.df = None
        self.train_data = None
        self.test_data = None

        # 模型
        self.xgb_model = None
        self.lstm_model = None

        # 結果
        self.results = {}

    def load_data(self):
        """
        從數據庫載入數據
        """
        logger.info(f"載入數據: {self.exchange} {self.symbol} {self.timeframe}")

        query = """
            SELECT
                o.open_time,
                o.open,
                o.high,
                o.low,
                o.close,
                o.volume,
                o.quote_volume
            FROM ohlcv o
            JOIN markets m ON o.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s
                AND m.symbol = %s
                AND o.timeframe = %s
            ORDER BY o.open_time
        """

        self.df = pd.read_sql_query(
            query,
            self.conn,
            params=(self.exchange, self.symbol, self.timeframe),
            parse_dates=['open_time']
        )

        # 設置索引
        self.df.set_index('open_time', inplace=True)

        logger.info(f"載入 {len(self.df)} 筆數據")
        logger.info(f"時間範圍: {self.df.index.min()} ~ {self.df.index.max()}")
        logger.info(f"數據概覽:\n{self.df.describe()}")

        return self.df

    def create_features(self):
        """
        創建技術指標特徵
        """
        logger.info("創建技術指標特徵")

        # 初始化特徵生成器
        tech_indicators = TechnicalIndicators()
        price_features = PriceFeatures()
        volume_features = VolumeFeatures()

        # 生成特徵
        tech_features = tech_indicators.calculate_all(self.df)
        price_feat = price_features.calculate_all(self.df)
        volume_feat = volume_features.calculate_all(self.df)

        # 合併特徵（移除重複列）
        # 提取非 OHLCV 列
        tech_cols = [col for col in tech_features.columns
                    if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
        price_cols = [col for col in price_feat.columns
                     if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]
        volume_cols = [col for col in volume_feat.columns
                      if col not in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']]

        # 合併所有特徵
        features = pd.concat([
            tech_features[tech_cols],
            price_feat[price_cols],
            volume_feat[volume_cols]
        ], axis=1)

        # 移除包含 NaN 的行（向前填充以減少數據損失）
        features = features.fillna(method='ffill').dropna()
        self.df = self.df.loc[features.index]

        logger.info(f"特徵數量: {len(features.columns)}")
        logger.info(f"特徵列表: {features.columns.tolist()}")

        return features

    def split_data(self, train_ratio: float = 0.8):
        """
        分割訓練集和測試集

        Args:
            train_ratio: 訓練集比例
        """
        split_idx = int(len(self.df) * train_ratio)

        self.train_data = self.df.iloc[:split_idx].copy()
        self.test_data = self.df.iloc[split_idx:].copy()

        logger.info(f"訓練集大小: {len(self.train_data)}")
        logger.info(f"測試集大小: {len(self.test_data)}")
        logger.info(f"訓練集時間: {self.train_data.index.min()} ~ {self.train_data.index.max()}")
        logger.info(f"測試集時間: {self.test_data.index.min()} ~ {self.test_data.index.max()}")

    def train_xgboost(self, features_train: pd.DataFrame, **kwargs):
        """
        訓練 XGBoost 模型

        Args:
            features_train: 訓練特徵
            **kwargs: XGBoost 參數
        """
        logger.info("=" * 80)
        logger.info("訓練 XGBoost 模型")
        logger.info("=" * 80)

        # 創建模型
        self.xgb_model = XGBoostForecast(**kwargs)

        # 訓練
        self.xgb_model.fit(
            y_train=self.train_data['close'],
            external_features=features_train,
            val_ratio=0.2,
            verbose=True
        )

        # 預測
        y_pred_train = self.xgb_model.predict(
            self.train_data['close'],
            features_train
        )

        # 評估
        metrics_train = self.xgb_model.evaluate(
            self.train_data['close'].iloc[-len(y_pred_train):],
            y_pred_train
        )

        logger.info(f"訓練集評估結果:")
        for metric, value in metrics_train.items():
            logger.info(f"  {metric}: {value:.6f}")

        self.results['xgboost'] = {
            'model': self.xgb_model,
            'train_metrics': metrics_train,
            'training_history': self.xgb_model.get_training_history()
        }

        return self.xgb_model

    def train_lstm(self, features_train: pd.DataFrame = None, **kwargs):
        """
        訓練 LSTM 模型

        Args:
            features_train: 訓練特徵（可選）
            **kwargs: LSTM 參數
        """
        logger.info("=" * 80)
        logger.info("訓練 LSTM 模型")
        logger.info("=" * 80)

        # 創建模型
        self.lstm_model = LSTMForecast(**kwargs)

        # 訓練
        self.lstm_model.fit(
            y_train=self.train_data['close'],
            features=features_train,
            val_ratio=0.2,
            early_stopping_patience=15,
            verbose=True
        )

        # 預測
        y_pred_train = self.lstm_model.predict(
            self.train_data['close'],
            features_train
        )

        # 評估
        metrics_train = self.lstm_model.evaluate(
            self.train_data['close'].iloc[-len(y_pred_train):],
            y_pred_train
        )

        logger.info(f"訓練集評估結果:")
        for metric, value in metrics_train.items():
            logger.info(f"  {metric}: {value:.6f}")

        self.results['lstm'] = {
            'model': self.lstm_model,
            'train_metrics': metrics_train,
            'training_history': self.lstm_model.get_training_history()
        }

        return self.lstm_model

    def evaluate_models(self, features_test: pd.DataFrame):
        """
        在測試集上評估模型

        Args:
            features_test: 測試特徵
        """
        logger.info("=" * 80)
        logger.info("測試集評估")
        logger.info("=" * 80)

        results = {}

        # XGBoost 評估
        if self.xgb_model is not None:
            logger.info("評估 XGBoost 模型")
            y_pred_xgb = self.xgb_model.predict(
                self.test_data['close'],
                features_test
            )
            metrics_xgb = self.xgb_model.evaluate(
                self.test_data['close'].iloc[-len(y_pred_xgb):],
                y_pred_xgb
            )

            logger.info(f"XGBoost 測試集結果:")
            for metric, value in metrics_xgb.items():
                logger.info(f"  {metric}: {value:.6f}")

            results['xgboost'] = {
                'predictions': y_pred_xgb,
                'metrics': metrics_xgb
            }
            self.results['xgboost']['test_metrics'] = metrics_xgb
            self.results['xgboost']['predictions'] = y_pred_xgb

        # LSTM 評估
        if self.lstm_model is not None:
            logger.info("評估 LSTM 模型")
            y_pred_lstm = self.lstm_model.predict(
                self.test_data['close'],
                features_test
            )
            metrics_lstm = self.lstm_model.evaluate(
                self.test_data['close'].iloc[-len(y_pred_lstm):],
                y_pred_lstm
            )

            logger.info(f"LSTM 測試集結果:")
            for metric, value in metrics_lstm.items():
                logger.info(f"  {metric}: {value:.6f}")

            results['lstm'] = {
                'predictions': y_pred_lstm,
                'metrics': metrics_lstm
            }
            self.results['lstm']['test_metrics'] = metrics_lstm
            self.results['lstm']['predictions'] = y_pred_lstm

        return results

    def compare_models(self):
        """
        比較模型性能
        """
        logger.info("=" * 80)
        logger.info("模型比較")
        logger.info("=" * 80)

        if 'xgboost' not in self.results or 'lstm' not in self.results:
            logger.warning("需要訓練兩個模型後才能比較")
            return

        # 比較測試集指標
        comparison = pd.DataFrame({
            'XGBoost': self.results['xgboost']['test_metrics'],
            'LSTM': self.results['lstm']['test_metrics']
        })

        logger.info("\n測試集性能比較:")
        logger.info(f"\n{comparison.to_string()}")

        # 計算改進百分比
        improvement = ((comparison['LSTM'] - comparison['XGBoost']) /
                      comparison['XGBoost'].abs() * 100)

        logger.info("\nLSTM 相對 XGBoost 的改進 (%):")
        logger.info(f"\n{improvement.to_string()}")

        # 保存比較結果
        comparison_path = os.path.join(self.output_dir, 'metrics_comparison.csv')
        comparison.to_csv(comparison_path)
        logger.info(f"比較結果已保存至: {comparison_path}")

        return comparison

    def plot_results(self):
        """
        繪製結果圖表
        """
        logger.info("繪製結果圖表")

        # 設置繪圖風格
        sns.set_style('whitegrid')
        plt.rcParams['figure.figsize'] = (15, 10)

        fig, axes = plt.subplots(3, 2, figsize=(18, 14))

        # 1. 訓練損失對比
        ax = axes[0, 0]
        if 'xgboost' in self.results:
            history_xgb = self.results['xgboost']['training_history']
            ax.plot(history_xgb['iteration'], history_xgb['train_rmse'],
                   label='XGBoost Train', alpha=0.7)
            ax.plot(history_xgb['iteration'], history_xgb['val_rmse'],
                   label='XGBoost Val', alpha=0.7)

        if 'lstm' in self.results:
            history_lstm = self.results['lstm']['training_history']
            ax.plot(history_lstm['epoch'], history_lstm['train_loss'],
                   label='LSTM Train', alpha=0.7)
            ax.plot(history_lstm['epoch'], history_lstm['val_loss'],
                   label='LSTM Val', alpha=0.7)

        ax.set_xlabel('Iteration / Epoch')
        ax.set_ylabel('Loss')
        ax.set_title('Training Loss Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. 測試集預測對比
        ax = axes[0, 1]
        test_indices = self.test_data.index

        if 'xgboost' in self.results and 'predictions' in self.results['xgboost']:
            y_pred_xgb = self.results['xgboost']['predictions']
            ax.plot(test_indices[-len(y_pred_xgb):], y_pred_xgb,
                   label='XGBoost', alpha=0.7, linewidth=1.5)

        if 'lstm' in self.results and 'predictions' in self.results['lstm']:
            y_pred_lstm = self.results['lstm']['predictions']
            ax.plot(test_indices[-len(y_pred_lstm):], y_pred_lstm,
                   label='LSTM', alpha=0.7, linewidth=1.5)

        ax.plot(test_indices, self.test_data['close'],
               label='Actual', alpha=0.8, linewidth=2, color='black')
        ax.set_xlabel('Time')
        ax.set_ylabel('Price')
        ax.set_title('Test Set Predictions Comparison')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        # 3. 預測誤差分布 - XGBoost
        ax = axes[1, 0]
        if 'xgboost' in self.results and 'predictions' in self.results['xgboost']:
            y_pred_xgb = self.results['xgboost']['predictions']
            y_true = self.test_data['close'].iloc[-len(y_pred_xgb):].values
            errors_xgb = y_true - y_pred_xgb
            ax.hist(errors_xgb, bins=50, alpha=0.7, edgecolor='black')
            ax.axvline(0, color='red', linestyle='--', linewidth=2)
            ax.set_xlabel('Prediction Error')
            ax.set_ylabel('Frequency')
            ax.set_title('XGBoost Error Distribution')
            ax.grid(True, alpha=0.3)

        # 4. 預測誤差分布 - LSTM
        ax = axes[1, 1]
        if 'lstm' in self.results and 'predictions' in self.results['lstm']:
            y_pred_lstm = self.results['lstm']['predictions']
            y_true = self.test_data['close'].iloc[-len(y_pred_lstm):].values
            errors_lstm = y_true - y_pred_lstm
            ax.hist(errors_lstm, bins=50, alpha=0.7, edgecolor='black', color='orange')
            ax.axvline(0, color='red', linestyle='--', linewidth=2)
            ax.set_xlabel('Prediction Error')
            ax.set_ylabel('Frequency')
            ax.set_title('LSTM Error Distribution')
            ax.grid(True, alpha=0.3)

        # 5. 性能指標對比
        ax = axes[2, 0]
        if 'xgboost' in self.results and 'lstm' in self.results:
            metrics = ['mse', 'rmse', 'mae', 'r2', 'mape', 'direction_accuracy']
            xgb_values = [self.results['xgboost']['test_metrics'][m] for m in metrics]
            lstm_values = [self.results['lstm']['test_metrics'][m] for m in metrics]

            x = np.arange(len(metrics))
            width = 0.35

            ax.bar(x - width/2, xgb_values, width, label='XGBoost', alpha=0.8)
            ax.bar(x + width/2, lstm_values, width, label='LSTM', alpha=0.8)

            ax.set_ylabel('Value')
            ax.set_title('Performance Metrics Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(metrics, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')

        # 6. 預測 vs 實際散點圖
        ax = axes[2, 1]
        if 'xgboost' in self.results and 'lstm' in self.results:
            y_pred_xgb = self.results['xgboost']['predictions']
            y_pred_lstm = self.results['lstm']['predictions']

            min_len = min(len(y_pred_xgb), len(y_pred_lstm))
            y_true = self.test_data['close'].iloc[-min_len:].values

            ax.scatter(y_true, y_pred_xgb[-min_len:], alpha=0.5, label='XGBoost', s=20)
            ax.scatter(y_true, y_pred_lstm[-min_len:], alpha=0.5, label='LSTM', s=20)

            # 繪製理想線
            min_val = min(y_true.min(), y_pred_xgb.min(), y_pred_lstm.min())
            max_val = max(y_true.max(), y_pred_xgb.max(), y_pred_lstm.max())
            ax.plot([min_val, max_val], [min_val, max_val],
                   'r--', linewidth=2, label='Perfect Prediction')

            ax.set_xlabel('Actual Price')
            ax.set_ylabel('Predicted Price')
            ax.set_title('Prediction vs Actual')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # 保存圖表
        plot_path = os.path.join(self.output_dir, 'model_comparison.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"圖表已保存至: {plot_path}")

        plt.close()

    def save_results(self):
        """
        保存結果
        """
        logger.info("保存結果")

        # 保存模型
        if self.xgb_model is not None:
            xgb_path = os.path.join(self.output_dir, 'xgboost_model.joblib')
            self.xgb_model.save_model(xgb_path)

        if self.lstm_model is not None:
            lstm_path = os.path.join(self.output_dir, 'lstm_model.pth')
            self.lstm_model.save_model(lstm_path)

        # 保存元數據
        metadata = {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'train_size': len(self.train_data),
            'test_size': len(self.test_data),
            'train_period': {
                'start': str(self.train_data.index.min()),
                'end': str(self.train_data.index.max())
            },
            'test_period': {
                'start': str(self.test_data.index.min()),
                'end': str(self.test_data.index.max())
            },
            'timestamp': datetime.now().isoformat()
        }

        # 添加測試指標
        if 'xgboost' in self.results:
            metadata['xgboost_metrics'] = {
                k: float(v) for k, v in self.results['xgboost']['test_metrics'].items()
            }

        if 'lstm' in self.results:
            metadata['lstm_metrics'] = {
                k: float(v) for k, v in self.results['lstm']['test_metrics'].items()
            }

        metadata_path = os.path.join(self.output_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"元數據已保存至: {metadata_path}")

    def run(self):
        """
        執行完整的訓練與比較流程
        """
        logger.info("=" * 80)
        logger.info(f"開始模型訓練與比較: {self.exchange} {self.symbol} {self.timeframe}")
        logger.info("=" * 80)

        # 1. 載入數據
        self.load_data()

        # 2. 創建特徵
        features = self.create_features()

        # 3. 分割數據
        self.split_data(train_ratio=0.8)

        # 分割特徵
        features_train = features.loc[self.train_data.index]
        features_test = features.loc[self.test_data.index]

        # 4. 訓練 XGBoost
        self.train_xgboost(
            features_train,
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            early_stopping_rounds=20
        )

        # 5. 訓練 LSTM（簡化版本以提高訓練速度）
        self.train_lstm(
            features_train,
            sequence_length=30,  # 減少序列長度
            hidden_size=64,      # 減少隱藏單元
            num_layers=1,        # 單層 LSTM
            dropout=0.2,
            learning_rate=0.001,
            batch_size=64,       # 增加批次大小
            epochs=50,           # 減少訓練輪數
            device='cpu'
        )

        # 6. 測試集評估
        self.evaluate_models(features_test)

        # 7. 比較模型
        self.compare_models()

        # 8. 繪製結果
        self.plot_results()

        # 9. 保存結果
        self.save_results()

        logger.info("=" * 80)
        logger.info("訓練與比較完成！")
        logger.info("=" * 80)

    def __del__(self):
        """
        清理資源
        """
        if hasattr(self, 'conn') and self.conn is not None:
            self.conn.close()


def main():
    """
    主函數
    """
    # 創建比較實例
    comparison = ModelComparison(
        exchange='bybit',
        symbol='BTC/USDT',
        timeframe='1h',
        output_dir='results/model_comparison_bybit_btc_1h'
    )

    # 執行訓練與比較
    comparison.run()


if __name__ == '__main__':
    main()
