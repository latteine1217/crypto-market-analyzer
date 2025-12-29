#!/usr/bin/env python3
"""
簡易告警 Webhook 接收器
用於記錄測試期間的告警事件
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# 告警日誌目錄
ALERT_LOG_DIR = Path("/Users/latteine/Documents/coding/finance/monitoring/test_results/alerts")
ALERT_LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_alert(alert_data, category="general"):
    """記錄告警到檔案"""
    timestamp = datetime.now().isoformat()

    # 時間序列日誌
    log_file = ALERT_LOG_DIR / f"alerts_{category}.jsonl"
    with open(log_file, 'a') as f:
        f.write(json.dumps({
            "timestamp": timestamp,
            "data": alert_data
        }) + '\n')

    # 彙總統計
    summary_file = ALERT_LOG_DIR / "alert_summary.json"
    if summary_file.exists():
        with open(summary_file, 'r') as f:
            summary = json.load(f)
    else:
        summary = {"total": 0, "by_category": {}, "by_severity": {}}

    summary["total"] += 1
    summary["by_category"][category] = summary["by_category"].get(category, 0) + 1

    # 統計嚴重程度
    for alert in alert_data.get("alerts", []):
        severity = alert.get("labels", {}).get("severity", "unknown")
        summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"[{timestamp}] [{category.upper()}] Alert logged")


@app.route('/webhook', methods=['POST'])
def webhook_general():
    """一般告警接收"""
    data = request.json
    log_alert(data, "general")
    return jsonify({"status": "ok"}), 200


@app.route('/webhook/critical', methods=['POST'])
def webhook_critical():
    """嚴重告警接收"""
    data = request.json
    log_alert(data, "critical")

    # 輸出到控制台
    print("\n" + "=" * 80)
    print("🚨 CRITICAL ALERT 🚨")
    for alert in data.get("alerts", []):
        print(f"Alert: {alert.get('labels', {}).get('alertname')}")
        print(f"Summary: {alert.get('annotations', {}).get('summary')}")
        print(f"Description: {alert.get('annotations', {}).get('description')}")
    print("=" * 80 + "\n")

    return jsonify({"status": "ok"}), 200


@app.route('/webhook/stability', methods=['POST'])
def webhook_stability():
    """穩定性測試告警"""
    data = request.json
    log_alert(data, "stability")
    return jsonify({"status": "ok"}), 200


@app.route('/webhook/performance', methods=['POST'])
def webhook_performance():
    """性能測試告警"""
    data = request.json
    log_alert(data, "performance")
    return jsonify({"status": "ok"}), 200


@app.route('/webhook/data_quality', methods=['POST'])
def webhook_data_quality():
    """資料品質告警"""
    data = request.json
    log_alert(data, "data_quality")
    return jsonify({"status": "ok"}), 200


@app.route('/health', methods=['GET'])
def health():
    """健康檢查"""
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    print("Alert Webhook Server starting...")
    print(f"Alert logs will be saved to: {ALERT_LOG_DIR}")
    app.run(host='0.0.0.0', port=9099, debug=False)
