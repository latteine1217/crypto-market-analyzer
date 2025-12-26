"""
流動性熱力圖（掛單熱力圖）

功能：
1. 從 orderbook_snapshots 讀取歷史訂單簿資料
2. 聚合不同時間點的流動性分布
3. 生成熱力圖視覺化
4. 識別流動性集中區域（支撐/阻力位）
"""
import pandas as pd
import numpy as np
import psycopg2
from typing import Optional, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json


class LiquidityHeatmap:
    """流動性熱力圖分析器"""

    def __init__(
        self,
        db_host: str = 'localhost',
        db_port: int = 5432,
        db_name: str = 'crypto_db',
        db_user: str = 'crypto',
        db_password: str = 'crypto_pass'
    ):
        """初始化資料庫連接"""
        self.conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )

    def fetch_orderbook_history(
        self,
        exchange: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        從資料庫讀取訂單簿歷史資料

        Args:
            exchange: 交易所名稱
            symbol: 交易對
            start_time: 開始時間
            end_time: 結束時間
            limit: 最大筆數

        Returns:
            包含 timestamp, bids, asks 的 DataFrame
        """
        query = """
            SELECT
                obs.timestamp,
                obs.bids,
                obs.asks
            FROM orderbook_snapshots obs
            JOIN markets m ON obs.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE e.name = %s AND m.symbol = %s
        """

        params = [exchange, symbol]

        if start_time:
            query += " AND obs.timestamp >= %s"
            params.append(start_time)

        if end_time:
            query += " AND obs.timestamp <= %s"
            params.append(end_time)

        query += " ORDER BY obs.timestamp DESC LIMIT %s"
        params.append(limit)

        df = pd.read_sql_query(query, self.conn, params=params)
        return df

    def aggregate_liquidity(
        self,
        orderbook_df: pd.DataFrame,
        price_resolution: float = 0.01  # 價格區間精度（百分比）
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        聚合訂單簿資料，計算每個價格層級的累計流動性

        Args:
            orderbook_df: 訂單簿歷史資料
            price_resolution: 價格分組精度（相對百分比）

        Returns:
            (bids_aggregated, asks_aggregated) 兩個 DataFrame
            columns: ['price_level', 'cumulative_volume', 'count']
        """
        all_bids = []
        all_asks = []

        # 收集所有訂單簿數據
        for idx, row in orderbook_df.iterrows():
            timestamp = row['timestamp']
            bids = row['bids']
            asks = row['asks']

            # 如果是 JSONB，已經被 psycopg2 轉換為 Python list
            for price, volume in bids:
                all_bids.append({
                    'timestamp': timestamp,
                    'price': float(price),
                    'volume': float(volume)
                })

            for price, volume in asks:
                all_asks.append({
                    'timestamp': timestamp,
                    'price': float(price),
                    'volume': float(volume)
                })

        # 轉換為 DataFrame
        bids_df = pd.DataFrame(all_bids)
        asks_df = pd.DataFrame(all_asks)

        if bids_df.empty or asks_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 計算價格區間（基於中間價的百分比）
        mid_price = (bids_df['price'].max() + asks_df['price'].min()) / 2

        # 將價格分組到區間
        def assign_price_level(price, mid, resolution):
            return round(((price / mid) - 1) / resolution) * resolution

        bids_df['price_level'] = bids_df['price'].apply(
            lambda p: assign_price_level(p, mid_price, price_resolution)
        )
        asks_df['price_level'] = asks_df['price'].apply(
            lambda p: assign_price_level(p, mid_price, price_resolution)
        )

        # 聚合每個價格層級的流動性
        bids_agg = bids_df.groupby('price_level').agg({
            'volume': 'sum',
            'price': 'count'
        }).rename(columns={'volume': 'cumulative_volume', 'price': 'count'})

        asks_agg = asks_df.groupby('price_level').agg({
            'volume': 'sum',
            'price': 'count'
        }).rename(columns={'volume': 'cumulative_volume', 'price': 'count'})

        return bids_agg.reset_index(), asks_agg.reset_index()

    def create_heatmap_data(
        self,
        orderbook_df: pd.DataFrame,
        time_bins: int = 50,
        price_bins: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        建立熱力圖資料矩陣

        Args:
            orderbook_df: 訂單簿歷史資料
            time_bins: 時間軸分箱數
            price_bins: 價格軸分箱數

        Returns:
            (time_edges, price_edges, volume_matrix)
            volume_matrix[i, j] = 時間區間 i，價格區間 j 的累計掛單量
        """
        all_data = []

        for idx, row in orderbook_df.iterrows():
            timestamp = pd.to_datetime(row['timestamp'])
            bids = row['bids']
            asks = row['asks']

            # 處理 Bids
            for price, volume in bids:
                all_data.append({
                    'timestamp': timestamp,
                    'price': float(price),
                    'volume': float(volume),
                    'side': 'bid'
                })

            # 處理 Asks
            for price, volume in asks:
                all_data.append({
                    'timestamp': timestamp,
                    'price': float(price),
                    'volume': float(volume),
                    'side': 'ask'
                })

        df = pd.DataFrame(all_data)

        if df.empty:
            return np.array([]), np.array([]), np.array([[]])

        # 轉換時間為數值（秒）
        df['time_numeric'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds()

        # 建立 2D histogram
        H, time_edges, price_edges = np.histogram2d(
            df['time_numeric'],
            df['price'],
            bins=[time_bins, price_bins],
            weights=df['volume']
        )

        return time_edges, price_edges, H

    def plot_liquidity_heatmap(
        self,
        exchange: str,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        time_bins: int = 50,
        price_bins: int = 100,
        save_path: Optional[str] = None
    ):
        """
        繪製流動性熱力圖

        Args:
            exchange: 交易所
            symbol: 交易對
            start_time: 開始時間
            end_time: 結束時間
            time_bins: 時間分箱數
            price_bins: 價格分箱數
            save_path: 儲存路徑（若指定）
        """
        # 讀取資料
        print(f"正在讀取 {exchange} {symbol} 的訂單簿資料...")
        df = self.fetch_orderbook_history(exchange, symbol, start_time, end_time)

        if df.empty:
            print("沒有找到訂單簿資料")
            return

        print(f"讀取到 {len(df)} 筆訂單簿快照")

        # 建立熱力圖資料
        time_edges, price_edges, volume_matrix = self.create_heatmap_data(
            df, time_bins, price_bins
        )

        # 繪製熱力圖
        fig, ax = plt.subplots(figsize=(14, 8))

        # 使用 imshow 繪製熱力圖
        im = ax.imshow(
            volume_matrix.T,
            aspect='auto',
            origin='lower',
            cmap='YlOrRd',
            interpolation='bilinear'
        )

        # 設定標籤
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price Level', fontsize=12)
        ax.set_title(
            f'Liquidity Heatmap - {exchange.upper()} {symbol}\n'
            f'{df["timestamp"].min()} to {df["timestamp"].max()}',
            fontsize=14
        )

        # 添加顏色條
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Cumulative Volume', fontsize=12)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"熱力圖已儲存至: {save_path}")

        plt.show()

    def identify_liquidity_clusters(
        self,
        orderbook_df: pd.DataFrame,
        percentile_threshold: float = 90.0
    ) -> Tuple[List[float], List[float]]:
        """
        識別流動性集中區域（潛在的支撐/阻力位）

        Args:
            orderbook_df: 訂單簿歷史資料
            percentile_threshold: 流動性百分位閾值

        Returns:
            (support_levels, resistance_levels)
        """
        bids_agg, asks_agg = self.aggregate_liquidity(orderbook_df)

        if bids_agg.empty or asks_agg.empty:
            return [], []

        # 計算流動性閾值
        bid_threshold = np.percentile(
            bids_agg['cumulative_volume'], percentile_threshold
        )
        ask_threshold = np.percentile(
            asks_agg['cumulative_volume'], percentile_threshold
        )

        # 找出高流動性區域
        support_levels = bids_agg[
            bids_agg['cumulative_volume'] >= bid_threshold
        ]['price_level'].tolist()

        resistance_levels = asks_agg[
            asks_agg['cumulative_volume'] >= ask_threshold
        ]['price_level'].tolist()

        return support_levels, resistance_levels

    def plot_liquidity_profile(
        self,
        exchange: str,
        symbol: str,
        save_path: Optional[str] = None
    ):
        """
        繪製流動性分布剖面圖

        顯示不同價格層級的累計掛單量
        """
        df = self.fetch_orderbook_history(exchange, symbol, limit=100)

        if df.empty:
            print("沒有找到訂單簿資料")
            return

        bids_agg, asks_agg = self.aggregate_liquidity(df, price_resolution=0.001)

        if bids_agg.empty or asks_agg.empty:
            return

        # 繪製剖面圖
        fig, ax = plt.subplots(figsize=(12, 6))

        # Bids (買單) - 綠色
        ax.barh(
            bids_agg['price_level'],
            bids_agg['cumulative_volume'],
            color='green',
            alpha=0.6,
            label='Bids (Support)'
        )

        # Asks (賣單) - 紅色
        ax.barh(
            asks_agg['price_level'],
            asks_agg['cumulative_volume'],
            color='red',
            alpha=0.6,
            label='Asks (Resistance)'
        )

        ax.set_xlabel('Cumulative Volume', fontsize=12)
        ax.set_ylabel('Price Level (% from mid)', fontsize=12)
        ax.set_title(
            f'Liquidity Profile - {exchange.upper()} {symbol}',
            fontsize=14
        )
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"流動性剖面圖已儲存至: {save_path}")

        plt.show()

    def close(self):
        """關閉資料庫連接"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def analyze_liquidity(
    exchange: str,
    symbol: str,
    output_dir: str = './reports/liquidity'
):
    """
    執行完整的流動性分析（便捷函數）

    Args:
        exchange: 交易所
        symbol: 交易對
        output_dir: 輸出目錄
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    with LiquidityHeatmap() as analyzer:
        print(f"\n{'=' * 80}")
        print(f"流動性分析 - {exchange.upper()} {symbol}")
        print(f"{'=' * 80}\n")

        # 1. 繪製熱力圖
        heatmap_path = f"{output_dir}/{exchange}_{symbol.replace('/', '_')}_heatmap.png"
        analyzer.plot_liquidity_heatmap(
            exchange, symbol,
            save_path=heatmap_path
        )

        # 2. 繪製流動性剖面圖
        profile_path = f"{output_dir}/{exchange}_{symbol.replace('/', '_')}_profile.png"
        analyzer.plot_liquidity_profile(
            exchange, symbol,
            save_path=profile_path
        )

        # 3. 識別支撐/阻力位
        df = analyzer.fetch_orderbook_history(exchange, symbol, limit=100)
        support, resistance = analyzer.identify_liquidity_clusters(df)

        print(f"\n流動性集中區域（潛在支撐/阻力位）：")
        print(f"  支撐位: {support[:5] if support else '無'}")
        print(f"  阻力位: {resistance[:5] if resistance else '無'}")

        print(f"\n{'=' * 80}")
        print("分析完成")
        print(f"{'=' * 80}\n")
