"""
MAD 異常檢測服務
持續監控價格數據並導出 Prometheus metrics
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# 添加專案路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anomaly.mad_detector import RealtimeMADDetector

# 日誌配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus Metrics
anomaly_detected = Counter(
    'mad_anomaly_detected_total',
    'Total number of anomalies detected by MAD',
    ['symbol', 'severity']
)

anomaly_score = Gauge(
    'mad_anomaly_score',
    'Current anomaly score for symbol',
    ['symbol']
)

price_current = Gauge(
    'price_current',
    'Current price of symbol',
    ['symbol', 'exchange']
)

price_median = Gauge(
    'mad_price_median',
    'Median price in the current window',
    ['symbol']
)

price_mad_value = Gauge(
    'mad_value',
    'Current MAD value for symbol',
    ['symbol']
)

detection_latency = Histogram(
    'mad_detection_latency_seconds',
    'Time spent on anomaly detection',
    ['symbol']
)

last_check_timestamp = Gauge(
    'mad_last_check_timestamp',
    'Timestamp of last anomaly check',
    ['symbol']
)


class MADService:
    """MAD 異常檢測服務"""

    def __init__(
        self,
        symbols: List[str] = None,
        threshold: float = 3.0,
        window_size: int = 100,
        check_interval: int = 30,
        metrics_port: int = 8002
    ):
        """
        初始化服務

        Args:
            symbols: 監控的交易對列表
            threshold: 異常閾值
            window_size: 滑動窗口大小
            check_interval: 檢查間隔（秒）
            metrics_port: Prometheus metrics 端口
        """
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        self.threshold = threshold
        self.window_size = window_size
        self.check_interval = check_interval
        self.metrics_port = metrics_port

        # 初始化檢測器
        self.detector = RealtimeMADDetector(
            threshold=threshold,
            window_size=window_size,
            symbols=self.symbols
        )

        # 資料庫連接
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'crypto_db'),
            'user': os.getenv('POSTGRES_USER', 'crypto'),
            'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass')
        }

        logger.info(
            f"MAD Service initialized: symbols={self.symbols}, "
            f"threshold={threshold}, window_size={window_size}, "
            f"check_interval={check_interval}s, metrics_port={metrics_port}"
        )

    def get_db_connection(self):
        """獲取資料庫連接"""
        return psycopg2.connect(**self.db_config)

    def fetch_recent_prices(self, symbol: str, limit: int = None) -> pd.DataFrame:
        """
        從資料庫獲取最近的價格資料

        Args:
            symbol: 交易對
            limit: 資料筆數限制

        Returns:
            價格資料 DataFrame
        """
        limit = limit or self.window_size

        query = """
        SELECT
            o.open_time as timestamp,
            o.close as price,
            o.volume,
            e.name as exchange
        FROM ohlcv o
        JOIN markets m ON o.market_id = m.id
        JOIN exchanges e ON m.exchange_id = e.id
        WHERE m.symbol = %s
          AND o.timeframe = '1m'
        ORDER BY o.open_time DESC
        LIMIT %s
        """

        try:
            with self.get_db_connection() as conn:
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(symbol, limit)
                )

            # 按時間順序排列
            df = df.sort_values('timestamp').reset_index(drop=True)

            logger.debug(f"獲取 {symbol} 的 {len(df)} 筆價格資料")
            return df

        except Exception as e:
            logger.error(f"獲取 {symbol} 價格資料失敗: {e}")
            return pd.DataFrame()

    def check_anomaly(self, symbol: str):
        """
        檢查單個交易對的異常

        Args:
            symbol: 交易對符號
        """
        start_time = time.time()

        try:
            # 獲取最近價格
            df = self.fetch_recent_prices(symbol)

            if df.empty or len(df) < 30:
                logger.warning(f"{symbol}: 資料不足，跳過檢測")
                return

            # 獲取最新價格
            latest_price = df.iloc[-1]['price']
            latest_timestamp = df.iloc[-1]['timestamp']
            exchange = df.iloc[-1].get('exchange', 'unknown')

            # 檢測異常
            is_anomaly, score = self.detector.add_data_point(
                symbol=symbol,
                value=latest_price,
                timestamp=latest_timestamp
            )

            # 獲取統計資訊
            stats = self.detector.get_stats()[symbol]

            # 更新 Prometheus metrics
            price_current.labels(symbol=symbol, exchange=exchange).set(latest_price)
            anomaly_score.labels(symbol=symbol).set(score)
            price_median.labels(symbol=symbol).set(stats['current_median'])
            price_mad_value.labels(symbol=symbol).set(stats['current_mad'])
            last_check_timestamp.labels(symbol=symbol).set(time.time())

            # 記錄異常
            if is_anomaly:
                severity = 'critical' if score > self.threshold * 1.5 else 'warning'
                anomaly_detected.labels(symbol=symbol, severity=severity).inc()

                logger.warning(
                    f"🚨 異常檢測: {symbol} | "
                    f"價格: {latest_price:.2f} | "
                    f"中位數: {stats['current_median']:.2f} | "
                    f"MAD: {stats['current_mad']:.4f} | "
                    f"分數: {score:.2f} | "
                    f"嚴重度: {severity}"
                )

            # 記錄延遲
            latency = time.time() - start_time
            detection_latency.labels(symbol=symbol).observe(latency)

        except Exception as e:
            logger.error(f"檢查 {symbol} 異常時發生錯誤: {e}", exc_info=True)

    def run(self):
        """運行服務主循環"""
        logger.info(f"啟動 Prometheus metrics server 於端口 {self.metrics_port}")
        start_http_server(self.metrics_port)

        logger.info("開始 MAD 異常檢測循環")

        while True:
            try:
                for symbol in self.symbols:
                    self.check_anomaly(symbol)

                logger.info(
                    f"完成一輪檢測，等待 {self.check_interval} 秒... "
                    f"[統計: {self.get_summary()}]"
                )
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("收到中斷信號，正在關閉服務...")
                break
            except Exception as e:
                logger.error(f"服務運行錯誤: {e}", exc_info=True)
                time.sleep(self.check_interval)

    def get_summary(self) -> str:
        """獲取檢測摘要"""
        stats = self.detector.get_stats()
        summary_parts = []

        for symbol, stat in stats.items():
            if stat['total_checked'] > 0:
                anomaly_rate = (
                    stat['anomalies_detected'] / stat['total_checked'] * 100
                )
                summary_parts.append(
                    f"{symbol}: {stat['anomalies_detected']}/{stat['total_checked']} "
                    f"({anomaly_rate:.1f}%)"
                )

        return ", ".join(summary_parts) if summary_parts else "無資料"


def main():
    """主函數"""
    # 從環境變數讀取配置
    symbols = os.getenv('MAD_SYMBOLS', 'BTCUSDT,ETHUSDT').split(',')
    threshold = float(os.getenv('MAD_THRESHOLD', '3.0'))
    window_size = int(os.getenv('MAD_WINDOW_SIZE', '100'))
    check_interval = int(os.getenv('MAD_CHECK_INTERVAL', '30'))
    metrics_port = int(os.getenv('MAD_METRICS_PORT', '8002'))

    logger.info("="*60)
    logger.info("MAD 異常檢測服務")
    logger.info("="*60)
    logger.info(f"監控交易對: {symbols}")
    logger.info(f"異常閾值: {threshold}")
    logger.info(f"窗口大小: {window_size}")
    logger.info(f"檢查間隔: {check_interval}s")
    logger.info(f"Metrics 端口: {metrics_port}")
    logger.info("="*60)

    # 創建並運行服務
    service = MADService(
        symbols=symbols,
        threshold=threshold,
        window_size=window_size,
        check_interval=check_interval,
        metrics_port=metrics_port
    )

    service.run()


if __name__ == '__main__':
    main()
