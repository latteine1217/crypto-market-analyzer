"""
快取管理器

使用 Redis 快取資料以減少資料庫查詢頻率
"""
import redis
import json
import pandas as pd
from typing import Optional, Any
from loguru import logger
from datetime import timedelta


class CacheManager:
    """Redis 快取管理器"""

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 5  # 預設 5 秒過期
    ):
        """
        初始化快取管理器

        Args:
            host: Redis 主機
            port: Redis 端口
            db: Redis 資料庫編號
            password: Redis 密碼
            default_ttl: 預設快取過期時間（秒）
        """
        self.default_ttl = default_ttl
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=2
            )
            # 測試連接
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Redis 快取已啟用: {host}:{port}/{db}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"無法連接 Redis，快取已停用: {e}")
            self.redis_client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """
        從快取取得資料

        Args:
            key: 快取鍵

        Returns:
            快取的資料，若不存在或快取停用則返回 None
        """
        if not self.enabled:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                logger.debug(f"快取命中: {key}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"讀取快取失敗 {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        設定快取

        Args:
            key: 快取鍵
            value: 要快取的資料
            ttl: 過期時間（秒），若為 None 則使用預設值

        Returns:
            是否成功設定快取
        """
        if not self.enabled:
            return False

        try:
            expire_time = ttl if ttl is not None else self.default_ttl
            serialized = json.dumps(value, default=str)
            self.redis_client.setex(
                key,
                timedelta(seconds=expire_time),
                serialized
            )
            logger.debug(f"快取已設定: {key} (TTL={expire_time}s)")
            return True
        except Exception as e:
            logger.error(f"設定快取失敗 {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """刪除快取"""
        if not self.enabled:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"快取已刪除: {key}")
            return True
        except Exception as e:
            logger.error(f"刪除快取失敗 {key}: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        清除符合模式的所有快取

        Args:
            pattern: Redis 鍵模式（如 "market:*"）

        Returns:
            刪除的鍵數量
        """
        if not self.enabled:
            return 0

        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=500
                )
                if keys:
                    deleted += self.redis_client.delete(*keys)
                if cursor == 0:
                    break
            if deleted:
                logger.info(f"已清除 {deleted} 個快取 (pattern={pattern})")
            return deleted
        except Exception as e:
            logger.error(f"清除快取失敗 {pattern}: {e}")
            return 0

    def make_key(self, *parts) -> str:
        """
        建立快取鍵

        Args:
            *parts: 鍵的組成部分

        Returns:
            組合後的鍵（用 : 分隔）

        Example:
            >>> make_key('market', 'binance', 'BTC/USDT')
            'market:binance:BTC/USDT'
        """
        return ':'.join(str(p) for p in parts)

    def get_df(self, key: str) -> Optional[pd.DataFrame]:
        """
        從快取取得 DataFrame

        Args:
            key: 快取鍵

        Returns:
            DataFrame 或 None
        """
        data = self.get(key)
        if data is not None:
            try:
                df = pd.DataFrame(data)
                # 還原 timestamp 欄位為 datetime
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                return df
            except Exception as e:
                logger.error(f"還原 DataFrame 失敗 {key}: {e}")
                return None
        return None

    def set_df(
        self,
        key: str,
        df: pd.DataFrame,
        ttl: Optional[int] = None
    ) -> bool:
        """
        快取 DataFrame

        Args:
            key: 快取鍵
            df: 要快取的 DataFrame
            ttl: 過期時間（秒）

        Returns:
            是否成功
        """
        try:
            # 轉換為 dict（records 格式）
            data = df.to_dict('records')
            return self.set(key, data, ttl)
        except Exception as e:
            logger.error(f"快取 DataFrame 失敗 {key}: {e}")
            return False
