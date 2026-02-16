"""
Signal Monitor (Bybit Optimized)
市場異常訊號掃描器

職責：
1. 定期掃描資料庫中的指標 (Funding Rate, OI, CVD)
2. 根據預定義規則觸發訊號
3. 將訊號寫入 market_signals 表 (支援多時間框架)
"""
import os
from typing import List, Dict
from loguru import logger

from loaders.db_loader import DatabaseLoader
from utils.notifier import TelegramNotifier

class SignalMonitor:
    def __init__(self):
        self.loader = DatabaseLoader()
        self.notifier = TelegramNotifier()
        self.TOP_SYMBOLS_LIMIT = 10
        
        # 閾值設定
        self.THRESHOLDS = {
            'funding_high': 0.0005,  # 0.05%
            'funding_low': -0.0005,  # -0.05%
            'oi_spike_pct': 0.05,    # 5% (1h change)
            'liquidation_usd': 500000, # $500k single liquidation
            'liquidation_cluster_usd': 3000000, # $3M aggregate in 1m
            'obi_extreme': 0.6,       # |OBI| > 0.6 (60% imbalance)
        }
        # 交易時框配置：短線（5m）+ 波段（1h/4h/1d）
        self.TIMEFRAME_CONFIG = {
            '5m': {
                'lookback': '24 hours',
                'interval': '5 minutes',
                'min_points': 36,
                'price_break_pct': 0.0015,
                'horizon': 'short',
            },
            '1h': {
                'lookback': '21 days',
                'interval': '1 hour',
                'min_points': 30,
                'price_break_pct': 0.003,
                'horizon': 'swing',
            },
            '4h': {
                'lookback': '120 days',
                'interval': '4 hours',
                'min_points': 24,
                'price_break_pct': 0.004,
                'horizon': 'swing',
            },
            '1d': {
                'lookback': '365 days',
                'interval': '1 day',
                'min_points': 20,
                'price_break_pct': 0.006,
                'horizon': 'swing',
            },
        }

    def _map_liquidation_impact_side(self, raw_side: str) -> str:
        """
        將爆倉 side 映射為價格影響方向。

        規則：
        - buy / short 代表空單被強平，通常對價格偏多（bullish）
        - sell / long 代表多單被強平，通常對價格偏空（bearish）
        """
        side = (raw_side or "").lower()
        if side in ("buy", "short"):
            return "bullish"
        if side in ("sell", "long"):
            return "bearish"
        return "neutral"

    def scan(self):
        """執行全市場掃描 (Multi-Timeframe)"""
        logger.info("Starting Multi-Timeframe Market Signal Scan...")
        signals = []
        
        try:
            # 取得活躍市場列表 (Top N by 24h volume, Bybit Linear)
            active_markets = self._get_top_symbols(limit=self.TOP_SYMBOLS_LIMIT)
            
            # 1. 掃描資金費率異常
            signals.extend(self._scan_funding_rates(active_markets))
            
            # 2. 掃描 OI 突增
            signals.extend(self._scan_oi_spikes(active_markets))

            # 3. 掃描爆倉 (單筆大額 + 叢集)
            signals.extend(self._scan_liquidations(active_markets))

            # 4. 掃描 OBI 極端失衡
            signals.extend(self._scan_obi_extremes(active_markets))

            # 5. 多時間框架掃描（短線 + 波段）
            cvd_timeframes = self._get_cvd_timeframes()
            for timeframe in cvd_timeframes:
                signals.extend(self._scan_cvd_divergence_mtf(active_markets, timeframe))
            
            if signals:
                count = self.loader.insert_market_signals(signals)
                logger.success(f"Generated {count} new market signals.")
                
                # 發送高優先級告警
                for sig in signals:
                    if sig['severity'] in ['warning', 'critical']:
                        self.notifier.send_signal_alert(sig)
            else:
                logger.info("No signals detected in current scan.")
        except Exception as e:
            logger.error(f"Error during signal scan: {e}")

    def _get_cvd_timeframes(self) -> List[str]:
        """
        取得 CVD 掃描時框。
        可由 SIGNAL_TIMEFRAMES 覆蓋，格式如：5m,1h,4h,1d
        """
        default_timeframes = ['5m', '1h', '4h', '1d']
        raw = os.getenv("SIGNAL_TIMEFRAMES", "")
        if not raw:
            return default_timeframes

        parsed = [tf.strip() for tf in raw.split(',') if tf.strip()]
        valid = [tf for tf in parsed if tf in self.TIMEFRAME_CONFIG]
        if valid:
            return valid

        logger.warning(
            f"Invalid SIGNAL_TIMEFRAMES='{raw}', fallback to default: {default_timeframes}"
        )
        return default_timeframes

    def _resolve_ohlcv_source_timeframe(
        self,
        cur,
        symbol: str,
        timeframe: str,
        lookback: str,
        interval_literal: str,
        min_points: int
    ) -> str:
        """
        優先使用原生時框；若資料不足，回退到 1m 聚合。
        """
        cur.execute(
            """
            SELECT COUNT(*)
            FROM ohlcv o
            JOIN markets m ON o.market_id = m.id
            JOIN exchanges e ON m.exchange_id = e.id
            WHERE m.symbol = %s
              AND e.name = 'bybit'
              AND o.time > NOW() - (%s)::interval
              AND o.timeframe = %s
            """,
            (symbol, lookback, timeframe)
        )
        native_count = int(cur.fetchone()[0] or 0)
        if native_count >= min_points:
            return timeframe

        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT time_bucket('{interval_literal}', o.time) AS bucket
                FROM ohlcv o
                JOIN markets m ON o.market_id = m.id
                JOIN exchanges e ON m.exchange_id = e.id
                WHERE m.symbol = %s
                  AND e.name = 'bybit'
                  AND o.time > NOW() - (%s)::interval
                  AND o.timeframe = '1m'
                GROUP BY bucket
            ) t
            """,
            (symbol, lookback)
        )
        fallback_count = int(cur.fetchone()[0] or 0)
        if fallback_count >= min_points:
            return '1m'
        return ""

    def _scan_obi_extremes(self, symbols: List[str]) -> List[Dict]:
        """
        掃描 Order Book Imbalance 極端失衡
        """
        signals = []
        if not symbols:
            return signals
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT ON (m.symbol)
                            os.time,
                            m.symbol,
                            os.obi,
                            os.mid_price
                        FROM orderbook_snapshots os
                        JOIN markets m ON os.market_id = m.id
                        WHERE os.time > NOW() - INTERVAL '15 minutes'
                          AND ABS(os.obi) >= %s
                          AND m.symbol = ANY(%s)
                        ORDER BY m.symbol, os.time DESC
                    """, (self.THRESHOLDS['obi_extreme'], symbols))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        timestamp, symbol, obi, price = row
                        obi = float(obi)
                        side = 'bullish' if obi > 0 else 'bearish'
                        
                        signals.append({
                            'time': timestamp,
                            'symbol': symbol,
                            'signal_type': 'obi_extreme',
                            'side': side,
                            'severity': 'info' if abs(obi) < 0.8 else 'warning',
                            'price_at_signal': float(price),
                            'message': f"OBI Extreme: {symbol} imbalance at {obi*100:.2f}% ({side})",
                            'metadata': {'obi': obi, 'mid_price': float(price)}
                        })
        except Exception as e:
            logger.error(f"Error scanning OBI extremes: {e}")
        return signals

    def _get_top_symbols(self, limit: int = 10) -> List[str]:
        """取得 Bybit 前 N 大合約（依 24h 成交量）"""
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT m.symbol
                        FROM ohlcv o
                        JOIN markets m ON o.market_id = m.id
                        JOIN exchanges e ON m.exchange_id = e.id
                        WHERE e.name = 'bybit'
                          AND m.market_type = 'linear_perpetual'
                          AND m.is_active = TRUE
                          AND o.timeframe = '1m'
                          AND o.time >= NOW() - INTERVAL '24 hours'
                        GROUP BY m.symbol
                        ORDER BY SUM(o.volume) DESC
                        LIMIT %s
                    """, (limit,))
                    symbols = [row[0] for row in cur.fetchall()]
                    if symbols:
                        return symbols
        except:
            pass
        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

    def _scan_oi_spikes(self, symbols: List[str]) -> List[Dict]:
        """
        掃描 Open Interest 突增 (1小時變動率)
        """
        signals = []
        if not symbols:
            return signals
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH oi_changes AS (
                            SELECT 
                                m.symbol,
                                mm.value as current_oi,
                                LAG(mm.value) OVER (PARTITION BY m.id ORDER BY mm.time ASC) as prev_oi,
                                mm.time as current_ts,
                                LAG(mm.time) OVER (PARTITION BY m.id ORDER BY mm.time ASC) as prev_ts
                            FROM market_metrics mm
                            JOIN markets m ON mm.market_id = m.id
                            JOIN exchanges e ON m.exchange_id = e.id
                            WHERE mm.name = 'open_interest'
                              AND e.name = 'bybit'
                              AND m.symbol = ANY(%s)
                              AND mm.time > NOW() - INTERVAL '4 hours'
                        )
                        SELECT * FROM oi_changes 
                        WHERE prev_oi IS NOT NULL 
                          AND prev_oi > 0
                          AND (current_ts - prev_ts) <= INTERVAL '70 minutes' -- ✅ 確保對比的是連續的 1 小時數據
                          AND (current_oi - prev_oi) / prev_oi > %s
                        ORDER BY current_ts DESC;
                    """, (symbols, self.THRESHOLDS['oi_spike_pct']))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        symbol, curr, prev, timestamp, _prev_time = row
                        curr_f = float(curr)
                        prev_f = float(prev)
                        change_pct = (curr_f - prev_f) / prev_f
                        signals.append({
                            'time': timestamp,
                            'symbol': symbol,
                            'signal_type': 'oi_spike',
                            'side': 'neutral',
                            'severity': 'info' if change_pct < 0.1 else 'warning',
                            'price_at_signal': None,
                            'message': f"OI Spike: {symbol} OI increased by {change_pct*100:.2f}% in the last hour",
                            'metadata': {'current_oi': curr_f, 'prev_oi': prev_f, 'change_pct': float(change_pct)}
                        })
        except Exception as e:
            logger.error(f"Error scanning OI spikes: {e}")
        return signals

    def _scan_liquidations(self, symbols: List[str]) -> List[Dict]:
        """
        掃描爆倉 (單筆大額 + 叢集)
        """
        signals = []
        if not symbols:
            return signals
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    # 1. 掃描單筆巨鯨爆倉
                    cur.execute("""
                        SELECT time, symbol, side, value_usd, price
                        FROM liquidations
                        WHERE value_usd >= %s
                          AND time > NOW() - INTERVAL '5 minutes'
                          AND exchange = 'bybit'
                          AND symbol = ANY(%s)
                        ORDER BY time DESC
                    """, (self.THRESHOLDS['liquidation_usd'], symbols))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        timestamp, symbol, side, value, price = row
                        value = float(value)
                        price = float(price)
                        impact_side = self._map_liquidation_impact_side(side)
                        signals.append({
                            'time': timestamp,
                            'symbol': symbol,
                            'signal_type': 'liquidation_whale',
                            'side': impact_side,
                            'severity': 'warning' if value < 2000000 else 'critical',
                            'price_at_signal': price,
                            'message': f"Whale Liquidation: ${value/1e6:.2f}M {side} liquidated on {symbol}",
                            'metadata': {'value_usd': value, 'side': side, 'type': 'single'}
                        })
                        
                    # 2. 掃描爆倉叢集 (Liquidation Cluster)
                    cur.execute("""
                        SELECT 
                            MAX(time) as last_time,
                            symbol,
                            side,
                            SUM(value_usd) as total_value,
                            AVG(price) as avg_price,
                            COUNT(*) as count
                        FROM liquidations
                        WHERE time > NOW() - INTERVAL '1 minute'
                          AND exchange = 'bybit'
                          AND symbol = ANY(%s)
                        GROUP BY symbol, side
                        HAVING SUM(value_usd) >= %s
                    """, (symbols, self.THRESHOLDS['liquidation_cluster_usd']))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        timestamp, symbol, side, total_value, avg_price, count = row
                        total_value = float(total_value)
                        avg_price = float(avg_price)
                        impact_side = self._map_liquidation_impact_side(side)
                        signals.append({
                            'time': timestamp, # Use latest time in cluster
                            'symbol': symbol,
                            'signal_type': 'liquidation_cluster',
                            'side': impact_side,
                            'severity': 'critical',
                            'price_at_signal': avg_price,
                            'message': f"Liquidation Cluster: ${total_value/1e6:.2f}M {side} rekt in 1m ({count} orders)",
                            'metadata': {'value_usd': total_value, 'count': count, 'side': side, 'type': 'cluster'}
                        })
                        
        except Exception as e:
            logger.error(f"Error scanning liquidations: {e}")
        return signals

    def _scan_cvd_divergence_mtf(self, symbols: List[str], timeframe: str) -> List[Dict]:
        """
        掃描 CVD 背離 (支援 MTF)
        """
        signals = []
        cfg = self.TIMEFRAME_CONFIG.get(timeframe)
        if not cfg:
            return signals

        lookback = cfg['lookback']
        interval_literal = cfg['interval']
        min_points = int(cfg['min_points'])
        price_break_pct = float(cfg['price_break_pct'])
        horizon = cfg['horizon']

        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    for symbol in symbols:
                        source_timeframe = self._resolve_ohlcv_source_timeframe(
                            cur=cur,
                            symbol=symbol,
                            timeframe=timeframe,
                            lookback=lookback,
                            interval_literal=interval_literal,
                            min_points=min_points
                        )
                        if not source_timeframe:
                            continue

                        query = f"""
                            WITH cvd_agg AS (
                                SELECT
                                    time_bucket('{interval_literal}', cvd.bucket) as bucket,
                                    SUM(cvd.volume_delta) as volume_delta
                                FROM market_cvd_1m cvd
                                JOIN markets m ON cvd.market_id = m.id
                                JOIN exchanges e ON m.exchange_id = e.id
                                WHERE m.symbol = %s AND e.name = 'bybit'
                                  AND cvd.bucket > NOW() - INTERVAL '{lookback}'
                                GROUP BY bucket
                            ),
                            price_agg AS (
                                SELECT
                                    time_bucket('{interval_literal}', o.time) as bucket,
                                    MAX(o.high) as price_high,
                                    MIN(o.low) as price_low
                                FROM ohlcv o
                                JOIN markets m ON o.market_id = m.id
                                JOIN exchanges e ON m.exchange_id = e.id
                                WHERE m.symbol = %s AND e.name = 'bybit'
                                  AND o.time > NOW() - INTERVAL '{lookback}'
                                  AND o.timeframe = %s
                                GROUP BY bucket
                            ),
                            raw_data AS (
                                SELECT
                                    p.bucket as time,
                                    p.price_high,
                                    p.price_low,
                                    COALESCE(cvd.volume_delta, 0) as volume_delta
                                FROM price_agg p
                                LEFT JOIN cvd_agg cvd ON p.bucket = cvd.bucket
                                ORDER BY p.bucket ASC
                            ),
                            cumulative_cvd AS (
                                SELECT
                                    time,
                                    price_high,
                                    price_low,
                                    SUM(volume_delta) OVER (ORDER BY time) as cvd
                                FROM raw_data
                            )
                            SELECT * FROM cumulative_cvd;
                        """
                        cur.execute(query, (symbol, symbol, source_timeframe))
                        rows = cur.fetchall()
                        
                        if not rows or len(rows) < min_points:
                            continue
                        # psycopg 對 numeric 會回傳 Decimal，這裡統一轉 float，避免 Decimal * float 例外
                        cleaned = []
                        for t, price_high, price_low, cvd in rows:
                            cleaned.append((
                                t,
                                float(price_high) if price_high is not None else None,
                                float(price_low) if price_low is not None else None,
                                float(cvd) if cvd is not None else 0.0,
                            ))
                        rows = cleaned

                        mid = len(rows) // 2
                        p1, p2 = rows[:mid], rows[mid:]
                        
                        # 熊背離 (Bearish Divergence)
                        h1 = max(p1, key=lambda x: x[1])
                        h2 = max(p2, key=lambda x: x[1])
                        if h2[1] > h1[1] * (1 + price_break_pct) and h2[3] < h1[3]:
                            signals.append({
                                'time': h2[0], 'symbol': symbol,
                                'signal_type': f'cvd_divergence_{timeframe}',
                                'side': 'bearish', 'severity': 'warning',
                                'price_at_signal': float(h2[1]),
                                'message': f"[{timeframe}/{horizon}] Bearish Divergence: Price HH, CVD LH",
                                'metadata': {
                                    'timeframe': timeframe,
                                    'horizon': horizon,
                                    'source_timeframe': source_timeframe,
                                    'p1_price': float(h1[1]),
                                    'p2_price': float(h2[1]),
                                    'p1_cvd': float(h1[3]),
                                    'p2_cvd': float(h2[3])
                                }
                            })

                        # 牛背離 (Bullish Divergence)
                        l1 = min(p1, key=lambda x: x[2])
                        l2 = min(p2, key=lambda x: x[2])
                        if l2[2] < l1[2] * (1 - price_break_pct) and l2[3] > l1[3]:
                            signals.append({
                                'time': l2[0], 'symbol': symbol,
                                'signal_type': f'cvd_divergence_{timeframe}',
                                'side': 'bullish', 'severity': 'warning',
                                'price_at_signal': float(l2[2]),
                                'message': f"[{timeframe}/{horizon}] Bullish Divergence: Price LL, CVD HL",
                                'metadata': {
                                    'timeframe': timeframe,
                                    'horizon': horizon,
                                    'source_timeframe': source_timeframe,
                                    'p1_price': float(l1[2]),
                                    'p2_price': float(l2[2]),
                                    'p1_cvd': float(l1[3]),
                                    'p2_cvd': float(l2[3])
                                }
                            })
        except Exception as e:
            logger.error(f"Error scanning CVD divergence ({timeframe}): {e}")
        return signals

    def _scan_funding_rates(self, symbols: List[str]) -> List[Dict]:
        """
        掃描極端資金費率
        """
        signals = []
        if not symbols:
            return signals
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT ON (m.symbol)
                            mm.time,
                            m.symbol,
                            mm.value,
                            e.name as exchange
                        FROM market_metrics mm
                        JOIN markets m ON mm.market_id = m.id
                        JOIN exchanges e ON m.exchange_id = e.id
                        WHERE mm.name = 'funding_rate'
                          AND mm.time > NOW() - INTERVAL '1 hour'
                          AND e.name = 'bybit'
                          AND m.symbol = ANY(%s)
                        ORDER BY m.symbol, mm.time DESC
                    """, (symbols,))
                    rows = cur.fetchall()
                    
                    for row in rows:
                        timestamp, symbol, rate, exchange = row
                        rate = float(rate)
                        
                        if abs(rate) > self.THRESHOLDS['funding_high']:
                            side = 'bearish' if rate > 0 else 'bullish'
                            signals.append({
                                'time': timestamp,
                                'symbol': symbol,
                                'signal_type': 'funding_extreme',
                                'side': side,
                                'severity': 'warning' if abs(rate) < 0.001 else 'critical',
                                'price_at_signal': None,
                                'message': f"Extreme Funding: {rate*100:.4f}% on {exchange}",
                                'metadata': {'rate': rate, 'exchange': exchange}
                            })
        except Exception as e:
            logger.error(f"Error scanning funding rates: {e}")
        return signals

if __name__ == "__main__":
    monitor = SignalMonitor()
    monitor.scan()
