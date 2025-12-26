#!/bin/bash

# 驗證專案設定腳本

echo "=========================================="
echo "Crypto Market Analyzer - Setup Verification"
echo "=========================================="

# 檢查Docker
echo -n "Checking Docker... "
if command -v docker &> /dev/null; then
    echo "✓ Docker installed"
else
    echo "✗ Docker not found. Please install Docker first."
    exit 1
fi

# 檢查Docker Compose
echo -n "Checking Docker Compose... "
if command -v docker-compose &> /dev/null; then
    echo "✓ Docker Compose installed"
else
    echo "✗ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# 檢查Python
echo -n "Checking Python... "
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✓ Python $PYTHON_VERSION installed"
else
    echo "✗ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# 檢查.env檔案
echo -n "Checking .env file... "
if [ -f "collector-py/.env" ]; then
    echo "✓ .env file exists"
else
    echo "! .env file not found"
    echo "  Creating from .env.example..."
    cp collector-py/.env.example collector-py/.env
    echo "✓ .env file created"
fi

# 檢查Docker服務狀態
echo -n "Checking Docker services... "
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
    docker-compose ps
else
    echo "! Services are not running"
    echo "  Run 'make start' to start services"
fi

echo "=========================================="
echo "Verification completed!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Run 'make start' to start database and Redis"
echo "2. Run 'make install-collector' to install Python dependencies"
echo "3. Run 'make collector' to start data collection"
echo "4. Run 'make jupyter' to start Jupyter Lab"
