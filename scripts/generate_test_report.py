#!/usr/bin/env python3
"""
生成長期運行測試報告
整合監控數據、告警記錄、系統狀態
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # 非互動模式
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def load_metrics_timeseries(test_id):
    """載入時序監控數據"""
    ts_file = Path(f"/Users/latteine/Documents/coding/finance/monitoring/test_results/{test_id}/metrics_timeseries.jsonl")

    if not ts_file.exists():
        return []

    metrics = []
    with open(ts_file, 'r') as f:
        for line in f:
            metrics.append(json.loads(line))

    return metrics


def load_alert_logs():
    """載入告警記錄"""
    alert_dir = Path("/Users/latteine/Documents/coding/finance/monitoring/test_results/alerts")

    alerts = {
        "critical": [],
        "stability": [],
        "performance": [],
        "data_quality": [],
        "general": []
    }

    for category in alerts.keys():
        log_file = alert_dir / f"alerts_{category}.jsonl"
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    alerts[category].append(json.loads(line))

    return alerts


def generate_resource_charts(metrics, output_dir):
    """生成資源使用圖表"""
    if not metrics:
        return

    timestamps = [datetime.fromisoformat(m['timestamp']) for m in metrics]

    # CPU 使用率
    cpu_usage = [m['system_resources']['cpu']['percent_avg'] for m in metrics]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, cpu_usage, label='CPU Usage %', linewidth=2)
    ax.set_xlabel('Time')
    ax.set_ylabel('CPU Usage (%)')
    ax.set_title('CPU Usage Over Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / 'cpu_usage.png', dpi=150)
    plt.close()

    # 記憶體使用率
    mem_usage = [m['system_resources']['memory']['percent'] for m in metrics]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, mem_usage, label='Memory Usage %', linewidth=2, color='orange')
    ax.set_xlabel('Time')
    ax.set_ylabel('Memory Usage (%)')
    ax.set_title('Memory Usage Over Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / 'memory_usage.png', dpi=150)
    plt.close()

    # 磁碟使用率
    disk_usage = [m['system_resources']['disk']['percent'] for m in metrics]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, disk_usage, label='Disk Usage %', linewidth=2, color='green')
    ax.set_xlabel('Time')
    ax.set_ylabel('Disk Usage (%)')
    ax.set_title('Disk Usage Over Time')
    ax.grid(True, alpha=0.3)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / 'disk_usage.png', dpi=150)
    plt.close()


def generate_html_report(test_id, metrics, alerts, output_dir):
    """生成 HTML 報告"""
    if not metrics:
        print("沒有足夠的數據生成報告")
        return

    # 計算統計
    start_time = metrics[0]['timestamp']
    end_time = metrics[-1]['timestamp']
    duration = (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds() / 3600

    cpu_usage = [m['system_resources']['cpu']['percent_avg'] for m in metrics]
    mem_usage = [m['system_resources']['memory']['percent'] for m in metrics]
    disk_usage = [m['system_resources']['disk']['percent'] for m in metrics]

    # 載入告警統計
    alert_summary_file = Path("/Users/latteine/Documents/coding/finance/monitoring/test_results/alerts/alert_summary.json")
    if alert_summary_file.exists():
        with open(alert_summary_file, 'r') as f:
            alert_summary = json.load(f)
    else:
        alert_summary = {"total": 0, "by_category": {}, "by_severity": {}}

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Long Run Test Report - {test_id}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .summary-box {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric.success {{
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
        }}
        .metric.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .chart {{
            margin: 20px 0;
            text-align: center;
        }}
        .chart img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        .status-pass {{
            color: #28a745;
            font-weight: bold;
        }}
        .status-fail {{
            color: #dc3545;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Long Run Test Report</h1>

        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 4px; margin-bottom: 20px;">
            <strong>Test ID:</strong> {test_id}<br>
            <strong>Start Time:</strong> {start_time}<br>
            <strong>End Time:</strong> {end_time}<br>
            <strong>Duration:</strong> {duration:.2f} hours<br>
            <strong>Data Points:</strong> {len(metrics)}
        </div>

        <h2>📊 Summary</h2>
        <div class="summary-box">
            <div class="metric success">
                <div class="metric-label">Test Duration</div>
                <div class="metric-value">{duration:.1f}h</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg CPU Usage</div>
                <div class="metric-value">{sum(cpu_usage)/len(cpu_usage):.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Memory Usage</div>
                <div class="metric-value">{sum(mem_usage)/len(mem_usage):.1f}%</div>
            </div>
            <div class="metric {'warning' if alert_summary['total'] > 10 else 'success'}">
                <div class="metric-label">Total Alerts</div>
                <div class="metric-value">{alert_summary['total']}</div>
            </div>
        </div>

        <h2>💻 Resource Usage Statistics</h2>
        <table>
            <tr>
                <th>Resource</th>
                <th>Min</th>
                <th>Max</th>
                <th>Avg</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>CPU (%)</td>
                <td>{min(cpu_usage):.2f}</td>
                <td>{max(cpu_usage):.2f}</td>
                <td>{sum(cpu_usage)/len(cpu_usage):.2f}</td>
                <td class="{'status-pass' if max(cpu_usage) < 80 else 'status-fail'}">
                    {'PASS' if max(cpu_usage) < 80 else 'WARN'}
                </td>
            </tr>
            <tr>
                <td>Memory (%)</td>
                <td>{min(mem_usage):.2f}</td>
                <td>{max(mem_usage):.2f}</td>
                <td>{sum(mem_usage)/len(mem_usage):.2f}</td>
                <td class="{'status-pass' if max(mem_usage) < 85 else 'status-fail'}">
                    {'PASS' if max(mem_usage) < 85 else 'WARN'}
                </td>
            </tr>
            <tr>
                <td>Disk (%)</td>
                <td>{min(disk_usage):.2f}</td>
                <td>{max(disk_usage):.2f}</td>
                <td>{sum(disk_usage)/len(disk_usage):.2f}</td>
                <td class="{'status-pass' if max(disk_usage) < 90 else 'status-fail'}">
                    {'PASS' if max(disk_usage) < 90 else 'WARN'}
                </td>
            </tr>
        </table>

        <h2>📈 Resource Usage Charts</h2>
        <div class="chart">
            <img src="cpu_usage.png" alt="CPU Usage">
        </div>
        <div class="chart">
            <img src="memory_usage.png" alt="Memory Usage">
        </div>
        <div class="chart">
            <img src="disk_usage.png" alt="Disk Usage">
        </div>

        <h2>🚨 Alert Summary</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Count</th>
            </tr>
    """

    for category, count in alert_summary.get('by_category', {}).items():
        html_content += f"""
            <tr>
                <td>{category.upper()}</td>
                <td>{count}</td>
            </tr>
        """

    html_content += """
        </table>

        <h2>📋 Test Results</h2>
        <table>
            <tr>
                <th>Test Category</th>
                <th>Criteria</th>
                <th>Result</th>
            </tr>
    """

    # 評估測試結果
    test_results = [
        ("Stability", "No critical alerts", "PASS" if alert_summary.get('by_severity', {}).get('critical', 0) == 0 else "FAIL"),
        ("Performance", "CPU < 80%", "PASS" if max(cpu_usage) < 80 else "FAIL"),
        ("Performance", "Memory < 85%", "PASS" if max(mem_usage) < 85 else "FAIL"),
        ("Performance", "Disk < 90%", "PASS" if max(disk_usage) < 90 else "FAIL"),
        ("Duration", f"Run for {duration:.1f}h", "PASS"),
    ]

    for category, criteria, result in test_results:
        status_class = "status-pass" if result == "PASS" else "status-fail"
        html_content += f"""
            <tr>
                <td>{category}</td>
                <td>{criteria}</td>
                <td class="{status_class}">{result}</td>
            </tr>
        """

    html_content += f"""
        </table>

        <div class="footer">
            Generated: {datetime.now().isoformat()}<br>
            Crypto Market Analyzer - Long Run Test System
        </div>
    </div>
</body>
</html>
    """

    # 儲存 HTML 報告
    report_file = output_dir / "test_report.html"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML 報告已生成: {report_file}")


def main():
    """主程式"""
    if len(sys.argv) < 2:
        print("使用方式: python generate_test_report.py <test_id>")
        sys.exit(1)

    test_id = sys.argv[1]
    output_dir = Path(f"/Users/latteine/Documents/coding/finance/monitoring/test_results/{test_id}")

    if not output_dir.exists():
        print(f"測試目錄不存在: {output_dir}")
        sys.exit(1)

    print(f"=== 生成測試報告 ===")
    print(f"測試 ID: {test_id}")
    print(f"輸出目錄: {output_dir}")

    # 載入數據
    print("\n載入監控數據...")
    metrics = load_metrics_timeseries(test_id)
    print(f"載入了 {len(metrics)} 個數據點")

    print("\n載入告警記錄...")
    alerts = load_alert_logs()

    # 生成圖表
    print("\n生成資源使用圖表...")
    generate_resource_charts(metrics, output_dir)

    # 生成 HTML 報告
    print("\n生成 HTML 報告...")
    generate_html_report(test_id, metrics, alerts, output_dir)

    print("\n✅ 報告生成完成！")


if __name__ == "__main__":
    main()
