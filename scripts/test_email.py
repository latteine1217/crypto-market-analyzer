#!/usr/bin/env python3
"""
郵件功能測試腳本

測試報表系統的郵件發送功能
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'data-analyzer' / 'src'))

from reports.email_sender import EmailSender
from loguru import logger


def test_smtp_connection():
    """測試 SMTP 連接"""
    logger.info("=" * 60)
    logger.info("測試 1: SMTP 連接測試")
    logger.info("=" * 60)

    # 從環境變數讀取配置
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM', smtp_user)
    smtp_to = os.getenv('SMTP_TO', smtp_user)  # 預設發給自己

    # 檢查配置
    if not smtp_user or not smtp_password:
        logger.error("❌ SMTP 配置不完整")
        logger.error(f"   SMTP_USER: {'✓' if smtp_user else '✗ 未設定'}")
        logger.error(f"   SMTP_PASSWORD: {'✓' if smtp_password else '✗ 未設定'}")
        logger.error(f"   SMTP_FROM: {smtp_from or '✗ 未設定'}")
        logger.error(f"   SMTP_TO: {smtp_to or '✗ 未設定'}")
        return False

    logger.info(f"✓ SMTP_USER: {smtp_user}")
    logger.info(f"✓ SMTP_FROM: {smtp_from}")
    logger.info(f"✓ SMTP_TO: {smtp_to}")
    logger.info(f"✓ SMTP_PASSWORD: {'*' * len(smtp_password)} (已設定)")

    # 建立郵件發送器
    sender = EmailSender(
        smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        smtp_port=int(os.getenv('SMTP_PORT', 587)),
        smtp_user=smtp_user,
        smtp_password=smtp_password
    )

    # 建立測試郵件內容
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 5px; }}
            .content {{ margin-top: 20px; padding: 20px; background: #f5f5f5; border-radius: 5px; }}
            .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
            .success {{ color: #28a745; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📧 Crypto Market Analyzer</h1>
            <h2>郵件功能測試</h2>
        </div>

        <div class="content">
            <p class="success">✅ 郵件系統配置成功！</p>

            <h3>測試資訊：</h3>
            <ul>
                <li><strong>測試時間：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                <li><strong>SMTP 伺服器：</strong>{os.getenv('SMTP_HOST', 'smtp.gmail.com')}</li>
                <li><strong>寄件人：</strong>{smtp_from}</li>
                <li><strong>收件人：</strong>{smtp_to}</li>
            </ul>

            <h3>系統狀態：</h3>
            <ul>
                <li>✅ SMTP 連接正常</li>
                <li>✅ 郵件發送功能可用</li>
                <li>✅ HTML 格式支援正常</li>
            </ul>

            <p>接下來您可以：</p>
            <ol>
                <li>查看每日/每週報表排程狀態</li>
                <li>手動觸發報表生成並發送</li>
                <li>檢查報表生成日誌</li>
            </ol>
        </div>

        <div class="footer">
            <p>此郵件由 Crypto Market Analyzer 自動發送</p>
            <p>如有問題，請檢查系統日誌或聯繫管理員</p>
        </div>
    </body>
    </html>
    """

    # 發送測試郵件
    logger.info("\n發送測試郵件...")

    success = sender.send_report(
        to_addresses=[smtp_to],
        subject=f"📧 Crypto Market Analyzer - 郵件測試 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        html_content=html_content
    )

    if success:
        logger.success("\n✅ 測試郵件發送成功！")
        logger.info(f"   請檢查收件匣：{smtp_to}")
        logger.info("   如果沒收到，請檢查垃圾郵件資料夾")
        return True
    else:
        logger.error("\n❌ 測試郵件發送失敗")
        logger.error("   請檢查：")
        logger.error("   1. SMTP 帳號密碼是否正確")
        logger.error("   2. Gmail 兩步驟驗證是否已啟用")
        logger.error("   3. 應用程式專用密碼是否正確")
        logger.error("   4. 網路連線是否正常")
        return False


def test_with_attachment():
    """測試帶附件的郵件發送"""
    logger.info("\n" + "=" * 60)
    logger.info("測試 2: 附件發送測試（可選）")
    logger.info("=" * 60)

    # 檢查是否有現成的報表
    report_dir = Path(__file__).parent.parent / 'data-analyzer' / 'results'
    pdf_files = list(report_dir.glob('**/*.pdf'))

    if not pdf_files:
        logger.warning("⚠️  未找到 PDF 報表檔案，跳過附件測試")
        return True

    # 使用第一個找到的 PDF
    pdf_file = pdf_files[0]
    logger.info(f"使用測試附件：{pdf_file.name}")

    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_to = os.getenv('SMTP_TO', smtp_user)

    sender = EmailSender(
        smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
        smtp_port=int(os.getenv('SMTP_PORT', 587)),
        smtp_user=smtp_user,
        smtp_password=smtp_password
    )

    html_content = f"""
    <html>
    <body>
        <h2>📎 附件測試</h2>
        <p>此郵件包含一個 PDF 附件：<strong>{pdf_file.name}</strong></p>
        <p>請確認附件可以正常開啟。</p>
    </body>
    </html>
    """

    success = sender.send_report(
        to_addresses=[smtp_to],
        subject=f"📎 Crypto Market Analyzer - 附件測試 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        html_content=html_content,
        attachments=[pdf_file]
    )

    if success:
        logger.success("✅ 附件測試成功")
        return True
    else:
        logger.error("❌ 附件測試失敗")
        return False


def main():
    """主函數"""
    logger.info("\n" + "=" * 60)
    logger.info("Crypto Market Analyzer - 郵件功能測試")
    logger.info("=" * 60 + "\n")

    # 測試 1: 基本郵件發送
    if not test_smtp_connection():
        logger.error("\n基本郵件測試失敗，請檢查配置後重試")
        sys.exit(1)

    # 測試 2: 附件發送（可選）
    # test_with_attachment()

    logger.info("\n" + "=" * 60)
    logger.success("所有測試完成！")
    logger.info("=" * 60 + "\n")

    logger.info("下一步：")
    logger.info("1. 檢查郵件是否收到")
    logger.info("2. 啟動報表排程器（已在運行）")
    logger.info("3. 等待每日 08:00 或每週一 09:00 收到自動報表")
    logger.info("4. 或手動觸發報表生成：")
    logger.info("   python scripts/generate_daily_report.py")


if __name__ == "__main__":
    main()
