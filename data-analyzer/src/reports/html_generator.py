"""
HTML Report Generator - HTML 報表生成器

職責：
1. 生成 Overview 層級的 HTML 報表（給非技術人）
2. 生成 Detail 層級的 HTML 報表（給 quant/engineer）
3. 生成單一回測報表
4. 生成資料品質報表
"""
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger
import json

from .image_utils import collect_backtest_images, create_embedded_image_html


class HTMLReportGenerator:
    """HTML 報表生成器"""

    def __init__(self):
        """初始化 HTML 報表生成器"""
        self.template_dir = Path(__file__).parent / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def generate_overview(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "overview.html"
    ) -> Path:
        """
        生成 Overview 報表（給非技術人）

        Args:
            report_data: 報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 HTML 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        # 準備摘要數據
        metadata = report_data.get('metadata', {})
        quality_summary = report_data.get('quality_summary', [])
        backtest_results = report_data.get('backtest_results', [])

        # 計算關鍵指標
        key_metrics = self._calculate_key_metrics(report_data)

        # 生成 HTML 內容
        html_content = self._render_overview_template(
            metadata=metadata,
            key_metrics=key_metrics,
            quality_summary=quality_summary,
            backtest_results=backtest_results
        )

        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ Overview 報表已生成：{output_path}")
        return output_path

    def generate_detail(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "detail.html"
    ) -> Path:
        """
        生成 Detail 報表（給 quant/engineer）

        Args:
            report_data: 報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 HTML 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        # 生成詳細 HTML 內容
        html_content = self._render_detail_template(report_data)

        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ Detail 報表已生成：{output_path}")
        return output_path

    def generate_backtest_report(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "backtest_report.html"
    ) -> Path:
        """
        生成單一回測報表

        Args:
            report_data: 回測報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 HTML 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        # 生成回測報表 HTML
        html_content = self._render_backtest_template(report_data)

        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ 回測報表已生成：{output_path}")
        return output_path

    def generate_quality_report(
        self,
        report_data: Dict,
        output_dir: Path,
        filename: str = "quality_report.html"
    ) -> Path:
        """
        生成資料品質報表

        Args:
            report_data: 品質報表資料
            output_dir: 輸出目錄
            filename: 檔案名稱

        Returns:
            生成的 HTML 檔案路徑
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        # 生成品質報表 HTML
        html_content = self._render_quality_template(report_data)

        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ 資料品質報表已生成：{output_path}")
        return output_path

    def _calculate_key_metrics(self, report_data: Dict) -> Dict:
        """計算關鍵指標"""
        quality_summary = report_data.get('quality_summary', [])
        backtest_results = report_data.get('backtest_results', [])

        # 資料品質指標
        if quality_summary:
            avg_quality = sum(q.get('quality_score', 0) for q in quality_summary) / len(quality_summary)
            total_missing = sum(q.get('missing_count', 0) for q in quality_summary)
            failed_checks = sum(1 for q in quality_summary if not q.get('is_valid', True))
        else:
            avg_quality = 0
            total_missing = 0
            failed_checks = 0

        # 回測績效指標
        best_strategy = None
        best_return = -float('inf')

        for result in backtest_results:
            metrics = result.get('metrics', {})
            if metrics:
                total_return = metrics.get('total_return', 0)
                if total_return > best_return:
                    best_return = total_return
                    best_strategy = result.get('strategy_name', 'Unknown')

        return {
            'avg_quality_score': avg_quality,
            'total_missing_data': total_missing,
            'failed_quality_checks': failed_checks,
            'best_strategy': best_strategy,
            'best_return': best_return * 100 if best_return != -float('inf') else 0,
            'total_strategies': len(backtest_results),
        }

    def _render_overview_template(
        self,
        metadata: Dict,
        key_metrics: Dict,
        quality_summary: List[Dict],
        backtest_results: List[Dict]
    ) -> str:
        """渲染 Overview 模板"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Market Analyzer - Overview Report</title>
    {self._get_common_styles()}
</head>
<body>
    <div class="container">
        <!-- 標題區域 -->
        <header class="header">
            <h1>📊 Crypto Market Analyzer</h1>
            <h2>Overview Report - {metadata.get('report_type', 'Unknown').title()}</h2>
            <p class="subtitle">
                Period: {metadata.get('start_date', 'N/A')} ~ {metadata.get('end_date', 'N/A')}
            </p>
            <p class="generated-time">Generated at: {metadata.get('generated_at', 'N/A')}</p>
        </header>

        <!-- 關鍵指標卡片 -->
        <section class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon">📈</div>
                <div class="metric-content">
                    <h3>Best Strategy</h3>
                    <p class="metric-value">{key_metrics.get('best_strategy', 'N/A')}</p>
                    <p class="metric-detail">Return: {key_metrics.get('best_return', 0):.2f}%</p>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">✅</div>
                <div class="metric-content">
                    <h3>Data Quality</h3>
                    <p class="metric-value">{key_metrics.get('avg_quality_score', 0):.1f}/100</p>
                    <p class="metric-detail">Average Score</p>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">⚠️</div>
                <div class="metric-content">
                    <h3>Quality Issues</h3>
                    <p class="metric-value">{key_metrics.get('failed_quality_checks', 0)}</p>
                    <p class="metric-detail">Failed Checks</p>
                </div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">🔍</div>
                <div class="metric-content">
                    <h3>Strategies Tested</h3>
                    <p class="metric-value">{key_metrics.get('total_strategies', 0)}</p>
                    <p class="metric-detail">Total Count</p>
                </div>
            </div>
        </section>

        <!-- 回測策略績效比較 -->
        <section class="section">
            <h2>💼 Strategy Performance Comparison</h2>
            {self._render_backtest_comparison_table(backtest_results)}
        </section>

        <!-- 資料品質摘要 -->
        <section class="section">
            <h2>📋 Data Quality Summary</h2>
            {self._render_quality_summary_table(quality_summary)}
        </section>

        <!-- 頁尾 -->
        <footer class="footer">
            <p>Generated by Crypto Market Analyzer | Report Agent v1.0</p>
            <p>For detailed technical analysis, please refer to the Detail Report</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def _render_detail_template(self, report_data: Dict) -> str:
        """渲染 Detail 模板"""
        metadata = report_data.get('metadata', {})
        quality_summary = report_data.get('quality_summary', [])
        backtest_results = report_data.get('backtest_results', [])

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Market Analyzer - Detail Report</title>
    {self._get_common_styles()}
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>🔬 Crypto Market Analyzer - Detail Report</h1>
            <h2>{metadata.get('report_type', 'Unknown').title()} Report</h2>
            <p class="subtitle">Period: {metadata.get('start_date', 'N/A')} ~ {metadata.get('end_date', 'N/A')}</p>
        </header>

        <!-- Metadata 資訊 -->
        <section class="section">
            <h2>📝 Report Metadata</h2>
            <pre class="json-display">{json.dumps(metadata, indent=2)}</pre>
        </section>

        <!-- 詳細回測結果 -->
        <section class="section">
            <h2>📊 Detailed Backtest Results</h2>
            {self._render_detailed_backtest_results(backtest_results)}
        </section>

        <!-- 詳細品質資料 -->
        <section class="section">
            <h2>🔍 Detailed Quality Data</h2>
            {self._render_detailed_quality_data(quality_summary)}
        </section>

        <footer class="footer">
            <p>Technical Detail Report | Crypto Market Analyzer v1.0</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def _render_backtest_template(self, report_data: Dict) -> str:
        """渲染回測報表模板"""
        metadata = report_data.get('metadata', {})
        metrics = report_data.get('metrics', {})
        strategy_name = metadata.get('strategy_name', 'Unknown')

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report - {strategy_name}</title>
    {self._get_common_styles()}
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📈 Backtest Report</h1>
            <h2>{strategy_name}</h2>
            <p class="subtitle">
                Data Period: {metadata.get('data_period', {}).get('start', 'N/A')} ~
                {metadata.get('data_period', {}).get('end', 'N/A')}
            </p>
        </header>

        <!-- 績效指標 -->
        <section class="section">
            <h2>💰 Performance Metrics</h2>
            {self._render_metrics_cards(metrics)}
        </section>

        <!-- 交易統計 -->
        <section class="section">
            <h2>📊 Trade Statistics</h2>
            {self._render_trade_statistics(metrics)}
        </section>

        <footer class="footer">
            <p>Generated at: {metadata.get('generated_at', 'N/A')}</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def _render_quality_template(self, report_data: Dict) -> str:
        """渲染資料品質報表模板"""
        metadata = report_data.get('metadata', {})
        quality_summary = report_data.get('quality_summary', [])

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Quality Report</title>
    {self._get_common_styles()}
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>✅ Data Quality Report</h1>
            <p class="subtitle">Last {metadata.get('hours', 'N/A')} Hours</p>
            <p class="generated-time">Generated at: {metadata.get('generated_at', 'N/A')}</p>
        </header>

        <section class="section">
            <h2>📋 Quality Summary</h2>
            {self._render_quality_summary_table(quality_summary)}
        </section>

        <footer class="footer">
            <p>Data Quality Report | Crypto Market Analyzer v1.0</p>
        </footer>
    </div>
</body>
</html>
"""
        return html

    def _render_backtest_comparison_table(self, backtest_results: List[Dict]) -> str:
        """渲染回測比較表格（含圖表）"""
        if not backtest_results:
            return "<p class='no-data'>No backtest results available</p>"

        sections = []

        # 先顯示表格
        rows = []
        for result in backtest_results:
            strategy_name = result.get('strategy_name', 'Unknown')
            metrics = result.get('metrics', {})

            if not metrics:
                rows.append(f"""
                    <tr>
                        <td>{strategy_name}</td>
                        <td colspan="5" class="no-data">No metrics available (visualization only)</td>
                    </tr>
                """)
                continue

            total_return = metrics.get('total_return', 0) * 100
            sharpe = metrics.get('sharpe_ratio', 0)
            max_dd = metrics.get('max_drawdown', 0) * 100
            win_rate = metrics.get('win_rate', 0) * 100
            total_trades = metrics.get('total_trades', 0)

            rows.append(f"""
                <tr>
                    <td><strong>{strategy_name}</strong></td>
                    <td class="{'positive' if total_return > 0 else 'negative'}">{total_return:.2f}%</td>
                    <td>{sharpe:.3f}</td>
                    <td class="negative">-{max_dd:.2f}%</td>
                    <td>{win_rate:.1f}%</td>
                    <td>{total_trades}</td>
                </tr>
            """)

        sections.append(f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Strategy</th>
                    <th>Total Return</th>
                    <th>Sharpe Ratio</th>
                    <th>Max Drawdown</th>
                    <th>Win Rate</th>
                    <th>Trades</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """)

        # 顯示視覺化圖表（如果有的話）
        results_dir = Path("results/backtest_reports")
        if results_dir.exists():
            for result in backtest_results:
                strategy_name = result.get('strategy_name', 'Unknown')
                strategy_dir = results_dir / strategy_name

                if strategy_dir.exists():
                    images = collect_backtest_images(strategy_dir)

                    if images:
                        sections.append(f"""
                        <div class="strategy-charts">
                            <h3>📊 {strategy_name} Visualizations</h3>
                            <div class="charts-grid">
                        """)

                        # 權益曲線
                        if 'equity_curve' in images:
                            sections.append(f"""
                                <div class="chart-item">
                                    <h4>Equity Curve</h4>
                                    <img src="{images['equity_curve']}" alt="Equity Curve" class="chart-img">
                                </div>
                            """)

                        # 回撤圖
                        if 'drawdown' in images:
                            sections.append(f"""
                                <div class="chart-item">
                                    <h4>Drawdown</h4>
                                    <img src="{images['drawdown']}" alt="Drawdown" class="chart-img">
                                </div>
                            """)

                        # 交易信號
                        if 'signals' in images:
                            sections.append(f"""
                                <div class="chart-item">
                                    <h4>Trading Signals</h4>
                                    <img src="{images['signals']}" alt="Signals" class="chart-img">
                                </div>
                            """)

                        # 績效指標
                        if 'metrics' in images:
                            sections.append(f"""
                                <div class="chart-item">
                                    <h4>Performance Metrics</h4>
                                    <img src="{images['metrics']}" alt="Metrics" class="chart-img">
                                </div>
                            """)

                        sections.append("""
                            </div>
                        </div>
                        """)

        return ''.join(sections)

    def _render_quality_summary_table(self, quality_summary: List[Dict]) -> str:
        """渲染資料品質摘要表格"""
        if not quality_summary:
            return "<p class='no-data'>No quality data available</p>"

        # 只顯示前 20 筆
        summary_slice = quality_summary[:20]

        rows = []
        for record in summary_slice:
            symbol = record.get('symbol', 'N/A')
            exchange = record.get('exchange', 'N/A')
            quality_score = record.get('quality_score', 0)
            is_valid = record.get('is_valid', True)
            missing_count = record.get('missing_count', 0)

            status_class = 'positive' if is_valid else 'negative'
            status_text = '✓ Valid' if is_valid else '✗ Invalid'

            rows.append(f"""
                <tr>
                    <td>{symbol}</td>
                    <td>{exchange}</td>
                    <td class="{'positive' if quality_score >= 90 else 'warning' if quality_score >= 70 else 'negative'}">
                        {quality_score:.1f}/100
                    </td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{missing_count}</td>
                </tr>
            """)

        return f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Exchange</th>
                    <th>Quality Score</th>
                    <th>Status</th>
                    <th>Missing Count</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        {f'<p class="note">Showing 20 of {len(quality_summary)} records</p>' if len(quality_summary) > 20 else ''}
        """

    def _render_detailed_backtest_results(self, backtest_results: List[Dict]) -> str:
        """渲染詳細回測結果"""
        if not backtest_results:
            return "<p class='no-data'>No backtest results</p>"

        sections = []
        for result in backtest_results:
            strategy_name = result.get('strategy_name', 'Unknown')
            metrics = result.get('metrics', {})

            sections.append(f"""
                <div class="subsection">
                    <h3>{strategy_name}</h3>
                    <pre class="json-display">{json.dumps(metrics, indent=2)}</pre>
                </div>
            """)

        return ''.join(sections)

    def _render_detailed_quality_data(self, quality_summary: List[Dict]) -> str:
        """渲染詳細品質資料"""
        if not quality_summary:
            return "<p class='no-data'>No quality data</p>"

        return f"""
        <div class="subsection">
            <pre class="json-display">{json.dumps(quality_summary[:10], indent=2)}</pre>
            {f'<p class="note">Showing 10 of {len(quality_summary)} records</p>' if len(quality_summary) > 10 else ''}
        </div>
        """

    def _render_metrics_cards(self, metrics: Dict) -> str:
        """渲染績效指標卡片"""
        total_return = metrics.get('total_return', 0) * 100
        sharpe = metrics.get('sharpe_ratio', 0)
        max_dd = metrics.get('max_drawdown', 0) * 100
        win_rate = metrics.get('win_rate', 0) * 100

        return f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Return</h3>
                <p class="metric-value {'positive' if total_return > 0 else 'negative'}">
                    {total_return:.2f}%
                </p>
            </div>
            <div class="metric-card">
                <h3>Sharpe Ratio</h3>
                <p class="metric-value">{sharpe:.3f}</p>
            </div>
            <div class="metric-card">
                <h3>Max Drawdown</h3>
                <p class="metric-value negative">-{max_dd:.2f}%</p>
            </div>
            <div class="metric-card">
                <h3>Win Rate</h3>
                <p class="metric-value">{win_rate:.1f}%</p>
            </div>
        </div>
        """

    def _render_trade_statistics(self, metrics: Dict) -> str:
        """渲染交易統計"""
        return f"""
        <table class="data-table">
            <tr><th>Total Trades</th><td>{metrics.get('total_trades', 0)}</td></tr>
            <tr><th>Win Trades</th><td>{metrics.get('win_trades', 0)}</td></tr>
            <tr><th>Loss Trades</th><td>{metrics.get('loss_trades', 0)}</td></tr>
            <tr><th>Avg Win</th><td class="positive">{metrics.get('avg_win', 0)*100:.2f}%</td></tr>
            <tr><th>Avg Loss</th><td class="negative">{metrics.get('avg_loss', 0)*100:.2f}%</td></tr>
            <tr><th>Profit Factor</th><td>{metrics.get('profit_factor', 0):.2f}</td></tr>
        </table>
        """

    def _get_common_styles(self) -> str:
        """獲取通用 CSS 樣式"""
        return """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 50px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #2E86AB 0%, #1A5F7A 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header h2 { font-size: 1.5em; font-weight: 300; margin-bottom: 10px; }
        .subtitle { font-size: 1.1em; opacity: 0.9; }
        .generated-time { font-size: 0.9em; opacity: 0.7; margin-top: 10px; }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
        }
        .metric-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
            transition: transform 0.2s;
        }
        .metric-card:hover { transform: translateY(-5px); }
        .metric-icon { font-size: 3em; }
        .metric-content h3 { font-size: 0.9em; color: #666; margin-bottom: 5px; }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2E86AB;
        }
        .metric-detail { font-size: 0.85em; color: #888; }

        .section {
            padding: 40px;
            border-top: 1px solid #eee;
        }
        .section h2 {
            font-size: 1.8em;
            margin-bottom: 20px;
            color: #333;
        }
        .subsection {
            margin-top: 20px;
            padding: 20px;
            background: #f9f9f9;
            border-left: 4px solid #2E86AB;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .data-table th, .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .data-table th {
            background: #2E86AB;
            color: white;
            font-weight: 600;
        }
        .data-table tr:hover { background: #f5f5f5; }

        .positive { color: #27ae60; font-weight: bold; }
        .negative { color: #e74c3c; font-weight: bold; }
        .warning { color: #f39c12; font-weight: bold; }
        .no-data { color: #999; font-style: italic; text-align: center; padding: 20px; }
        .note { font-size: 0.9em; color: #666; margin-top: 10px; text-align: center; }

        .json-display {
            background: #282c34;
            color: #abb2bf;
            padding: 20px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .footer {
            background: #f5f5f5;
            padding: 30px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }

        /* 圖表樣式 */
        .strategy-charts {
            margin-top: 30px;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }
        .strategy-charts h3 {
            margin-bottom: 20px;
            color: #2E86AB;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .chart-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .chart-item h4 {
            margin-bottom: 10px;
            color: #555;
            font-size: 1.1em;
        }
        .chart-img {
            width: 100%;
            height: auto;
            border-radius: 4px;
        }
    </style>
        """


# 範例用法
if __name__ == "__main__":
    generator = HTMLReportGenerator()

    # 測試資料
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

    # 生成 Overview
    output_path = generator.generate_overview(
        report_data=test_data,
        output_dir=Path("test_reports"),
        filename="test_overview.html"
    )

    print(f"測試報表已生成：{output_path}")
