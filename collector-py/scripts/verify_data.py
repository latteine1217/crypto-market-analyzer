"""
驗證區塊鏈資料是否正確載入
"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import sys

# 載入環境變數
load_dotenv(Path(__file__).parent.parent / '.env')


async def verify_data():
    """驗證資料"""
    logger.info("=" * 60)
    logger.info("驗證區塊鏈資料")
    logger.info("=" * 60)

    # 資料庫配置
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass'),
        'database': os.getenv('POSTGRES_DB', 'crypto_db')
    }

    try:
        conn = await asyncpg.connect(**db_config)

        # 查詢每個區塊鏈的交易數量
        logger.info("\n各區塊鏈交易數量:")
        stats = await conn.fetch("""
            SELECT
                b.name,
                b.full_name,
                COUNT(wt.time) as tx_count,
                MIN(wt.time) as earliest_tx,
                MAX(wt.time) as latest_tx
            FROM blockchains b
            LEFT JOIN whale_transactions wt ON b.id = wt.blockchain_id
            GROUP BY b.id, b.name, b.full_name
            ORDER BY b.id
        """)

        for row in stats:
            if row['tx_count'] > 0:
                logger.success(
                    f"  {row['name']} ({row['full_name']}): {row['tx_count']} 筆交易 "
                    f"({row['earliest_tx']} ~ {row['latest_tx']})"
                )
            else:
                logger.info(f"  {row['name']} ({row['full_name']}): 無資料")

        # 查詢 Ethereum 交易詳情
        eth_txs = await conn.fetch("""
            SELECT
                tx_hash,
                time as tx_timestamp,
                from_addr as from_address,
                to_addr as to_address,
                amount_usd,
                asset as token_symbol
            FROM whale_transactions
            WHERE blockchain_id = (SELECT id FROM blockchains WHERE name = 'ETH')
            ORDER BY time DESC
            LIMIT 10
        """)

        if eth_txs:
            logger.info(f"\n最新 {len(eth_txs)} 筆 Ethereum 交易:")
            for i, tx in enumerate(eth_txs, 1):
                logger.info(f"\n  [{i}] 交易哈希: {tx['tx_hash'][:20]}...")
                logger.info(f"      時間: {tx['tx_timestamp']}")
                logger.info(f"      從: {tx['from_address'][:20]}...")
                logger.info(f"      到: {tx['to_address'][:20]}...")
                if tx['amount_usd']:
                    logger.info(f"      美元: ${tx['amount_usd']:,.2f}")
                logger.info(f"      幣種: {tx['token_symbol']}")

        # 統計資訊
        logger.info("\n" + "=" * 60)
        logger.info("資料庫統計")
        logger.info("=" * 60)

        total_txs = await conn.fetchval("SELECT COUNT(*) FROM whale_transactions")
        
        logger.info(f"總交易數: {total_txs}")

        await conn.close()

        logger.info("\n" + "=" * 60)
        logger.success("資料驗證完成！")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"驗證失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 配置 logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = asyncio.run(verify_data())
    sys.exit(0 if success else 1)
