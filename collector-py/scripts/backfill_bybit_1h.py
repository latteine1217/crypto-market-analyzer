"""
Bybit 歷史 1 小時 K 線回填腳本
用途：批次抓取 Bybit 過去一年的 1h OHLCV 資料
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta, timezone
from time import sleep
from loguru import logger

from connectors.bybit_rest import BybitClient
from loaders.db_loader import DatabaseLoader


def backfill_bybit_1h(symbol: str, days: int = 365):
    """
    回填 Bybit 1 小時 K 線資料

    Args:
        symbol: 交易對符號（如 "BTC/USDT"）
        days: 回填天數（預設 365 天）
    """
    logger.info("=" * 80)
    logger.info(f"🔄 開始回填 Bybit 歷史 1h K 線資料")
    logger.info(f"📊 交易對: {symbol}")
    logger.info(f"📅 回填天數: {days} 天")
    logger.info("=" * 80)

    # 初始化連接器和載入器
    client = BybitClient()
    loader = DatabaseLoader()

    # 取得 market_id
    try:
        market_id = loader.get_market_id('bybit', symbol)
        if not market_id:
            logger.error(f"❌ 無法取得或創建 market_id for {symbol}")
            return
        logger.info(f"✅ 使用 market_id: {market_id}")
    except Exception as e:
        logger.error(f"❌ 取得 market_id 失敗: {e}")
        return

    # 計算時間範圍
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    logger.info(f"📅 時間範圍: {start_date} ~ {end_date}")

    # Bybit API 限制：每次最多 1000 條
    # 1h K 線，1000 條 = 1000 小時 = 約 41.7 天
    batch_hours = 1000
    batch_days = batch_hours / 24  # 約 41.7 天

    total_batches = int(days / batch_days) + 1
    logger.info(f"📦 總批次數: {total_batches} (每批次 {batch_hours} 小時)")

    # 批次抓取
    total_inserted = 0
    failed_batches = []
    current_start = start_date

    for batch_num in range(1, total_batches + 1):
        try:
            # 計算本批次的結束時間
            current_end = min(
                current_start + timedelta(hours=batch_hours),
                end_date
            )

            # 如果已經超過結束時間，停止
            if current_start >= end_date:
                break

            since_ts = int(current_start.timestamp() * 1000)

            logger.info(
                f"[{batch_num}/{total_batches}] 📥 抓取 {current_start.strftime('%Y-%m-%d %H:%M')} "
                f"~ {current_end.strftime('%Y-%m-%d %H:%M')}"
            )

            # 抓取資料
            ohlcv_data = client.fetch_ohlcv(
                symbol=symbol,
                timeframe='1h',
                since=since_ts,
                limit=1000
            )

            if not ohlcv_data:
                logger.warning(f"⚠️  批次 {batch_num} 無資料")
                current_start = current_end
                continue

            # 寫入資料庫
            inserted = loader.insert_ohlcv_batch(
                market_id=market_id,
                timeframe='1h',
                ohlcv_data=ohlcv_data
            )

            total_inserted += inserted
            logger.success(
                f"✅ 批次 {batch_num} 完成，寫入 {inserted} 筆資料 "
                f"(累計: {total_inserted:,} 筆)"
            )

            # 移到下一個批次
            current_start = current_end

            # 延遲避免速率限制（Bybit rate limit: 20ms）
            if batch_num < total_batches:
                sleep(0.1)  # 100ms 延遲

        except Exception as e:
            logger.error(f"❌ 批次 {batch_num} 失敗: {e}")
            failed_batches.append((batch_num, current_start, str(e)))
            # 失敗後等待更久
            sleep(1)
            # 繼續下一個批次
            current_start = current_end

    # 總結報告
    logger.info("=" * 80)
    logger.info("🎉 回填完成！")
    logger.info(f"✅ 成功批次: {total_batches - len(failed_batches)}/{total_batches}")
    logger.info(f"📊 總寫入筆數: {total_inserted:,} 條")
    logger.info(f"📈 預期每交易對: ~{days * 24:,} 條 (完成度: {total_inserted / (days * 24) * 100:.1f}%)")

    if failed_batches:
        logger.warning(f"⚠️  失敗批次數: {len(failed_batches)}")
        for batch_num, start_time, error in failed_batches:
            logger.warning(f"  批次 {batch_num}: {start_time} - {error}")

    logger.info("=" * 80)


def main():
    """回填三個主要交易對"""
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    days = 365  # 一年

    logger.add(
        "logs/backfill_bybit_1h.log",
        rotation="100 MB",
        retention="10 days",
        level="INFO"
    )

    logger.info("🚀 開始回填 Bybit 過去一年的 1h K 線資料")
    logger.info(f"📊 交易對: {', '.join(symbols)}")
    logger.info(f"📅 天數: {days} 天")
    logger.info("")

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"處理第 {i}/{len(symbols)} 個交易對: {symbol}")
        logger.info(f"{'='*80}\n")

        try:
            backfill_bybit_1h(symbol, days)
        except KeyboardInterrupt:
            logger.warning("⚠️  用戶中斷回填程序")
            break
        except Exception as e:
            logger.error(f"❌ {symbol} 回填失敗: {e}")
            continue

        # 交易對之間稍微等待
        if i < len(symbols):
            logger.info("⏸️  等待 5 秒後處理下一個交易對...")
            sleep(5)

    logger.info("\n" + "="*80)
    logger.info("🏁 所有交易對回填完成！")
    logger.info("="*80)


if __name__ == "__main__":
    main()
