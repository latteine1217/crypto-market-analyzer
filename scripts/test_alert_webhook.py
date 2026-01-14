#!/usr/bin/env python3
"""
測試 Alert Webhook Handler 功能
包括：圖表生成、郵件發送
"""
import sys
import os
from pathlib import Path

# 添加路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "collector-py" / "src" / "monitors"))

from alert_chart_generator import AlertChartGenerator
from loguru import logger


def test_chart_generation():
    """測試圖表生成功能"""
    logger.info("=== Testing Chart Generation ===")
    
    # 從環境變數或使用預設值（與 docker-compose.yml 一致）
    db_conn_str = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'crypto_db')} "
        f"user={os.getenv('DB_USER', 'crypto')} "
        f"password={os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'crypto_pass'))}"
    )
    
    output_dir = Path("/tmp/alert_charts_test")
    generator = AlertChartGenerator(db_conn_str, output_dir)
    
    # 測試 1: 蠟燭圖（使用較長的回溯時間以包含歷史資料）
    logger.info("Test 1: Candlestick Chart")
    chart1 = generator.generate_candlestick_chart(
        symbol="BTCUSDT",
        exchange="bybit",
        timeframe="1h",
        hours_back=240,  # 10 天，確保包含歷史資料
        title="TEST: BTC/USDT 1H Candlestick",
        annotation="⚠️ TEST ALERT: Price dropped by 3.5% in 5 minutes"
    )
    
    if chart1 and chart1.exists():
        logger.success(f"✓ Candlestick chart generated: {chart1}")
        logger.info(f"  Size: {chart1.stat().st_size / 1024:.1f} KB")
    else:
        logger.error("✗ Failed to generate candlestick chart")
        return False
    
    # 測試 2: 價格對比圖（使用 1h 資料）
    logger.info("Test 2: Price Comparison Chart")
    chart2 = generator.generate_price_comparison_chart(
        symbol="BTCUSDT",
        exchange="bybit",
        hours_back=240,  # 10 天
        timeframe="1h",   # 使用 1h 資料
        title="TEST: BTC/USDT Price Movement",
        highlight_recent_hours=24  # 突出最近 24 小時
    )
    
    if chart2 and chart2.exists():
        logger.success(f"✓ Price comparison chart generated: {chart2}")
        logger.info(f"  Size: {chart2.stat().st_size / 1024:.1f} KB")
    else:
        logger.error("✗ Failed to generate price comparison chart")
        return False
    
    logger.success("✓ All chart generation tests passed")
    return True


def test_email_sending():
    """測試郵件發送功能（可選）"""
    logger.info("=== Testing Email Sending ===")
    
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials not set, skipping email test")
        logger.info("  Set SMTP_USER and SMTP_PASSWORD to enable email testing")
        return True
    
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "data-analyzer" / "src"))
        from reports.email_sender import EmailSender
        
        sender = EmailSender(
            smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', 587)),
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            use_tls=True
        )
        
        # 查找測試圖表
        chart_dir = Path("/tmp/alert_charts_test")
        charts = list(chart_dir.glob("*.png"))
        
        if not charts:
            logger.warning("No test charts found, generating...")
            test_chart_generation()
            charts = list(chart_dir.glob("*.png"))
        
        # 發送測試郵件
        html_content = """
        <html>
        <body>
            <h2>🔔 Alert Webhook Handler - Test Email</h2>
            <p>This is a test email from the Alert Webhook Handler.</p>
            <p><strong>Features tested:</strong></p>
            <ul>
                <li>✓ Chart generation (Candlestick & Price Comparison)</li>
                <li>✓ Email sending with attachments</li>
            </ul>
            <p><strong>Attachments:</strong> {count} chart(s)</p>
            <hr>
            <p style="font-size: 12px; color: #666;">
                Generated at: {time}
            </p>
        </body>
        </html>
        """.format(
            count=len(charts),
            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        success = sender.send_report(
            to_addresses=[smtp_user],
            subject="[TEST] Alert Webhook Handler - Chart Generation Test",
            html_content=html_content,
            attachments=charts[:2]  # 只附加前2個圖表
        )
        
        if success:
            logger.success(f"✓ Test email sent to {smtp_user}")
            return True
        else:
            logger.error("✗ Failed to send test email")
            return False
    
    except ImportError as e:
        logger.error(f"Failed to import EmailSender: {e}")
        return False
    except Exception as e:
        logger.error(f"Email test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_webhook_endpoint():
    """測試 Webhook 端點（可選）"""
    logger.info("=== Testing Webhook Endpoint ===")
    
    try:
        import requests
        
        # 測試 health 端點
        response = requests.get('http://localhost:9100/health', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            logger.success("✓ Webhook handler is healthy")
            logger.info(f"  Email configured: {data.get('email_configured')}")
            logger.info(f"  Chart dir: {data.get('chart_dir')}")
            logger.info(f"  Log dir: {data.get('log_dir')}")
            return True
        else:
            logger.error(f"✗ Health check failed: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        logger.warning("Webhook handler not running, skipping endpoint test")
        logger.info("  Start the handler with: ./scripts/start_alert_webhook.sh")
        return True
    except Exception as e:
        logger.error(f"Webhook test failed: {e}")
        return False


if __name__ == '__main__':
    from datetime import datetime
    
    logger.info("Starting Alert Webhook Handler Tests")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    results = []
    
    # 測試 1: 圖表生成
    results.append(("Chart Generation", test_chart_generation()))
    
    # 測試 2: 郵件發送（可選）
    if os.getenv('TEST_EMAIL_SEND') == 'true':
        results.append(("Email Sending", test_email_sending()))
    else:
        logger.info("=== Skipping Email Test ===")
        logger.info("  Set TEST_EMAIL_SEND=true to enable email testing")
    
    # 測試 3: Webhook 端點（可選）
    results.append(("Webhook Endpoint", test_webhook_endpoint()))
    
    # 總結
    logger.info("=" * 60)
    logger.info("Test Summary:")
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        logger.success("\n✓ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n✗ Some tests failed")
        sys.exit(1)
