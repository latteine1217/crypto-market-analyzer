"""
外部數據任務模組
負責 BitInfoCharts 富豪榜、CoinMarketCal 事件數據、Fear & Greed Index
"""
from datetime import datetime, timezone
from loguru import logger
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

def run_etf_flows_task(orchestrator):
    """ETF 資金流向收集任務（每日一次）"""
    try:
        count = orchestrator.etf_flows_collector.run_collection(
            orchestrator.db
        )
        if count > 0:
            logger.success(f"Collected {count} ETF flows records")
        # 記錄未知產品代碼（若有）
        unknown = orchestrator.etf_flows_collector.get_last_unknown_codes()
        for asset, codes in unknown.items():
            for code in codes:
                orchestrator.metrics.record_etf_unknown_product(asset=asset, product_code=code)

        # 更新新鮮度指標
        run_etf_freshness_task(orchestrator)
    except Exception as e:
        logger.error(f"ETF flows collection failed: {e}")

def run_etf_freshness_task(orchestrator):
    """ETF 資料新鮮度檢查（Prometheus 指標）"""
    try:
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT metadata->>'asset_type' AS asset_type, MAX(time) AS latest_time
                    FROM global_indicators
                    WHERE category = 'etf'
                      AND metadata->>'asset_type' IS NOT NULL
                    GROUP BY asset_type
                """)
                rows = cur.fetchall()

        if not rows:
            logger.warning("No ETF data found for freshness check")
            return

        now = datetime.now(timezone.utc)
        for asset_type, latest_time in rows:
            if not latest_time:
                continue
            age_seconds = (now - latest_time).total_seconds()
            orchestrator.metrics.update_etf_latest_timestamp(asset=asset_type, timestamp=latest_time.timestamp())
            orchestrator.metrics.update_etf_staleness_seconds(asset=asset_type, seconds=age_seconds)

            if age_seconds > 36 * 3600:
                logger.warning(
                    f"ETF data stale for {asset_type}: last update {latest_time.isoformat()} ({age_seconds/3600:.1f}h ago)"
                )
    except Exception as e:
        logger.error(f"ETF freshness check failed: {e}")
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

                # 將時間戳對齊到小時，避免重複數據並方便時序分析
                timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)
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

def run_whale_task(orchestrator):
    """鏈上大額轉帳 (Whale Transactions) 收集任務"""
    try:
        count = orchestrator.whale_collector.run_collection(orchestrator.db)
        if count > 0:
            logger.success(f"Collected {count} whale transactions from BTC Mempool")
    except Exception as e:
        logger.error(f"Whale collection failed: {e}")

def run_events_task(orchestrator):
    """經濟與加密事件收集任務（CoinMarketCal）"""
    try:
        with orchestrator.db.get_connection() as conn:
            # 收集 CoinMarketCal 加密事件
            cmc_count = run_coinmarketcal_collection(conn)
            if cmc_count > 0:
                logger.success(f"Collected {cmc_count} crypto events from CoinMarketCal")
    except Exception as e:
        logger.error(f"Events collection failed: {e}")
