"""
XGBoost 模型完整評估腳本

訓練 XGBoost 模型並在測試集上進行詳細評估
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
from features.technical_indicators import TechnicalIndicators
from features.price_features import PriceFeatures
from features.volume_features import VolumeFeatures

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XGBoostEvaluator:
    """
    XGBoost 模型評估器
    """

    def __init__(
        self,
        exchange: str = 'bybit',
        symbol: str = 'BTC/USDT',
        timeframe: str = '1h',
        output_dir: str = 'results/xgboost_evaluation'
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
        self.features_train = None
        self.features_test = None

        # 模型
        self.model = None

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
        features = features.ffill().dropna()
        self.df = self.df.loc[features.index]

        logger.info(f"特徵數量: {len(features.columns)}")
        logger.info(f"有效數據量: {len(features)}")

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

    def train_model(self, features, **kwargs):
        """
        訓練 XGBoost 模型

        Args:
            features: 完整特徵
            **kwargs: XGBoost 參數
        """
        logger.info("=" * 80)
        logger.info("訓練 XGBoost 模型")
        logger.info("=" * 80)

        # 分割特徵
        self.features_train = features.loc[self.train_data.index]
        self.features_test = features.loc[self.test_data.index]

        # 創建模型
        self.model = XGBoostForecast(**kwargs)

        # 訓練
        self.model.fit(
            y_train=self.train_data['close'],
            external_features=self.features_train,
            val_ratio=0.2,
            verbose=True
        )

        logger.info("訓練完成")

        return self.model

    def evaluate_on_train(self):
        """
        在訓練集上評估
        """
        logger.info("訓練集評估")

        # 預測
        y_pred_train = self.model.predict(
            self.train_data['close'],
            self.features_train
        )

        # 評估
        metrics_train = self.model.evaluate(
            self.train_data['close'].iloc[-len(y_pred_train):],
            y_pred_train
        )

        logger.info("訓練集指標:")
        for metric, value in metrics_train.items():
            logger.info(f"  {metric}: {value:.6f}")

        self.results['train'] = {
            'metrics': metrics_train,
            'predictions': y_pred_train,
            'actual': self.train_data['close'].iloc[-len(y_pred_train):].values
        }

        return metrics_train

    def evaluate_on_test(self):
        """
        在測試集上評估
        """
        logger.info("=" * 80)
        logger.info("測試集評估")
        logger.info("=" * 80)

        # 預測
        y_pred_test = self.model.predict(
            self.test_data['close'],
            self.features_test
        )

        # 評估
        metrics_test = self.model.evaluate(
            self.test_data['close'].iloc[-len(y_pred_test):],
            y_pred_test
        )

        logger.info("測試集指標:")
        for metric, value in metrics_test.items():
            logger.info(f"  {metric}: {value:.6f}")

        self.results['test'] = {
            'metrics': metrics_test,
            'predictions': y_pred_test,
            'actual': self.test_data['close'].iloc[-len(y_pred_test):].values,
            'timestamps': self.test_data.index[-len(y_pred_test):]
        }

        return metrics_test

    def analyze_feature_importance(self, top_n: int = 20):
        """
        分析特徵重要性

        Args:
            top_n: 顯示前 N 個重要特徵
        """
        logger.info("分析特徵重要性")

        importance_df = self.model.get_feature_importance(importance_type='gain')

        # 保存完整的特徵重要性
        importance_path = os.path.join(self.output_dir, 'feature_importance.csv')
        importance_df.to_csv(importance_path, index=False)
        logger.info(f"特徵重要性已保存至: {importance_path}")

        # 顯示前 N 個
        logger.info(f"\n前 {top_n} 個重要特徵:")
        for idx, row in importance_df.head(top_n).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.2f}")

        self.results['feature_importance'] = importance_df

        return importance_df

    def plot_results(self):
        """
        繪製詳細的結果圖表
        """
        logger.info("繪製結果圖表")

        # 設置繪圖風格
        sns.set_style('whitegrid')

        # 創建大圖
        fig = plt.figure(figsize=(20, 16))
        gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)

        # 1. 測試集預測 vs 實際（主圖）
        ax1 = fig.add_subplot(gs[0, :])
        test_timestamps = self.results['test']['timestamps']
        test_actual = self.results['test']['actual']
        test_pred = self.results['test']['predictions']

        ax1.plot(test_timestamps, test_actual, label='Actual', linewidth=2, alpha=0.8)
        ax1.plot(test_timestamps, test_pred, label='Predicted', linewidth=2, alpha=0.8)
        ax1.fill_between(test_timestamps, test_actual, test_pred, alpha=0.2)
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Price (USDT)')
        ax1.set_title('Test Set: Actual vs Predicted Price', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # 2. 預測誤差時序圖
        ax2 = fig.add_subplot(gs[1, 0])
        errors = test_actual - test_pred
        ax2.plot(test_timestamps, errors, linewidth=1, alpha=0.7)
        ax2.axhline(y=0, color='r', linestyle='--', linewidth=2)
        ax2.fill_between(test_timestamps, 0, errors, alpha=0.3)
        ax2.set_xlabel('Time')
        ax2.set_ylabel('Prediction Error (USDT)')
        ax2.set_title('Prediction Error Over Time')
        ax2.grid(True, alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        # 3. 誤差分布直方圖
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.hist(errors, bins=50, edgecolor='black', alpha=0.7)
        ax3.axvline(errors.mean(), color='r', linestyle='--', linewidth=2, label=f'Mean: {errors.mean():.2f}')
        ax3.axvline(0, color='g', linestyle='--', linewidth=2, label='Zero')
        ax3.set_xlabel('Prediction Error (USDT)')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Error Distribution')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # 4. Q-Q 圖（檢查誤差是否服從正態分布）
        ax4 = fig.add_subplot(gs[1, 2])
        from scipy import stats
        stats.probplot(errors, dist="norm", plot=ax4)
        ax4.set_title('Q-Q Plot (Error Normality Check)')
        ax4.grid(True, alpha=0.3)

        # 5. 預測 vs 實際散點圖
        ax5 = fig.add_subplot(gs[2, 0])
        ax5.scatter(test_actual, test_pred, alpha=0.5, s=20)
        # 理想線
        min_val = min(test_actual.min(), test_pred.min())
        max_val = max(test_actual.max(), test_pred.max())
        ax5.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2, label='Perfect Prediction')
        ax5.set_xlabel('Actual Price (USDT)')
        ax5.set_ylabel('Predicted Price (USDT)')
        ax5.set_title('Prediction vs Actual Scatter Plot')
        ax5.legend()
        ax5.grid(True, alpha=0.3)

        # 6. 絕對誤差百分比
        ax6 = fig.add_subplot(gs[2, 1])
        ape = np.abs(errors / test_actual) * 100
        ax6.plot(test_timestamps, ape, linewidth=1, alpha=0.7)
        ax6.axhline(y=ape.mean(), color='r', linestyle='--', linewidth=2,
                   label=f'Mean: {ape.mean():.3f}%')
        ax6.set_xlabel('Time')
        ax6.set_ylabel('Absolute Percentage Error (%)')
        ax6.set_title('Absolute Percentage Error Over Time')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        plt.setp(ax6.xaxis.get_majorticklabels(), rotation=45)

        # 7. 訓練損失曲線
        ax7 = fig.add_subplot(gs[2, 2])
        history = self.model.get_training_history()
        ax7.plot(history['iteration'], history['train_rmse'], label='Train RMSE', alpha=0.7)
        ax7.plot(history['iteration'], history['val_rmse'], label='Val RMSE', alpha=0.7)
        ax7.set_xlabel('Iteration')
        ax7.set_ylabel('RMSE')
        ax7.set_title('Training History')
        ax7.legend()
        ax7.grid(True, alpha=0.3)

        # 8. 特徵重要性（前20）
        ax8 = fig.add_subplot(gs[3, :2])
        top_features = self.results['feature_importance'].head(20)
        y_pos = np.arange(len(top_features))
        ax8.barh(y_pos, top_features['importance'].values, alpha=0.8)
        ax8.set_yticks(y_pos)
        ax8.set_yticklabels(top_features['feature'].values)
        ax8.invert_yaxis()
        ax8.set_xlabel('Importance (Gain)')
        ax8.set_title('Top 20 Feature Importance')
        ax8.grid(True, alpha=0.3, axis='x')

        # 9. 性能指標表格
        ax9 = fig.add_subplot(gs[3, 2])
        ax9.axis('tight')
        ax9.axis('off')

        metrics_data = []
        for metric, value in self.results['test']['metrics'].items():
            metrics_data.append([metric.upper(), f'{value:.6f}'])

        table = ax9.table(cellText=metrics_data,
                         colLabels=['Metric', 'Value'],
                         cellLoc='left',
                         loc='center',
                         colWidths=[0.4, 0.6])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        ax9.set_title('Test Set Performance Metrics', fontsize=12, fontweight='bold', pad=20)

        # 保存圖表
        plot_path = os.path.join(self.output_dir, 'xgboost_evaluation.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"圖表已保存至: {plot_path}")

        plt.close()

    def generate_report(self):
        """
        生成詳細的文字報告
        """
        logger.info("生成詳細報告")

        report_path = os.path.join(self.output_dir, 'evaluation_report.md')

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# XGBoost 模型評估報告\n\n")
            f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 1. 數據集資訊\n\n")
            f.write(f"- **交易所**: {self.exchange}\n")
            f.write(f"- **交易對**: {self.symbol}\n")
            f.write(f"- **時間週期**: {self.timeframe}\n")
            f.write(f"- **總數據量**: {len(self.df)} 筆\n")
            f.write(f"- **訓練集**: {len(self.train_data)} 筆\n")
            f.write(f"- **測試集**: {len(self.test_data)} 筆\n")
            f.write(f"- **特徵數量**: {len(self.features_train.columns)}\n")
            f.write(f"- **時間範圍**: {self.df.index.min()} ~ {self.df.index.max()}\n\n")

            f.write("## 2. 模型配置\n\n")
            f.write(f"- **模型類型**: XGBoost Regressor\n")
            f.write(f"- **樹數量**: {self.model.n_estimators}\n")
            f.write(f"- **最大深度**: {self.model.max_depth}\n")
            f.write(f"- **學習率**: {self.model.learning_rate}\n")
            f.write(f"- **子樣本比例**: {self.model.subsample}\n")
            f.write(f"- **特徵採樣**: {self.model.colsample_bytree}\n\n")

            f.write("## 3. 測試集性能\n\n")
            f.write("| 指標 | 數值 | 說明 |\n")
            f.write("|------|------|------|\n")
            metrics = self.results['test']['metrics']
            f.write(f"| RMSE | {metrics['rmse']:.2f} | 均方根誤差 |\n")
            f.write(f"| MAE | {metrics['mae']:.2f} | 平均絕對誤差 |\n")
            f.write(f"| R² | {metrics['r2']:.6f} | 決定係數 |\n")
            f.write(f"| MAPE | {metrics['mape']:.3f}% | 平均絕對百分比誤差 |\n")
            f.write(f"| 方向準確率 | {metrics['direction_accuracy']:.2f}% | 漲跌方向預測準確率 |\n\n")

            f.write("## 4. 訓練集性能\n\n")
            f.write("| 指標 | 數值 |\n")
            f.write("|------|------|\n")
            train_metrics = self.results['train']['metrics']
            for metric, value in train_metrics.items():
                f.write(f"| {metric.upper()} | {value:.6f} |\n")
            f.write("\n")

            f.write("## 5. 模型分析\n\n")

            # 過擬合分析
            train_r2 = train_metrics['r2']
            test_r2 = metrics['r2']
            r2_diff = train_r2 - test_r2

            f.write("### 5.1 泛化能力分析\n\n")
            f.write(f"- 訓練集 R²: {train_r2:.6f}\n")
            f.write(f"- 測試集 R²: {test_r2:.6f}\n")
            f.write(f"- R² 差距: {r2_diff:.6f}\n\n")

            if r2_diff < 0.05:
                f.write("**結論**: 模型泛化能力良好，無明顯過擬合。\n\n")
            elif r2_diff < 0.1:
                f.write("**結論**: 模型存在輕微過擬合，但仍可接受。\n\n")
            else:
                f.write("**結論**: 模型存在明顯過擬合，需要調整。\n\n")

            f.write("### 5.2 預測誤差分析\n\n")
            errors = self.results['test']['actual'] - self.results['test']['predictions']
            f.write(f"- 誤差均值: {errors.mean():.2f} USDT\n")
            f.write(f"- 誤差標準差: {errors.std():.2f} USDT\n")
            f.write(f"- 誤差最大值: {errors.max():.2f} USDT\n")
            f.write(f"- 誤差最小值: {errors.min():.2f} USDT\n\n")

            f.write("### 5.3 前10個重要特徵\n\n")
            top_features = self.results['feature_importance'].head(10)
            f.write("| 排名 | 特徵名稱 | 重要性 |\n")
            f.write("|------|----------|--------|\n")
            for idx, (i, row) in enumerate(top_features.iterrows(), 1):
                f.write(f"| {idx} | {row['feature']} | {row['importance']:.2f} |\n")
            f.write("\n")

            f.write("## 6. 結論與建議\n\n")

            if test_r2 > 0.95:
                f.write("### ✅ 模型表現優秀\n\n")
                f.write("模型在測試集上表現出色，R² 超過 0.95，預測準確度高。\n\n")
            elif test_r2 > 0.85:
                f.write("### ✓ 模型表現良好\n\n")
                f.write("模型在測試集上表現良好，可用於實際預測。\n\n")
            else:
                f.write("### ⚠ 模型需要改進\n\n")
                f.write("模型表現有待提升，建議進行以下優化：\n\n")

            f.write("**建議**:\n\n")
            if r2_diff > 0.1:
                f.write("1. 模型存在過擬合，考慮：\n")
                f.write("   - 增加正則化（調整 reg_alpha, reg_lambda）\n")
                f.write("   - 減少模型複雜度（減小 max_depth）\n")
                f.write("   - 增加訓練數據\n\n")

            f.write("2. 特徵工程優化：\n")
            f.write("   - 基於特徵重要性進行特徵選擇\n")
            f.write("   - 嘗試添加更多有價值的技術指標\n")
            f.write("   - 考慮特徵交互項\n\n")

            f.write("3. 超參數調優：\n")
            f.write("   - 使用網格搜索或貝葉斯優化\n")
            f.write("   - 交叉驗證確保穩定性\n\n")

        logger.info(f"報告已保存至: {report_path}")

    def save_results(self):
        """
        保存結果
        """
        logger.info("保存結果")

        # 保存模型
        model_path = os.path.join(self.output_dir, 'xgboost_model.joblib')
        self.model.save_model(model_path)

        # 保存預測結果
        predictions_df = pd.DataFrame({
            'timestamp': self.results['test']['timestamps'],
            'actual': self.results['test']['actual'],
            'predicted': self.results['test']['predictions'],
            'error': self.results['test']['actual'] - self.results['test']['predictions']
        })
        predictions_path = os.path.join(self.output_dir, 'predictions.csv')
        predictions_df.to_csv(predictions_path, index=False)
        logger.info(f"預測結果已保存至: {predictions_path}")

        # 保存元數據
        metadata = {
            'exchange': self.exchange,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'train_size': len(self.train_data),
            'test_size': len(self.test_data),
            'n_features': len(self.features_train.columns),
            'train_period': {
                'start': str(self.train_data.index.min()),
                'end': str(self.train_data.index.max())
            },
            'test_period': {
                'start': str(self.test_data.index.min()),
                'end': str(self.test_data.index.max())
            },
            'test_metrics': {
                k: float(v) for k, v in self.results['test']['metrics'].items()
            },
            'train_metrics': {
                k: float(v) for k, v in self.results['train']['metrics'].items()
            },
            'timestamp': datetime.now().isoformat()
        }

        metadata_path = os.path.join(self.output_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"元數據已保存至: {metadata_path}")

    def run(self):
        """
        執行完整的評估流程
        """
        logger.info("=" * 80)
        logger.info("開始 XGBoost 模型評估")
        logger.info("=" * 80)

        # 1. 載入數據
        self.load_data()

        # 2. 創建特徵
        features = self.create_features()

        # 3. 分割數據
        self.split_data(train_ratio=0.8)

        # 4. 訓練模型
        self.train_model(
            features,
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            early_stopping_rounds=20
        )

        # 5. 訓練集評估
        self.evaluate_on_train()

        # 6. 測試集評估
        self.evaluate_on_test()

        # 7. 特徵重要性分析
        self.analyze_feature_importance(top_n=20)

        # 8. 繪製結果
        self.plot_results()

        # 9. 生成報告
        self.generate_report()

        # 10. 保存結果
        self.save_results()

        logger.info("=" * 80)
        logger.info("XGBoost 評估完成！")
        logger.info(f"結果保存在: {self.output_dir}")
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
    evaluator = XGBoostEvaluator(
        exchange='bybit',
        symbol='BTC/USDT',
        timeframe='1h',
        output_dir='results/xgboost_btc_1h'
    )

    evaluator.run()


if __name__ == '__main__':
    main()
