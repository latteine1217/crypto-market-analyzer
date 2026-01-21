import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from loguru import logger
from connectors.open_interest_collector import OpenInterestCollector
from loaders.db_loader import DatabaseLoader

def backfill_oi_deep():
    db = DatabaseLoader()
    collector = OpenInterestCollector(exchange_name='bybit')
    # 5m 是 Bybit 歷史 API 通常支援的最小週期，1000 筆可覆蓋 ~3.5 天
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
    
    try:
        for symbol in symbols:
            logger.info(f"Deep Backfilling OI for {symbol}...")
            history = collector.fetch_open_interest_history(symbol, timeframe='5m', limit=1000)
            
            market_id = db.get_market_id('bybit', symbol)
            if not market_id: continue
                
            count = 0
            for record in history:
                db.insert_open_interest(market_id, record)
                count += 1
            logger.success(f"Deep Backfilled {count} OI records for {symbol}")
    except Exception as e:
        logger.error(f"Deep Backfill failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_oi_deep()
