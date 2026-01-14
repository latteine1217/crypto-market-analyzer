#!/usr/bin/env python3
"""
告警 Webhook 處理器
接收 Alertmanager 的 webhook，生成 K 線圖並發送郵件

職責：
1. 接收 Alertmanager webhook
2. 解析告警資訊
3. 生成相關的 K 線圖附件
4. 發送帶附件的郵件告警
"""
from flask import Flask, request, jsonify
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import os
import sys

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "data-analyzer" / "src"))

from loguru import logger
from alert_chart_generator import AlertChartGenerator

# 嘗試導入 EmailSender（可選）
EMAIL_AVAILABLE = False
try:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "data-analyzer" / "src"))
    from reports.email_sender import EmailSender as _EmailSender
    EMAIL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"EmailSender not available, email sending disabled: {e}")
    _EmailSender = None

app = Flask(__name__)

# === 配置 ===
DB_CONN_STR = (
    f"host={os.getenv('DB_HOST', 'localhost')} "
    f"port={os.getenv('DB_PORT', '5432')} "
    f"dbname={os.getenv('DB_NAME', 'crypto_db')} "
    f"user={os.getenv('DB_USER', 'crypto')} "
    f"password={os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'crypto_pass'))}"
)

CHART_OUTPUT_DIR = Path(os.getenv('ALERT_CHART_DIR', '/tmp/alert_charts'))
ALERT_LOG_DIR = Path(os.getenv('ALERT_LOG_DIR', '/tmp/alert_logs'))
ALERT_LOG_DIR.mkdir(parents=True, exist_ok=True)

# === 初始化 ===
chart_generator = AlertChartGenerator(DB_CONN_STR, CHART_OUTPUT_DIR)

email_sender = None
if EMAIL_AVAILABLE and _EmailSender:
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if smtp_user and smtp_password:
        email_sender = _EmailSender(
            smtp_host=os.getenv('SMTP_HOST', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('SMTP_PORT', 587)),
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            use_tls=True
        )
        logger.info("✓ EmailSender initialized")
    else:
        logger.warning("SMTP credentials not set, email sending disabled")


def extract_symbol_from_alert(alert: Dict) -> Optional[str]:
    """從告警中提取交易對符號"""
    labels = alert.get('labels', {})
    
    # 嘗試從 label 中獲取 symbol
    symbol = labels.get('symbol')
    if symbol:
        return symbol
    
    # 嘗試從 alertname 中推斷（如 PriceSpike, PriceDrop）
    alertname = labels.get('alertname', '')
    if 'BTC' in alertname:
        return 'BTCUSDT'
    elif 'ETH' in alertname:
        return 'ETHUSDT'
    
    # 嘗試從 annotations 中提取
    annotations = alert.get('annotations', {})
    for field in ['summary', 'description']:
        text = annotations.get(field, '')
        if 'BTC' in text:
            return 'BTCUSDT'
        elif 'ETH' in text:
            return 'ETHUSDT'
    
    return None


def should_generate_chart(alertname: str) -> bool:
    """判斷是否需要生成 K 線圖"""
    # 價格相關告警需要 K 線圖
    price_related = [
        'PriceSpike', 'PriceDrop', 'ExtremePriceVolatility', 'PriceStagnant',
        'MADAnomalyDetected', 'MADSevereAnomaly'
    ]
    
    return alertname in price_related


def generate_alert_charts(alert: Dict) -> List[Path]:
    """
    根據告警類型生成相應的圖表

    Returns:
        圖表檔案路徑列表
    """
    charts = []
    
    try:
        alertname = alert.get('labels', {}).get('alertname', '')
        symbol = extract_symbol_from_alert(alert)
        
        if not symbol:
            logger.warning(f"Cannot extract symbol from alert: {alertname}")
            return charts
        
        if not should_generate_chart(alertname):
            logger.info(f"Alert {alertname} does not require chart")
            return charts
        
        logger.info(f"Generating charts for {alertname} ({symbol})")
        
        # 生成蠟燭圖（較長時間範圍以確保包含歷史資料）
        annotation = alert.get('annotations', {}).get('summary', '')
        chart1 = chart_generator.generate_candlestick_chart(
            symbol=symbol,
            exchange='bybit',
            timeframe='1h',
            hours_back=240,  # 10 天，確保包含歷史資料
            title=f"{symbol} - {alertname}",
            annotation=f"⚠️ {annotation}"
        )
        if chart1:
            charts.append(chart1)
        
        # 生成價格對比圖（使用 1h 資料）
        chart2 = chart_generator.generate_price_comparison_chart(
            symbol=symbol,
            exchange='bybit',
            hours_back=240,  # 10 天
            timeframe='1h',  # 使用 1h 資料
            title=f"{symbol} Price Movement - {alertname}",
            highlight_recent_hours=24  # 突出最近 24 小時
        )
        if chart2:
            charts.append(chart2)
        
        logger.info(f"✓ Generated {len(charts)} charts for {alertname}")
    
    except Exception as e:
        logger.error(f"Failed to generate charts: {e}")
        import traceback
        traceback.print_exc()
    
    return charts


def format_alert_email_html(alert_data: Dict, charts: List[Path]) -> str:
    """
    生成告警郵件的 HTML 內容

    Args:
        alert_data: Alertmanager webhook 資料
        charts: 圖表檔案路徑列表

    Returns:
        HTML 內容
    """
    alerts = alert_data.get('alerts', [])
    
    # 提取共同屬性
    group_labels = alert_data.get('groupLabels', {})
    alertname = group_labels.get('alertname', 'Unknown')
    
    # 統計告警數量
    firing_count = sum(1 for a in alerts if a.get('status') == 'firing')
    resolved_count = sum(1 for a in alerts if a.get('status') == 'resolved')
    
    # 判斷嚴重程度
    severity_levels = [a.get('labels', {}).get('severity', 'info') for a in alerts]
    highest_severity = 'critical' if 'critical' in severity_levels else (
        'warning' if 'warning' in severity_levels else 'info'
    )
    
    # 顏色主題
    severity_colors = {
        'critical': ('#d32f2f', '🚨'),
        'warning': ('#f57c00', '⚠️'),
        'info': ('#1976d2', 'ℹ️')
    }
    color, emoji = severity_colors.get(highest_severity, ('#1976d2', 'ℹ️'))
    
    # 構建 HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 30px;
            }}
            .header {{
                background-color: {color};
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                margin: -30px -30px 20px -30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .summary {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .alert-box {{
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
                margin: 15px 0;
                background-color: #fafafa;
            }}
            .alert-box h3 {{
                margin-top: 0;
                color: {color};
            }}
            .label {{
                display: inline-block;
                padding: 4px 8px;
                margin: 2px;
                background-color: #e0e0e0;
                border-radius: 3px;
                font-size: 12px;
            }}
            .status-firing {{
                background-color: #ffcdd2;
                color: #c62828;
                font-weight: bold;
            }}
            .status-resolved {{
                background-color: #c8e6c9;
                color: #2e7d32;
                font-weight: bold;
            }}
            .charts {{
                margin-top: 30px;
            }}
            .chart-notice {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
                color: #666;
                text-align: center;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            table th {{
                background-color: #f5f5f5;
                padding: 10px;
                text-align: left;
                border-bottom: 2px solid #ddd;
            }}
            table td {{
                padding: 10px;
                border-bottom: 1px solid #eee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{emoji} Crypto Analyzer Alert</h1>
                <p style="margin: 5px 0 0 0; font-size: 14px;">
                    Alert: <strong>{alertname}</strong> | 
                    Severity: <strong>{highest_severity.upper()}</strong>
                </p>
            </div>
            
            <div class="summary">
                <strong>📊 Alert Summary</strong><br>
                Firing: <span class="status-firing">{firing_count}</span> | 
                Resolved: <span class="status-resolved">{resolved_count}</span> | 
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </div>
    """
    
    # 添加每個告警的詳細資訊
    for idx, alert in enumerate(alerts, 1):
        status = alert.get('status', 'unknown')
        labels = alert.get('labels', {})
        annotations = alert.get('annotations', {})
        
        status_class = 'status-firing' if status == 'firing' else 'status-resolved'
        
        html += f"""
            <div class="alert-box">
                <h3>Alert #{idx} - <span class="{status_class}">{status.upper()}</span></h3>
                <p><strong>Summary:</strong> {annotations.get('summary', 'N/A')}</p>
                <p><strong>Description:</strong> {annotations.get('description', 'N/A')}</p>
                
                <p><strong>Labels:</strong><br>
        """
        
        for key, value in labels.items():
            html += f'<span class="label">{key}: {value}</span> '
        
        starts_at = alert.get('startsAt', 'N/A')
        ends_at = alert.get('endsAt', 'N/A') if status == 'resolved' else 'Ongoing'
        
        html += f"""
                </p>
                <p style="font-size: 12px; color: #666;">
                    <strong>Started:</strong> {starts_at}<br>
                    <strong>Ends:</strong> {ends_at}
                </p>
            </div>
        """
    
    # 添加圖表說明
    if charts:
        html += f"""
            <div class="chart-notice">
                📈 <strong>Attached Charts:</strong> {len(charts)} chart(s) attached to this email
                <ul>
        """
        for chart_path in charts:
            html += f"<li>{chart_path.name}</li>"
        html += """
                </ul>
                <em>Please check the attachments to view the K-line charts.</em>
            </div>
        """
    
    # 添加頁尾
    html += """
            <div class="footer">
                <p>This is an automated alert from <strong>Crypto Market Analyzer</strong></p>
                <p>For more information, please check Grafana dashboards or Prometheus alerts.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def send_alert_email(alert_data: Dict, charts: List[Path]) -> bool:
    """
    發送告警郵件（帶圖表附件）

    Args:
        alert_data: Alertmanager webhook 資料
        charts: 圖表檔案路徑列表

    Returns:
        是否成功
    """
    if not email_sender:
        logger.warning("Email sender not configured, skipping email")
        return False
    
    try:
        # 提取告警資訊
        group_labels = alert_data.get('groupLabels', {})
        alertname = group_labels.get('alertname', 'Unknown Alert')
        
        # 判斷嚴重程度
        alerts = alert_data.get('alerts', [])
        severity_levels = [a.get('labels', {}).get('severity', 'info') for a in alerts]
        highest_severity = 'critical' if 'critical' in severity_levels else (
            'warning' if 'warning' in severity_levels else 'info'
        )
        
        # 構建郵件主旨
        severity_prefix = {
            'critical': '[🚨 CRITICAL]',
            'warning': '[⚠️ WARNING]',
            'info': '[ℹ️ INFO]'
        }
        
        subject = f"{severity_prefix.get(highest_severity, '[ALERT]')} Crypto Analyzer - {alertname}"
        
        # 生成 HTML 內容
        html_content = format_alert_email_html(alert_data, charts)
        
        # 收件人列表
        to_addresses = [os.getenv('ALERT_EMAIL_TO', os.getenv('SMTP_USER'))]
        
        # 發送郵件
        success = email_sender.send_report(
            to_addresses=to_addresses,
            subject=subject,
            html_content=html_content,
            attachments=charts if charts else None
        )
        
        if success:
            logger.info(f"✓ Alert email sent: {alertname}")
        else:
            logger.error(f"✗ Failed to send alert email: {alertname}")
        
        return success
    
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/webhook/alerts', methods=['POST'])
def webhook_alerts():
    """接收 Alertmanager webhook"""
    try:
        alert_data = request.json
        
        if not alert_data:
            logger.warning("Received empty alert data")
            return jsonify({"status": "error", "message": "Empty data"}), 400
        
        # 記錄告警到日誌
        timestamp = datetime.now().isoformat()
        log_file = ALERT_LOG_DIR / f"alerts_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        import json
        with open(log_file, 'a') as f:
            f.write(json.dumps({
                "timestamp": timestamp,
                "data": alert_data
            }) + '\n')
        
        logger.info(f"Received alert webhook: {alert_data.get('groupLabels', {})}")
        
        # 生成圖表
        charts = []
        for alert in alert_data.get('alerts', []):
            alert_charts = generate_alert_charts(alert)
            charts.extend(alert_charts)
        
        # 發送郵件
        email_sent = False
        if charts or alert_data.get('alerts'):
            email_sent = send_alert_email(alert_data, charts)
            logger.info(f"Email sent: {email_sent}")
        
        # 清理舊圖表（保留24小時）
        chart_generator.cleanup_old_charts(hours=24)
        
        return jsonify({
            "status": "ok",
            "charts_generated": len(charts),
            "email_sent": email_sent if charts else False
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing alert webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    return jsonify({
        "status": "healthy",
        "email_configured": email_sender is not None,
        "chart_dir": str(CHART_OUTPUT_DIR),
        "log_dir": str(ALERT_LOG_DIR)
    }), 200


if __name__ == '__main__':
    logger.info("Alert Webhook Handler starting...")
    logger.info(f"Chart output: {CHART_OUTPUT_DIR}")
    logger.info(f"Alert logs: {ALERT_LOG_DIR}")
    logger.info(f"Email configured: {email_sender is not None}")
    
    port = int(os.getenv('ALERT_WEBHOOK_PORT', 9100))
    app.run(host='0.0.0.0', port=port, debug=False)
