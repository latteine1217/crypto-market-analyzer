"""
使用 Python 初始化區塊鏈巨鯨追蹤資料庫
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


async def init_database():
    """初始化資料庫"""
    logger.info("=" * 60)
    logger.info("初始化區塊鏈巨鯨追蹤資料庫")
    logger.info("=" * 60)

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

        # 讀取並執行 schema 文件
        schema_files = [
            'database/schemas/01_init.sql',
            'database/schemas/02_blockchain_whale_tracking.sql'
        ]

        for schema_file in schema_files:
            schema_path = Path(__file__).parent.parent / schema_file

            if not schema_path.exists():
                logger.error(f"✗ 找不到 schema 文件: {schema_file}")
                continue

            logger.info(f"\n執行 {schema_file}...")

            with open(schema_path, 'r', encoding='utf-8') as f:
                sql = f.read()

            try:
                await conn.execute(sql)
                logger.success(f"✓ {schema_file} 執行成功")
            except Exception as e:
                logger.error(f"✗ {schema_file} 執行失敗: {e}")

        # 顯示統計資訊
        logger.info("\n" + "=" * 60)
        logger.info("資料庫統計")
        logger.info("=" * 60)

        # 表格列表
        tables = await conn.fetch("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)

        logger.info("\n表格列表:")
        for row in tables:
            logger.info(f"  {row['tablename']}: {row['size']}")

        # 區塊鏈列表
        blockchains = await conn.fetch("""
            SELECT id, name, full_name, native_token, is_active
            FROM blockchains
            ORDER BY id
        """)

        logger.info("\n區塊鏈列表:")
        for row in blockchains:
            status = "✓" if row['is_active'] else "✗"
            logger.info(f"  {status} [{row['id']}] {row['name']} ({row['full_name']}) - {row['native_token']}")

        # 關閉連線
        await conn.close()

        logger.info("\n" + "=" * 60)
        logger.success("資料庫初始化完成!")
        logger.info("=" * 60)
        logger.info("\n準備開始收集區塊鏈資料!")
        logger.info("執行測試: cd collector-py && python3 test_blockchain_etl.py")

        return True

    except Exception as e:
        logger.error(f"✗ 資料庫初始化失敗: {e}")
        return False


if __name__ == '__main__':
    # 配置 logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
