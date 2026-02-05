import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from loguru import logger

# 加入 src 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from connectors.bybit_rest import BybitClient
from loaders.db_loader import DatabaseLoader

async def backfill_trades(symbol: str, hours: int = 24):
    """
    回填歷史成交數據 (Tick Data)
    主要用於修復 CVD 漂移與提供高精度回測
    """
    logger.info(f"🚀 Starting trades backfill for {symbol} (Last {hours} hours)")
    
    db = DatabaseLoader()
    client = BybitClient()
    market_id = db.get_market_id('bybit', symbol)
    
    ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}:USDT" if "USDT" in symbol else symbol
    
    try:
        # 獲取最近成交 (Bybit V5 限制通常為 1000 筆)
        trades = client.fetch_trades(ccxt_symbol, limit=1000)
        
        if not trades:
            logger.warning(f"No trades found for {symbol}")
            return

        formatted_trades = []
        for t in trades:
            formatted_trades.append({
                'id': t['id'],
                'timestamp': t['timestamp'],
                'price': float(t['price']),
                'amount': float(t['amount']),
                'side': t['side']
            })
            
        count = db.insert_trades_batch(market_id, formatted_trades)
        logger.success(f"✅ Successfully backfilled {count} trades for {symbol}")
        
        # 觸發 TimescaleDB 的連續聚合刷新 (CVD 重建)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CALL refresh_continuous_aggregate('market_cvd_1m', NULL, NULL);")
                logger.info("🔄 Triggered CVD continuous aggregate refresh")
                
    except Exception as e:
        logger.error(f"❌ Failed to backfill trades: {e}")

if __name__ == "__main__":
    symbols = ['BTCUSDT', 'ETHUSDT']
    for s in symbols:
        asyncio.run(backfill_trades(s))
