#!/usr/bin/env python3
"""
每日報表生成腳本

用途：定期（cron/scheduler）自動生成日報
"""
import sys
from pathlib import Path
from datetime import datetime

# 加入專案路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "data-analyzer" / "src"))

from reports import ReportAgent
from loguru import logger


def main():
    """生成每日報表"""
    logger.info("=" * 60)
    logger.info("開始生成每日報表")
    logger.info(f"時間：{datetime.now()}")
    logger.info("=" * 60)

    try:
        # 初始化 Report Agent
        agent = ReportAgent(
            output_dir=str(project_root / "reports"),
            db_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'crypto_market',
                'user': 'postgres',
                'password': ''  # 應從環境變數讀取
            }
        )

        # 生成日報
        result = agent.generate_comprehensive_report(
            report_type='daily',
            markets=['BTC/USDT', 'ETH/USDT'],
            strategies=['RSI', 'MA_Cross', 'BuyAndHold'],
            formats=['html', 'pdf']  # 同時生成 HTML 和 PDF
        )

        logger.info("\n✅ 每日報表生成成功！")
        logger.info(f"報表期間：{result['period']['start']} ~ {result['period']['end']}")
        logger.info(f"資料品質記錄：{result['statistics']['quality_records']}")
        logger.info(f"回測策略數：{result['statistics']['strategies']}")

        logger.info("\n生成的檔案：")
        for format_type, path in result['output_paths'].items():
            logger.info(f"  {format_type}: {path}")

        agent.close()

        logger.info("\n" + "=" * 60)
        logger.info("每日報表生成流程完成")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"❌ 報表生成失敗：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
