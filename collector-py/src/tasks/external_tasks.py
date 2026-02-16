"""
外部數據任務模組
負責 BitInfoCharts 富豪榜、CoinMarketCal 事件數據、Fear & Greed Index
"""
import os
from datetime import datetime, timezone
from loguru import logger
from connectors.coinmarketcal_collector import run_coinmarketcal_collection

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


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


def _latest_btc_etf_et_date(orchestrator):
    """查詢目前 DB 中 BTC ETF 的最新美東交易日"""
    try:
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX((time AT TIME ZONE 'America/New_York')::date)
                    FROM global_indicators
                    WHERE category = 'etf'
                      AND metadata->>'asset_type' = 'BTC'
                """)
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        logger.error(f"Failed to query latest ETF ET date: {e}")
        return None


def _today_et_date():
    et_tz = ZoneInfo("America/New_York") if ZoneInfo else timezone.utc
    return datetime.now(et_tz).date()

def _btc_etf_total_history_days(orchestrator) -> int:
    """查詢目前 DB 中 BTC ETF(TOTAL) 有多少個 distinct 美東交易日（用於判斷是否需要一次性回填）"""
    try:
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(DISTINCT (time AT TIME ZONE 'America/New_York')::date)
                    FROM global_indicators
                    WHERE category = 'etf'
                      AND name = 'TOTAL'
                      AND metadata->>'asset_type' = 'BTC'
                """)
                row = cur.fetchone()
                return int(row[0] or 0) if row else 0
    except Exception as e:
        logger.warning(f"Failed to query BTC ETF history days: {e}")
        return 0

def _has_btc_etf_products_for_et_date(orchestrator, target_et_date) -> bool:
    """檢查指定美東交易日是否已有單檔 ETF 資料（用於避免重複呼叫 API）"""
    try:
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 1
                    FROM global_indicators
                    WHERE category='etf'
                      AND metadata->>'asset_type'='BTC'
                      AND name <> 'TOTAL'
                      AND (time AT TIME ZONE 'America/New_York')::date = %s
                    LIMIT 1
                    """,
                    (target_et_date,),
                )
                return cur.fetchone() is not None
    except Exception as e:
        logger.warning(f"Failed to query ETF products existence: {e}")
        return False


def run_etf_flows_task(orchestrator):
    """ETF 資金流向收集任務（盤後窗口每小時輪詢，當日成功後跳過）"""
    etf_source = (os.getenv("ETF_SOURCE", "sosovalue") or "sosovalue").lower()
    today_et = _today_et_date()
    count_total = 0
    count_products = 0
    error_message = None
    try:
        latest_et_date = _latest_btc_etf_et_date(orchestrator)
        if latest_et_date is not None and latest_et_date >= today_et:
            logger.info(
                f"ETF already up-to-date for ET date {latest_et_date}, skip collection"
            )
            # 若之前只寫入 TOTAL 而缺少單檔資料，這裡補抓一次（避免 dashboard issuer 圖表空白）
            if etf_source != "farside" and getattr(orchestrator, "etf_products_collector", None):
                try:
                    if not _has_btc_etf_products_for_et_date(orchestrator, today_et):
                        cnt = orchestrator.etf_products_collector.run_collection(orchestrator.db, days=1)
                        if int(cnt or 0) > 0:
                            logger.success(f"Collected {int(cnt or 0)} ETF product metrics records")
                except Exception as e:
                    logger.warning(f"ETF product metrics collection failed: {e}")
            run_etf_freshness_task(orchestrator)
            return

        # 控制 SoSoValue 免費版呼叫頻率：失敗時不要在窗口內一直燒配額
        # 預設每天最多嘗試 3 次（可用 ETF_SOSO_MAX_ATTEMPTS_PER_DAY 調整）
        max_attempts = int(os.getenv("ETF_SOSO_MAX_ATTEMPTS_PER_DAY", "3"))
        if etf_source != "farside" and max_attempts > 0:
            try:
                with orchestrator.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT COUNT(*)
                            FROM system_logs
                            WHERE module='collector'
                              AND level='ETF_FLOWS_FETCH'
                              AND (time AT TIME ZONE 'America/New_York')::date = %s
                              AND metadata->>'source' = 'sosovalue'
                            """,
                            (today_et,),
                        )
                        attempts = int(cur.fetchone()[0] or 0)
                        if attempts >= max_attempts:
                            logger.warning(
                                f"SoSoValue ETF fetch attempts reached {attempts}/{max_attempts} for ET date {today_et}, skip"
                            )
                            return
            except Exception as e:
                logger.warning(f"Failed to check SoSoValue daily attempts: {e}")

        # --- 一次性回填：DB 目前 ETF 歷史天數不足時，首次寫入完整 ~300 天（不增加 API 呼叫次數）---
        lookback_days = int(os.getenv("ETF_COLLECTION_LOOKBACK_DAYS", "7"))
        if etf_source != "farside":
            min_days = int(os.getenv("ETF_SOSO_BACKFILL_MIN_DAYS", "60"))
            backfill_days = int(os.getenv("ETF_SOSO_BACKFILL_DAYS", "300"))
            hist_days = _btc_etf_total_history_days(orchestrator)
            if hist_days < min_days:
                effective_days = max(lookback_days, backfill_days)
                logger.warning(
                    f"BTC ETF history days={hist_days} < {min_days}; enable one-time backfill (lookback_days={effective_days})"
                )
                lookback_days = effective_days

        count = orchestrator.etf_flows_collector.run_collection(orchestrator.db, days=lookback_days)
        count_total = int(count or 0)
        if count_total > 0:
            logger.success(f"Collected {count_total} ETF flows records")
        else:
            logger.warning("ETF flow collection returned 0 records")

        # 單檔 ETF metrics：只在 SoSoValue source 且該 ET 交易日尚未入庫時抓取
        if etf_source != "farside" and getattr(orchestrator, "etf_products_collector", None):
            try:
                if not _has_btc_etf_products_for_et_date(orchestrator, today_et):
                    cnt = orchestrator.etf_products_collector.run_collection(orchestrator.db, days=1)
                    count_products = int(cnt or 0)
                    if count_products > 0:
                        logger.success(f"Collected {count_products} ETF product metrics records")
                    else:
                        logger.warning("ETF product metrics collection returned 0 records")
            except Exception as e:
                logger.warning(f"ETF product metrics collection failed: {e}")

        # 記錄未知產品代碼（若有）
        unknown = orchestrator.etf_flows_collector.get_last_unknown_codes()
        for asset, codes in unknown.items():
            for code in codes:
                orchestrator.metrics.record_etf_unknown_product(asset=asset, product_code=code)

        # 更新新鮮度指標
        run_etf_freshness_task(orchestrator)
    except Exception as e:
        error_message = str(e)
        logger.error(f"ETF flows collection failed: {e}")
    finally:
        # 記錄抓取品質到 system_logs（用於監控與配額稽核）
        # 注意：即使失敗也要記錄，才能讓「每日最大嘗試次數」有效，避免在窗口內一直重試燒配額。
        try:
            meta = {
                "source": "sosovalue" if etf_source != "farside" else "farside",
                "asset_type": "BTC",
                "rows_inserted_total": int(count_total or 0),
                "rows_inserted_products": int(count_products or 0),
                "rows_inserted": int((count_total or 0) + (count_products or 0)),
            }
            if error_message:
                meta["error_message"] = error_message
            fp = getattr(orchestrator.etf_flows_collector, "last_schema_fingerprint", None)
            if fp:
                meta["schema_fingerprint"] = fp
            orchestrator.db.insert_system_log(
                module="collector",
                level="ETF_FLOWS_FETCH",
                message="ETF flows fetch completed" if not error_message else "ETF flows fetch failed",
                value=float((count_total or 0) + (count_products or 0)),
                metadata=meta,
            )
        except Exception:
            pass


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
        # rich list 是日更型資料：每天 00:15 跑一次，並將 time 對齊到 00:00
        # 若該時間點已入庫，直接跳過，避免無效抓取與反爬風險。
        timestamp = datetime.now().replace(minute=0, second=0, microsecond=0)
        started_at = datetime.now(timezone.utc)
        with orchestrator.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM blockchains WHERE name = 'BTC'")
                res = cur.fetchone()
                blockchain_id = res[0] if res else None
                if blockchain_id:
                    # 若已存在快照但內容明顯異常（例如 total_balance 總和過低），允許重抓覆寫修正。
                    cur.execute(
                        """
                        SELECT
                          COUNT(*) AS cnt,
                          COALESCE(SUM(total_balance), 0) AS sum_balance
                        FROM address_tier_snapshots
                        WHERE blockchain_id = %s AND time = %s
                        """,
                        (blockchain_id, timestamp),
                    )
                    cnt, sum_balance = cur.fetchone()
                    if int(cnt or 0) > 0:
                        # 合理總量應接近 BTC circulating supply（~千萬級）。若低於 1,000,000 幾乎可判定為解析/欄位映射錯誤。
                        if float(sum_balance or 0) >= 1_000_000:
                            logger.info(f"Rich list already exists for {timestamp.isoformat()}, skip fetch")
                            return
                        logger.warning(
                            f"Rich list snapshot exists but looks invalid (cnt={cnt}, sum_balance={sum_balance}), refetch to repair"
                        )

        stats = orchestrator.rich_list_collector.fetch_distribution_data()
        if not stats:
            duration = (datetime.now(timezone.utc) - started_at).total_seconds()
            orchestrator.db.insert_system_log(
                module="collector",
                level="BITINFO_RICH_LIST",
                message="BitInfoCharts rich list fetch returned empty",
                value=0,
                metadata={
                    "source": "bitinfocharts",
                    "dataset": "btc_rich_list",
                    "timestamp": timestamp.isoformat(),
                    "duration_seconds": duration,
                    "fetch_method": getattr(orchestrator.rich_list_collector, "last_fetch_method", "unknown"),
                },
            )
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
                inserted_count = 0
                for row in stats:
                    # 使用 V3 Schema 表名: address_tier_snapshots, 欄位: time
                    cur.execute("""
                        INSERT INTO address_tier_snapshots
                        (time, blockchain_id, tier_name, address_count, total_balance)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (time, blockchain_id, tier_name) DO UPDATE
                        SET address_count = EXCLUDED.address_count,
                            total_balance = EXCLUDED.total_balance
                    """, (timestamp, blockchain_id, row['rank_group'], row['address_count'], row['total_balance']))
                    if cur.rowcount:
                        inserted_count += int(cur.rowcount)
                conn.commit()
            logger.success(f"Inserted rich list records for BTC into address_tier_snapshots")

        # --- 品質與來源 metadata 落庫（system_logs）---
        duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        fetch_method = getattr(orchestrator.rich_list_collector, "last_fetch_method", "unknown")
        source_last_updated = getattr(orchestrator.rich_list_collector, "last_source_last_updated", None)
        schema_fingerprint = getattr(orchestrator.rich_list_collector, "last_schema_fingerprint", None)
        columns = getattr(orchestrator.rich_list_collector, "last_columns", None)

        # 上一次 fingerprint（用於 schema change 偵測）
        prev_fp = None
        try:
            with orchestrator.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT metadata->>'schema_fingerprint'
                        FROM system_logs
                        WHERE module='collector'
                          AND level='BITINFO_RICH_LIST'
                          AND metadata->>'source'='bitinfocharts'
                          AND metadata->>'dataset'='btc_rich_list'
                          AND metadata ? 'schema_fingerprint'
                        ORDER BY time DESC
                        LIMIT 1
                        """
                    )
                    row = cur.fetchone()
                    prev_fp = row[0] if row else None
        except Exception as e:
            logger.warning(f"Failed to query previous BitInfoCharts schema fingerprint: {e}")

        schema_changed = bool(prev_fp and schema_fingerprint and prev_fp != schema_fingerprint)
        orchestrator.db.insert_system_log(
            module="collector",
            level="BITINFO_RICH_LIST",
            message="BitInfoCharts rich list fetch ok",
            value=float(inserted_count),
            metadata={
                "source": "bitinfocharts",
                "dataset": "btc_rich_list",
                "timestamp": timestamp.isoformat(),
                "duration_seconds": duration,
                "rows_parsed": len(stats),
                "rows_inserted": inserted_count,
                "fetch_method": fetch_method,
                "source_last_updated": source_last_updated,
                "schema_fingerprint": schema_fingerprint,
                "schema_changed": schema_changed,
                "prev_schema_fingerprint": prev_fp,
                "columns": columns,
            },
        )
        if schema_changed:
            logger.warning(
                f"BitInfoCharts schema fingerprint changed: prev={prev_fp}, current={schema_fingerprint}"
            )
    except Exception as e:
        logger.error(f"Rich list collection failed: {e}")
        try:
            orchestrator.db.insert_system_log(
                module="collector",
                level="BITINFO_RICH_LIST",
                message=f"BitInfoCharts rich list task failed: {e}",
                value=0,
                metadata={"source": "bitinfocharts", "dataset": "btc_rich_list"},
            )
        except Exception:
            pass


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
