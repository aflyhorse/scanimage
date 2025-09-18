<!-- markdownlint-disable MD029 -->
# 图片透视校正Web应用

一个基于Flask的Web应用，用于对拍摄的照片进行透视校正和后处理，特别适用于扫描文档、名片、书页等场景。

## 功能特性

- **图片上传**: 支持 PNG, JPG, JPEG, GIF, BMP 格式
- **输出模式选择**:
  - 彩色模式：自动调色和白平衡
  - 黑白模式：高对比度，近白色底色
- **交互式区域选择**: 在图片上拖拽四个角点选择梯形区域
- **透视校正**: 将梯形区域校正为标准长方形
- **图像后处理**: 根据选择的模式进行相应的图像优化
- **旋转功能**: 支持左右旋转调整图片方向
- **一键下载**: 以时间戳命名的PNG格式下载

## 技术栈

- **后端**: Flask, OpenCV, PIL/Pillow, NumPy
- **前端**: Bootstrap 5, JavaScript Canvas API
- **部署**: Gunicorn (生产环境)

## 安装和运行

### 开发环境

1. 创建并激活虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 运行开发服务器：

```bash
python app.py
```

4. 打开浏览器访问: <http://localhost:5000>

### 生产部署

1. 使用Gunicorn运行：

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

2. 使用Docker部署：

```bash
docker build -t scanimage .
docker run -p 5000:5000 scanimage
```

3. 使用Nginx反向代理（推荐）：
参考 `deployment/nginx.conf` 配置文件

## 使用说明

1. **上传图片**: 点击"选择文件"上传照片，选择输出模式（彩色或黑白）
2. **选择区域**: 在图片上拖拽四个蓝色圆点，选择需要校正的梯形区域
3. **处理图片**: 点击"开始处理"按钮进行透视校正和图像优化
4. **调整方向**: 使用左右旋转按钮调整图片方向
5. **下载结果**: 点击"下载图片"保存处理后的图片

## API接口

### POST /upload

上传图片文件

**参数**:

- `file`: 图片文件 (multipart/form-data)

**返回**:

```json
{
    "success": true,
    "filename": "20240917_143022_image.jpg",
    "image_data": "base64_encoded_image_data"
}
```

### POST /process

处理图片透视校正

**参数**:

```json
{
    "filename": "uploaded_filename",
    "corners": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
    "color_mode": "color" // or "grayscale"
}
```

**返回**:

```json
{
    "success": true,
    "processed_filename": "20240917_143045.png",
    "image_data": "base64_encoded_processed_image"
}
```

### POST /rotate

旋转处理后的图片

**参数**:

```json
{
    "filename": "processed_filename",
    "angle": 90 // or -90
}
```

### GET /download/```<filename>```

下载处理后的图片

## 目录结构

```text
scanimage/
├── app.py                # Flask应用主文件
├── requirements.in       # 依赖包源文件
├── requirements.txt      # 锁定版本的依赖包
├── Dockerfile            # Docker配置文件
├── .env.example          # 环境变量示例
├── templates/            # HTML模板
│   └── index.html.jinja2
├── static/               # 静态文件
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── uploads/              # 上传文件目录
├── processed/            # 处理后文件目录
├── doc/                  # 文档目录
│   └── README.md
└── deployment/           # 部署配置
    ├── nginx.conf
    └── systemd.service
```

## 算法说明

### 透视校正算法

使用OpenCV的 `getPerspectiveTransform()` 和 `warpPerspective()` 函数：

1. 根据用户选择的四个角点计算透视变换矩阵
2. 计算校正后图像的最佳尺寸
3. 应用透视变换得到校正后的长方形图像

### 图像后处理

**彩色模式**:

- 自动白平衡：调整RGB三个通道的平均值到目标灰度
- 对比度增强：提高图像对比度
- 色彩增强：适度提高色彩饱和度

**黑白模式**:

- 转换为灰度图像
- 自适应阈值处理：增强文字与背景的对比度
- 形态学操作：清理噪点，改善图像质量

## 性能优化

- 图片大小限制：最大16MB
- 前端图片缩放显示，减少内存占用
- 异步处理，改善用户体验
- 自动清理临时文件

## 安全考虑

- 文件类型验证
- 文件名安全处理
- 文件大小限制
- 临时文件清理
- CSRF保护（生产环境需要）

## 许可证

GPLv3
