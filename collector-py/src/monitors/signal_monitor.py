"""
Signal Monitor (Bybit Optimized)
市場異常訊號掃描器

職責：
1. 定期掃描資料庫中的指標 (Funding Rate, OI, CVD)
2. 根據預定義規則觸發訊號
3. 將訊號寫入 market_signals 表 (支援多時間框架)
"""
import time
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from loguru import logger

from loaders.db_loader import DatabaseLoader

class SignalMonitor:
    def __init__(self):
        self.loader = DatabaseLoader()
        
        # 閾值設定
        self.THRESHOLDS = {
            'funding_high': 0.0005,  # 0.05%
            'funding_low': -0.0005,  # -0.05%
            'oi_spike_pct': 0.05,    # 5% (1h change)
            'liquidation_usd': 500000 # $500k single liquidation
        }

    def scan(self):
        """執行全市場掃描 (Multi-Timeframe)"""
        logger.info("Starting Multi-Timeframe Market Signal Scan...")
        signals = []
        
        try:
            # 取得活躍市場列表 (Bybit Linear)
            active_markets = self._get_active_markets()
            
            # 1. 掃描資金費率異常
            signals.extend(self._scan_funding_rates())
            
            # 2. 掃描 OI 突增
            signals.extend(self._scan_oi_spikes())

            # 3. 掃描大額爆倉
            signals.extend(self._scan_liquidations())

            # 4. 多時間框架掃描 (1m, 15m, 1h)
            for timeframe in ['1m', '15m', '1h']:
                signals.extend(self._scan_cvd_divergence_mtf(active_markets, timeframe))
            
            if signals:
                count = self.loader.insert_market_signals(signals)
                logger.success(f"Generated {count} new market signals.")
            else:
                logger.info("No signals detected in current scan.")
        except Exception as e:
            logger.error(f"Error during signal scan: {e}")

    def _get_active_markets(self) -> List[str]:
        """取得 Bybit 活躍合約市場"""
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT m.symbol FROM markets m
                        JOIN exchanges e ON m.exchange_id = e.id
                        WHERE e.name = 'bybit' AND m.market_type = 'linear_perpetual'
                        AND m.is_active = TRUE
                    """)
                    return [row[0] for row in cur.fetchall()]
        except:
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

    def _scan_oi_spikes(self) -> List[Dict]:
        """
        掃描 Open Interest 突增 (1小時變動率)
        """
        signals = []
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        WITH oi_changes AS (
                            SELECT 
                                m.symbol,
                                mm.value as current_oi,
                                LAG(mm.value) OVER (PARTITION BY m.id ORDER BY mm.time ASC) as prev_oi,
                                mm.time
                            FROM market_metrics mm
                            JOIN markets m ON mm.market_id = m.id
                            JOIN exchanges e ON m.exchange_id = e.id
                            WHERE mm.name = 'open_interest'
                              AND e.name = 'bybit'
                              AND mm.time > NOW() - INTERVAL '2 hours'
                        )
                        SELECT * FROM oi_changes 
                        WHERE prev_oi IS NOT NULL 
                          AND (current_oi - prev_oi) / prev_oi > %s
                        ORDER BY time DESC;
                    """, (self.THRESHOLDS['oi_spike_pct'],))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        symbol, curr, prev, timestamp = row
                        change_pct = (curr - prev) / prev
                        signals.append({
                            'time': timestamp,
                            'symbol': symbol,
                            'signal_type': 'oi_spike',
                            'side': 'neutral',
                            'severity': 'info' if change_pct < 0.1 else 'warning',
                            'price_at_signal': None,
                            'message': f"OI Spike: {symbol} OI increased by {change_pct*100:.2f}% in the last hour",
                            'metadata': {'current_oi': float(curr), 'prev_oi': float(prev), 'change_pct': float(change_pct)}
                        })
        except Exception as e:
            logger.error(f"Error scanning OI spikes: {e}")
        return signals

    def _scan_liquidations(self) -> List[Dict]:
        """
        掃描大額爆倉
        """
        signals = []
        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT time, symbol, side, value_usd, price
                        FROM liquidations
                        WHERE value_usd >= %s
                          AND time > NOW() - INTERVAL '10 minutes'
                          AND exchange = 'bybit'
                        ORDER BY time DESC
                    """, (self.THRESHOLDS['liquidation_usd'],))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        timestamp, symbol, side, value, price = row
                        signals.append({
                            'time': timestamp,
                            'symbol': symbol,
                            'signal_type': 'liquidation_cascade',
                            'side': 'bullish' if side == 'short' else 'bearish', # 空頭爆倉對價格是多頭動力
                            'severity': 'warning' if value < 2000000 else 'critical',
                            'price_at_signal': float(price),
                            'message': f"Large Liquidation: ${value/1e6:.2f}M {side} liquidated on {symbol}",
                            'metadata': {'value_usd': float(value), 'side': side}
                        })
        except Exception as e:
            logger.error(f"Error scanning liquidations: {e}")
        return signals

    def _scan_cvd_divergence_mtf(self, symbols: List[str], timeframe: str) -> List[Dict]:
        """
        掃描 CVD 背離 (支援 MTF)
        """
        signals = []
        lookback = {
            '1m': '2 hours',
            '15m': '24 hours',
            '1h': '72 hours'
        }.get(timeframe, '2 hours')

        try:
            with self.loader.get_connection() as conn:
                with conn.cursor() as cur:
                    for symbol in symbols:
                        query = f"""
                            WITH raw_data AS (
                                SELECT
                                    o.time,
                                    o.high as price_high,
                                    o.low as price_low,
                                    cvd.volume_delta
                                FROM ohlcv o
                                JOIN market_cvd_1m cvd ON o.time = cvd.bucket AND o.market_id = cvd.market_id
                                JOIN markets m ON o.market_id = m.id
                                JOIN exchanges e ON m.exchange_id = e.id
                                WHERE m.symbol = %s AND e.name = 'bybit'
                                  AND o.time > NOW() - INTERVAL '{lookback}'
                                  AND o.timeframe = '{timeframe}'
                                ORDER BY o.time ASC
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
                        cur.execute(query, (symbol,))
                        rows = cur.fetchall()
                        
                        if not rows or len(rows) < 20: continue

                        mid = len(rows) // 2
                        p1, p2 = rows[:mid], rows[mid:]
                        
                        # 熊背離 (Bearish Divergence)
                        h1 = max(p1, key=lambda x: x[1])
                        h2 = max(p2, key=lambda x: x[1])
                        if h2[1] > h1[1] * 1.002 and h2[3] < h1[3]:
                            signals.append({
                                'time': h2[0], 'symbol': symbol,
                                'signal_type': f'cvd_divergence_{timeframe}',
                                'side': 'bearish', 'severity': 'warning',
                                'price_at_signal': float(h2[1]),
                                'message': f"[{timeframe}] Bearish Divergence: Price HH, CVD LH",
                                'metadata': {'p1_price': float(h1[1]), 'p2_price': float(h2[1]), 'p1_cvd': float(h1[3]), 'p2_cvd': float(h2[3])}
                            })

                        # 牛背離 (Bullish Divergence)
                        l1 = min(p1, key=lambda x: x[2])
                        l2 = min(p2, key=lambda x: x[2])
                        if l2[2] < l1[2] * 0.998 and l2[3] > l1[3]:
                            signals.append({
                                'time': l2[0], 'symbol': symbol,
                                'signal_type': f'cvd_divergence_{timeframe}',
                                'side': 'bullish', 'severity': 'warning',
                                'price_at_signal': float(l2[2]),
                                'message': f"[{timeframe}] Bullish Divergence: Price LL, CVD HL",
                                'metadata': {'p1_price': float(l1[2]), 'p2_price': float(l2[2]), 'p1_cvd': float(l1[3]), 'p2_cvd': float(l2[3])}
                            })
        except Exception as e:
            logger.error(f"Error scanning CVD divergence ({timeframe}): {e}")
        return signals

    def _scan_funding_rates(self) -> List[Dict]:
        """
        掃描極端資金費率
        """
        signals = []
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
                        ORDER BY m.symbol, mm.time DESC
                    """)
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
