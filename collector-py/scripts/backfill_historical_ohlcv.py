"""
歷史 OHLCV 資料回填腳本
用途：批次抓取指定時間範圍的歷史 K 線資料

使用範例：
    python scripts/backfill_historical_ohlcv.py --symbol BTCUSDT --timeframe 1m --days 90
    python scripts/backfill_historical_ohlcv.py --symbol ETHUSDT --timeframe 1h --days 365
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import List, Tuple
from loguru import logger

from connectors.binance_rest import BinanceRESTConnector
from loaders.db_loader import DatabaseLoader


def calculate_time_ranges(
    start_date: datetime,
    end_date: datetime,
    batch_size: int = 1000,
    timeframe: str = "1m"
) -> List[Tuple[int, int]]:
    """
    計算需要抓取的時間範圍切片

    Args:
        start_date: 開始時間
        end_date: 結束時間
        batch_size: 每批次筆數（Binance 限制 1000）
        timeframe: K 線週期

    Returns:
        [(start_ts_ms, end_ts_ms), ...]
    """
    # 時間週期對應的毫秒數
    timeframe_ms = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }

    if timeframe not in timeframe_ms:
        raise ValueError(f"不支援的時間週期: {timeframe}")

    interval_ms = timeframe_ms[timeframe]
    batch_duration_ms = batch_size * interval_ms

    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)

    ranges = []
    current_start = start_ts

    while current_start < end_ts:
        current_end = min(current_start + batch_duration_ms, end_ts)
        ranges.append((current_start, current_end))
        current_start = current_end

    return ranges


def backfill_ohlcv(
    symbol: str,
    timeframe: str,
    days: int,
    batch_delay: float = 0.5
):
    """
    回填歷史 OHLCV 資料

    Args:
        symbol: 交易對符號（如 "BTCUSDT"）
        timeframe: K 線週期（如 "1m"）
        days: 回填天數
        batch_delay: 批次間延遲（秒），避免觸發速率限制
    """
    logger.info("=" * 60)
    logger.info(f"開始回填歷史資料")
    logger.info(f"交易對: {symbol}")
    logger.info(f"週期: {timeframe}")
    logger.info(f"回填天數: {days}")
    logger.info("=" * 60)

    # 初始化連接器和載入器
    connector = BinanceRESTConnector(enable_rate_limit=True, timeout=30)
    loader = DatabaseLoader()

    # 計算時間範圍
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # ccxt 格式的 symbol（如 "BTC/USDT"）
    ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}" if len(symbol) > 3 else symbol

    # 取得 market_id（使用 loader 的方法）
    try:
        market_id = loader.get_market_id('binance', ccxt_symbol)
        if not market_id:
            logger.error(f"無法取得或創建 market_id for {ccxt_symbol}")
            raise ValueError(f"Market {ccxt_symbol} 不存在且無法創建")

        logger.info(f"使用 market_id: {market_id}")

    except Exception as e:
        logger.error(f"取得 market_id 失敗: {e}")
        raise

    # 計算需要抓取的時間範圍
    time_ranges = calculate_time_ranges(start_date, end_date, 1000, timeframe)
    total_batches = len(time_ranges)

    logger.info(f"總共需要抓取 {total_batches} 個批次")
    logger.info(f"時間範圍: {start_date} 至 {end_date}")

    # 批次抓取
    total_inserted = 0
    failed_batches = []

    for i, (start_ts, end_ts) in enumerate(time_ranges, 1):
        try:
            logger.info(f"[{i}/{total_batches}] 抓取 {datetime.fromtimestamp(start_ts/1000, tz=timezone.utc)} ...")

            # 抓取資料
            ohlcv_data = connector.fetch_ohlcv(
                symbol=ccxt_symbol,
                timeframe=timeframe,
                since=start_ts,
                limit=1000
            )

            if not ohlcv_data:
                logger.warning(f"批次 {i} 無資料")
                continue

            # 寫入資料庫
            inserted = loader.insert_ohlcv_batch(
                market_id=market_id,
                timeframe=timeframe,
                ohlcv_data=ohlcv_data
            )

            total_inserted += inserted
            logger.info(f"✓ 批次 {i} 完成，寫入 {inserted} 筆資料（累計: {total_inserted}）")

            # 延遲避免速率限制
            if i < total_batches:
                sleep(batch_delay)

        except Exception as e:
            logger.error(f"✗ 批次 {i} 失敗: {e}")
            failed_batches.append((i, start_ts, end_ts, str(e)))
            # 失敗後等待更久
            sleep(batch_delay * 3)

    # 總結報告
    logger.info("=" * 60)
    logger.info("回填完成")
    logger.info(f"成功批次: {total_batches - len(failed_batches)}/{total_batches}")
    logger.info(f"總寫入筆數: {total_inserted}")

    if failed_batches:
        logger.warning(f"失敗批次數: {len(failed_batches)}")
        for batch_num, start_ts, end_ts, error in failed_batches:
            logger.warning(
                f"  批次 {batch_num}: "
                f"{datetime.fromtimestamp(start_ts/1000, tz=timezone.utc)} - {error}"
            )

    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="回填歷史 OHLCV 資料")
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="交易對符號（如 BTCUSDT）"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1m",
        choices=["1m", "5m", "15m", "1h", "4h", "1d"],
        help="K 線週期"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="回填天數（預設 90 天）"
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=0.5,
        help="批次間延遲秒數（預設 0.5 秒）"
    )

    args = parser.parse_args()

    try:
        backfill_ohlcv(
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            batch_delay=args.batch_delay
        )
    except KeyboardInterrupt:
        logger.warning("用戶中斷回填程序")
    except Exception as e:
        logger.error(f"回填失敗: {e}")
        raise


if __name__ == "__main__":
    main()
