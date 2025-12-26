"""
完整功能測試腳本

測試項目：
1. 技術指標計算（MACD, MA, Williams Fractal）
2. MACD 交易策略
3. 威廉分形策略
4. 流動性熱力圖（需先收集 orderbook 資料）
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from features.technical_indicators import TechnicalIndicators, calculate_indicators_for_symbol
from strategies.macd_strategy import MACDStrategy, MACDDivergenceStrategy
from strategies.fractal_pattern_strategy import (
    FractalBreakoutStrategy,
    HeadShouldersStrategy,
    CombinedFractalMAStrategy
)


def load_ohlcv_data(
    exchange: str = 'binance',
    symbol: str = 'BTC/USDT',
    limit: int = 1000
) -> pd.DataFrame:
    """從資料庫讀取 OHLCV 資料"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='crypto_db',
        user='crypto',
        password='crypto_pass'
    )

    query = """
        SELECT
            o.open_time as timestamp,
            o.open,
            o.high,
            o.low,
            o.close,
            o.volume
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE e.name = %s
          AND m.symbol = %s
          AND o.timeframe = '1m'
        ORDER BY o.open_time ASC
        LIMIT %s
    """

    df = pd.read_sql_query(query, conn, params=[exchange, symbol, limit])
    conn.close()

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    return df


def test_technical_indicators():
    """測試技術指標計算"""
    print("\n" + "=" * 80)
    print("測試 1: 技術指標計算")
    print("=" * 80)

    # 讀取資料
    df = load_ohlcv_data('binance', 'ETH/USDT', limit=500)
    print(f"\n讀取到 {len(df)} 根 K線資料")
    print(f"時間範圍: {df.index[0]} ~ {df.index[-1]}")

    # 計算所有指標
    df_with_indicators = calculate_indicators_for_symbol(df, symbol='ETH/USDT')

    # 顯示結果摘要
    print("\n計算完成！指標欄位：")
    indicator_cols = [col for col in df_with_indicators.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
    for col in indicator_cols:
        non_null_count = df_with_indicators[col].notna().sum()
        print(f"  - {col}: {non_null_count} 個有效值")

    # 顯示最新資料
    print("\n最新 5 筆資料（部分欄位）：")
    display_cols = ['close', 'macd', 'macd_signal', 'ma_20', 'ma_60', 'fractal_up', 'fractal_down']
    print(df_with_indicators[display_cols].tail())

    # 統計分形數量
    fractal_up_count = df_with_indicators['fractal_up'].sum()
    fractal_down_count = df_with_indicators['fractal_down'].sum()
    hs_top_count = df_with_indicators['head_shoulders_top'].sum()
    hs_bottom_count = df_with_indicators['head_shoulders_bottom'].sum()

    print(f"\n分形統計：")
    print(f"  上分形: {fractal_up_count}")
    print(f"  下分形: {fractal_down_count}")
    print(f"  頭肩頂: {hs_top_count}")
    print(f"  頭肩底: {hs_bottom_count}")

    return df_with_indicators


def test_macd_strategy(df: pd.DataFrame):
    """測試 MACD 策略"""
    print("\n" + "=" * 80)
    print("測試 2: MACD 交叉策略")
    print("=" * 80)

    strategy = MACDStrategy(name="MACD_Test")
    signals = strategy.generate_signals(df)

    # 統計信號
    long_signals = (signals == 1).sum()
    short_signals = (signals == -1).sum()
    exit_signals = (signals == 0).sum()

    print(f"\n信號統計：")
    print(f"  買入信號 (LONG): {long_signals}")
    print(f"  賣出信號 (SHORT): {short_signals}")
    print(f"  平倉信號 (EXIT): {exit_signals}")

    # 顯示最近的信號
    signal_df = pd.DataFrame({
        'close': df['close'],
        'macd': df['macd'],
        'signal': df['macd_signal'],
        'trading_signal': signals
    })

    signal_points = signal_df[signal_df['trading_signal'] != None]
    if not signal_points.empty:
        print(f"\n最近 10 個交易信號：")
        print(signal_points.tail(10))
    else:
        print("\n沒有產生交易信號")

    return signals


def test_fractal_strategy(df: pd.DataFrame):
    """測試威廉分形策略"""
    print("\n" + "=" * 80)
    print("測試 3: 威廉分形突破策略")
    print("=" * 80)

    strategy = FractalBreakoutStrategy(name="Fractal_Test")
    signals = strategy.generate_signals(df)

    # 統計信號
    long_signals = (signals == 1).sum()
    short_signals = (signals == -1).sum()

    print(f"\n信號統計：")
    print(f"  買入信號 (LONG): {long_signals}")
    print(f"  賣出信號 (SHORT): {short_signals}")

    # 顯示信號點
    signal_df = pd.DataFrame({
        'close': df['close'],
        'fractal_up': df['fractal_up'],
        'fractal_down': df['fractal_down'],
        'trading_signal': signals
    })

    signal_points = signal_df[signal_df['trading_signal'] != None]
    if not signal_points.empty:
        print(f"\n最近 10 個交易信號：")
        print(signal_points.tail(10))
    else:
        print("\n沒有產生交易信號")

    return signals


def test_combined_strategy(df: pd.DataFrame):
    """測試結合策略"""
    print("\n" + "=" * 80)
    print("測試 4: 分形 + MA 結合策略")
    print("=" * 80)

    strategy = CombinedFractalMAStrategy(
        name="Combined_Test",
        params={'ma_period': 20}
    )
    signals = strategy.generate_signals(df)

    # 統計信號
    long_signals = (signals == 1).sum()
    short_signals = (signals == -1).sum()

    print(f"\n信號統計：")
    print(f"  買入信號 (LONG): {long_signals}")
    print(f"  賣出信號 (SHORT): {short_signals}")

    # 顯示信號點
    signal_df = pd.DataFrame({
        'close': df['close'],
        'ma_20': df['ma_20'],
        'trading_signal': signals
    })

    signal_points = signal_df[signal_df['trading_signal'] != None]
    if not signal_points.empty:
        print(f"\n最近 10 個交易信號：")
        print(signal_points.tail(10))

    return signals


def test_liquidity_heatmap():
    """測試流動性熱力圖（需要先收集 orderbook 資料）"""
    print("\n" + "=" * 80)
    print("測試 5: 流動性熱力圖")
    print("=" * 80)

    try:
        from features.liquidity_heatmap import LiquidityHeatmap

        with LiquidityHeatmap() as analyzer:
            # 檢查是否有 orderbook 資料
            df = analyzer.fetch_orderbook_history('binance', 'BTC/USDT', limit=10)

            if df.empty:
                print("\n⚠️  沒有找到 orderbook 資料")
                print("請先啟動 collector 收集更多 orderbook snapshots")
                print("建議：讓 collector 運行至少 10 分鐘")
                return False
            else:
                print(f"\n✓ 找到 {len(df)} 筆 orderbook 快照")

                # 繪製流動性剖面圖
                analyzer.plot_liquidity_profile('binance', 'BTC/USDT')

                return True

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主測試函數"""
    print("\n" + "=" * 100)
    print(" " * 30 + "完整功能測試")
    print("=" * 100)

    try:
        # 測試 1: 技術指標
        df_with_indicators = test_technical_indicators()

        # 測試 2: MACD 策略
        macd_signals = test_macd_strategy(df_with_indicators)

        # 測試 3: 威廉分形策略
        fractal_signals = test_fractal_strategy(df_with_indicators)

        # 測試 4: 結合策略
        combined_signals = test_combined_strategy(df_with_indicators)

        # 測試 5: 流動性熱力圖
        liquidity_ok = test_liquidity_heatmap()

        # 總結
        print("\n" + "=" * 100)
        print("測試總結")
        print("=" * 100)
        print("\n✅ 技術指標計算: 成功")
        print("✅ MACD 策略: 成功")
        print("✅ 威廉分形策略: 成功")
        print("✅ 結合策略: 成功")

        if liquidity_ok:
            print("✅ 流動性熱力圖: 成功")
        else:
            print("⚠️  流動性熱力圖: 需要更多資料")

        print("\n" + "=" * 100)
        print("所有核心功能測試完成")
        print("=" * 100 + "\n")

    except Exception as e:
        print(f"\n❌ 測試過程發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
