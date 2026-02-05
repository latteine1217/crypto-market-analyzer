import os
import sys
import asyncio
from datetime import datetime, timezone
from loguru import logger

# 加入 src 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from connectors.bybit_rest import BybitClient
from loaders.db_loader import DatabaseLoader
from config_loader import load_configs

async def calibrate_cvd():
    """
    CVD 校準任務
    抓取 24h Volume 作為真值錨點，解決 WebSocket 丟包導致的 CVD 漂移
    """
    logger.info("🚀 Starting CVD Calibration Task...")
    
    # 載入配置
    configs = load_configs()
    db = DatabaseLoader()
    client = BybitClient()
    
    # 獲取所有活躍市場
    markets = db.get_active_markets()
    
    for m in markets:
        market_id = m['id']
        symbol = m['symbol'] # 例如 BTCUSDT
        
        # 轉換為 CCXT 格式 (Bybit V5 Linear)
        ccxt_symbol = f"{symbol[:3]}/{symbol[3:]}:USDT" if "USDT" in symbol else symbol
        
        try:
            # 1. 獲取交易所 Ticker (真值)
            ticker = client.fetch_ticker(ccxt_symbol)
            exchange_vol_24h = float(ticker.get('baseVolume', 0))
            
            if exchange_vol_24h == 0:
                continue
                
            # 2. 獲取本地資料庫中 24h 的成交量總和
            query = """
                SELECT SUM(amount) 
                FROM trades 
                WHERE market_id = %s 
                AND time >= NOW() - INTERVAL '24 hours'
            """
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (market_id,))
                    local_vol_24h = float(cur.fetchone()[0] or 0)
            
            # 3. 計算差異 (Drift)
            drift_ratio = (local_vol_24h / exchange_vol_24h) if exchange_vol_24h > 0 else 1.0
            logger.info(f"📊 {symbol} | Exchange: {exchange_vol_24h:.2f} | Local: {local_vol_24h:.2f} | Drift: {(1-drift_ratio)*100:.2f}%")
            
            # 4. 寫入錨點表
            # anchor_type = 'volume_24h'
            # system_cvd = 當時本地 24h 累積的成交量
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO market_anchors (market_id, time, anchor_type, value, system_cvd)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (market_id, datetime.now(timezone.utc), 'volume_24h', exchange_vol_24h, local_vol_24h)
                    )
            
        except Exception as e:
            logger.error(f"❌ Failed to calibrate {symbol}: {e}")

    logger.info("✅ CVD Calibration Task Completed.")

if __name__ == "__main__":
    asyncio.run(calibrate_cvd())
