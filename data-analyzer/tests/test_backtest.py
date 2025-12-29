"""
回測框架測試腳本

用途：測試完整的回測流程，整合特徵工程與策略執行
"""
import sys
from pathlib import Path

# 加入 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from features.feature_pipeline import FeaturePipeline
from feature_selection.selection_pipeline import SelectionPipeline
from backtesting.engine import BacktestEngine
from backtesting.strategy import BuyAndHoldStrategy, MovingAverageCrossStrategy
from backtesting.visualizer import BacktestVisualizer
from strategies.rsi_strategy import RSIStrategy


def test_backtest():
    """測試完整回測流程"""

    print("=" * 60)
    print("回測框架完整測試")
    print("=" * 60)

    # ========== 步驟 1: 載入資料與計算特徵 ==========
    print("\n### 步驟 1: 載入資料與計算特徵 ###")

    feature_pipeline = FeaturePipeline()

    df_features = feature_pipeline.run(
        symbol='BTC/USDT',
        timeframe='1m',
        limit=500,
        dropna=True
    )

    if df_features.empty:
        print("❌ 無法載入資料")
        return

    print(f"原始資料筆數: {len(df_features)}")
    print(f"原始特徵數: {df_features.shape[1]}")

    # ========== 步驟 2: 特徵選擇與優化 ==========
    print("\n### 步驟 2: 特徵選擇與優化 ###")

    # 準備目標變數
    df_features['target'] = df_features['close'].pct_change(1).shift(-1)
    df_features = df_features.dropna()

    selection_pipeline = SelectionPipeline()

    df_selected, report = selection_pipeline.run(
        df=df_features,
        target_col='target',
        methods=['remove_constant', 'remove_low_variance', 'remove_correlated'],
        scale_method='standard',
        correlation_threshold=0.95,
        variance_threshold=0.01,
        clip_outliers=True,
        outlier_std=3.0
    )

    print(f"選擇後特徵數: {df_selected.shape[1]}")
    print(f"選擇後資料筆數: {len(df_selected)}")

    # ========== 步驟 3: 準備回測資料 ==========
    print("\n### 步驟 3: 準備回測資料 ###")

    # 分離市場資料（OHLCV）與特徵
    market_cols = ['open', 'high', 'low', 'close', 'volume']
    market_data = df_features[market_cols].copy()

    # 只保留有特徵的時間點
    common_index = market_data.index.intersection(df_selected.index)
    market_data = market_data.loc[common_index]

    # 移除 target 欄位，只保留特徵
    features_data = df_selected.drop(columns=['target'], errors='ignore')

    print(f"市場資料筆數: {len(market_data)}")
    print(f"特徵資料筆數: {len(features_data)}")

    # ========== 步驟 4: 執行回測 - Buy and Hold ==========
    print("\n### 步驟 4a: Buy and Hold 策略 ###")

    engine1 = BacktestEngine(
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    strategy1 = BuyAndHoldStrategy()

    results1 = engine1.run(
        data=market_data,
        strategy=strategy1,
        features=features_data,
        symbol='BTC/USDT'
    )

    # ========== 步驟 4b: MA Cross 策略 ==========
    print("\n### 步驟 4b: MA Cross 策略 ###")

    engine2 = BacktestEngine(
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    strategy2 = MovingAverageCrossStrategy(fast_period=10, slow_period=30)

    results2 = engine2.run(
        data=market_data,
        strategy=strategy2,
        features=features_data,
        symbol='BTC/USDT'
    )

    # ========== 步驟 4c: RSI 策略 ==========
    print("\n### 步驟 4c: RSI 策略 ###")

    engine3 = BacktestEngine(
        initial_capital=10000.0,
        commission_rate=0.001,
        slippage_rate=0.0005
    )

    strategy3 = RSIStrategy(
        rsi_period=14,
        oversold_threshold=30,
        overbought_threshold=70
    )

    results3 = engine3.run(
        data=market_data,
        strategy=strategy3,
        features=features_data,
        symbol='BTC/USDT'
    )

    # ========== 步驟 5: 比較策略績效 ==========
    print("\n### 步驟 5: 策略績效比較 ###")
    print("=" * 60)

    strategies_comparison = [
        ('Buy and Hold', results1['metrics']),
        ('MA Cross (10/30)', results2['metrics']),
        ('RSI (14, 30/70)', results3['metrics']),
    ]

    print(f"{'策略':<20} {'總收益':<12} {'Sharpe':<10} {'最大回撤':<12} {'交易次數':<10}")
    print("-" * 70)

    for name, metrics in strategies_comparison:
        total_return = metrics.get('total_return', 0) * 100
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0) * 100
        trades = metrics.get('total_trades', 0)

        print(f"{name:<20} {total_return:>10.2f}%  {sharpe:>8.3f}  {max_dd:>10.2f}%  {trades:>8}")

    print("=" * 60)

    # ========== 步驟 6: 顯示詳細結果 ==========
    print("\n### 步驟 6: 詳細交易記錄（RSI 策略）###")

    trades_df = results3['trades']
    if not trades_df.empty:
        print("\n前 10 筆交易：")
        print(trades_df.head(10)[['symbol', 'side', 'quantity', 'price', 'commission', 'pnl']])
    else:
        print("無交易記錄")

    signals_df = results3['signals']
    if not signals_df.empty:
        print(f"\n信號統計：")
        print(signals_df['action'].value_counts())
    else:
        print("無信號記錄")

    # ========== 步驟 7: 生成視覺化報告 ==========
    print("\n### 步驟 7: 生成視覺化報告 ###")

    # 建立視覺化器
    visualizer = BacktestVisualizer(figsize=(15, 10))

    # 生成報告目錄
    report_dir = Path(__file__).parent.parent / "results" / "backtest_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n生成視覺化報告至：{report_dir}")

    # 為每個策略生成完整報告
    strategies_to_visualize = [
        ('BuyAndHold', results1),
        ('MA_Cross', results2),
        ('RSI', results3),
    ]

    for strategy_name, results in strategies_to_visualize:
        print(f"\n正在生成 {strategy_name} 報告...")

        # 生成視覺化報告
        visualizer.plot_comprehensive_report(
            equity_curve=results['equity_curve'],
            market_data=market_data,
            signals=results['signals'],
            trades=results['trades'],
            metrics=results['metrics'],
            strategy_name=strategy_name,
            save_dir=str(report_dir / strategy_name)
        )

        # 保存 JSON 結構化資料
        strategy_result_dir = report_dir / strategy_name
        strategy_result_dir.mkdir(parents=True, exist_ok=True)

        result_json = {
            'strategy_name': strategy_name,
            'metadata': {
                'generated_at': pd.Timestamp.now().isoformat(),
                'symbol': 'BTC/USDT',
                'data_period': {
                    'start': market_data.index[0].isoformat(),
                    'end': market_data.index[-1].isoformat(),
                },
                'total_bars': len(market_data),
            },
            'metrics': results['metrics'],
            'has_visualizations': True,
        }

        json_path = strategy_result_dir / f"{strategy_name}_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(result_json, f, indent=2, ensure_ascii=False, default=str)

        print(f"✓ JSON 資料已保存：{json_path.name}")

    print("\n" + "=" * 60)
    print("✅ 回測測試完成！")
    print(f"📊 視覺化報告已生成至：{report_dir}")
    print("=" * 60)

    return {
        'buy_and_hold': results1,
        'ma_cross': results2,
        'rsi': results3,
        'market_data': market_data,
        'report_dir': report_dir,
    }


if __name__ == "__main__":
    results = test_backtest()
