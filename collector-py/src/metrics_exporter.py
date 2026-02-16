"""
Prometheus Metrics Exporter
提供系統運行指標給 Prometheus 收集
"""
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server
from loguru import logger
from typing import Optional
import threading


class CollectorMetrics:
    """
    Collector 監控指標

    提供以下類型的指標：
    - 資料收集統計（Counter）
    - 當前狀態（Gauge）
    - API 請求延遲（Histogram）
    - 系統資訊（Info）
    """

    def __init__(self):
        """初始化所有 Prometheus 指標"""

        # ========== 資料收集計數器 ==========
        # OHLCV K 線數據
        self.ohlcv_collected_total = Counter(
            'collector_ohlcv_collected_total',
            'Total number of OHLCV candles collected',
            ['exchange', 'symbol', 'timeframe']
        )

        # 交易數據
        self.trades_collected_total = Counter(
            'collector_trades_collected_total',
            'Total number of trades collected',
            ['exchange', 'symbol']
        )

        # 訂單簿快照
        self.orderbook_snapshots_total = Counter(
            'collector_orderbook_snapshots_total',
            'Total number of orderbook snapshots collected',
            ['exchange', 'symbol']
        )

        # ========== API 請求統計 ==========
        # API 請求總數
        self.api_requests_total = Counter(
            'collector_api_requests_total',
            'Total number of API requests',
            ['exchange', 'endpoint', 'status']
        )

        # API 錯誤計數
        self.api_errors_total = Counter(
            'collector_api_errors_total',
            'Total number of API errors',
            ['exchange', 'endpoint', 'error_type']
        )

        # API 請求延遲
        self.api_request_duration_seconds = Histogram(
            'collector_api_request_duration_seconds',
            'API request duration in seconds',
            ['exchange', 'endpoint'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
        )

        # ========== 資料品質指標 ==========
        # 資料驗證失敗
        self.validation_failures_total = Counter(
            'collector_validation_failures_total',
            'Total number of validation failures',
            ['exchange', 'symbol', 'validation_type']
        )

        # 資料品質分數
        self.data_quality_score = Gauge(
            'collector_data_quality_score',
            'Data quality score (0-100)',
            ['exchange', 'symbol', 'timeframe']
        )

        # 資料缺失率
        self.data_missing_rate = Gauge(
            'collector_data_missing_rate',
            'Data missing rate percentage',
            ['exchange', 'symbol', 'timeframe']
        )

        # ========== 補資料任務 ==========
        # 待處理的補資料任務數
        self.backfill_tasks_pending = Gauge(
            'collector_backfill_tasks_pending',
            'Number of pending backfill tasks'
        )

        # 補資料任務完成數
        self.backfill_tasks_completed_total = Counter(
            'collector_backfill_tasks_completed_total',
            'Total number of completed backfill tasks',
            ['status']  # success, failed
        )

        # ========== 系統狀態 ==========
        # Collector 運行狀態（1=running, 0=stopped）
        self.collector_running = Gauge(
            'collector_running',
            'Collector running status (1=running, 0=stopped)'
        )

        # ========== 排程任務健康度 ==========
        self.scheduler_job_runs_total = Counter(
            'collector_scheduler_job_runs_total',
            'Total number of scheduler job runs',
            ['job_id', 'status']  # success, failed
        )

        self.scheduler_job_duration_seconds = Histogram(
            'collector_scheduler_job_duration_seconds',
            'Scheduler job duration in seconds',
            ['job_id'],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
        )

        self.scheduler_job_last_success_timestamp = Gauge(
            'collector_scheduler_job_last_success_timestamp',
            'Unix timestamp of last successful scheduler job run',
            ['job_id']
        )

        self.scheduler_job_last_failure_timestamp = Gauge(
            'collector_scheduler_job_last_failure_timestamp',
            'Unix timestamp of last failed scheduler job run',
            ['job_id']
        )

        # 連續失敗計數
        self.consecutive_failures = Gauge(
            'collector_consecutive_failures',
            'Number of consecutive failures',
            ['exchange', 'symbol', 'timeframe']
        )

        # 最後成功收集時間（Unix timestamp）
        self.last_successful_collection_timestamp = Gauge(
            'collector_last_successful_collection_timestamp',
            'Timestamp of last successful collection',
            ['exchange', 'symbol', 'timeframe']
        )

        # ========== ETF 資料新鮮度 ==========
        self.etf_latest_timestamp = Gauge(
            'collector_etf_latest_timestamp',
            'Latest ETF flow timestamp (UTC)',
            ['asset']
        )

        self.etf_staleness_seconds = Gauge(
            'collector_etf_staleness_seconds',
            'Seconds since latest ETF flow update',
            ['asset']
        )

        self.etf_unknown_products_total = Counter(
            'collector_etf_unknown_products_total',
            'Total number of unknown ETF product codes detected',
            ['asset', 'product_code']
        )

        # ========== 資料庫操作 ==========
        # 資料庫寫入操作
        self.db_writes_total = Counter(
            'collector_db_writes_total',
            'Total number of database write operations',
            ['table', 'status']  # success, failed
        )

        # 資料庫連線池狀態
        self.db_pool_connections = Gauge(
            'collector_db_pool_connections',
            'Number of database pool connections',
            ['state']  # active, idle, idle_in_transaction
        )

        # 連接池使用率（百分比）
        self.db_pool_usage_rate = Gauge(
            'collector_db_pool_usage_rate',
            'Database connection pool usage rate percentage (0-100)'
        )

        # 連接池總連接數
        self.db_pool_total_connections = Gauge(
            'collector_db_pool_total_connections',
            'Total number of database connections in pool'
        )

        # ========== 系統資訊 ==========
        # Collector 資訊
        self.collector_info = Info(
            'collector_info',
            'Collector version and configuration'
        )

        # 初始化系統資訊
        self.collector_info.info({
            'version': '2.0.0',
            'type': 'rest_collector',
            'language': 'python'
        })

        # 設定初始狀態
        self.collector_running.set(1)

        logger.info("Prometheus metrics initialized")

    # ========== 便捷方法 ==========

    def record_ohlcv_collection(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        count: int
    ):
        """記錄 OHLCV 數據收集"""
        self.ohlcv_collected_total.labels(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe
        ).inc(count)

    def record_trade_collection(
        self,
        exchange: str,
        symbol: str,
        count: int
    ):
        """記錄交易數據收集"""
        self.trades_collected_total.labels(
            exchange=exchange,
            symbol=symbol
        ).inc(count)

    def record_scheduler_job(
        self,
        job_id: str,
        status: str,
        duration_seconds: float,
        timestamp: float
    ):
        """記錄排程任務執行情況"""
        self.scheduler_job_runs_total.labels(job_id=job_id, status=status).inc()
        self.scheduler_job_duration_seconds.labels(job_id=job_id).observe(duration_seconds)
        if status == 'success':
            self.scheduler_job_last_success_timestamp.labels(job_id=job_id).set(timestamp)
        else:
            self.scheduler_job_last_failure_timestamp.labels(job_id=job_id).set(timestamp)

    def record_orderbook_snapshot(
        self,
        exchange: str,
        symbol: str
    ):
        """記錄訂單簿快照收集"""
        self.orderbook_snapshots_total.labels(
            exchange=exchange,
            symbol=symbol
        ).inc()

    def record_api_request(
        self,
        exchange: str,
        endpoint: str,
        status: str,  # success, failed, rate_limited
        duration: Optional[float] = None
    ):
        """記錄 API 請求"""
        self.api_requests_total.labels(
            exchange=exchange,
            endpoint=endpoint,
            status=status
        ).inc()

        if duration is not None:
            self.api_request_duration_seconds.labels(
                exchange=exchange,
                endpoint=endpoint
            ).observe(duration)

    def record_api_error(
        self,
        exchange: str,
        endpoint: str,
        error_type: str  # network, timeout, rate_limit, server_error
    ):
        """記錄 API 錯誤"""
        self.api_errors_total.labels(
            exchange=exchange,
            endpoint=endpoint,
            error_type=error_type
        ).inc()

    def record_validation_failure(
        self,
        exchange: str,
        symbol: str,
        validation_type: str  # price_jump, missing_data, timestamp_error
    ):
        """記錄驗證失敗"""
        self.validation_failures_total.labels(
            exchange=exchange,
            symbol=symbol,
            validation_type=validation_type
        ).inc()

    def update_data_quality(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        score: float,
        missing_rate: float
    ):
        """更新資料品質指標"""
        self.data_quality_score.labels(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe
        ).set(score)

        self.data_missing_rate.labels(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe
        ).set(missing_rate)

    def update_backfill_stats(
        self,
        pending: int
    ):
        """更新補資料任務統計"""
        self.backfill_tasks_pending.set(pending)

    def record_backfill_completion(
        self,
        status: str  # success, failed
    ):
        """記錄補資料任務完成"""
        self.backfill_tasks_completed_total.labels(status=status).inc()

    def update_consecutive_failures(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        count: int
    ):
        """更新連續失敗計數"""
        self.consecutive_failures.labels(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe
        ).set(count)

    def update_last_collection_time(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        timestamp: float
    ):
        """更新最後成功收集時間"""
        self.last_successful_collection_timestamp.labels(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe
        ).set(timestamp)

    def update_etf_latest_timestamp(self, asset: str, timestamp: float):
        """更新 ETF 最新時間"""
        self.etf_latest_timestamp.labels(asset=asset).set(timestamp)

    def update_etf_staleness_seconds(self, asset: str, seconds: float):
        """更新 ETF 新鮮度（秒）"""
        self.etf_staleness_seconds.labels(asset=asset).set(seconds)

    def record_etf_unknown_product(self, asset: str, product_code: str):
        """記錄未知 ETF 產品代碼"""
        self.etf_unknown_products_total.labels(asset=asset, product_code=product_code).inc()

    def record_db_write(
        self,
        table: str,
        status: str,  # success, failed
        count: int = 1
    ):
        """記錄資料庫寫入操作"""
        self.db_writes_total.labels(
            table=table,
            status=status
        ).inc(count)

    def update_db_pool_connections(
        self,
        active: int,
        idle: int,
        idle_in_transaction: int = 0
    ):
        """更新資料庫連線池狀態"""
        self.db_pool_connections.labels(state='active').set(active)
        self.db_pool_connections.labels(state='idle').set(idle)
        self.db_pool_connections.labels(state='idle_in_transaction').set(idle_in_transaction)

    def update_db_pool_stats(
        self,
        total: int,
        usage_rate: float
    ):
        """更新資料庫連線池統計"""
        self.db_pool_total_connections.set(total)
        self.db_pool_usage_rate.set(usage_rate)

    def set_running_status(self, running: bool):
        """設定 Collector 運行狀態"""
        self.collector_running.set(1 if running else 0)


class MetricsServer:
    """
    Prometheus Metrics HTTP Server

    在獨立線程中運行 HTTP server 暴露 /metrics 端點
    """

    def __init__(self, port: int = 8000):
        """
        初始化 Metrics Server

        Args:
            port: HTTP server 端口（預設 8000）
        """
        self.port = port
        self.server_thread: Optional[threading.Thread] = None
        self.metrics = CollectorMetrics()

    def start(self):
        """啟動 Metrics HTTP Server（在背景線程中）"""
        try:
            # 在背景線程中啟動 HTTP server
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name='MetricsServer'
            )
            self.server_thread.start()
            logger.info(f"Metrics server started on port {self.port}")
            logger.info(f"Metrics endpoint: http://localhost:{self.port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise

    def _run_server(self):
        """在背景執行 HTTP server"""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics HTTP server listening on port {self.port}")
        except Exception as e:
            logger.error(f"Metrics server error: {e}")

    def get_metrics(self) -> CollectorMetrics:
        """取得 Metrics 實例"""
        return self.metrics


# 全局 metrics server 實例（單例模式）
_metrics_server: Optional[MetricsServer] = None


def get_metrics_server(port: int = 8000) -> MetricsServer:
    """
    取得全局 Metrics Server 實例（單例模式）

    Args:
        port: HTTP server 端口

    Returns:
        MetricsServer 實例
    """
    global _metrics_server

    if _metrics_server is None:
        _metrics_server = MetricsServer(port=port)

    return _metrics_server


def start_metrics_server(port: int = 8000) -> CollectorMetrics:
    """
    啟動 Metrics Server 並返回 Metrics 實例

    Args:
        port: HTTP server 端口

    Returns:
        CollectorMetrics 實例
    """
    server = get_metrics_server(port=port)
    server.start()
    return server.get_metrics()
