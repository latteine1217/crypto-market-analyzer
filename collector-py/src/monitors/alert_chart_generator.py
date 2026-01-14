"""
告警圖表生成器
生成 K 線圖、交易量圖等附件，用於告警郵件
"""
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 非互動模式
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import mplfinance as mpf
from loguru import logger
import psycopg2
from psycopg2.extras import RealDictCursor


class AlertChartGenerator:
    """告警圖表生成器"""

    def __init__(self, db_conn_str: str, output_dir: Path):
        """
        初始化圖表生成器

        Args:
            db_conn_str: 資料庫連接字串
            output_dir: 圖表輸出目錄
        """
        self.db_conn_str = db_conn_str
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"AlertChartGenerator initialized, output: {self.output_dir}")

    def _get_ohlcv_data(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        hours_back: int = 24
    ) -> Optional[pd.DataFrame]:
        """
        從資料庫獲取 OHLCV 資料

        Args:
            symbol: 交易對（如 BTCUSDT 或 BTC/USDT）
            exchange: 交易所（如 bybit）
            timeframe: 時間框架（如 1h）
            hours_back: 回溯小時數

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            # 正規化 symbol 格式（BTCUSDT → BTC/USDT）
            if '/' not in symbol and len(symbol) >= 6:
                # 假設格式為 XXXUSDT, XXXETH 等
                if symbol.endswith('USDT'):
                    symbol = f"{symbol[:-4]}/USDT"
                elif symbol.endswith('BTC'):
                    symbol = f"{symbol[:-3]}/BTC"
                elif symbol.endswith('ETH'):
                    symbol = f"{symbol[:-3]}/ETH"
            
            conn = psycopg2.connect(self.db_conn_str)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 查詢最近的 K 線資料（使用正確的 schema）
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
                WHERE m.symbol = %s
                    AND e.name = %s
                    AND o.timeframe = %s
                    AND o.open_time >= NOW() - INTERVAL '%s hours'
                ORDER BY o.open_time ASC
            """
            cursor.execute(query, (symbol, exchange, timeframe, hours_back))
            rows = cursor.fetchall()
            
            cursor.close()
            conn.close()

            if not rows:
                logger.warning(f"No data found for {symbol}/{exchange}/{timeframe}")
                return None

            df = pd.DataFrame(rows)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            
            logger.info(f"Loaded {len(df)} OHLCV records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to get OHLCV data: {e}")
            return None

    def generate_candlestick_chart(
        self,
        symbol: str,
        exchange: str = "bybit",
        timeframe: str = "1h",
        hours_back: int = 24,
        title: Optional[str] = None,
        annotation: Optional[str] = None
    ) -> Optional[Path]:
        """
        生成 K 線圖（蠟燭圖）

        Args:
            symbol: 交易對
            exchange: 交易所
            timeframe: 時間框架
            hours_back: 回溯小時數
            title: 圖表標題（可選）
            annotation: 標註文字（可選）

        Returns:
            圖表檔案路徑，失敗返回 None
        """
        try:
            # 獲取資料
            df = self._get_ohlcv_data(symbol, exchange, timeframe, hours_back)
            if df is None or df.empty:
                logger.error(f"No data to plot for {symbol}")
                return None

            # 設定圖表樣式
            mc = mpf.make_marketcolors(
                up='#26A69A',      # 綠色（上漲）
                down='#EF5350',    # 紅色（下跌）
                edge='inherit',
                wick='inherit',
                volume='in',
                alpha=0.9
            )
            
            s = mpf.make_mpf_style(
                marketcolors=mc,
                gridstyle='-',
                gridcolor='#E0E0E0',
                facecolor='white',
                figcolor='white',
                y_on_right=False
            )

            # 設定圖表大小和標題
            if title is None:
                title = f"{symbol} {timeframe.upper()} Candlestick Chart"
            
            # 添加移動平均線
            mav = (7, 25) if timeframe in ['1h', '4h'] else (5, 20)
            
            # 生成圖表
            fig, axes = mpf.plot(
                df,
                type='candle',
                style=s,
                title=title,
                ylabel='Price (USDT)',
                volume=True,
                ylabel_lower='Volume',
                mav=mav,
                figsize=(14, 8),
                datetime_format='%m-%d %H:%M',
                xrotation=15,
                returnfig=True,
                warn_too_much_data=len(df) + 1  # 避免警告
            )
            
            # 添加標註（如果有）
            if annotation:
                # 在圖表頂部添加告警訊息
                fig.text(
                    0.5, 0.95,
                    annotation,
                    ha='center',
                    va='top',
                    fontsize=11,
                    color='red',
                    weight='bold',
                    bbox=dict(
                        boxstyle='round,pad=0.5',
                        facecolor='yellow',
                        alpha=0.7,
                        edgecolor='red'
                    ),
                    transform=fig.transFigure
                )
            
            # 添加生成時間戳
            fig.text(
                0.99, 0.01,
                f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                ha='right',
                va='bottom',
                fontsize=8,
                color='gray',
                transform=fig.transFigure
            )
            
            # 保存圖表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol}_{timeframe}_{timestamp}.png"
            output_path = self.output_dir / filename
            
            fig.savefig(
                output_path,
                dpi=100,
                bbox_inches='tight',
                facecolor='white'
            )
            plt.close(fig)
            
            logger.info(f"✓ Chart saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate candlestick chart: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_price_comparison_chart(
        self,
        symbol: str,
        exchange: str = "bybit",
        hours_back: int = 48,
        timeframe: str = "1h",  # 新增參數：時間框架
        title: Optional[str] = None,
        highlight_recent_hours: int = 1
    ) -> Optional[Path]:
        """
        生成價格對比圖（折線圖，突出顯示最近的價格變動）

        Args:
            symbol: 交易對
            exchange: 交易所
            hours_back: 回溯小時數
            timeframe: 時間框架（預設 1h，如果沒有 5m 資料）
            title: 圖表標題
            highlight_recent_hours: 突出顯示最近 N 小時

        Returns:
            圖表檔案路徑
        """
        try:
            # 獲取資料（使用指定的時間框架）
            df = self._get_ohlcv_data(symbol, exchange, timeframe, hours_back)
            if df is None or df.empty:
                return None

            # 創建圖表
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), 
                                           gridspec_kw={'height_ratios': [3, 1]})
            
            if title is None:
                title = f"{symbol} Price Movement (Last {hours_back}h)"
            
            fig.suptitle(title, fontsize=14, weight='bold')
            
            # === 上圖：價格折線圖 ===
            timestamps = df.index
            closes = df['close']
            
            # 繪製完整價格線
            ax1.plot(timestamps, closes, color='steelblue', linewidth=1.5, label='Close Price')
            
            # 突出顯示最近的價格（不同顏色）
            cutoff_time = timestamps[-1] - timedelta(hours=highlight_recent_hours)
            recent_mask = timestamps >= cutoff_time
            
            ax1.plot(
                timestamps[recent_mask],
                closes[recent_mask],
                color='red',
                linewidth=2.5,
                label=f'Last {highlight_recent_hours}h'
            )
            
            # 添加當前價格標記
            current_price = closes.iloc[-1]
            ax1.scatter([timestamps[-1]], [current_price], 
                       color='red', s=100, zorder=5, marker='o')
            ax1.text(
                timestamps[-1], current_price,
                f'  ${current_price:,.2f}',
                verticalalignment='center',
                fontsize=10,
                color='red',
                weight='bold'
            )
            
            # 添加移動平均線
            ma_7 = closes.rolling(window=7).mean()
            ma_25 = closes.rolling(window=25).mean()
            ax1.plot(timestamps, ma_7, '--', alpha=0.7, linewidth=1, label='MA(7)')
            ax1.plot(timestamps, ma_25, '--', alpha=0.7, linewidth=1, label='MA(25)')
            
            ax1.set_ylabel('Price (USDT)', fontsize=11)
            ax1.legend(loc='upper left', fontsize=9)
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=15, ha='right')
            
            # === 下圖：成交量 ===
            volumes = df['volume']
            colors = ['green' if closes.iloc[i] >= df['open'].iloc[i] else 'red' 
                     for i in range(len(df))]
            
            ax2.bar(timestamps, volumes, color=colors, alpha=0.6, width=0.003)
            ax2.set_ylabel('Volume', fontsize=11)
            ax2.set_xlabel('Time (UTC)', fontsize=11)
            ax2.grid(True, alpha=0.3, axis='y')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=15, ha='right')
            
            # 添加生成時間
            fig.text(
                0.99, 0.01,
                f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                ha='right', va='bottom', fontsize=8, color='gray'
            )
            
            plt.tight_layout()
            
            # 保存圖表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{symbol}_price_comparison_{timestamp}.png"
            output_path = self.output_dir / filename
            
            fig.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"✓ Price comparison chart saved: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate price comparison chart: {e}")
            import traceback
            traceback.print_exc()
            return None

    def cleanup_old_charts(self, hours: int = 24):
        """
        清理舊的圖表檔案

        Args:
            hours: 清理超過 N 小時的圖表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            count = 0
            
            for chart_file in self.output_dir.glob("*.png"):
                file_time = datetime.fromtimestamp(chart_file.stat().st_mtime)
                if file_time < cutoff_time:
                    chart_file.unlink()
                    count += 1
            
            logger.info(f"✓ Cleaned up {count} old chart files (older than {hours}h)")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old charts: {e}")


# === 測試用法 ===
if __name__ == "__main__":
    import os
    
    db_conn_str = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'crypto_db')} "
        f"user={os.getenv('DB_USER', 'crypto')} "
        f"password={os.getenv('DB_PASSWORD', 'crypto123')}"
    )
    
    output_dir = Path("/tmp/alert_charts")
    generator = AlertChartGenerator(db_conn_str, output_dir)
    
    # 測試生成蠟燭圖
    chart1 = generator.generate_candlestick_chart(
        symbol="BTCUSDT",
        exchange="bybit",
        timeframe="1h",
        hours_back=48,
        title="BTC/USDT 1H Candlestick Chart",
        annotation="⚠️ ALERT: Price dropped by 3.5% in 5 minutes"
    )
    
    if chart1:
        print(f"✓ Candlestick chart generated: {chart1}")
    
    # 測試生成價格對比圖
    chart2 = generator.generate_price_comparison_chart(
        symbol="BTCUSDT",
        exchange="bybit",
        hours_back=48,
        highlight_recent_hours=2
    )
    
    if chart2:
        print(f"✓ Price comparison chart generated: {chart2}")
    
    # 測試清理舊檔案
    generator.cleanup_old_charts(hours=1)
