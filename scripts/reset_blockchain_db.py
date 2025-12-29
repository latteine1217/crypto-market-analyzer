"""
重置區塊鏈巨鯨追蹤資料庫（刪除舊表並重建）
"""
import asyncio
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import sys

# 載入環境變數
load_dotenv(Path(__file__).parent.parent / 'collector-py' / '.env')


async def reset_database():
    """重置資料庫"""
    logger.warning("=" * 60)
    logger.warning("警告：即將刪除所有區塊鏈追蹤資料表！")
    logger.warning("=" * 60)

    # 資料庫配置
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass'),
        'database': os.getenv('POSTGRES_DB', 'crypto_db')
    }

    logger.info(f"連接到資料庫: {db_config['host']}:{db_config['port']}/{db_config['database']}")

    try:
        # 建立連線
        conn = await asyncpg.connect(**db_config)
        logger.success("✓ 資料庫連接成功")

        # 刪除舊表（按依賴順序）
        logger.info("\n刪除舊表...")
        drop_tables = [
            "DROP TABLE IF EXISTS whale_transactions CASCADE;",
            "DROP TABLE IF EXISTS whale_addresses CASCADE;",
            "DROP TABLE IF EXISTS tracked_tokens CASCADE;",
            "DROP TABLE IF EXISTS blockchains CASCADE;",
        ]

        for drop_sql in drop_tables:
            try:
                await conn.execute(drop_sql)
                table_name = drop_sql.split()[4]
                logger.info(f"  ✓ 刪除 {table_name}")
            except Exception as e:
                logger.warning(f"  ⚠ {drop_sql}: {e}")

        # 刪除函數
        logger.info("\n刪除舊函數...")
        drop_functions = [
            "DROP FUNCTION IF EXISTS get_latest_whale_tx_time CASCADE;",
            "DROP FUNCTION IF EXISTS get_exchange_flow_stats CASCADE;",
            "DROP FUNCTION IF EXISTS get_anomaly_transactions CASCADE;",
            "DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;",
        ]

        for drop_sql in drop_functions:
            try:
                await conn.execute(drop_sql)
                logger.info(f"  ✓ {drop_sql}")
            except Exception as e:
                logger.warning(f"  ⚠ {drop_sql}: {e}")

        logger.success("\n✓ 清理完成！")

        # 執行新的 schema
        logger.info("\n執行新 schema...")
        schema_file = Path(__file__).parent.parent / 'database/schemas/02_blockchain_whale_tracking.sql'

        with open(schema_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        try:
            await conn.execute(sql)
            logger.success("✓ Schema 執行成功")
        except Exception as e:
            logger.error(f"✗ Schema 執行失敗: {e}")
            raise

        # 驗證表格
        logger.info("\n" + "=" * 60)
        logger.info("驗證新表格")
        logger.info("=" * 60)

        # 檢查表格
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename IN ('blockchains', 'whale_addresses', 'whale_transactions', 'tracked_tokens')
            ORDER BY tablename
        """)

        logger.info("\n區塊鏈追蹤表格:")
        for row in tables:
            logger.success(f"  ✓ {row['tablename']}")

        # 檢查 whale_transactions 欄位
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'whale_transactions'
            ORDER BY ordinal_position
        """)

        logger.info("\nwhale_transactions 欄位:")
        for row in columns:
            logger.info(f"  - {row['column_name']}: {row['data_type']}")

        # 區塊鏈列表
        blockchains = await conn.fetch("""
            SELECT id, name, full_name, native_token
            FROM blockchains
            ORDER BY id
        """)

        logger.info("\n區塊鏈列表:")
        for row in blockchains:
            logger.success(f"  ✓ [{row['id']}] {row['name']} ({row['full_name']}) - {row['native_token']}")

        # 關閉連線
        await conn.close()

        logger.info("\n" + "=" * 60)
        logger.success("資料庫重置完成！")
        logger.info("=" * 60)
        logger.info("\n準備執行測試:")
        logger.info("cd collector-py && python3 test_blockchain_etl.py")

        return True

    except Exception as e:
        logger.error(f"✗ 資料庫重置失敗: {e}")
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

    success = asyncio.run(reset_database())
    sys.exit(0 if success else 1)
