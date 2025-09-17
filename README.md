# 图片透视校正Web应用

## 示例

<https://www.lunes.cn/scanimage>

## 快速开始

这是一个基于Flask的Web应用，用于对拍摄的照片进行透视校正和后处理。

### 1. 项目设置

```bash
./setup.sh
```

### 2. 启动应用

```bash
./start.sh
```

### 3. 访问应用

打开浏览器访问: <http://localhost:5000>

## 主要功能

1. **图片上传**: 支持多种图片格式
2. **模式选择**: 彩色/黑白处理模式
3. **区域选择**: 交互式选择梯形区域
4. **透视校正**: 自动将梯形校正为长方形
5. **图像优化**: 根据模式进行调色或对比度优化
6. **旋转调整**: 手动调整图片方向
7. **一键下载**: 保存为timestamp.png格式

## 技术特性

- 前端：Bootstrap 5 + Canvas API
- 后端：Flask + OpenCV + PIL
- 算法：透视变换、自适应阈值、白平衡
- 部署：Docker + Nginx + Gunicorn

## 目录结构

```text
scanimage/
├── app.py             # 主应用文件
├── start.sh           # 启动脚本
├── setup.sh           # 设置脚本
├── requirements.txt   # 依赖包
├── Dockerfile         # Docker配置
├── templates/         # HTML模板
├── static/            # 静态文件
├── uploads/           # 上传目录
├── processed/         # 处理结果目录
├── deployment/        # 部署配置
└── doc/               # 文档
```

## 生产部署

```bash
# Docker方式
docker build -t scanimage .
docker run -p 5000:5000 scanimage

# 或直接使用Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

详细文档请查看 `doc/README.md`

## 致谢

为了一叠醋（帮家里人把照片修成适合打印的图）包的饺子。

代码使用 Claude Sonnet 4 高速开发，全程仅使用 1.5 小时。只有这一段和顶上的示例部分是人工输入的。感谢 Anthropic 和 VSCode / GitHub Copilot.
