"""
PDF Report Generator - PDF 報表生成器

職責：
1. 將 HTML 報表轉換為 PDF
2. 支援 Overview 與 Detail 兩層報表
3. 支援單一回測報表與資料品質報表
"""
from typing import Dict
from pathlib import Path
from loguru import logger

from .html_generator import HTMLReportGenerator

# PDF 生成套件（可選）
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError, Exception) as e:
    WEASYPRINT_AVAILABLE = False
    logger.warning(f"WeasyPrint 不可用：{type(e).__name__}")
    HTML = None
    CSS = None


class PDFReportGenerator:
    """PDF 報表生成器"""

    def __init__(self):
        """初始化 PDF 報表生成器"""
        self.html_generator = HTMLReportGenerator()

        if not WEASYPRINT_AVAILABLE:
            logger.warning(
                "WeasyPrint 未安裝。請執行：pip install weasyprint\n"
                "目前 PDF 功能將使用備用方案（保存 HTML 副本）"
            )

    def generate_overview(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "overview.pdf"
    ) -> Path:
        """
        生成 Overview PDF 報表

        Args:
            report_data: 報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 PDF 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        if WEASYPRINT_AVAILABLE:
            # 生成 HTML 內容
            html_content = self.html_generator._render_overview_template(
                metadata=report_data.get('metadata', {}),
                key_metrics=self.html_generator._calculate_key_metrics(report_data),
                quality_summary=report_data.get('quality_summary', []),
                backtest_results=report_data.get('backtest_results', [])
            )

            # 轉換為 PDF
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"✓ PDF Overview 已生成：{output_path}")
        else:
            # 備用方案：生成 HTML 檔案
            logger.warning(f"使用備用方案：生成 HTML 檔案代替 PDF")
            output_path = output_dir / filename.replace('.pdf', '.html')
            self.html_generator.generate_overview(
                report_data=report_data,
                output_dir=output_dir,
                filename=output_path.name
            )

        return output_path

    def generate_detail(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "detail.pdf"
    ) -> Path:
        """
        生成 Detail PDF 報表

        Args:
            report_data: 報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 PDF 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        if WEASYPRINT_AVAILABLE:
            html_content = self.html_generator._render_detail_template(report_data)
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"✓ PDF Detail 已生成：{output_path}")
        else:
            logger.warning(f"使用備用方案：生成 HTML 檔案代替 PDF")
            output_path = output_dir / filename.replace('.pdf', '.html')
            self.html_generator.generate_detail(
                report_data=report_data,
                output_dir=output_dir,
                filename=output_path.name
            )

        return output_path

    def generate_backtest_report(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "backtest_report.pdf"
    ) -> Path:
        """
        生成回測 PDF 報表

        Args:
            report_data: 回測資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 PDF 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        if WEASYPRINT_AVAILABLE:
            html_content = self.html_generator._render_backtest_template(report_data)
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"✓ 回測 PDF 報表已生成：{output_path}")
        else:
            logger.warning(f"使用備用方案：生成 HTML 檔案代替 PDF")
            output_path = output_dir / filename.replace('.pdf', '.html')
            self.html_generator.generate_backtest_report(
                report_data=report_data,
                output_dir=output_dir,
                filename=output_path.name
            )

        return output_path

    def generate_quality_report(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "quality_report.pdf"
    ) -> Path:
        """
        生成資料品質 PDF 報表

        Args:
            report_data: 品質資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 PDF 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        if WEASYPRINT_AVAILABLE:
            html_content = self.html_generator._render_quality_template(report_data)
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"✓ 品質 PDF 報表已生成：{output_path}")
        else:
            logger.warning(f"使用備用方案：生成 HTML 檔案代替 PDF")
            output_path = output_dir / filename.replace('.pdf', '.html')
            self.html_generator.generate_quality_report(
                report_data=report_data,
                output_dir=output_dir,
                filename=output_path.name
            )

        return output_path


# 範例用法
if __name__ == "__main__":
    from datetime import datetime

    generator = PDFReportGenerator()

    test_data = {
        'metadata': {
            'report_type': 'daily',
            'start_date': '2024-12-25',
            'end_date': '2024-12-26',
            'generated_at': datetime.now().isoformat(),
        },
        'quality_summary': [
            {
                'symbol': 'BTC/USDT',
                'exchange': 'Binance',
                'quality_score': 95.5,
                'is_valid': True,
                'missing_count': 2,
            }
        ],
        'backtest_results': [
            {
                'strategy_name': 'RSI',
                'metrics': {
                    'total_return': 0.15,
                    'sharpe_ratio': 1.25,
                    'max_drawdown': 0.08,
                    'win_rate': 0.65,
                    'total_trades': 50,
                }
            }
        ],
    }

    output_path = generator.generate_overview(
        report_data=test_data,
        output_dir=Path("test_reports"),
        filename="test_overview.pdf"
    )

    print(f"測試 PDF 報表已生成：{output_path}")
