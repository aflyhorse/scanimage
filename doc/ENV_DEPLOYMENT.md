# 环境变量和 Gunicorn 部署指南

## 环境变量配置

### 1. 配置文件说明

| 文件 | 用途 | 说明 |
|-----|-----|-----|
| `.env.example` | 模板文件 | 标准部署的环境变量模板 |
| `.env.subdirectory` | 子目录模板 | 子目录部署的环境变量模板 |
| `.env` | 实际配置 | 运行时使用的环境变量文件（不包含在版本控制中） |

### 2. 环境变量说明

```bash
# Flask应用配置
FLASK_APP=app.py                    # Flask应用入口
FLASK_ENV=production                # 环境模式：development/production
SECRET_KEY=your-secret-key          # 应用密钥（生产环境必须修改）

# 子目录部署配置
SCRIPT_NAME=/scanimage              # 子路径前缀，根目录部署时为空

# 服务器配置
HOST=127.0.0.1                     # 绑定地址
PORT=5000                           # 端口号
WORKERS=4                           # Gunicorn worker 进程数

# 文件配置
MAX_CONTENT_LENGTH=20971520         # 最大文件大小（字节）
UPLOAD_FOLDER=uploads               # 上传文件夹
PROCESSED_FOLDER=processed          # 处理后文件夹

# 日志配置
LOG_LEVEL=INFO                      # 日志级别
LOG_FILE=logs/scanimage.log         # 日志文件路径
```

## 部署方式

### 1. 根目录部署

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置（重要：修改 SECRET_KEY）
nano .env

# 启动生产服务器
./start_production.sh
```

### 2. 子目录部署

```bash
# 使用子目录启动脚本（自动处理配置）
./start_subdirectory.sh

# 或手动配置
cp .env.subdirectory .env
nano .env  # 根据需要调整配置
gunicorn --config gunicorn.conf.py app:app
```

## Gunicorn 配置

### 配置文件：`gunicorn.conf.py`

Gunicorn 配置会自动读取环境变量：

- 服务器绑定：`HOST:PORT`
- Worker 数量：`WORKERS`
- 日志配置：`LOG_LEVEL`, `LOG_FILE`
- 环境传递：`SCRIPT_NAME`, `SECRET_KEY` 等

### 自动功能

1. **环境变量加载**：应用启动时自动加载 `.env` 文件
2. **目录创建**：自动创建 `logs`, `uploads`, `processed` 目录
3. **配置验证**：启动脚本会检查必要的配置文件

## 启动脚本说明

| 脚本 | 用途 | 环境 |
|-----|-----|-----|
| `start.sh` | 开发环境 | Development |
| `start_production.sh` | 生产环境（根目录） | Production |
| `start_subdirectory.sh` | 子目录部署 | Production |

## 生产环境注意事项

### 1. 安全配置

```bash
# 生成强密钥
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# HTTPS 环境下的安全设置
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
```

### 2. 性能优化

```bash
# Worker 数量建议
WORKERS=$((2 * $(nproc) + 1))  # CPU核数 * 2 + 1

# 文件大小限制
MAX_CONTENT_LENGTH=20971520    # 20MB，根据需要调整
```

### 3. 监控和日志

```bash
# 日志轮转（建议配置 logrotate）
LOG_FILE=logs/scanimage.log

# 系统服务配置（可选）
sudo systemctl enable scanimage
sudo systemctl start scanimage
```

## 故障排除

### 常见问题

1. **环境变量未生效**
   - 检查 `.env` 文件是否存在
   - 确认 `python-dotenv` 已安装
   - 验证变量名称拼写

2. **子目录路径问题**
   - 确认 `SCRIPT_NAME` 设置正确
   - 检查反向代理配置
   - 验证前端 API 路径

3. **权限问题**
   - 确保启动脚本有执行权限
   - 检查日志目录写权限
   - 验证上传目录权限

### 调试命令

```bash
# 查看环境变量
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(dict(os.environ))"

# 测试配置
gunicorn --config gunicorn.conf.py --check-config app:app

# 查看进程
ps aux | grep gunicorn

# 查看日志
tail -f logs/scanimage.log
```

## 系统服务配置（可选）

创建 systemd 服务文件 `/etc/systemd/system/scanimage.service`：

```ini
[Unit]
Description=ScanImage Web Application
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/scanimage
Environment=PATH=/path/to/scanimage/.venv/bin
ExecStart=/path/to/scanimage/start_production.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable scanimage
sudo systemctl start scanimage
```
