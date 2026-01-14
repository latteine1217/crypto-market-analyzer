#!/usr/bin/env python3
"""
報表排程服務

功能：
1. 每日報表：每日 08:00 (台北時間) 生成
2. 每週報表：每週一 09:00 (台北時間) 生成
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import pytz

# 加入專案路徑
# 在 Docker 容器中，/workspace 就是 data-analyzer 目錄
# /workspace/scripts 是 scripts 目錄（掛載為 ro）
# /workspace/reports 掛載到專案 reports 目錄
# 因此 src 目錄在 /workspace/src
workspace_path = Path("/workspace/src") if Path("/workspace/src").exists() else Path(__file__).parent.parent / "data-analyzer" / "src"
sys.path.insert(0, str(workspace_path))

# 設定專案根目錄（在容器中為 /workspace）
project_root = Path("/workspace") if Path("/workspace/src").exists() else Path(__file__).parent.parent

from reports import ReportAgent


class ReportScheduler:
    """報表排程服務"""

    def __init__(self):
        """初始化排程器"""
        self.tz = pytz.timezone(os.getenv('TZ', 'Asia/Taipei'))
        self.misfire_grace_seconds = int(os.getenv('REPORT_MISFIRE_GRACE_SECONDS', 604800))
        self.scheduler = BlockingScheduler(
            timezone=self.tz,
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': self.misfire_grace_seconds
            }
        )

        # 資料庫配置
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'crypto_db'),
            'user': os.getenv('POSTGRES_USER', 'crypto'),
            'password': os.getenv('POSTGRES_PASSWORD', 'crypto_pass')
        }

        # 郵件配置
        self.smtp_config = {
            'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', 587)),
            'user': os.getenv('SMTP_USER', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from': os.getenv('SMTP_FROM', os.getenv('SMTP_USER', '')),
            'to': os.getenv('SMTP_TO', '').split(',')
        }

        # 報表配置
        self.output_dir = project_root / "reports"
        self.output_dir.mkdir(exist_ok=True)

        logger.info("報表排程器初始化完成")
        logger.info(f"時區：{self.tz}")
        logger.info(f"資料庫：{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        logger.info(f"輸出目錄：{self.output_dir}")
        logger.info(f"Misfire 容忍時間：{self.misfire_grace_seconds} 秒")

    def send_email(self, subject: str, body: str, attachments: list = None):
        """發送郵件

        Args:
            subject: 郵件主題
            body: 郵件內容 (HTML)
            attachments: 附件路徑列表
        """
        if not self.smtp_config['user'] or not self.smtp_config['password']:
            logger.warning("未配置 SMTP，跳過郵件發送")
            return

        if not self.smtp_config['to']:
            logger.warning("未配置收件人，跳過郵件發送")
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_config['from']
            msg['To'] = ', '.join(self.smtp_config['to'])
            msg['Subject'] = subject

            # 郵件內容
            msg.attach(MIMEText(body, 'html'))

            # 附件
            if attachments:
                for file_path in attachments:
                    if Path(file_path).exists():
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {Path(file_path).name}'
                            )
                            msg.attach(part)

            # 發送郵件
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                server.starttls()
                server.login(self.smtp_config['user'], self.smtp_config['password'])
                server.send_message(msg)

            logger.info(f"✅ 郵件發送成功：{subject}")

        except Exception as e:
            logger.error(f"❌ 郵件發送失敗：{e}")

    def generate_daily_report(self):
        """生成每日報表（單一 symbol）"""
        logger.info("=" * 80)
        logger.info("開始生成每日報表")
        logger.info(f"時間：{datetime.now(self.tz)}")
        logger.info("=" * 80)

        try:
            agent = ReportAgent(
                output_dir=str(self.output_dir),
                db_config=self.db_config
            )

            # 生成日報（單一 symbol）
            result = agent.generate_comprehensive_report(
                report_type='daily',
                markets=['BTC/USDT'],  # Phase 6.2: 單一 symbol
                strategies=['RSI', 'MACD'],
                formats=['html', 'pdf']
            )

            logger.info("\n✅ 每日報表生成成功！")
            logger.info(f"報表期間：{result['period']['start']} ~ {result['period']['end']}")
            logger.info(f"資料品質記錄：{result['statistics']['quality_records']}")
            logger.info(f"回測策略數：{result['statistics']['strategies']}")

            # 準備郵件
            subject = f"[Crypto Analyzer] 每日報表 - {datetime.now(self.tz).strftime('%Y-%m-%d')}"
            
            # 檢查是否有 PDF 或 HTML 報表
            pdf_path = result['output_paths'].get('pdf')
            html_overview_path = result['output_paths'].get('html_overview')
            
            if pdf_path:
                # 如果有 PDF，郵件正文為摘要，附件為 PDF
                body = f"""
                <html>
                <body>
                    <h2>每日報表</h2>
                    <p>報表期間：{result['period']['start']} ~ {result['period']['end']}</p>
                    <h3>資料品質</h3>
                    <ul>
                        <li>品質記錄數：{result['statistics']['quality_records']}</li>
                    </ul>
                    <h3>策略表現</h3>
                    <ul>
                        <li>回測策略數：{result['statistics']['strategies']}</li>
                    </ul>
                    <p>詳細報表請見附件 PDF</p>
                </body>
                </html>
                """
                logger.info(f"將附加 PDF 報表：{pdf_path}")
                self.send_email(
                    subject=subject,
                    body=body,
                    attachments=[pdf_path]
                )
            elif html_overview_path:
                # 如果沒有 PDF，將完整 HTML 報表嵌入郵件正文
                with open(html_overview_path, 'r', encoding='utf-8') as f:
                    body = f.read()
                logger.info(f"將完整 HTML 報表嵌入郵件正文：{html_overview_path}")
                self.send_email(
                    subject=subject,
                    body=body,
                    attachments=None
                )
            else:
                logger.warning("無可用的報表文件，跳過郵件發送")

            agent.close()
            logger.info("每日報表流程完成")

        except Exception as e:
            logger.error(f"❌ 每日報表生成失敗：{e}")
            import traceback
            traceback.print_exc()

    def generate_weekly_report(self):
        """生成每週報表（整體）"""
        logger.info("=" * 80)
        logger.info("開始生成每週報表")
        logger.info(f"時間：{datetime.now(self.tz)}")
        logger.info("=" * 80)

        try:
            agent = ReportAgent(
                output_dir=str(self.output_dir),
                db_config=self.db_config
            )

            # 生成週報（整體）
            result = agent.generate_comprehensive_report(
                report_type='weekly',
                markets=['BTC/USDT', 'ETH/USDT'],  # Phase 6.2: 多 symbol
                strategies=['RSI', 'MACD', 'Fractal'],
                formats=['html', 'pdf']
            )

            logger.info("\n✅ 每週報表生成成功！")
            logger.info(f"報表期間：{result['period']['start']} ~ {result['period']['end']}")

            # 準備郵件
            subject = f"[Crypto Analyzer] 每週報表 - Week {datetime.now(self.tz).isocalendar()[1]}"
            
            # 檢查是否有 PDF 或 HTML 報表
            pdf_path = result['output_paths'].get('pdf')
            html_overview_path = result['output_paths'].get('html_overview')
            
            if pdf_path:
                # 如果有 PDF，郵件正文為摘要，附件為 PDF
                body = f"""
                <html>
                <body>
                    <h2>每週報表</h2>
                    <p>報表期間：{result['period']['start']} ~ {result['period']['end']}</p>
                    <h3>資料品質趨勢</h3>
                    <p>週品質記錄數：{result['statistics']['quality_records']}</p>
                    <h3>策略排行</h3>
                    <p>回測策略數：{result['statistics']['strategies']}</p>
                    <p>詳細報表請見附件 PDF</p>
                </body>
                </html>
                """
                logger.info(f"將附加 PDF 報表：{pdf_path}")
                self.send_email(
                    subject=subject,
                    body=body,
                    attachments=[pdf_path]
                )
            elif html_overview_path:
                # 如果沒有 PDF，將完整 HTML 報表嵌入郵件正文
                with open(html_overview_path, 'r', encoding='utf-8') as f:
                    body = f.read()
                logger.info(f"將完整 HTML 報表嵌入郵件正文：{html_overview_path}")
                self.send_email(
                    subject=subject,
                    body=body,
                    attachments=None
                )
            else:
                logger.warning("無可用的報表文件，跳過郵件發送")

            agent.close()
            logger.info("每週報表流程完成")

        except Exception as e:
            logger.error(f"❌ 每週報表生成失敗：{e}")
            import traceback
            traceback.print_exc()

    def start(self):
        """啟動排程服務"""
        # 每日報表：每日 08:00 (台北時間)
        self.scheduler.add_job(
            self.generate_daily_report,
            CronTrigger(hour=8, minute=0, timezone=self.tz),
            id='daily_report',
            name='每日報表'
        )
        logger.info("✅ 已設定每日報表排程：每日 08:00 (台北時間)")

        # 每週報表：每週一 09:00 (台北時間)
        self.scheduler.add_job(
            self.generate_weekly_report,
            CronTrigger(day_of_week='mon', hour=9, minute=0, timezone=self.tz),
            id='weekly_report',
            name='每週報表'
        )
        logger.info("✅ 已設定每週報表排程：每週一 09:00 (台北時間)")

        logger.info("\n" + "=" * 80)
        logger.info("報表排程服務啟動")
        logger.info("=" * 80)

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("\n報表排程服務停止")


def main():
    """主程式"""
    scheduler = ReportScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()
