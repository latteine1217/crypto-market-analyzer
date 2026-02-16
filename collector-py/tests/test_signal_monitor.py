"""
SignalMonitor 單元測試
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from monitors.signal_monitor import SignalMonitor


def test_map_liquidation_impact_side():
    monitor = SignalMonitor.__new__(SignalMonitor)

    assert monitor._map_liquidation_impact_side("buy") == "bullish"
    assert monitor._map_liquidation_impact_side("short") == "bullish"
    assert monitor._map_liquidation_impact_side("sell") == "bearish"
    assert monitor._map_liquidation_impact_side("long") == "bearish"
    assert monitor._map_liquidation_impact_side("unknown") == "neutral"


def test_scan_oi_spikes_unpack_row_shape():
    monitor = SignalMonitor.__new__(SignalMonitor)
    monitor.THRESHOLDS = {'oi_spike_pct': 0.05}

    now = datetime.now(timezone.utc)
    rows = [
        ("BTCUSDT", 120.0, 100.0, now, now - timedelta(hours=1)),
    ]

    mock_cur = MagicMock()
    mock_cur.fetchall.return_value = rows

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_loader = MagicMock()
    mock_loader.get_connection.return_value.__enter__.return_value = mock_conn

    monitor.loader = mock_loader

    signals = monitor._scan_oi_spikes(["BTCUSDT"])

    assert len(signals) == 1
    assert signals[0]["symbol"] == "BTCUSDT"
    assert signals[0]["signal_type"] == "oi_spike"
    assert signals[0]["time"] == now


def test_get_cvd_timeframes_default_and_override():
    monitor = SignalMonitor.__new__(SignalMonitor)
    monitor.TIMEFRAME_CONFIG = {
        '5m': {},
        '1h': {},
        '4h': {},
        '1d': {},
    }

    with patch.dict('os.environ', {}, clear=False):
        assert monitor._get_cvd_timeframes() == ['5m', '1h', '4h', '1d']

    with patch.dict('os.environ', {'SIGNAL_TIMEFRAMES': '5m,1h,4h,1d'}, clear=False):
        assert monitor._get_cvd_timeframes() == ['5m', '1h', '4h', '1d']

    with patch.dict('os.environ', {'SIGNAL_TIMEFRAMES': '5m,invalid,1h'}, clear=False):
        assert monitor._get_cvd_timeframes() == ['5m', '1h']


@pytest.mark.parametrize(
    "native_count,fallback_count,expected",
    [
        (40, 0, '1h'),
        (0, 50, '1m'),
        (0, 0, ''),
    ],
)
def test_resolve_ohlcv_source_timeframe(native_count, fallback_count, expected):
    monitor = SignalMonitor.__new__(SignalMonitor)

    cur = MagicMock()
    cur.fetchone.side_effect = [(native_count,), (fallback_count,)]

    source = monitor._resolve_ohlcv_source_timeframe(
        cur=cur,
        symbol='BTCUSDT',
        timeframe='1h',
        lookback='21 days',
        interval_literal='1 hour',
        min_points=30
    )

    assert source == expected
