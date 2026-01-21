import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from loguru import logger
from datetime import datetime, timezone
from connectors.open_interest_collector import OpenInterestCollector
from loaders.db_loader import DatabaseLoader

def backfill_oi():
    db = DatabaseLoader()
    collector = OpenInterestCollector(exchange_name='bybit')
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
    
    try:
        for symbol in symbols:
            logger.info(f"Backfilling OI history for {symbol}...")
            # 抓取 5m 粒度的歷史 OI (100筆)
            history = collector.fetch_open_interest_history(symbol, timeframe='5m', limit=100)
            
            market_id = db.get_market_id('bybit', symbol)
            if not market_id:
                logger.warning(f"Market not found for {symbol}")
                continue
                
            count = 0
            for record in history:
                db.insert_open_interest(market_id, record)
                count += 1
            
            logger.success(f"Backfilled {count} OI records for {symbol}")
            
    except Exception as e:
        logger.error(f"OI Backfill failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_oi()
