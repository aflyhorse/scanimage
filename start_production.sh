#!/bin/bash

# 生产环境启动脚本（根目录部署）
# 使用方法: ./start_production.sh

echo "Starting ScanImage application (Production)..."

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "No .env file found, copying .env.example as .env"
    cp .env.example .env
    echo "Please edit .env file to configure your application"
    exit 1
fi

# 显示配置信息
echo "Configuration:"
echo "- Loading environment from .env file"
echo "- Application will be available at the configured HOST:PORT"
echo ""

# 创建必要的目录
mkdir -p logs uploads processed

# 启动Gunicorn
echo "Starting Gunicorn server..."
gunicorn --config gunicorn.conf.py app:app