import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

# 加入 src 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from connectors.bybit_rest import BybitClient
from loaders.db_loader import DatabaseLoader

async def backfill_liquidations(symbol: str, days: int = 7):
    """
    回填歷史爆倉數據 (Bybit V5)
    """
    logger.info(f"🚀 Starting liquidation backfill for {symbol} (Last {days} days)")
    
    db = DatabaseLoader()
    client = BybitClient()
    
    # 轉換符號
    ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}:USDT" if "USDT" in symbol else symbol
    
    try:
        # Bybit V5 fetch_liquidations 範例 (CCXT 支援)
        # 注意：並非所有交易所都提供長期的歷史爆倉 REST 接口
        # Bybit 通常提供最近 50-100 筆或最近幾小時的
        
        liquidations = client.exchange.fetch_liquidations(ccxt_symbol)
        if not liquidations:
            logger.warning(f"No historical liquidations found for {symbol} via REST API")
            return

        formatted_liqs = []
        for liq in liquidations:
            formatted_liqs.append({
                'time': datetime.fromtimestamp(liq['timestamp'] / 1000, tz=timezone.utc),
                'exchange': 'bybit',
                'symbol': symbol,
                'side': liq['side'], # 'buy' or 'sell'
                'price': liq['price'],
                'quantity': liq['amount'],
                'value_usd': liq['price'] * liq['amount']
            })
            
        count = db.insert_liquidations_batch(formatted_liqs)
        logger.success(f"✅ Successfully backfilled {count} liquidations for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Failed to backfill liquidations: {e}")

if __name__ == "__main__":
    # 預設回填熱門幣種
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    for s in symbols:
        asyncio.run(backfill_liquidations(s))
