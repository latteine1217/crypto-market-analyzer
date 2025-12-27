"""
基於 XGBoost 預測的交易策略回測
"""

import numpy as np
import pandas as pd
import psycopg2
import logging
import json
import joblib
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TradingStrategy:
    """交易策略基類"""

    def __init__(self, name):
        self.name = name
        self.positions = []
        self.trades = []

    def generate_signals(self, predictions, actuals):
        """生成交易信號（需在子類中實現）"""
        raise NotImplementedError


class ThresholdStrategy(TradingStrategy):
    """閾值策略：當預測變化超過閾值時交易"""

    def __init__(self, threshold=0.005):
        super().__init__(f"Threshold_{threshold}")
        self.threshold = threshold

    def generate_signals(self, predictions, actuals):
        """
        生成信號：
        - 預測上漲 > threshold: 買入 (1)
        - 預測下跌 < -threshold: 賣出 (-1)
        - 其他: 持平 (0)
        """
        pred_returns = np.diff(predictions) / predictions[:-1]
        signals = np.zeros(len(predictions))

        for i in range(1, len(predictions)):
            if pred_returns[i-1] > self.threshold:
                signals[i] = 1  # 買入
            elif pred_returns[i-1] < -self.threshold:
                signals[i] = -1  # 賣出
            else:
                signals[i] = 0  # 持平

        return signals


class DirectionStrategy(TradingStrategy):
    """方向策略：根據預測方向交易"""

    def __init__(self):
        super().__init__("Direction")

    def generate_signals(self, predictions, actuals):
        """
        生成信號：
        - 預測上漲: 買入 (1)
        - 預測下跌: 賣出 (-1)
        """
        pred_direction = np.diff(predictions) > 0
        signals = np.zeros(len(predictions))

        for i in range(1, len(predictions)):
            signals[i] = 1 if pred_direction[i-1] else -1

        return signals


class MomentumStrategy(TradingStrategy):
    """動量策略：結合預測和實際價格動量"""

    def __init__(self, lookback=5):
        super().__init__(f"Momentum_{lookback}")
        self.lookback = lookback

    def generate_signals(self, predictions, actuals):
        """
        生成信號：預測方向與近期動量一致時交易
        """
        pred_direction = np.diff(predictions) > 0
        signals = np.zeros(len(predictions))

        for i in range(self.lookback + 1, len(predictions)):
            # 計算近期動量
            recent_momentum = actuals[i-1] - actuals[i-self.lookback-1]

            # 預測方向與動量一致
            if pred_direction[i-1] and recent_momentum > 0:
                signals[i] = 1
            elif not pred_direction[i-1] and recent_momentum < 0:
                signals[i] = -1

        return signals


class BacktestEngine:
    """回測引擎"""

    def __init__(
        self,
        initial_capital=10000,
        commission_rate=0.001,  # 0.1% 手續費
        slippage_rate=0.0005    # 0.05% 滑價
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def run_backtest(self, prices, signals):
        """
        運行回測

        Args:
            prices: 實際價格序列
            signals: 交易信號 (1: 買入, -1: 賣出, 0: 持平)

        Returns:
            回測結果字典
        """
        logger.info("開始回測...")

        portfolio_value = [self.initial_capital]
        cash = self.initial_capital
        position = 0  # 持倉數量
        trades = []

        for i in range(len(signals)):
            current_price = prices[i]

            # 執行交易
            if signals[i] == 1 and position <= 0:  # 買入信號
                # 計算可買入數量（使用全部現金）
                cost_with_fees = current_price * (1 + self.commission_rate + self.slippage_rate)
                buy_quantity = cash / cost_with_fees

                if buy_quantity > 0:
                    total_cost = buy_quantity * cost_with_fees
                    cash -= total_cost
                    position += buy_quantity

                    trades.append({
                        'index': i,
                        'action': 'BUY',
                        'price': current_price,
                        'quantity': buy_quantity,
                        'cost': total_cost,
                        'cash_after': cash,
                        'position_after': position
                    })

            elif signals[i] == -1 and position > 0:  # 賣出信號
                # 賣出全部持倉
                sell_price = current_price * (1 - self.commission_rate - self.slippage_rate)
                sell_proceeds = position * sell_price

                cash += sell_proceeds

                trades.append({
                    'index': i,
                    'action': 'SELL',
                    'price': current_price,
                    'quantity': position,
                    'proceeds': sell_proceeds,
                    'cash_after': cash,
                    'position_after': 0
                })

                position = 0

            # 計算當前組合價值
            current_value = cash + position * current_price
            portfolio_value.append(current_value)

        # 最終平倉
        if position > 0:
            final_price = prices[-1] * (1 - self.commission_rate - self.slippage_rate)
            final_proceeds = position * final_price
            cash += final_proceeds
            trades.append({
                'index': len(signals) - 1,
                'action': 'FINAL_SELL',
                'price': prices[-1],
                'quantity': position,
                'proceeds': final_proceeds,
                'cash_after': cash,
                'position_after': 0
            })

        final_value = cash

        logger.info(f"回測完成。初始資金: ${self.initial_capital:.2f}, 最終價值: ${final_value:.2f}")

        return {
            'portfolio_value': portfolio_value,
            'trades': trades,
            'final_value': final_value,
            'total_return': (final_value - self.initial_capital) / self.initial_capital * 100
        }

    def calculate_metrics(self, portfolio_value, trades):
        """計算策略績效指標"""
        logger.info("計算績效指標...")

        portfolio_value = np.array(portfolio_value)

        # 報酬
        total_return = (portfolio_value[-1] - portfolio_value[0]) / portfolio_value[0] * 100

        # 計算日報酬率
        returns = np.diff(portfolio_value) / portfolio_value[:-1]

        # Sharpe Ratio (假設無風險利率為 0)
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

        # Maximum Drawdown
        cumulative_max = np.maximum.accumulate(portfolio_value)
        drawdowns = (portfolio_value - cumulative_max) / cumulative_max
        max_drawdown = np.min(drawdowns) * 100

        # 勝率
        winning_trades = sum(1 for t in trades if t.get('proceeds', 0) > t.get('cost', float('inf')))
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        metrics = {
            'Total_Return': total_return,
            'Sharpe_Ratio': sharpe_ratio,
            'Max_Drawdown': max_drawdown,
            'Win_Rate': win_rate,
            'Total_Trades': total_trades,
            'Final_Value': portfolio_value[-1]
        }

        logger.info("績效指標:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}")

        return metrics


def load_model_and_data():
    """載入模型和數據"""
    logger.info("載入模型和數據...")

    # 載入 XGBoost 模型
    model_path = Path('results/xgboost_btc_1h/xgboost_model.joblib')
    if not model_path.exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")

    model_data = joblib.load(model_path)
    model = model_data['model']
    feature_names = model_data.get('feature_names', [])

    logger.info("模型載入成功")

    # 載入數據
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

    logger.info(f"數據載入成功: {len(df)} 筆")

    return model, df, feature_names


def create_features(df):
    """創建特徵"""
    from src.features.technical_indicators import TechnicalIndicators
    from src.features.price_features import PriceFeatures
    from src.features.volume_features import VolumeFeatures

    tech_indicators = TechnicalIndicators()
    price_features = PriceFeatures()
    volume_features = VolumeFeatures()

    tech_feat = tech_indicators.calculate_all(df)
    price_feat = price_features.calculate_all(df)
    volume_feat = volume_features.calculate_all(df)

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

    features = features.ffill().dropna()

    # 確保只保留數值型列
    numeric_columns = features.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) < len(features.columns):
        non_numeric = set(features.columns) - set(numeric_columns)
        logger.warning(f"移除非數值列: {non_numeric}")
        features = features[numeric_columns]

    return features


def plot_backtest_results(strategies_results, output_dir):
    """繪製回測結果"""
    logger.info("繪製回測結果...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. 組合價值曲線
    ax1 = axes[0, 0]
    for strategy_name, results in strategies_results.items():
        portfolio_value = results['backtest']['portfolio_value']
        ax1.plot(portfolio_value, label=strategy_name, linewidth=1.5, alpha=0.8)

    ax1.axhline(y=10000, color='black', linestyle='--', linewidth=1, label='Initial Capital')
    ax1.set_title('Portfolio Value Over Time')
    ax1.set_xlabel('Time Step')
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 總報酬比較
    ax2 = axes[0, 1]
    strategy_names = list(strategies_results.keys())
    returns = [strategies_results[s]['metrics']['Total_Return'] for s in strategy_names]
    colors = ['green' if r > 0 else 'red' for r in returns]

    bars = ax2.bar(strategy_names, returns, color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax2.set_title('Total Return by Strategy')
    ax2.set_ylabel('Return (%)')
    ax2.grid(True, alpha=0.3, axis='y')

    for i, v in enumerate(returns):
        ax2.text(i, v + (2 if v > 0 else -2), f'{v:.2f}%',
                ha='center', va='bottom' if v > 0 else 'top', fontweight='bold')

    # 3. Sharpe Ratio 比較
    ax3 = axes[1, 0]
    sharpe_ratios = [strategies_results[s]['metrics']['Sharpe_Ratio'] for s in strategy_names]

    bars = ax3.bar(strategy_names, sharpe_ratios, alpha=0.7, color='steelblue')
    ax3.set_title('Sharpe Ratio by Strategy')
    ax3.set_ylabel('Sharpe Ratio')
    ax3.grid(True, alpha=0.3, axis='y')

    for i, v in enumerate(sharpe_ratios):
        ax3.text(i, v + 0.05, f'{v:.2f}', ha='center', va='bottom', fontweight='bold')

    # 4. Max Drawdown 比較
    ax4 = axes[1, 1]
    drawdowns = [strategies_results[s]['metrics']['Max_Drawdown'] for s in strategy_names]

    bars = ax4.bar(strategy_names, drawdowns, alpha=0.7, color='coral')
    ax4.set_title('Maximum Drawdown by Strategy')
    ax4.set_ylabel('Max Drawdown (%)')
    ax4.grid(True, alpha=0.3, axis='y')

    for i, v in enumerate(drawdowns):
        ax4.text(i, v - 0.5, f'{v:.2f}%', ha='center', va='top', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_dir / 'backtest_results.png', dpi=150, bbox_inches='tight')
    logger.info(f"回測結果圖已保存至 {output_dir / 'backtest_results.png'}")


def generate_backtest_report(strategies_results, output_dir):
    """生成回測報告"""
    report = f"""# 交易策略回測報告

**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 回測配置

- **初始資金**: $10,000
- **手續費**: 0.1%
- **滑價**: 0.05%
- **數據期間**: Bybit BTC/USDT 1小時數據

## 2. 策略概覽

"""

    for strategy_name, results in strategies_results.items():
        report += f"""
### {strategy_name}

**策略說明**: {results['description']}

**績效指標**:

| 指標 | 數值 |
|------|------|
| 總報酬 | {results['metrics']['Total_Return']:.2f}% |
| Sharpe Ratio | {results['metrics']['Sharpe_Ratio']:.4f} |
| 最大回撤 | {results['metrics']['Max_Drawdown']:.2f}% |
| 勝率 | {results['metrics']['Win_Rate']:.2f}% |
| 交易次數 | {results['metrics']['Total_Trades']} |
| 最終價值 | ${results['metrics']['Final_Value']:.2f} |

"""

    # 找出最佳策略
    best_strategy = max(strategies_results.keys(),
                       key=lambda s: strategies_results[s]['metrics']['Total_Return'])

    report += f"""
## 3. 最佳策略

**{best_strategy}** 表現最佳，總報酬達到 **{strategies_results[best_strategy]['metrics']['Total_Return']:.2f}%**。

## 4. Buy & Hold 基準

為了比較策略效果，我們計算了簡單的買入持有策略：

- 在回測開始時買入並持有到結束
- 不進行任何交易
- 僅承擔初始買入的手續費和滑價

## 5. 風險警告

⚠️ **重要提醒**:

1. **回測結果不代表未來表現**
2. **實際交易會有更多滑價和市場衝擊成本**
3. **未考慮資金費率、流動性風險等因素**
4. **建議在模擬環境中充分測試後再投入實盤**

## 6. 後續建議

1. **樣本外測試**: 在未見過的數據上驗證策略
2. **參數優化**: 針對不同市場環境調整參數
3. **風險管理**: 添加止損、倉位管理等風控機制
4. **多策略組合**: 考慮多策略分散風險
"""

    with open(output_dir / 'backtest_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    logger.info(f"回測報告已保存至 {output_dir / 'backtest_report.md'}")


def main():
    """主函數"""
    logger.info("=" * 80)
    logger.info("開始交易策略回測")
    logger.info("=" * 80)

    # 1. 載入已有的預測結果（從 XGBoost 評估）
    predictions_path = Path('results/xgboost_btc_1h/predictions.csv')
    if not predictions_path.exists():
        raise FileNotFoundError(f"預測結果文件不存在: {predictions_path}")

    predictions_df = pd.read_csv(predictions_path)
    predictions = predictions_df['predicted'].values
    actuals = predictions_df['actual'].values

    logger.info(f"載入預測結果: {len(predictions)} 筆")
    logger.info(f"預測範圍: {predictions.min():.2f} ~ {predictions.max():.2f}")
    logger.info(f"實際範圍: {actuals.min():.2f} ~ {actuals.max():.2f}")

    # 5. 定義策略
    strategies = [
        ThresholdStrategy(threshold=0.005),
        ThresholdStrategy(threshold=0.01),
        DirectionStrategy(),
        MomentumStrategy(lookback=5)
    ]

    # 6. 回測引擎
    engine = BacktestEngine(
        initial_capital=10000,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    # 7. 運行回測
    strategies_results = {}

    for strategy in strategies:
        logger.info(f"\n{'='*60}")
        logger.info(f"回測策略: {strategy.name}")
        logger.info(f"{'='*60}")

        signals = strategy.generate_signals(predictions, actuals)
        backtest_result = engine.run_backtest(actuals, signals)
        metrics = engine.calculate_metrics(backtest_result['portfolio_value'], backtest_result['trades'])

        strategies_results[strategy.name] = {
            'backtest': backtest_result,
            'metrics': metrics,
            'description': strategy.__class__.__doc__.strip()
        }

    # 8. Buy & Hold 基準
    logger.info(f"\n{'='*60}")
    logger.info("計算 Buy & Hold 基準")
    logger.info(f"{'='*60}")

    buy_hold_signals = np.ones(len(actuals))
    buy_hold_signals[1:] = 0  # 只在第一天買入
    buy_hold_result = engine.run_backtest(actuals, buy_hold_signals)
    buy_hold_metrics = engine.calculate_metrics(buy_hold_result['portfolio_value'], buy_hold_result['trades'])

    strategies_results['Buy_&_Hold'] = {
        'backtest': buy_hold_result,
        'metrics': buy_hold_metrics,
        'description': '買入並持有到結束'
    }

    # 9. 保存結果
    output_dir = Path('results/backtest_results')
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存詳細結果
    for strategy_name, results in strategies_results.items():
        strategy_dir = output_dir / strategy_name
        strategy_dir.mkdir(exist_ok=True)

        # 保存指標
        with open(strategy_dir / 'metrics.json', 'w') as f:
            json.dump(results['metrics'], f, indent=2)

        # 保存交易記錄
        trades_df = pd.DataFrame(results['backtest']['trades'])
        if not trades_df.empty:
            trades_df.to_csv(strategy_dir / 'trades.csv', index=False)

    # 10. 繪製圖表
    plot_backtest_results(strategies_results, output_dir)

    # 11. 生成報告
    generate_backtest_report(strategies_results, output_dir)

    logger.info("=" * 80)
    logger.info("交易策略回測完成！")
    logger.info("=" * 80)

    # 打印摘要
    print("\n" + "=" * 100)
    print("回測結果摘要")
    print("=" * 100)

    for strategy_name, results in strategies_results.items():
        print(f"\n【{strategy_name}】")
        print(f"  總報酬: {results['metrics']['Total_Return']:.2f}%")
        print(f"  Sharpe Ratio: {results['metrics']['Sharpe_Ratio']:.4f}")
        print(f"  最大回撤: {results['metrics']['Max_Drawdown']:.2f}%")
        print(f"  勝率: {results['metrics']['Win_Rate']:.2f}%")
        print(f"  交易次數: {results['metrics']['Total_Trades']}")

    print("\n" + "=" * 100)


if __name__ == '__main__':
    main()
