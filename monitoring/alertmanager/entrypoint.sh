#!/bin/sh
# Alertmanager 啟動腳本
# 用於替換配置檔案中的環境變數

set -e

echo "替換 Alertmanager 配置中的環境變數..."

# 使用 sed 替換環境變數（Alpine 自帶 sed）
sed -e "s|\${SMTP_HOST}|${SMTP_HOST}|g" \
    -e "s|\${SMTP_PORT}|${SMTP_PORT}|g" \
    -e "s|\${SMTP_USER}|${SMTP_USER}|g" \
    -e "s|\${SMTP_PASSWORD}|${SMTP_PASSWORD}|g" \
    -e "s|\${SMTP_FROM}|${SMTP_FROM}|g" \
    -e "s|\${ALERT_EMAIL_TO}|${ALERT_EMAIL_TO}|g" \
    /etc/alertmanager/alertmanager.yml.template > /etc/alertmanager/alertmanager.yml

echo "配置檔案已更新："
cat /etc/alertmanager/alertmanager.yml | head -20

# 啟動 Alertmanager
exec /bin/alertmanager "$@"
