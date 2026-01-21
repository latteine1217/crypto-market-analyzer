import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from loguru import logger
from datetime import datetime, timezone
from connectors.funding_rate_collector import FundingRateCollector
from loaders.db_loader import DatabaseLoader

def backfill_funding():
    db = DatabaseLoader()
    collector = FundingRateCollector(exchange_name='bybit')
    
    # 取得 Bybit 活躍合約市場
    try:
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
        
        for symbol in symbols:
            logger.info(f"Backfilling funding history for {symbol}...")
            # 抓取歷史資金費率
            history = collector.fetch_funding_rate_history(symbol, limit=100)
            
            market_id = db.get_market_id('bybit', symbol)
            if not market_id:
                logger.warning(f"Market not found for {symbol}")
                continue
                
            count = 0
            for record in history:
                db.insert_funding_rate(market_id, record)
                count += 1
            
            logger.success(f"Backfilled {count} records for {symbol}")
            
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill_funding()