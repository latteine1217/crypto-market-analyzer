"""
測試 Order Book 收集功能
"""
import sys
from pathlib import Path

# 添加 src 到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from loguru import logger
from config import settings
from connectors.binance_rest import BinanceRESTConnector
from loaders.db_loader import DatabaseLoader

# 配置日誌
logger.remove()
logger.add(
    sys.stdout,
    level='INFO',
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)


def test_orderbook_collection():
    """測試訂單簿收集"""
    logger.info("=" * 80)
    logger.info("開始測試 Order Book 收集功能")
    logger.info("=" * 80)

    # 初始化
    db = DatabaseLoader()
    connector = BinanceRESTConnector(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_api_secret
    )

    # 測試參數
    exchange_name = 'binance'
    symbol = 'BTC/USDT'
    limit = 10

    try:
        # 1. 取得 market_id
        logger.info(f"Step 1: 取得 market_id for {exchange_name}/{symbol}")
        market_id = db.get_market_id(exchange_name, symbol)
        logger.info(f"Market ID: {market_id}")

        # 2. 抓取 Order Book
        logger.info(f"Step 2: 抓取 Order Book (limit={limit})")
        orderbook = connector.fetch_order_book(symbol=symbol, limit=limit)

        logger.info(f"Order Book 資料:")
        logger.info(f"  - Timestamp: {orderbook.get('timestamp')}")
        logger.info(f"  - Bids 數量: {len(orderbook['bids'])}")
        logger.info(f"  - Asks 數量: {len(orderbook['asks'])}")
        logger.info(f"  - Best Bid: {orderbook['bids'][0] if orderbook['bids'] else 'N/A'}")
        logger.info(f"  - Best Ask: {orderbook['asks'][0] if orderbook['asks'] else 'N/A'}")

        # 3. 準備資料格式
        from datetime import datetime
        orderbook_data = [{
            'timestamp': orderbook.get('timestamp', int(datetime.now().timestamp() * 1000)),
            'bids': orderbook['bids'],
            'asks': orderbook['asks']
        }]

        # 4. 寫入資料庫
        logger.info("Step 3: 寫入資料庫")
        count = db.insert_orderbook_batch(market_id, orderbook_data)
        logger.success(f"成功寫入 {count} 筆 Order Book 快照")

        # 5. 驗證寫入
        logger.info("Step 4: 驗證資料庫寫入")
        import psycopg2
        with db.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    timestamp,
                    jsonb_array_length(bids) as bids_count,
                    jsonb_array_length(asks) as asks_count,
                    bids->0->>0 as best_bid_price,
                    asks->0->>0 as best_ask_price
                FROM orderbook_snapshots
                WHERE market_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (market_id,))

            row = cur.fetchone()
            if row:
                ts, bids_count, asks_count, best_bid, best_ask = row
                logger.success("資料庫驗證成功！")
                logger.info(f"  - Timestamp: {ts}")
                logger.info(f"  - Bids: {bids_count} 檔")
                logger.info(f"  - Asks: {asks_count} 檔")
                logger.info(f"  - Best Bid: {best_bid}")
                logger.info(f"  - Best Ask: {best_ask}")
            else:
                logger.error("資料庫中沒有找到資料！")

    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

    logger.info("=" * 80)
    logger.info("測試完成")
    logger.info("=" * 80)


if __name__ == '__main__':
    test_orderbook_collection()
