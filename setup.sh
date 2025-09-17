#!/bin/bash

# 项目设置脚本

echo "设置图片透视校正Web应用项目..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}' | awk -F. '{print $1"."$2}')
echo "检测到Python版本: $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "错误: 需要Python 3.8或更高版本"
    exit 1
fi

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
pip install -r requirements.txt

# 创建必要目录
echo "创建项目目录..."
mkdir -p uploads processed logs

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "创建环境配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件以配置您的环境"
fi

echo "项目设置完成！"
echo ""
echo "使用方法:"
echo "1. 开发环境: ./start.sh"
echo "2. 生产环境: gunicorn -w 4 -b 0.0.0.0:5000 app:app"
echo "3. Docker部署: docker build -t scanimage . && docker run -p 5000:5000 scanimage"
echo ""
echo "访问地址: http://localhost:5000"