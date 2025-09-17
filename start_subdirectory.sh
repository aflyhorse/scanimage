#!/bin/bash

# 子目录部署启动脚本
# 使用方法: ./start_subdirectory.sh

echo "Starting ScanImage application for subdirectory deployment..."

# 检查 .env 文件是否存在，如果不存在则使用子目录示例配置
if [ ! -f .env ]; then
    echo "No .env file found, copying .env.subdirectory as .env"
    cp .env.subdirectory .env
fi

# 显示配置信息
echo "Configuration:"
echo "- Loading environment from .env file"
echo "- Application will be available at: http://your-domain.com/scanimage/"
echo "- Make sure Caddy is configured with Caddyfile.subdirectory"
echo ""

# 创建日志目录
mkdir -p logs

# 启动Gunicorn
echo "Starting Gunicorn server..."
gunicorn --config gunicorn.conf.py app:app