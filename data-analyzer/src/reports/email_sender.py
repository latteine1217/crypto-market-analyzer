"""
Email Sender - 郵件發送模組

職責：
1. 發送 HTML 郵件
2. 支援附件（PDF 報表）
3. 支援批量發送
"""
from typing import List, Optional, Dict
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from loguru import logger


class EmailSender:
    """郵件發送器"""

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True
    ):
        """
        初始化郵件發送器

        Args:
            smtp_host: SMTP 伺服器地址
            smtp_port: SMTP 埠號
            smtp_user: SMTP 使用者名稱（郵箱地址）
            smtp_password: SMTP 密碼或應用專用密碼
            use_tls: 是否使用 TLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls

        logger.info(f"EmailSender 初始化：{smtp_host}:{smtp_port}")

    def send_report(
        self,
        to_addresses: List[str],
        subject: str,
        html_content: str,
        attachments: Optional[List[Path]] = None,
        cc_addresses: Optional[List[str]] = None
    ) -> bool:
        """
        發送報表郵件

        Args:
            to_addresses: 收件人列表
            subject: 郵件主旨
            html_content: HTML 內容
            attachments: 附件路徑列表
            cc_addresses: 副本收件人列表

        Returns:
            是否成功
        """
        if not self.smtp_user or not self.smtp_password:
            logger.error("SMTP 使用者名稱或密碼未設定")
            return False

        try:
            # 建立郵件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject

            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)

            # 添加 HTML 內容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # 添加附件
            if attachments:
                for attachment_path in attachments:
                    if not attachment_path.exists():
                        logger.warning(f"附件不存在：{attachment_path}")
                        continue

                    with open(attachment_path, 'rb') as f:
                        attach = MIMEApplication(f.read())
                        attach.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=attachment_path.name
                        )
                        msg.attach(attach)
                        logger.debug(f"✓ 添加附件：{attachment_path.name}")

            # 發送郵件
            all_recipients = to_addresses + (cc_addresses or [])

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, all_recipients, msg.as_string())

            logger.info(f"✓ 郵件已發送：{subject} → {', '.join(to_addresses)}")
            return True

        except Exception as e:
            logger.error(f"❌ 郵件發送失敗：{e}")
            import traceback
            traceback.print_exc()
            return False

    def send_report_from_files(
        self,
        to_addresses: List[str],
        subject: str,
        html_file: Path,
        pdf_attachments: Optional[List[Path]] = None
    ) -> bool:
        """
        從檔案讀取內容發送報表

        Args:
            to_addresses: 收件人列表
            subject: 郵件主旨
            html_file: HTML 檔案路徑
            pdf_attachments: PDF 附件列表

        Returns:
            是否成功
        """
        if not html_file.exists():
            logger.error(f"HTML 檔案不存在：{html_file}")
            return False

        # 讀取 HTML 內容
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        return self.send_report(
            to_addresses=to_addresses,
            subject=subject,
            html_content=html_content,
            attachments=pdf_attachments
        )

    @staticmethod
    def from_config(config: Dict) -> 'EmailSender':
        """
        從配置字典創建郵件發送器

        Args:
            config: 配置字典

        Returns:
            EmailSender 實例
        """
        return EmailSender(
            smtp_host=config.get('smtp_host', 'smtp.gmail.com'),
            smtp_port=config.get('smtp_port', 587),
            smtp_user=config.get('smtp_user'),
            smtp_password=config.get('smtp_password'),
            use_tls=config.get('use_tls', True)
        )


# 範例用法
if __name__ == "__main__":
    import os

    # 從環境變數讀取 SMTP 配置
    sender = EmailSender(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user=os.getenv('SMTP_USER', 'your-email@gmail.com'),
        smtp_password=os.getenv('SMTP_PASSWORD', 'your-app-password'),
        use_tls=True
    )

    # 測試發送郵件
    html_content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            h1 { color: #2E86AB; }
            .highlight { background: #f0f8ff; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>📊 Crypto Market Analyzer - Daily Report</h1>
        <div class="highlight">
            <p><strong>Report Date:</strong> 2024-12-26</p>
            <p><strong>Best Strategy:</strong> RSI (15.2% return)</p>
            <p><strong>Data Quality:</strong> 95.5/100</p>
        </div>
        <p>This is a test email from the Report Agent.</p>
    </body>
    </html>
    """

    success = sender.send_report(
        to_addresses=['felix.tc.tw@gmail.com'],
        subject='Test Report - Crypto Market Analyzer',
        html_content=html_content
    )

    if success:
        print("✓ 測試郵件發送成功")
    else:
        print("❌ 測試郵件發送失敗")
