#!/usr/bin/env python3
"""
BTC 地址分層追蹤 - 資料收集排程器

定期從免費資料源收集 BTC 地址分層資料並寫入資料庫
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from connectors.free_address_tier_collector import FreeAddressTierCollector
from loaders.address_tier_loader import AddressTierLoader


async def collect_and_store_data(
    collector: FreeAddressTierCollector,
    loader: AddressTierLoader,
    blockchain: str = 'BTC'
):
    """
    收集並儲存地址分層資料
    
    Args:
        collector: Glassnode 收集器
        loader: 資料載入器
        blockchain: 區塊鏈名稱
    """
    logger.info("=" * 80)
    logger.info(f"開始收集 {blockchain} 地址分層資料")
    logger.info(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        # 1. 收集最新資料
        logger.info("\n[步驟 1] 收集最新地址分層分布...")
        latest_data = await collector.collect_all_tiers()
        
        if not latest_data:
            logger.warning("⚠️  未收集到任何資料")
            return
        
        logger.success(f"✅ 成功收集 {len(latest_data)} 個分層的資料")
        
        # 2. 準備寫入資料庫的資料
        logger.info("\n[步驟 2] 準備資料...")
        snapshots = []
        snapshot_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 取得前一天資料以計算變動
        previous_snapshots = {}
        for tier_name in latest_data.keys():
            prev_snap = await loader.get_previous_snapshot(
                blockchain_name=blockchain,
                tier_name=tier_name,
                before_date=snapshot_date
            )
            if prev_snap:
                previous_snapshots[tier_name] = prev_snap
        
        # 組織資料
        for tier_name, data in latest_data.items():
            # 計算 24h 變動
            balance_change_24h = None
            if tier_name in previous_snapshots:
                prev_balance = previous_snapshots[tier_name]['total_balance']
                balance_change_24h = data['estimated_balance'] - prev_balance
            
            snapshots.append({
                'tier_name': tier_name,
                'snapshot_date': snapshot_date,  # 使用標準化的日期（00:00:00）
                'address_count': data['address_count'],
                'total_balance': data['estimated_balance'],
                'balance_change_24h': balance_change_24h,
                'metadata': {
                    'source': data.get('data_source', 'unknown'),
                    'data_quality': data.get('data_quality', 'unknown'),
                    'collected_at': datetime.now().isoformat(),
                    'original_timestamp': data['timestamp'].isoformat()  # 保留原始時間戳供追蹤
                }
            })
            
            # 顯示資訊
            change_str = ""
            if balance_change_24h:
                sign = "+" if balance_change_24h > 0 else ""
                change_str = f" (24h: {sign}{balance_change_24h:,.0f} BTC)"
            
            logger.info(
                f"  {tier_name:10s}: "
                f"{data['estimated_balance']:>15,.2f} BTC | "
                f"{data['address_count']:>12,} addresses"
                f"{change_str}"
            )
        
        # 3. 寫入資料庫
        logger.info("\n[步驟 3] 寫入資料庫...")
        success_count = await loader.insert_snapshots_batch(blockchain, snapshots)
        
        if success_count == len(snapshots):
            logger.success(f"✅ 成功寫入 {success_count}/{len(snapshots)} 筆資料")
        else:
            logger.warning(f"⚠️  部分寫入成功: {success_count}/{len(snapshots)}")
        
        # 4. 更新百分比統計
        logger.info("\n[步驟 4] 更新統計資訊...")
        await loader.update_percentages(blockchain, snapshot_date)
        logger.success("✅ 統計資訊已更新")
        
        logger.info("\n" + "=" * 80)
        logger.success(f"✅ {blockchain} 地址分層資料收集完成！")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"❌ 收集失敗: {e}")
        raise


async def main():
    """主程式"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 資料庫配置
    db_config = {
        'host': os.getenv('DB_HOST') or os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT') or os.getenv('POSTGRES_PORT', 5432)),
        'user': os.getenv('DB_USER') or os.getenv('POSTGRES_USER', 'crypto'),
        'password': os.getenv('DB_PASSWORD') or os.getenv('POSTGRES_PASSWORD', ''),
        'database': os.getenv('DB_NAME') or os.getenv('POSTGRES_DB', 'crypto_db'),
    }
    
    # 建立收集器與載入器（使用免費資料源）
    collector = FreeAddressTierCollector()
    loader = AddressTierLoader(db_config)
    
    try:
        await loader.connect()
        
        # 執行收集
        await collect_and_store_data(collector, loader, blockchain='BTC')
    
    except Exception as e:
        logger.error(f"❌ 執行失敗: {e}")
        raise
    
    finally:
        await collector.close()
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main())
