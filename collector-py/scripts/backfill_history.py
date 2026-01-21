import sys
import os
import time
from datetime import datetime, timedelta, timezone
import ccxt
from loguru import logger

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from loaders.db_loader import DatabaseLoader
from config import settings

# Setup Logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def get_start_time(days_ago: int) -> int:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return int(dt.timestamp() * 1000)

def backfill_symbol(db, exchange_name, market_id, symbol, timeframe, days):
    logger.info(f"Starting backfill for {symbol} {timeframe} ({days} days) on {exchange_name}...")
    
    # Use bybit for backfill
    exch = ccxt.bybit({
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    
    start_ts = get_start_time(days)
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    current_ts = start_ts
    
    total_inserted = 0
    
    while current_ts < now_ts:
        try:
            # CCXT handle symbol as BTCUSDT for Bybit
            candles = exch.fetch_ohlcv(symbol, timeframe, since=current_ts, limit=1000)
            if not candles:
                logger.info(f"No candles returned for {symbol} {timeframe} at {current_ts}")
                break
            
            # DatabaseLoader.insert_ohlcv_batch expects List[List] matching [ts, o, h, l, c, v]
            count = db.insert_ohlcv_batch(market_id, timeframe, candles)
            total_inserted += count
            
            last_ts = candles[-1][0]
            if last_ts <= current_ts:
                current_ts += 1000 * 60 * 60 # Advance 1h at least
            else:
                current_ts = last_ts + 1
            
            logger.info(f"[{symbol}] Inserted {len(candles)} candles. Progress: {datetime.fromtimestamp(current_ts/1000, tz=timezone.utc)}")
            
            if len(candles) < 200: # If returned less than a typical batch, we are close to now
                break
                
            time.sleep(exch.rateLimit / 1000)
            
        except Exception as e:
            logger.error(f"Error fetching/inserting: {e}")
            time.sleep(5)
            
    logger.success(f"Finished {symbol} {timeframe}. Total: {total_inserted}")

def main():
    try:
        db = DatabaseLoader()
        
        # Focus ONLY on Bybit now
        targets = [
            {'symbol': 'BTCUSDT', 'exchange': 'bybit'},
            {'symbol': 'ETHUSDT', 'exchange': 'bybit'}
        ]
        
        timeframes = [
            {'tf': '1d', 'days': 365},
            {'tf': '4h', 'days': 90},
            {'tf': '1h', 'days': 30},
            {'tf': '1m', 'days': 1} # Backfill 1 day of 1m data to avoid "not enough data" warnings
        ]
        
        for t in targets:
            # Get market_id from database
            market_id = db.get_market_id(t['exchange'], t['symbol'])
            if not market_id:
                logger.error(f"Market ID not found for {t['exchange']} {t['symbol']}")
                continue
                
            for tf_conf in timeframes:
                backfill_symbol(db, t['exchange'], market_id, t['symbol'], tf_conf['tf'], tf_conf['days'])
                
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    main()