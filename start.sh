#!/bin/bash

# 启动脚本 - 开发环境

echo "启动图片透视校正Web应用..."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖
echo "检查依赖包..."
pip install -r requirements.txt > /dev/null 2>&1

# 创建必要目录
mkdir -p uploads processed

# 设置环境变量
export FLASK_APP=app.py
export FLASK_ENV=development

echo "启动开发服务器..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"

# 启动Flask开发服务器
python app.py