"""
資料品質驗證器
職責：驗證資料是否可被下游模型使用，只標記不刪除

規則：
1. 只標記（flag），不隨意刪除資料
2. 任何資料修正都必須可關閉、有版本標記
3. 驗證結果要寫回 DB 或 metadata 表
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import numpy as np


class DataValidator:
    """
    資料品質驗證器

    提供以下檢查：
    - 時間序列連續性檢查
    - 價格跳點 / 交易量異常標記
    - 訂單簿深度合理性檢查
    """

    def __init__(
        self,
        price_jump_threshold: float = 0.1,  # 10% 價格跳動視為異常
        volume_spike_threshold: float = 5.0,  # 5 倍成交量視為異常
    ):
        """
        初始化驗證器

        Args:
            price_jump_threshold: 價格跳動閾值（百分比）
            volume_spike_threshold: 成交量異常倍數
        """
        self.price_jump_threshold = price_jump_threshold
        self.volume_spike_threshold = volume_spike_threshold

    def check_timestamp_order(
        self,
        timestamps: List[datetime]
    ) -> Tuple[bool, List[int]]:
        """
        檢查時間戳是否單調遞增

        Args:
            timestamps: 時間戳列表

        Returns:
            (是否通過, 異常索引列表)
        """
        out_of_order_indices = []

        for i in range(1, len(timestamps)):
            if timestamps[i] <= timestamps[i-1]:
                out_of_order_indices.append(i)

        is_valid = len(out_of_order_indices) == 0

        if not is_valid:
            logger.warning(
                f"Found {len(out_of_order_indices)} out-of-order timestamps"
            )

        return is_valid, out_of_order_indices

    def check_no_duplicates(
        self,
        data: List[Dict],
        key_fields: List[str]
    ) -> Tuple[bool, List[int]]:
        """
        檢查是否有重複資料

        Args:
            data: 資料列表
            key_fields: 用於判斷重複的欄位

        Returns:
            (是否通過, 重複資料索引列表)
        """
        seen = set()
        duplicate_indices = []

        for i, record in enumerate(data):
            key = tuple(record.get(field) for field in key_fields)

            if key in seen:
                duplicate_indices.append(i)
            else:
                seen.add(key)

        is_valid = len(duplicate_indices) == 0

        if not is_valid:
            logger.warning(f"Found {len(duplicate_indices)} duplicate records")

        return is_valid, duplicate_indices

    def check_price_jumps(
        self,
        prices: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Tuple[bool, List[Dict]]:
        """
        檢查價格異常跳動

        Args:
            prices: 價格列表
            timestamps: 對應的時間戳（可選，用於記錄）

        Returns:
            (是否通過, 異常記錄列表)
            異常記錄格式: {
                'index': int,
                'timestamp': datetime,
                'price': float,
                'prev_price': float,
                'change_pct': float
            }
        """
        anomalies = []

        for i in range(1, len(prices)):
            if prices[i-1] == 0:
                continue

            change_pct = abs(prices[i] - prices[i-1]) / prices[i-1]

            if change_pct > self.price_jump_threshold:
                anomaly = {
                    'index': i,
                    'price': prices[i],
                    'prev_price': prices[i-1],
                    'change_pct': change_pct
                }

                if timestamps:
                    anomaly['timestamp'] = timestamps[i]

                anomalies.append(anomaly)

        is_valid = len(anomalies) == 0

        if not is_valid:
            logger.warning(
                f"Found {len(anomalies)} price jumps "
                f"exceeding {self.price_jump_threshold*100}%"
            )

        return is_valid, anomalies

    def check_volume_spikes(
        self,
        volumes: List[float],
        window_size: int = 20
    ) -> Tuple[bool, List[Dict]]:
        """
        檢查成交量異常激增

        Args:
            volumes: 成交量列表
            window_size: 移動平均窗口大小

        Returns:
            (是否通過, 異常記錄列表)
        """
        if len(volumes) < window_size:
            logger.warning(
                f"Not enough data for volume spike check "
                f"({len(volumes)} < {window_size})"
            )
            return True, []

        volumes_array = np.array(volumes)
        anomalies = []

        for i in range(window_size, len(volumes)):
            window = volumes_array[i-window_size:i]
            avg_volume = window.mean()

            if avg_volume == 0:
                continue

            spike_ratio = volumes[i] / avg_volume

            if spike_ratio > self.volume_spike_threshold:
                anomalies.append({
                    'index': i,
                    'volume': volumes[i],
                    'avg_volume': avg_volume,
                    'spike_ratio': spike_ratio
                })

        is_valid = len(anomalies) == 0

        if not is_valid:
            logger.warning(
                f"Found {len(anomalies)} volume spikes "
                f"exceeding {self.volume_spike_threshold}x average"
            )

        return is_valid, anomalies

    def check_missing_intervals(
        self,
        timestamps: List[datetime],
        expected_interval: timedelta
    ) -> Tuple[bool, List[Dict]]:
        """
        檢查時間序列是否有缺失

        Args:
            timestamps: 時間戳列表
            expected_interval: 預期的時間間隔

        Returns:
            (是否通過, 缺失區段列表)
            缺失記錄格式: {
                'start_time': datetime,
                'end_time': datetime,
                'missing_count': int
            }
        """
        gaps = []

        for i in range(1, len(timestamps)):
            actual_interval = timestamps[i] - timestamps[i-1]

            if actual_interval > expected_interval * 1.5:  # 允許 50% 誤差
                missing_count = int(
                    actual_interval.total_seconds() /
                    expected_interval.total_seconds()
                ) - 1

                gaps.append({
                    'start_time': timestamps[i-1],
                    'end_time': timestamps[i],
                    'missing_count': missing_count,
                    'actual_interval': actual_interval
                })

        is_valid = len(gaps) == 0

        if not is_valid:
            total_missing = sum(g['missing_count'] for g in gaps)
            logger.warning(
                f"Found {len(gaps)} time gaps with "
                f"{total_missing} missing intervals"
            )

        return is_valid, gaps

    def validate_ohlcv_batch(
        self,
        ohlcv_data: List[List],
        timeframe: str
    ) -> Dict:
        """
        驗證 OHLCV 批次資料

        Args:
            ohlcv_data: [[timestamp, open, high, low, close, volume], ...]
            timeframe: 時間週期（用於推斷間隔）

        Returns:
            驗證結果摘要
        """
        if not ohlcv_data:
            return {'valid': True, 'errors': [], 'warnings': []}

        # 解析資料
        timestamps = [
            datetime.fromtimestamp(candle[0] / 1000)
            for candle in ohlcv_data
        ]
        closes = [candle[4] for candle in ohlcv_data]
        volumes = [candle[5] for candle in ohlcv_data]

        errors = []
        warnings = []

        # 檢查時間戳順序
        is_ordered, out_of_order = self.check_timestamp_order(timestamps)
        if not is_ordered:
            errors.append({
                'type': 'out_of_order_timestamp',
                'count': len(out_of_order),
                'indices': out_of_order
            })

        # 檢查價格跳動
        is_price_ok, price_jumps = self.check_price_jumps(closes, timestamps)
        if not is_price_ok:
            warnings.append({
                'type': 'price_jump',
                'count': len(price_jumps),
                'details': price_jumps[:10]  # 只記錄前 10 個
            })

        # 檢查成交量異常
        is_volume_ok, volume_spikes = self.check_volume_spikes(volumes)
        if not is_volume_ok:
            warnings.append({
                'type': 'volume_spike',
                'count': len(volume_spikes),
                'details': volume_spikes[:10]
            })

        # 檢查缺失區間
        interval_map = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4),
            '1d': timedelta(days=1)
        }
        expected_interval = interval_map.get(timeframe, timedelta(minutes=1))
        is_complete, gaps = self.check_missing_intervals(
            timestamps,
            expected_interval
        )
        if not is_complete:
            warnings.append({
                'type': 'missing_interval',
                'count': len(gaps),
                'details': gaps[:10]
            })

        return {
            'valid': len(errors) == 0,
            'total_records': len(ohlcv_data),
            'errors': errors,
            'warnings': warnings
        }

    def validate_ohlcv_stream(
        self,
        ohlcv_rows,
        timeframe: str,
        volume_window_size: int = 20,
        check_missing_intervals: bool = True
    ) -> Dict:
        """
        以串流方式驗證 OHLCV 資料，降低記憶體使用

        Args:
            ohlcv_rows: iterator yielding [timestamp_ms, open, high, low, close, volume]
            timeframe: 時間週期（用於推斷間隔）
            volume_window_size: 成交量異常檢查視窗大小
            check_missing_intervals: 是否在串流中檢查缺失區間

        Returns:
            驗證結果摘要
        """
        expected_interval = None
        if check_missing_intervals:
            interval_map = {
                '1m': timedelta(minutes=1),
                '5m': timedelta(minutes=5),
                '15m': timedelta(minutes=15),
                '1h': timedelta(hours=1),
                '4h': timedelta(hours=4),
                '1d': timedelta(days=1)
            }
            expected_interval = interval_map.get(timeframe, timedelta(minutes=1))

        total_records = 0
        out_of_order = []
        price_jumps = []
        volume_spikes = []
        gaps = []

        prev_timestamp = None
        prev_close = None

        from collections import deque
        volume_window = deque(maxlen=volume_window_size)
        volume_sum = 0.0

        for row in ohlcv_rows:
            total_records += 1
            timestamp = datetime.fromtimestamp(row[0] / 1000)
            close = row[4]
            volume = row[5]

            if prev_timestamp is not None:
                if timestamp <= prev_timestamp:
                    out_of_order.append(total_records - 1)

                if check_missing_intervals and expected_interval is not None:
                    actual_interval = timestamp - prev_timestamp
                    if actual_interval > expected_interval * 1.5:
                        missing_count = int(
                            actual_interval.total_seconds() /
                            expected_interval.total_seconds()
                        ) - 1
                        gaps.append({
                            'start_time': prev_timestamp,
                            'end_time': timestamp,
                            'missing_count': missing_count,
                            'actual_interval': actual_interval
                        })

            if prev_close is not None and prev_close != 0:
                change_pct = abs(close - prev_close) / prev_close
                if change_pct > self.price_jump_threshold:
                    price_jumps.append({
                        'index': total_records - 1,
                        'timestamp': timestamp,
                        'price': close,
                        'prev_price': prev_close,
                        'change_pct': change_pct
                    })

            if len(volume_window) == volume_window_size:
                avg_volume = volume_sum / volume_window_size
                if avg_volume != 0:
                    spike_ratio = volume / avg_volume
                    if spike_ratio > self.volume_spike_threshold:
                        volume_spikes.append({
                            'index': total_records - 1,
                            'volume': volume,
                            'avg_volume': avg_volume,
                            'spike_ratio': spike_ratio
                        })

            if len(volume_window) == volume_window_size:
                volume_sum -= volume_window[0]
            volume_window.append(volume)
            volume_sum += volume

            prev_timestamp = timestamp
            prev_close = close

        if total_records == 0:
            return {'valid': True, 'errors': [], 'warnings': []}

        errors = []
        warnings = []

        if out_of_order:
            errors.append({
                'type': 'out_of_order_timestamp',
                'count': len(out_of_order),
                'indices': out_of_order
            })

        if price_jumps:
            warnings.append({
                'type': 'price_jump',
                'count': len(price_jumps),
                'details': price_jumps[:10]
            })

        if volume_spikes:
            warnings.append({
                'type': 'volume_spike',
                'count': len(volume_spikes),
                'details': volume_spikes[:10]
            })

        if gaps and check_missing_intervals:
            warnings.append({
                'type': 'missing_interval',
                'count': len(gaps),
                'details': gaps[:10]
            })

        return {
            'valid': len(errors) == 0,
            'total_records': total_records,
            'errors': errors,
            'warnings': warnings
        }
