"""
外部數據任務模組
負責 CryptoPanic 新聞、BitInfoCharts 富豪榜、FRED 經濟數據、CoinMarketCal 事件數據、Fear & Greed Index
"""
from datetime import datetime
from loguru import logger
from connectors.fred_calendar_collector import run_fred_calendar_collection
from connectors.coinmarketcal_collector import run_coinmarketcal_collection

def run_fear_greed_task(orchestrator):
    """Fear & Greed Index 收集任務（每 6 小時）"""
    try:
        count = orchestrator.fear_greed_collector.run_collection(
            orchestrator.db
        )
        if count > 0:
            logger.success(f"Collected {count} Fear & Greed Index records")
    except Exception as e:
        logger.error(f"Fear & Greed collection failed: {e}")

def run_fred_task(orchestrator):
    """FRED 經濟指標收集任務（每週一次）"""
    try:
        count = orchestrator.fred_collector.run_collection(
            orchestrator.db
        )
        if count > 0:
            logger.success(f"Collected {count} FRED indicator records")
    except Exception as e:
        logger.error(f"FRED collection failed: {e}")

def run_etf_flows_task(orchestrator):
    """ETF 資金流向收集任務（每日一次）"""
    try:
        count = orchestrator.etf_flows_collector.run_collection(
            orchestrator.db
        )
        if count > 0:
            logger.success(f"Collected {count} ETF flows records")
    except Exception as e:
        logger.error(f"ETF flows collection failed: {e}")

def run_news_task(orchestrator):
    """新聞收集任務"""
    try:
        count = orchestrator.news_collector.run_collection(orchestrator.db)
        if count > 0:
            logger.success(f"Collected {count} news items from CryptoPanic")
    except Exception as e:
        logger.error(f"News collection failed: {e}")

def run_rich_list_task(orchestrator):
    """鏈上富豪榜收集任務"""
    try:
        stats = orchestrator.rich_list_collector.fetch_distribution_data()
        if not stats:
            return

        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM blockchains WHERE name = 'BTC'")
                res = cur.fetchone()
                blockchain_id = res[0] if res else None
                if not blockchain_id:
                    cur.execute("INSERT INTO blockchains (name, native_token) VALUES ('BTC', 'BTC') RETURNING id")
                    blockchain_id = cur.fetchone()[0]

                timestamp = datetime.now()
                for row in stats:
                    # 使用 V3 Schema 表名: address_tier_snapshots, 欄位: time
                    cur.execute("""
                        INSERT INTO address_tier_snapshots 
                        (time, blockchain_id, tier_name, address_count, total_balance)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (time, blockchain_id, tier_name) DO NOTHING
                    """, (timestamp, blockchain_id, row['rank_group'], row['address_count'], row['total_balance']))
                conn.commit()
            logger.success(f"Inserted rich list records for BTC into address_tier_snapshots")
    except Exception as e:
        logger.error(f"Rich list collection failed: {e}")

def run_events_task(orchestrator):
    """經濟與加密事件收集任務（FRED Economic Data + CoinMarketCal）"""
    try:
        with orchestrator.db.get_connection() as conn:
            # 收集 FRED 經濟數據事件
            fred_count = run_fred_calendar_collection(conn, months_ahead=3)
            if fred_count > 0:
                logger.success(f"Collected {fred_count} FRED economic events")
            
            # 收集 CoinMarketCal 加密事件
            cmc_count = run_coinmarketcal_collection(conn)
            if cmc_count > 0:
                logger.success(f"Collected {cmc_count} crypto events from CoinMarketCal")
            
            total_count = (fred_count or 0) + (cmc_count or 0)
            if total_count > 0:
                logger.info(f"Total events collected: {total_count}")
    except Exception as e:
        logger.error(f"Events collection failed: {e}")
