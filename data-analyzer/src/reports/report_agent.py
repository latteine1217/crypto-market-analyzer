"""
Report Agent - 報表生成代理

職責：
1. 整合資料品質摘要、模型結果、回測績效
2. 生成 HTML 與 PDF 報表
3. 提供 Overview 與 Detail 兩層報表
4. 支援定期排程報告生成
5. 郵件發送與資料庫記錄
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import pandas as pd
import json
import time
import psycopg2
import pytz

from .data_collector import ReportDataCollector
from .html_generator import HTMLReportGenerator
from .pdf_generator import PDFReportGenerator
from .email_sender import EmailSender


class ReportAgent:
    """
    報表生成代理

    整合所有資料來源，生成分層報表
    """

    def __init__(
        self,
        output_dir: str = "reports",
        db_config: Optional[Dict] = None,
        email_config: Optional[Dict] = None,
        timezone: str = "Asia/Taipei"
    ):
        """
        初始化 Report Agent

        Args:
            output_dir: 報表輸出目錄
            db_config: 資料庫配置
            email_config: 郵件配置
            timezone: 時區（預設：Asia/Taipei, UTC+8）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 設定時區
        self.tz = pytz.timezone(timezone)

        # 初始化資料收集器
        self.data_collector = ReportDataCollector(db_config=db_config)

        # 初始化報表生成器
        self.html_generator = HTMLReportGenerator()
        self.pdf_generator = PDFReportGenerator()

        # 初始化郵件發送器（可選）
        self.email_sender = None
        if email_config:
            try:
                self.email_sender = EmailSender.from_config(email_config)
                logger.info("✓ 郵件發送器已啟用")
            except Exception as e:
                logger.warning(f"郵件發送器初始化失敗：{e}")

        # 資料庫連接（用於記錄日誌）
        self.db_config = db_config
        self.db_conn = None
        if db_config:
            try:
                self.db_conn = psycopg2.connect(**db_config)
                logger.info("✓ 資料庫日誌記錄已啟用")
            except Exception as e:
                logger.warning(f"資料庫連接失敗：{e}")

        logger.info(f"Report Agent 初始化完成，輸出目錄：{self.output_dir}")

    def generate_comprehensive_report(
        self,
        report_type: str = "daily",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        markets: Optional[List[str]] = None,
        strategies: Optional[List[str]] = None,
        formats: List[str] = ["html", "pdf"]
    ) -> Dict:
        """
        生成綜合報表

        Args:
            report_type: 報表類型 ('daily', 'weekly', 'monthly')
            start_date: 起始日期
            end_date: 結束日期
            markets: 市場列表（如 ['BTC/USDT', 'ETH/USDT']）
            strategies: 策略列表（如 ['RSI', 'MA_Cross']）
            formats: 輸出格式列表 ['html', 'pdf']

        Returns:
            報表生成結果字典
        """
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"開始生成 {report_type} 綜合報表")
        logger.info("=" * 60)

        # 確定時間範圍
        if end_date is None:
            end_date = datetime.now(self.tz)
        if start_date is None:
            start_date = self._get_start_date_by_type(report_type, end_date)

        logger.info(f"報表期間：{start_date} 至 {end_date}")

        # ========== 步驟 1：收集資料 ==========
        logger.info("\n### 步驟 1：收集資料 ###")

        # 收集資料品質摘要
        quality_summary = self.data_collector.collect_quality_summary(
            start_date=start_date,
            end_date=end_date,
            markets=markets
        )
        logger.info(f"✓ 資料品質摘要：{len(quality_summary)} 筆記錄")

        # 收集回測結果
        backtest_results = self.data_collector.collect_backtest_results(
            strategies=strategies,
            start_date=start_date,
            end_date=end_date
        )
        logger.info(f"✓ 回測結果：{len(backtest_results)} 個策略")

        # 收集模型訓練結果（如果有的話）
        model_results = self.data_collector.collect_model_results(
            start_date=start_date,
            end_date=end_date
        )
        logger.info(f"✓ 模型結果：{len(model_results)} 個模型")

        # ========== 步驟 2：生成報表內容 ==========
        logger.info("\n### 步驟 2：生成報表內容 ###")

        report_data = {
            'metadata': {
                'report_type': report_type,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'generated_at': datetime.now(self.tz).isoformat(),
                'timezone': str(self.tz),
                'markets': markets or 'all',
                'strategies': strategies or 'all',
            },
            'quality_summary': quality_summary,
            'backtest_results': backtest_results,
            'model_results': model_results,
        }

        # 保存結構化資料（JSON）
        json_path = self._save_json(report_data, report_type, end_date)
        logger.info(f"✓ JSON 資料已保存：{json_path}")

        # ========== 步驟 3：生成報表檔案 ==========
        logger.info("\n### 步驟 3：生成報表檔案 ###")

        output_paths = {}

        # 生成 HTML 報表
        if 'html' in formats:
            # Overview 版本
            html_overview_path = self.html_generator.generate_overview(
                report_data=report_data,
                output_dir=self.output_dir / report_type,
                filename=f"{report_type}_overview_{end_date.strftime('%Y%m%d')}.html"
            )
            logger.info(f"✓ HTML Overview：{html_overview_path}")
            output_paths['html_overview'] = str(html_overview_path)

            # Detail 版本
            html_detail_path = self.html_generator.generate_detail(
                report_data=report_data,
                output_dir=self.output_dir / report_type,
                filename=f"{report_type}_detail_{end_date.strftime('%Y%m%d')}.html"
            )
            logger.info(f"✓ HTML Detail：{html_detail_path}")
            output_paths['html_detail'] = str(html_detail_path)

        # 生成 PDF 報表
        if 'pdf' in formats:
            # Overview 版本
            pdf_overview_path = self.pdf_generator.generate_overview(
                report_data=report_data,
                output_dir=self.output_dir / report_type,
                filename=f"{report_type}_overview_{end_date.strftime('%Y%m%d')}.pdf"
            )
            logger.info(f"✓ PDF Overview：{pdf_overview_path}")
            output_paths['pdf_overview'] = str(pdf_overview_path)

            # Detail 版本
            pdf_detail_path = self.pdf_generator.generate_detail(
                report_data=report_data,
                output_dir=self.output_dir / report_type,
                filename=f"{report_type}_detail_{end_date.strftime('%Y%m%d')}.pdf"
            )
            logger.info(f"✓ PDF Detail：{pdf_detail_path}")
            output_paths['pdf_detail'] = str(pdf_detail_path)

        logger.info("\n" + "=" * 60)
        logger.info("✅ 綜合報表生成完成！")
        logger.info("=" * 60)

        # ========== 步驟 4：記錄到資料庫 ==========
        report_log_id = None
        if self.db_conn:
            try:
                generation_time = time.time() - start_time if 'start_time' in locals() else 0
                report_log_id = self._log_report_to_db(
                    report_type=report_type,
                    start_date=start_date,
                    end_date=end_date,
                    output_paths=output_paths,
                    json_path=json_path,
                    statistics={
                        'quality_records': len(quality_summary),
                        'strategies': len(backtest_results),
                        'models': len(model_results),
                    },
                    generation_time=generation_time
                )
                logger.info(f"✓ 報表記錄已保存到資料庫：ID={report_log_id}")
            except Exception as e:
                logger.warning(f"資料庫記錄失敗：{e}")

        result = {
            'status': 'success',
            'report_type': report_type,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'output_paths': output_paths,
            'json_path': str(json_path),
            'statistics': {
                'quality_records': len(quality_summary),
                'strategies': len(backtest_results),
                'models': len(model_results),
            },
            'report_log_id': report_log_id
        }

        return result

    def generate_backtest_report(
        self,
        backtest_results: Dict,
        strategy_name: str,
        market_data: pd.DataFrame,
        formats: List[str] = ["html", "pdf"]
    ) -> Dict:
        """
        為單一回測結果生成報表

        Args:
            backtest_results: 回測結果字典（從 BacktestEngine.run() 返回）
            strategy_name: 策略名稱
            market_data: 市場資料
            formats: 輸出格式

        Returns:
            報表路徑字典
        """
        logger.info(f"為 {strategy_name} 生成回測報表")

        # 準備報表資料
        report_data = {
            'metadata': {
                'strategy_name': strategy_name,
                'generated_at': datetime.now(self.tz).isoformat(),
                'timezone': str(self.tz),
                'data_period': {
                    'start': market_data.index[0].isoformat(),
                    'end': market_data.index[-1].isoformat(),
                },
            },
            'metrics': backtest_results['metrics'],
            'equity_curve': backtest_results['equity_curve'].to_dict('records'),
            'trades': backtest_results['trades'].to_dict('records') if not backtest_results['trades'].empty else [],
            'signals': backtest_results['signals'].to_dict('records') if not backtest_results['signals'].empty else [],
        }

        # 保存 JSON
        json_path = self.output_dir / "backtests" / f"{strategy_name}_results.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        output_paths = {'json': str(json_path)}

        # 生成 HTML
        if 'html' in formats:
            html_path = self.html_generator.generate_backtest_report(
                report_data=report_data,
                output_dir=self.output_dir / "backtests",
                filename=f"{strategy_name}_report.html"
            )
            output_paths['html'] = str(html_path)

        # 生成 PDF
        if 'pdf' in formats:
            pdf_path = self.pdf_generator.generate_backtest_report(
                report_data=report_data,
                output_dir=self.output_dir / "backtests",
                filename=f"{strategy_name}_report.pdf"
            )
            output_paths['pdf'] = str(pdf_path)

        logger.info(f"✓ {strategy_name} 報表生成完成")
        return output_paths

    def generate_quality_report(
        self,
        markets: Optional[List[str]] = None,
        hours: int = 24,
        formats: List[str] = ["html"]
    ) -> Dict:
        """
        生成資料品質報表

        Args:
            markets: 市場列表
            hours: 統計時間範圍（小時）
            formats: 輸出格式

        Returns:
            報表路徑字典
        """
        logger.info(f"生成資料品質報表（過去 {hours} 小時）")

        end_date = datetime.now(self.tz)
        start_date = end_date - timedelta(hours=hours)

        # 收集資料品質摘要
        quality_summary = self.data_collector.collect_quality_summary(
            start_date=start_date,
            end_date=end_date,
            markets=markets
        )

        report_data = {
            'metadata': {
                'report_type': 'data_quality',
                'generated_at': end_date.isoformat(),
                'timezone': str(self.tz),
                'hours': hours,
                'markets': markets or 'all',
            },
            'quality_summary': quality_summary,
        }

        # 保存 JSON
        json_path = self.output_dir / "quality" / f"quality_{end_date.strftime('%Y%m%d_%H%M')}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        output_paths = {'json': str(json_path)}

        # 生成 HTML
        if 'html' in formats:
            html_path = self.html_generator.generate_quality_report(
                report_data=report_data,
                output_dir=self.output_dir / "quality",
                filename=f"quality_{end_date.strftime('%Y%m%d_%H%M')}.html"
            )
            output_paths['html'] = str(html_path)

        logger.info(f"✓ 資料品質報表生成完成")
        return output_paths

    def _get_start_date_by_type(
        self,
        report_type: str,
        end_date: datetime
    ) -> datetime:
        """根據報表類型計算起始日期"""
        if report_type == 'daily':
            return end_date - timedelta(days=1)
        elif report_type == 'weekly':
            return end_date - timedelta(weeks=1)
        elif report_type == 'monthly':
            return end_date - timedelta(days=30)
        else:
            return end_date - timedelta(days=1)

    def _save_json(
        self,
        data: Dict,
        report_type: str,
        end_date: datetime
    ) -> Path:
        """保存 JSON 資料"""
        json_dir = self.output_dir / report_type / "data"
        json_dir.mkdir(parents=True, exist_ok=True)

        json_path = json_dir / f"{report_type}_{end_date.strftime('%Y%m%d')}.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return json_path

    def _log_report_to_db(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        output_paths: Dict,
        json_path: Path,
        statistics: Dict,
        generation_time: float
    ) -> Optional[int]:
        """
        記錄報表生成到資料庫

        Returns:
            report_log_id
        """
        if not self.db_conn:
            return None

        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO report_generation_logs (
                        report_type,
                        generated_at,
                        start_date,
                        end_date,
                        html_path,
                        pdf_path,
                        json_path,
                        quality_records,
                        strategies_count,
                        models_count,
                        status,
                        generation_time
                    )
                    VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        report_type,
                        start_date,
                        end_date,
                        output_paths.get('html_overview'),
                        output_paths.get('pdf_overview'),
                        str(json_path),
                        statistics.get('quality_records', 0),
                        statistics.get('strategies', 0),
                        statistics.get('models', 0),
                        'success',
                        generation_time
                    )
                )
                report_log_id = cur.fetchone()[0]
                self.db_conn.commit()
                return report_log_id

        except Exception as e:
            logger.error(f"資料庫記錄失敗：{e}")
            self.db_conn.rollback()
            return None

    def send_report_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_file: Path,
        pdf_attachments: Optional[List[Path]] = None,
        report_log_id: Optional[int] = None
    ) -> bool:
        """
        發送報表郵件

        Args:
            to_addresses: 收件人列表
            subject: 郵件主旨
            html_file: HTML 檔案路徑
            pdf_attachments: PDF 附件列表
            report_log_id: 報表記錄 ID

        Returns:
            是否成功
        """
        if not self.email_sender:
            logger.warning("郵件發送器未啟用")
            return False

        success = self.email_sender.send_report_from_files(
            to_addresses=to_addresses,
            subject=subject,
            html_file=html_file,
            pdf_attachments=pdf_attachments
        )

        # 記錄郵件發送到資料庫
        if success and self.db_conn and report_log_id:
            try:
                with self.db_conn.cursor() as cur:
                    # 更新報表記錄
                    cur.execute(
                        """
                        UPDATE report_generation_logs
                        SET email_sent = TRUE,
                            email_recipients = %s,
                            email_sent_at = NOW()
                        WHERE id = %s
                        """,
                        (to_addresses, report_log_id)
                    )

                    # 插入郵件發送記錄
                    cur.execute(
                        """
                        INSERT INTO email_send_logs (
                            report_log_id,
                            recipients,
                            subject,
                            sent_at,
                            status,
                            attachment_count
                        )
                        VALUES (%s, %s, %s, NOW(), %s, %s)
                        """,
                        (
                            report_log_id,
                            to_addresses,
                            subject,
                            'success',
                            len(pdf_attachments) if pdf_attachments else 0
                        )
                    )
                    self.db_conn.commit()
                    logger.info("✓ 郵件發送記錄已保存到資料庫")

            except Exception as e:
                logger.warning(f"郵件發送記錄失敗：{e}")
                self.db_conn.rollback()

        return success

    def close(self):
        """關閉資源"""
        self.data_collector.close()
        if self.db_conn:
            self.db_conn.close()
            logger.info("資料庫連接已關閉")


# 範例用法
if __name__ == "__main__":
    # 初始化 Report Agent
    agent = ReportAgent(output_dir="reports")

    # 生成日報
    result = agent.generate_comprehensive_report(
        report_type='daily',
        markets=['BTC/USDT', 'ETH/USDT'],
        strategies=['RSI', 'MA_Cross'],
        formats=['html', 'pdf']
    )

    print(f"\n報表已生成：")
    for format_type, path in result['output_paths'].items():
        print(f"  {format_type}: {path}")

    agent.close()
