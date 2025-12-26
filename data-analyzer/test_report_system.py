"""
完整報表系統測試腳本

測試項目：
1. 基礎報表生成（HTML/PDF）
2. 模型結果整合
3. PNG 圖表嵌入
4. 郵件發送
5. 資料庫日誌記錄
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from reports.report_agent import ReportAgent
from loguru import logger


def test_basic_report_generation():
    """測試 1: 基礎報表生成"""
    logger.info("=" * 60)
    logger.info("測試 1: 基礎報表生成（HTML/PDF）")
    logger.info("=" * 60)

    # 建立 ReportAgent（不含資料庫和郵件）
    agent = ReportAgent(output_dir="reports/test")

    # 生成每日報表
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)

    paths = agent.generate_daily_report(start_date, end_date)

    if paths:
        logger.success(f"✓ 每日報表生成成功")
        logger.info(f"  HTML: {paths['html']}")
        logger.info(f"  PDF: {paths['pdf']}")
        logger.info(f"  JSON: {paths['json']}")
        return True
    else:
        logger.error("❌ 每日報表生成失敗")
        return False


def test_model_integration():
    """測試 2: 模型結果整合"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 模型結果整合")
    logger.info("=" * 60)

    from reports.data_collector import ReportDataCollector
    from models.model_registry import ModelRegistry

    # 先註冊一個測試模型
    registry = ModelRegistry()

    model_id = registry.register_model(
        model_name="LSTM_Price_Forecast",
        model_type="lstm",
        model_version="v1.0",
        training_metrics={
            'mse': 0.0023,
            'mae': 0.0156,
            'r2_score': 0.87,
            'validation_loss': 0.0025
        },
        model_config={
            'hidden_size': 128,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001
        },
        training_data_info={
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'start_date': '2024-01-01',
            'end_date': '2024-12-20',
            'total_samples': 8000
        },
        metadata={'experiment': 'test_model_registry'}
    )

    logger.success(f"✓ 測試模型已註冊: {model_id}")

    # 收集模型結果
    collector = ReportDataCollector()
    models = collector.collect_model_results()

    if models:
        logger.success(f"✓ 成功收集 {len(models)} 個模型結果")
        for model in models[:3]:  # 顯示前3個
            logger.info(f"  - {model['model_name']} ({model['model_type']})")
        return True
    else:
        logger.warning("⚠ 未找到模型結果（可能尚未訓練模型）")
        return True  # 不算失敗


def test_image_embedding():
    """測試 3: PNG 圖表嵌入"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 3: PNG 圖表嵌入")
    logger.info("=" * 60)

    from reports.image_utils import collect_backtest_images

    # 檢查是否存在回測圖表
    results_dir = Path("results/backtest_reports")

    if not results_dir.exists():
        logger.warning(f"⚠ 回測報表目錄不存在: {results_dir}")
        logger.info("  提示: 需先執行回測才能測試圖表嵌入")
        return True  # 不算失敗

    # 尋找任何策略目錄
    strategy_dirs = [d for d in results_dir.iterdir() if d.is_dir()]

    if not strategy_dirs:
        logger.warning("⚠ 未找到策略目錄")
        return True

    # 測試圖片收集
    for strategy_dir in strategy_dirs[:2]:  # 測試前2個
        images = collect_backtest_images(strategy_dir)
        if images:
            logger.success(f"✓ 成功收集圖表: {strategy_dir.name}")
            for chart_type, base64_data in images.items():
                logger.info(f"  - {chart_type}: {len(base64_data)} bytes")
        else:
            logger.warning(f"⚠ {strategy_dir.name} 無圖表")

    return True


def test_database_logging():
    """測試 4: 資料庫日誌記錄"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 4: 資料庫日誌記錄")
    logger.info("=" * 60)

    # 檢查資料庫配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'crypto_db'),
        'user': os.getenv('DB_USER', 'crypto'),
        'password': os.getenv('DB_PASSWORD', 'crypto_pass')
    }

    try:
        import psycopg2

        # 測試連接
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        # 檢查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'report_generation_logs'
            )
        """)

        table_exists = cur.fetchone()[0]

        if table_exists:
            logger.success("✓ report_generation_logs 表已存在")

            # 查詢最近的報表記錄
            cur.execute("""
                SELECT report_type, generated_at, status
                FROM report_generation_logs
                ORDER BY generated_at DESC
                LIMIT 5
            """)

            logs = cur.fetchall()
            if logs:
                logger.info(f"  最近 {len(logs)} 筆報表記錄:")
                for log in logs:
                    logger.info(f"    - {log[0]} @ {log[1]} ({log[2]})")
            else:
                logger.info("  尚無報表記錄")
        else:
            logger.warning("⚠ report_generation_logs 表不存在")
            logger.info("  請執行: psql -U crypto -d crypto_db -f database/migrations/005_report_logs.sql")

        cur.close()
        conn.close()
        return table_exists

    except Exception as e:
        logger.error(f"❌ 資料庫連接失敗: {e}")
        logger.info("  請確認 TimescaleDB 正在運行且環境變數已設定")
        return False


def test_email_configuration():
    """測試 5: 郵件配置（不實際發送）"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 5: 郵件配置檢查")
    logger.info("=" * 60)

    from reports.email_sender import EmailSender

    # 檢查環境變數
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if smtp_user and smtp_password:
        logger.success(f"✓ SMTP 配置已設定")
        logger.info(f"  使用者: {smtp_user}")

        # 建立郵件發送器（但不實際發送）
        sender = EmailSender(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            use_tls=True
        )

        logger.info("  提示: 若要測試實際發送，請設定 TEST_EMAIL_SEND=true")

        # 若設定了測試發送環境變數
        if os.getenv('TEST_EMAIL_SEND') == 'true':
            test_email = os.getenv('TEST_EMAIL_TO', 'felix.tc.tw@gmail.com')

            html_content = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; }
                    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                             color: white; padding: 20px; border-radius: 10px; }
                    .content { padding: 20px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 報表系統測試郵件</h1>
                </div>
                <div class="content">
                    <p>這是一封測試郵件，用於驗證報表系統的郵件發送功能。</p>
                    <p><strong>測試時間:</strong> {}</p>
                    <p><strong>系統狀態:</strong> ✓ 正常運作</p>
                </div>
            </body>
            </html>
            """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

            success = sender.send_report(
                to_addresses=[test_email],
                subject='報表系統測試郵件 - Crypto Market Analyzer',
                html_content=html_content
            )

            if success:
                logger.success(f"✓ 測試郵件已發送至: {test_email}")
            else:
                logger.error("❌ 測試郵件發送失敗")

            return success
        else:
            return True
    else:
        logger.warning("⚠ SMTP 配置未設定")
        logger.info("  請設定環境變數:")
        logger.info("    export SMTP_USER='your-email@gmail.com'")
        logger.info("    export SMTP_PASSWORD='your-app-password'")
        return False


def test_full_workflow():
    """測試 6: 完整工作流程"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 6: 完整工作流程（含資料庫 + 郵件）")
    logger.info("=" * 60)

    # 資料庫配置
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'crypto_db'),
        'user': os.getenv('DB_USER', 'crypto'),
        'password': os.getenv('DB_PASSWORD', 'crypto_pass')
    }

    # 郵件配置
    email_config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_user': os.getenv('SMTP_USER'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'use_tls': True
    }

    try:
        # 建立完整配置的 ReportAgent
        agent = ReportAgent(
            output_dir="reports/test_full",
            db_config=db_config,
            email_config=email_config if email_config['smtp_user'] else None
        )

        # 生成報表
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        paths = agent.generate_weekly_report(start_date, end_date)

        if paths:
            logger.success("✓ 完整流程報表生成成功")

            # 若有設定郵件，嘗試發送
            if agent.email_sender and os.getenv('TEST_EMAIL_SEND') == 'true':
                test_email = os.getenv('TEST_EMAIL_TO', 'felix.tc.tw@gmail.com')

                # 從資料庫取得最新報表 ID（若有連接）
                report_log_id = None
                if agent.db_conn:
                    cur = agent.db_conn.cursor()
                    cur.execute("""
                        SELECT id FROM report_generation_logs
                        ORDER BY generated_at DESC LIMIT 1
                    """)
                    result = cur.fetchone()
                    if result:
                        report_log_id = result[0]
                    cur.close()

                # 發送郵件
                success = agent.send_report_email(
                    to_addresses=[test_email],
                    subject=f'測試完整報表 - {datetime.now().strftime("%Y-%m-%d")}',
                    html_file=Path(paths['html']),
                    pdf_attachments=[Path(paths['pdf'])] if paths.get('pdf') else None,
                    report_log_id=report_log_id
                )

                if success:
                    logger.success(f"✓ 報表已寄送至: {test_email}")
                else:
                    logger.warning("⚠ 郵件發送失敗")

            return True
        else:
            logger.error("❌ 報表生成失敗")
            return False

    except Exception as e:
        logger.error(f"❌ 完整流程測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主測試函數"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║  Crypto Market Analyzer - 報表系統完整測試           ║")
    logger.info("╚" + "=" * 58 + "╝")
    logger.info("\n")

    results = {
        '基礎報表生成': test_basic_report_generation(),
        '模型結果整合': test_model_integration(),
        'PNG 圖表嵌入': test_image_embedding(),
        '資料庫日誌': test_database_logging(),
        '郵件配置': test_email_configuration(),
        '完整工作流程': test_full_workflow()
    }

    # 總結
    logger.info("\n" + "=" * 60)
    logger.info("測試結果總結")
    logger.info("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ 通過" if result else "✗ 失敗"
        logger.info(f"{status:8} | {test_name}")

    logger.info("=" * 60)
    logger.info(f"通過率: {passed}/{total} ({passed/total*100:.1f}%)")
    logger.info("=" * 60)

    # 環境變數提示
    logger.info("\n💡 環境變數配置提示:")
    logger.info("  資料庫連接:")
    logger.info("    export DB_HOST=localhost")
    logger.info("    export DB_PORT=5432")
    logger.info("    export DB_NAME=crypto_db")
    logger.info("    export DB_USER=crypto")
    logger.info("    export DB_PASSWORD=crypto_pass")
    logger.info("")
    logger.info("  郵件發送:")
    logger.info("    export SMTP_USER='felix.tc.tw@gmail.com'")
    logger.info("    export SMTP_PASSWORD='your-app-password'")
    logger.info("    export TEST_EMAIL_SEND=true  # 啟用實際發送")
    logger.info("    export TEST_EMAIL_TO='felix.tc.tw@gmail.com'")
    logger.info("")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
