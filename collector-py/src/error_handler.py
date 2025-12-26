"""
錯誤處理與重試機制
職責：
1. 提供裝飾器實作重試邏輯
2. 指數退避算法
3. 錯誤分類與記錄
4. 連續失敗檢測與告警
"""
import time
import functools
import psycopg2
from typing import Callable, Optional, Type, Tuple, Any
from datetime import datetime
from loguru import logger
import ccxt

from config import settings


class RetryConfig:
    """重試配置"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ):
        """
        Args:
            max_retries: 最大重試次數
            initial_delay: 初始延遲（秒）
            backoff_factor: 退避倍數
            max_delay: 最大延遲（秒）
            jitter: 是否加入隨機抖動
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter


class ErrorClassifier:
    """錯誤分類器"""

    @staticmethod
    def classify_exception(exc: Exception) -> str:
        """
        分類異常類型

        Args:
            exc: 異常對象

        Returns:
            錯誤類型字串
        """
        if isinstance(exc, ccxt.NetworkError):
            return 'network'
        elif isinstance(exc, ccxt.DDoSProtection):
            return 'rate_limit'
        elif isinstance(exc, ccxt.RateLimitExceeded):
            return 'rate_limit'
        elif isinstance(exc, ccxt.RequestTimeout):
            return 'timeout'
        elif isinstance(exc, ccxt.ExchangeNotAvailable):
            return 'exchange_unavailable'
        elif isinstance(exc, ccxt.ExchangeError):
            return 'exchange'
        elif isinstance(exc, psycopg2.Error):
            return 'database'
        elif isinstance(exc, ConnectionError):
            return 'network'
        elif isinstance(exc, TimeoutError):
            return 'timeout'
        else:
            return 'unknown'

    @staticmethod
    def is_retryable(error_type: str) -> bool:
        """
        判斷錯誤是否可重試

        Args:
            error_type: 錯誤類型

        Returns:
            是否可重試
        """
        retryable_errors = {
            'network',
            'rate_limit',
            'timeout',
            'exchange_unavailable'
        }
        return error_type in retryable_errors


class APIErrorLogger:
    """API 錯誤日誌記錄器"""

    def __init__(self, db_conn=None):
        """
        初始化錯誤記錄器

        Args:
            db_conn: 資料庫連接（可選）
        """
        self.conn = db_conn
        self.should_close_conn = False

        if self.conn is None:
            try:
                self.conn = psycopg2.connect(
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    dbname=settings.postgres_db,
                    user=settings.postgres_user,
                    password=settings.postgres_password
                )
                self.should_close_conn = True
            except Exception as e:
                logger.warning(f"Failed to connect to DB for error logging: {e}")
                self.conn = None

    def log_error(
        self,
        exchange_name: str,
        endpoint: str,
        error_type: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_params: Optional[dict] = None
    ):
        """
        記錄 API 錯誤到資料庫

        Args:
            exchange_name: 交易所名稱
            endpoint: API 端點
            error_type: 錯誤類型
            error_code: 錯誤代碼
            error_message: 錯誤訊息
            request_params: 請求參數
        """
        if self.conn is None:
            logger.warning("No DB connection, skipping error logging")
            return

        try:
            import json

            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_error_logs (
                        exchange_name, endpoint, error_type,
                        error_code, error_message, request_params, timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        exchange_name,
                        endpoint,
                        error_type,
                        error_code,
                        error_message,
                        json.dumps(request_params) if request_params else None
                    )
                )
                self.conn.commit()

            logger.debug(f"Logged API error: {exchange_name}/{endpoint} - {error_type}")

        except Exception as e:
            logger.error(f"Failed to log API error to DB: {e}")

    def close(self):
        """關閉資料庫連接"""
        if self.should_close_conn and self.conn:
            self.conn.close()


class ConsecutiveFailureTracker:
    """連續失敗追蹤器"""

    def __init__(self, threshold: int = 5):
        """
        Args:
            threshold: 連續失敗閾值
        """
        self.threshold = threshold
        self.failures: dict = {}  # {key: count}

    def record_failure(self, key: str) -> int:
        """
        記錄失敗

        Args:
            key: 追蹤鍵（如 'binance:BTCUSDT:ohlcv'）

        Returns:
            當前連續失敗次數
        """
        self.failures[key] = self.failures.get(key, 0) + 1
        count = self.failures[key]

        if count >= self.threshold:
            logger.warning(
                f"Consecutive failure threshold reached for {key}: {count} failures"
            )

        return count

    def record_success(self, key: str):
        """
        記錄成功（重置計數）

        Args:
            key: 追蹤鍵
        """
        if key in self.failures:
            del self.failures[key]

    def is_threshold_exceeded(self, key: str) -> bool:
        """
        檢查是否超過閾值

        Args:
            key: 追蹤鍵

        Returns:
            是否超過閾值
        """
        return self.failures.get(key, 0) >= self.threshold


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_errors: bool = True,
    exchange_name: Optional[str] = None,
    endpoint: Optional[str] = None
) -> Callable:
    """
    重試裝飾器（指數退避）

    Args:
        config: 重試配置
        retryable_exceptions: 可重試的異常類型
        log_errors: 是否記錄錯誤到資料庫
        exchange_name: 交易所名稱（用於錯誤日誌）
        endpoint: API 端點（用於錯誤日誌）

    Returns:
        裝飾器函數
    """
    if config is None:
        config = RetryConfig()

    error_logger = APIErrorLogger() if log_errors else None

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    return result

                except retryable_exceptions as e:
                    last_exception = e
                    error_type = ErrorClassifier.classify_exception(e)

                    # 記錄錯誤
                    if error_logger and exchange_name:
                        error_code = getattr(e, 'code', None)
                        error_logger.log_error(
                            exchange_name=exchange_name,
                            endpoint=endpoint or func.__name__,
                            error_type=error_type,
                            error_code=str(error_code) if error_code else None,
                            error_message=str(e)
                        )

                    # 檢查是否可重試
                    if not ErrorClassifier.is_retryable(error_type):
                        logger.error(
                            f"Non-retryable error in {func.__name__}: {error_type} - {e}"
                        )
                        raise

                    # 最後一次嘗試失敗
                    if attempt == config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded in {func.__name__}: {e}"
                        )
                        raise

                    # 計算延遲時間
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )

                    # 加入隨機抖動
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_retries} failed in {func.__name__} "
                        f"with {error_type}: {e}. Retrying in {delay:.2f}s..."
                    )

                    time.sleep(delay)

            # 理論上不會到這裡，但為了類型檢查
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# 全域連續失敗追蹤器
global_failure_tracker = ConsecutiveFailureTracker(threshold=10)


# 範例用法
if __name__ == "__main__":
    import ccxt

    # 測試重試機制
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=1.0,
        backoff_factor=2.0
    )

    @retry_with_backoff(
        config=retry_config,
        retryable_exceptions=(ccxt.NetworkError, ccxt.RequestTimeout),
        log_errors=True,
        exchange_name='binance',
        endpoint='fetch_ohlcv'
    )
    def fetch_with_retry():
        """模擬可能失敗的 API 請求"""
        import random
        if random.random() < 0.7:  # 70% 機率失敗
            raise ccxt.NetworkError("Connection timeout")
        return "Success!"

    try:
        result = fetch_with_retry()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")

    # 測試連續失敗追蹤
    tracker = ConsecutiveFailureTracker(threshold=3)
    key = "binance:BTCUSDT:ohlcv"

    for i in range(5):
        count = tracker.record_failure(key)
        print(f"Failure {i+1}: count = {count}")

        if tracker.is_threshold_exceeded(key):
            print(f"⚠️ Threshold exceeded for {key}!")
