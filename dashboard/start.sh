#!/bin/bash

# Crypto Market Analyzer Dashboard 啟動腳本

echo "=================================="
echo "Crypto Market Analyzer Dashboard"
echo "=================================="
echo ""

# 檢查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安裝"
    exit 1
fi

# 檢查依賴
if ! python3 -c "import dash" &> /dev/null; then
    echo "⚠️  依賴未安裝，正在安裝..."
    pip install -r requirements.txt
fi

# 檢查資料庫連接
echo "🔍 檢查資料庫連接..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='crypto_db',
        user='crypto',
        password='crypto_pass'
    )
    print('✅ 資料庫連接成功')
    conn.close()
except Exception as e:
    print(f'❌ 資料庫連接失敗: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "請確認 PostgreSQL 正在運行"
    exit 1
fi

echo ""
echo "🚀 啟動 Dashboard..."
echo "📊 訪問網址: http://localhost:8050"
echo ""
echo "按 Ctrl+C 停止服務"
echo ""

# 啟動應用
python3 app.py
