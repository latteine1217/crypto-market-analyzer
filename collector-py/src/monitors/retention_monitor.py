"""
資料保留策略監控模組
監控 TimescaleDB 連續聚合和資料保留策略的執行狀態
"""
from prometheus_client import Gauge, Counter, Info
from loguru import logger
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import psycopg2  # type: ignore
from psycopg2.extras import RealDictCursor  # type: ignore


class RetentionMonitorMetrics:
    """資料保留策略監控指標"""
    
    def __init__(self):
        # ========== 連續聚合狀態 ==========
        # 聚合視圖最後更新時間（Unix timestamp）
        self.aggregate_last_update_timestamp = Gauge(
            'timescaledb_continuous_aggregate_last_update_timestamp',
            'Last update timestamp of continuous aggregate view',
            ['view_name', 'table_name']
        )
        
        # 聚合視圖記錄數
        self.aggregate_record_count = Gauge(
            'timescaledb_continuous_aggregate_record_count',
            'Number of records in continuous aggregate view',
            ['view_name']
        )
        
        # 聚合視圖資料時間範圍（最舊資料的時間戳）
        self.aggregate_oldest_data_timestamp = Gauge(
            'timescaledb_continuous_aggregate_oldest_data_timestamp',
            'Timestamp of oldest data in continuous aggregate view',
            ['view_name']
        )
        
        # 聚合視圖資料時間範圍（最新資料的時間戳）
        self.aggregate_newest_data_timestamp = Gauge(
            'timescaledb_continuous_aggregate_newest_data_timestamp',
            'Timestamp of newest data in continuous aggregate view',
            ['view_name']
        )
        
        # ========== TimescaleDB Jobs 狀態 ==========
        # Job 執行狀態（1=enabled, 0=disabled）
        self.job_enabled = Gauge(
            'timescaledb_job_enabled',
            'Job enabled status (1=enabled, 0=disabled)',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # Job 最後成功執行時間
        self.job_last_success_timestamp = Gauge(
            'timescaledb_job_last_success_timestamp',
            'Last successful execution timestamp of job',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # Job 最後執行時間
        self.job_last_run_timestamp = Gauge(
            'timescaledb_job_last_run_timestamp',
            'Last execution timestamp of job',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # Job 下次排程執行時間
        self.job_next_start_timestamp = Gauge(
            'timescaledb_job_next_start_timestamp',
            'Next scheduled execution timestamp of job',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # Job 執行失敗總數
        self.job_failures_total = Counter(
            'timescaledb_job_failures_total',
            'Total number of job execution failures',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # Job 執行總時長（秒）
        self.job_total_duration_seconds = Gauge(
            'timescaledb_job_total_duration_seconds',
            'Total execution duration of job in seconds',
            ['job_id', 'job_type', 'hypertable_name']
        )
        
        # ========== 資料保留狀態 ==========
        # 實際資料保留期間（天數）
        self.data_actual_retention_days = Gauge(
            'timescaledb_data_actual_retention_days',
            'Actual data retention period in days',
            ['layer']
        )
        
        # 配置的保留期間（天數）
        self.data_expected_retention_days = Gauge(
            'timescaledb_data_expected_retention_days',
            'Expected data retention period in days',
            ['layer']
        )
        
        # 資料保留偏差（實際 - 預期，天數）
        self.data_retention_deviation_days = Gauge(
            'timescaledb_data_retention_deviation_days',
            'Deviation between actual and expected retention in days',
            ['layer']
        )
        
        # 資料記錄總數
        self.data_total_records = Gauge(
            'timescaledb_data_total_records',
            'Total number of records in layer',
            ['layer']
        )
        
        # ========== 資料完整性檢查 ==========
        # 聚合資料與原始資料比率
        self.aggregate_compression_ratio = Gauge(
            'timescaledb_aggregate_compression_ratio',
            'Compression ratio between raw data and aggregated data',
            ['source_layer', 'target_layer']
        )
        
        # 資料缺失檢測
        self.data_gap_detected = Counter(
            'timescaledb_data_gap_detected_total',
            'Total number of data gaps detected',
            ['layer']
        )
        
        # ========== 儲存空間統計 ==========
        # 表空間大小（bytes）
        self.table_size_bytes = Gauge(
            'timescaledb_table_size_bytes',
            'Table size in bytes',
            ['table_name']
        )
        
        # 索引空間大小（bytes）
        self.index_size_bytes = Gauge(
            'timescaledb_index_size_bytes',
            'Index size in bytes',
            ['table_name']
        )
        
        # ========== 監控資訊 ==========
        self.retention_monitor_info = Info(
            'timescaledb_retention_monitor',
            'Retention monitor information'
        )
        
        # 最後檢查時間
        self.last_check_timestamp = Gauge(
            'timescaledb_retention_monitor_last_check_timestamp',
            'Last check timestamp of retention monitor'
        )
        
        # 檢查執行時長
        self.check_duration_seconds = Gauge(
            'timescaledb_retention_monitor_check_duration_seconds',
            'Duration of retention check in seconds'
        )
        
        # 初始化監控資訊
        self.retention_monitor_info.info({
            'version': '1.0.0',
            'type': 'retention_monitor'
        })
        
        logger.info("Retention monitor metrics initialized")


class RetentionMonitor:
    """資料保留策略監控器"""
    
    # 預期保留期間配置（天數）
    EXPECTED_RETENTION = {
        'ohlcv (1m)': 7,
        'ohlcv_5m': 30,
        'ohlcv_15m': 90,
        'ohlcv_1h': 180,
        'ohlcv_1d': None,  # 永久保留
        'trades': 7,
        'orderbook_snapshots': 3
    }
    
    def __init__(
        self,
        db_config: Dict[str, Any],
        metrics: Optional[RetentionMonitorMetrics] = None
    ):
        """
        初始化監控器
        
        Args:
            db_config: 資料庫配置
            metrics: Prometheus 指標實例（可選）
        """
        self.db_config = db_config
        self.metrics = metrics or RetentionMonitorMetrics()
        self.conn: Any = None  # psycopg2 connection
        
    def connect(self):
        """建立資料庫連線"""
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                cursor_factory=RealDictCursor
            )
            logger.info("Database connection established for retention monitor")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """關閉資料庫連線"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def check_all(self):
        """執行所有監控檢查"""
        start_time = datetime.now()
        
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            logger.info("Starting retention policy monitoring check")
            
            # 1. 檢查連續聚合狀態
            self.check_continuous_aggregates()
            
            # 2. 檢查 TimescaleDB Jobs 狀態
            self.check_timescaledb_jobs()
            
            # 3. 檢查資料保留狀態
            self.check_retention_status()
            
            # 4. 檢查儲存空間
            self.check_storage_statistics()
            
            # 5. 檢查資料完整性
            self.check_data_integrity()
            
            # 更新檢查時間和執行時長
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics.last_check_timestamp.set(datetime.now().timestamp())
            self.metrics.check_duration_seconds.set(duration)
            
            logger.info(f"Retention policy monitoring check completed in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error during retention monitoring: {e}", exc_info=True)
            raise
    
    def check_continuous_aggregates(self):
        """檢查連續聚合視圖狀態"""
        logger.info("Checking continuous aggregates status")
        
        views = ['ohlcv_5m', 'ohlcv_15m', 'ohlcv_1h', 'ohlcv_1d']
        
        for view_name in views:
            try:
                # 查詢視圖資料統計
                query = f"""
                SELECT
                    COUNT(*) AS record_count,
                    MIN(open_time) AS oldest_time,
                    MAX(open_time) AS newest_time
                FROM {view_name}
                """
                
                with self.conn.cursor() as cur:  # type: ignore
                    cur.execute(query)
                    result = cur.fetchone()
                    
                    if result:
                        # 更新記錄數
                        self.metrics.aggregate_record_count.labels(
                            view_name=view_name
                        ).set(result['record_count'])  # type: ignore
                        
                        # 更新時間範圍
                        if result['oldest_time']:  # type: ignore
                            self.metrics.aggregate_oldest_data_timestamp.labels(
                                view_name=view_name
                            ).set(result['oldest_time'].timestamp())  # type: ignore
                        
                        if result['newest_time']:  # type: ignore
                            self.metrics.aggregate_newest_data_timestamp.labels(
                                view_name=view_name
                            ).set(result['newest_time'].timestamp())  # type: ignore
                            
                            # 更新最後更新時間
                            self.metrics.aggregate_last_update_timestamp.labels(
                                view_name=view_name,
                                table_name=view_name
                            ).set(result['newest_time'].timestamp())  # type: ignore
                        
                        logger.debug(
                            f"{view_name}: {result['record_count']} records, "  # type: ignore
                            f"range: {result['oldest_time']} to {result['newest_time']}"  # type: ignore
                        )
                
            except Exception as e:
                logger.error(f"Error checking {view_name}: {e}")
    
    def check_timescaledb_jobs(self):
        """檢查 TimescaleDB 任務狀態"""
        logger.info("Checking TimescaleDB jobs status")
        
        # 查詢所有與聚合和保留相關的 jobs
        # 使用 job_stats 表獲取執行統計
        query = """
        SELECT
            j.job_id,
            j.proc_name,
            j.hypertable_name,
            j.scheduled,
            js.last_run_started_at,
            js.last_successful_finish,
            js.next_start,
            js.total_runs,
            js.total_successes,
            js.total_failures,
            js.last_run_duration,
            ca.view_name
        FROM timescaledb_information.jobs j
        LEFT JOIN timescaledb_information.job_stats js ON j.job_id = js.job_id
        LEFT JOIN timescaledb_information.continuous_aggregates ca
            ON j.hypertable_name = ca.materialization_hypertable_name
        WHERE j.proc_name IN ('policy_refresh_continuous_aggregate', 'policy_retention')
        ORDER BY j.job_id
        """
        
        try:
            with self.conn.cursor() as cur:  # type: ignore
                cur.execute(query)
                jobs = cur.fetchall()  # type: ignore
                
                for job in jobs:  # type: ignore
                    job_id = str(job['job_id'])  # type: ignore
                    job_type = job['proc_name']  # type: ignore
                    hypertable = job['hypertable_name'] or job['view_name'] or 'unknown'  # type: ignore
                    
                    # Job 啟用狀態
                    self.metrics.job_enabled.labels(
                        job_id=job_id,
                        job_type=job_type,
                        hypertable_name=hypertable
                    ).set(1 if job['scheduled'] else 0)  # type: ignore
                    
                    # 最後成功執行時間
                    if job['last_successful_finish']:  # type: ignore
                        self.metrics.job_last_success_timestamp.labels(
                            job_id=job_id,
                            job_type=job_type,
                            hypertable_name=hypertable
                        ).set(job['last_successful_finish'].timestamp())  # type: ignore
                    
                    # 最後執行時間
                    if job['last_run_started_at']:  # type: ignore
                        self.metrics.job_last_run_timestamp.labels(
                            job_id=job_id,
                            job_type=job_type,
                            hypertable_name=hypertable
                        ).set(job['last_run_started_at'].timestamp())  # type: ignore
                    
                    # 下次排程時間
                    if job['next_start']:  # type: ignore
                        self.metrics.job_next_start_timestamp.labels(
                            job_id=job_id,
                            job_type=job_type,
                            hypertable_name=hypertable
                        ).set(job['next_start'].timestamp())  # type: ignore
                    
                    # 執行失敗數（注意：這是累積值，需要特殊處理）
                    # 由於 Counter 只能增加，我們在這裡只記錄日誌
                    if job['total_failures'] and job['total_failures'] > 0:  # type: ignore
                        logger.warning(
                            f"Job {job_id} ({job_type}) has {job['total_failures']} failures"  # type: ignore
                        )
                    
                    # 最後執行時長
                    if job['last_run_duration']:  # type: ignore
                        # last_run_duration 是 interval 類型，需要轉換為秒
                        duration_seconds = job['last_run_duration'].total_seconds()  # type: ignore
                        self.metrics.job_total_duration_seconds.labels(
                            job_id=job_id,
                            job_type=job_type,
                            hypertable_name=hypertable
                        ).set(duration_seconds)  # type: ignore
                    
                    logger.debug(
                        f"Job {job_id} ({job_type}): {hypertable}, "
                        f"scheduled={job['scheduled']}, "  # type: ignore
                        f"successes={job['total_successes']}/{job['total_runs']}"  # type: ignore
                    )
        
        except Exception as e:
            logger.error(f"Error checking TimescaleDB jobs: {e}")
    
    def check_retention_status(self):
        """檢查資料保留狀態"""
        logger.info("Checking data retention status")
        
        # 使用 v_retention_status 視圖
        query = "SELECT * FROM v_retention_status ORDER BY layer"
        
        try:
            with self.conn.cursor() as cur:  # type: ignore
                cur.execute(query)
                layers = cur.fetchall()  # type: ignore
                
                for layer in layers:  # type: ignore
                    layer_name = layer['layer']  # type: ignore
                    
                    # 記錄總數
                    self.metrics.data_total_records.labels(
                        layer=layer_name
                    ).set(layer['total_records'] or 0)  # type: ignore
                    
                    # 實際保留期間（天數）
                    if layer['actual_retention']:  # type: ignore
                        actual_days = layer['actual_retention'].days  # type: ignore
                        self.metrics.data_actual_retention_days.labels(
                            layer=layer_name
                        ).set(actual_days)
                    else:
                        actual_days = 0
                        self.metrics.data_actual_retention_days.labels(
                            layer=layer_name
                        ).set(0)
                    
                    # 預期保留期間
                    expected_days = self.EXPECTED_RETENTION.get(layer_name)
                    if expected_days is not None:
                        self.metrics.data_expected_retention_days.labels(
                            layer=layer_name
                        ).set(expected_days)
                        
                        # 計算偏差
                        deviation = actual_days - expected_days
                        self.metrics.data_retention_deviation_days.labels(
                            layer=layer_name
                        ).set(deviation)
                        
                        # 檢查是否超過預期保留期間太多（允許 20% 偏差）
                        if deviation > expected_days * 0.2:
                            logger.warning(
                                f"{layer_name} retention deviation: {deviation} days "
                                f"(actual: {actual_days}, expected: {expected_days})"
                            )
                    else:
                        # 永久保留
                        self.metrics.data_expected_retention_days.labels(
                            layer=layer_name
                        ).set(-1)
                    
                    logger.debug(
                        f"{layer_name}: {layer['total_records']} records, "  # type: ignore
                        f"retention: {actual_days} days"
                    )
        
        except Exception as e:
            logger.error(f"Error checking retention status: {e}")
    
    def check_storage_statistics(self):
        """檢查儲存空間統計"""
        logger.info("Checking storage statistics")
        
        tables = [
            'ohlcv', 'ohlcv_5m', 'ohlcv_15m', 'ohlcv_1h', 'ohlcv_1d',
            'trades', 'orderbook_snapshots'
        ]
        
        for table_name in tables:
            try:
                query = f"""
                SELECT
                    pg_relation_size('{table_name}'::regclass) AS table_size,
                    pg_total_relation_size('{table_name}'::regclass) - 
                        pg_relation_size('{table_name}'::regclass) AS index_size
                """
                
                with self.conn.cursor() as cur:  # type: ignore
                    cur.execute(query)
                    result = cur.fetchone()  # type: ignore
                    
                    if result:
                        self.metrics.table_size_bytes.labels(
                            table_name=table_name
                        ).set(result['table_size'])  # type: ignore
                        
                        self.metrics.index_size_bytes.labels(
                            table_name=table_name
                        ).set(result['index_size'])  # type: ignore
                        
                        logger.debug(
                            f"{table_name}: table={result['table_size']} bytes, "  # type: ignore
                            f"index={result['index_size']} bytes"  # type: ignore
                        )
            
            except Exception as e:
                logger.error(f"Error checking storage for {table_name}: {e}")
    
    def check_data_integrity(self):
        """檢查資料完整性（壓縮比等）"""
        logger.info("Checking data integrity")
        
        # 檢查 1m vs 5m 壓縮比
        try:
            query = """
            SELECT
                (SELECT COUNT(*) FROM ohlcv WHERE timeframe = '1m')::FLOAT AS raw_count,
                (SELECT COUNT(*) FROM ohlcv_5m)::FLOAT AS agg_count
            """
            
            with self.conn.cursor() as cur:  # type: ignore
                cur.execute(query)
                result = cur.fetchone()  # type: ignore
                
                if result and result['agg_count'] > 0:  # type: ignore
                    ratio = result['raw_count'] / result['agg_count']  # type: ignore
                    self.metrics.aggregate_compression_ratio.labels(
                        source_layer='ohlcv_1m',
                        target_layer='ohlcv_5m'
                    ).set(ratio)
                    
                    # 預期比率約為 5:1，如果偏差太大則警告
                    if abs(ratio - 5.0) > 1.0:
                        logger.warning(
                            f"1m vs 5m compression ratio abnormal: {ratio:.2f} "
                            f"(expected ~5.0)"
                        )
        
        except Exception as e:
            logger.error(f"Error checking data integrity: {e}")


def create_retention_monitor(db_config: Dict[str, Any]) -> RetentionMonitor:
    """
    創建資料保留監控器實例
    
    Args:
        db_config: 資料庫配置
        
    Returns:
        RetentionMonitor 實例
    """
    return RetentionMonitor(db_config)
