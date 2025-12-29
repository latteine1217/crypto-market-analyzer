"""
Binance / OKX 歷史 1 小時 K 線回填腳本
用途：使用舊的 Binance / OKX 連接器批次抓取過去一年 1h OHLCV

使用範例：
    python scripts/backfill_binance_okx_1h.py --exchanges binance,okx --symbols BTC/USDT ETH/USDT --days 365
    python scripts/backfill_binance_okx_1h.py --exchanges binance --symbols BTCUSDT --days 365
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Dict, Iterable, List
from loguru import logger

from connectors.binance_rest import BinanceRESTConnector
from connectors.okx_rest import OKXRESTConnector
from loaders.db_loader import DatabaseLoader


EXCHANGE_LIMITS = {
    "binance": 1000,
    "okx": 100,
}

EXCHANGE_DELAYS = {
    "binance": 0.2,
    "okx": 0.4,
}


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to ccxt format (e.g., BTCUSDT -> BTC/USDT)."""
    symbol = symbol.strip().upper()
    if "/" in symbol:
        return symbol
    if symbol.endswith("USDT") and len(symbol) > 4:
        return f"{symbol[:-4]}/USDT"
    return symbol


def init_connector(exchange_name: str):
    if exchange_name == "binance":
        return BinanceRESTConnector(enable_rate_limit=True, timeout=30)
    if exchange_name == "okx":
        return OKXRESTConnector(enable_rate_limit=True, timeout=30)
    raise ValueError(f"Unsupported exchange: {exchange_name}")


def backfill_exchange_1h(
    exchange_name: str,
    symbols: Iterable[str],
    days: int,
    batch_delay: float
):
    logger.info("=" * 80)
    logger.info(f"Start backfill 1h OHLCV: exchange={exchange_name}, days={days}")
    logger.info("=" * 80)

    connector = init_connector(exchange_name)
    loader = DatabaseLoader()
    limit = EXCHANGE_LIMITS[exchange_name]

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    for symbol in symbols:
        ccxt_symbol = normalize_symbol(symbol)
        logger.info("-" * 80)
        logger.info(f"Symbol: {ccxt_symbol}")

        try:
            market_id = loader.get_market_id(exchange_name, ccxt_symbol)
        except Exception as e:
            logger.error(f"Failed to get market_id for {exchange_name}/{ccxt_symbol}: {e}")
            continue

        if not market_id:
            logger.error(f"Missing market_id for {exchange_name}/{ccxt_symbol}")
            continue

        total_inserted = 0
        failed_batches: List[str] = []
        current_start = start_date

        while current_start < end_date:
            since_ts = int(current_start.timestamp() * 1000)
            try:
                logger.info(
                    f"Fetch {ccxt_symbol} from {current_start.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(limit={limit})"
                )

                ohlcv_data = connector.fetch_ohlcv(
                    symbol=ccxt_symbol,
                    timeframe="1h",
                    since=since_ts,
                    limit=limit
                )

                if not ohlcv_data:
                    logger.warning("Empty batch, advance window")
                    current_start = current_start + timedelta(hours=limit)
                    sleep(batch_delay)
                    continue

                # Filter by end_date to avoid overshooting
                end_ts = int(end_date.timestamp() * 1000)
                filtered = [row for row in ohlcv_data if row[0] < end_ts]

                if not filtered:
                    logger.info("No rows within range, stop for this symbol")
                    break

                inserted = loader.insert_ohlcv_batch(
                    market_id=market_id,
                    timeframe="1h",
                    ohlcv_data=filtered
                )
                total_inserted += inserted
                logger.info(f"Inserted {inserted} rows (total={total_inserted})")

                last_ts = filtered[-1][0]
                if last_ts <= since_ts:
                    logger.warning("Last timestamp did not advance; stop to avoid loop")
                    break

                current_start = datetime.fromtimestamp(
                    last_ts / 1000,
                    tz=timezone.utc
                ) + timedelta(hours=1)

                if current_start >= end_date:
                    break

                sleep(batch_delay)

            except Exception as e:
                logger.error(f"Batch failed: {e}")
                failed_batches.append(str(current_start))
                sleep(batch_delay * 3)
                current_start = current_start + timedelta(hours=limit)

        expected = days * 24
        completion = (total_inserted / expected * 100) if expected else 0
        logger.info(
            f"Done {ccxt_symbol}: inserted={total_inserted}, "
            f"expected~{expected}, completion={completion:.1f}%"
        )
        if failed_batches:
            logger.warning(f"Failed batches: {len(failed_batches)}")

    logger.info("=" * 80)


def parse_exchanges(raw: str) -> List[str]:
    exchanges = [item.strip().lower() for item in raw.split(",") if item.strip()]
    for exchange in exchanges:
        if exchange not in EXCHANGE_LIMITS:
            raise ValueError(f"Unsupported exchange: {exchange}")
    return exchanges


def main():
    parser = argparse.ArgumentParser(description="Backfill Binance/OKX 1h OHLCV")
    parser.add_argument(
        "--exchanges",
        type=str,
        default="binance,okx",
        help="Comma-separated exchanges: binance,okx"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        help="Symbols in ccxt format (e.g., BTC/USDT) or compact (e.g., BTCUSDT)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Backfill days (default: 365)"
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=None,
        help="Override batch delay seconds (default uses per-exchange delay)"
    )

    args = parser.parse_args()
    exchanges = parse_exchanges(args.exchanges)

    logger.add(
        "logs/backfill_binance_okx_1h.log",
        rotation="100 MB",
        retention="10 days",
        level="INFO"
    )

    for exchange_name in exchanges:
        delay = args.batch_delay
        if delay is None:
            delay = EXCHANGE_DELAYS[exchange_name]

        backfill_exchange_1h(
            exchange_name=exchange_name,
            symbols=args.symbols,
            days=args.days,
            batch_delay=delay
        )


if __name__ == "__main__":
    main()
