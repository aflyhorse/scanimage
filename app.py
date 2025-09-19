import os
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_bootstrap import Bootstrap5
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance
import base64
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# support subdirectory deployment
SCRIPT_NAME = os.environ.get("SCRIPT_NAME", "")
if SCRIPT_NAME:
    app.config["APPLICATION_ROOT"] = SCRIPT_NAME


app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your-secret-key-here")
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", "uploads")
app.config["PROCESSED_FOLDER"] = os.environ.get("PROCESSED_FOLDER", "processed")
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", "16777216"))
app.config["BOOTSTRAP_SERVE_LOCAL"] = True
bootstrap = Bootstrap5(app)

# Ensure upload and processed directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp"}


@app.context_processor
def inject_url_helpers():
    """提供模板中使用的URL辅助函数"""

    def static_url(filename):
        """生成包含子路径的静态文件URL"""
        script_root = request.script_root or ""
        static_url_path = url_for("static", filename=filename)
        return script_root + static_url_path

    return dict(static_url=static_url)


@app.context_processor
def inject_footer_config():
    """提供Footer配置"""
    return dict(
        footer_text=os.environ.get("FOOTER_TEXT", ""),
    )


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """主页面 - 图片上传界面"""
    return render_template("index.html.jinja2")


@app.route("/upload", methods=["POST"])
def upload_file():
    """处理图片上传"""
    if "file" not in request.files:
        return jsonify({"error": "没有文件被上传"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "没有选择文件"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Convert image to base64 for frontend display
        with open(filepath, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")

        return jsonify(
            {"success": True, "filename": filename, "image_data": img_base64}
        )

    return jsonify({"error": "不支持的文件格式"}), 400


@app.route("/process", methods=["POST"])
def process_image():
    """处理图像透视校正和后处理"""
    data = request.get_json()
    filename = data.get("filename")
    corners = data.get("corners")  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    color_mode = data.get("color_mode", "color")  # 'color' or 'grayscale'
    processing_option = data.get("processing_option", "adjusted")  # 新增处理选项

    if not filename or not corners:
        return jsonify({"error": "缺少必要参数"}), 400

    try:
        # Load image
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image = cv2.imread(image_path)
        if image is None:
            return jsonify({"error": "无法读取图像文件"}), 400

        # Perspective correction
        corrected_image = perspective_correction(image, corners)

        # Post-processing based on color mode and processing option
        if color_mode == "grayscale":
            # 使用统一的黑白图像处理函数
            processed_image = process_grayscale_image(
                corrected_image, processing_option
            )
        else:  # color mode
            # 使用统一的彩色图像处理函数
            processed_image = process_color_image(corrected_image, processing_option)

        # Save processed image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processed_filename = f"{timestamp}.png"
        processed_path = os.path.join(
            app.config["PROCESSED_FOLDER"], processed_filename
        )
        cv2.imwrite(processed_path, processed_image)

        # Convert to base64 for frontend
        _, buffer = cv2.imencode(".png", processed_image)
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify(
            {
                "success": True,
                "processed_filename": processed_filename,
                "image_data": img_base64,
            }
        )

    except Exception as e:
        return jsonify({"error": f"图像处理失败: {str(e)}"}), 500


@app.route("/reprocess", methods=["POST"])
def reprocess_image():
    """重新处理已上传的图像，使用新的处理选项"""
    data = request.get_json()
    filename = data.get("filename")
    corners = data.get("corners")
    color_mode = data.get("color_mode", "color")
    processing_option = data.get("processing_option", "adjusted")

    if not filename or not corners:
        return jsonify({"error": "缺少必要参数"}), 400

    try:
        # Load original image
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image = cv2.imread(image_path)
        if image is None:
            return jsonify({"error": "无法读取图像文件"}), 400

        # Perspective correction
        corrected_image = perspective_correction(image, corners)

        # Post-processing based on color mode and processing option
        if color_mode == "grayscale":
            # 使用统一的黑白图像处理函数
            processed_image = process_grayscale_image(
                corrected_image, processing_option
            )
        else:  # color mode
            # 使用统一的彩色图像处理函数
            processed_image = process_color_image(corrected_image, processing_option)

        # Save processed image (overwrite the current processed image)
        if data.get("processed_filename"):
            processed_filename = data.get("processed_filename")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            processed_filename = f"{timestamp}.png"

        processed_path = os.path.join(
            app.config["PROCESSED_FOLDER"], processed_filename
        )
        cv2.imwrite(processed_path, processed_image)

        # Convert to base64 for frontend
        _, buffer = cv2.imencode(".png", processed_image)
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify(
            {
                "success": True,
                "processed_filename": processed_filename,
                "image_data": img_base64,
            }
        )

    except Exception as e:
        return jsonify({"error": f"重新处理失败: {str(e)}"}), 500


@app.route("/rotate", methods=["POST"])
def rotate_image():
    """旋转图像"""
    data = request.get_json()
    filename = data.get("filename")
    angle = data.get("angle", 90)  # 90 or -90 degrees

    if not filename:
        return jsonify({"error": "缺少文件名参数"}), 400

    try:
        image_path = os.path.join(app.config["PROCESSED_FOLDER"], filename)
        image = cv2.imread(image_path)

        if image is None:
            return jsonify({"error": "无法读取图像文件"}), 400

        # Rotate image
        if angle == 90:
            rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == -90:
            rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return jsonify({"error": "不支持的旋转角度"}), 400

        # Save rotated image (overwrite)
        cv2.imwrite(image_path, rotated)

        # Convert to base64 for frontend
        _, buffer = cv2.imencode(".png", rotated)
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({"success": True, "image_data": img_base64})

    except Exception as e:
        return jsonify({"error": f"旋转失败: {str(e)}"}), 500


@app.route("/download/<filename>")
def download_file(filename):
    """下载处理后的图像"""
    try:
        file_path = os.path.join(app.config["PROCESSED_FOLDER"], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": f"下载失败: {str(e)}"}), 500


def perspective_correction(image, corners):
    """透视校正"""
    # Convert corners to numpy array
    src_points = np.array(corners, dtype=np.float32)

    # 简化的角点排序：按照左上、右上、右下、左下的顺序
    # 计算Y轴重心来分离上下两组点
    center_y = np.mean(src_points[:, 1])

    # 按照位置分类
    top_points = []
    bottom_points = []

    for point in src_points:
        if point[1] < center_y:
            top_points.append(point)
        else:
            bottom_points.append(point)

    # 确保每个部分有2个点
    if len(top_points) != 2 or len(bottom_points) != 2:
        # 如果分类失败，使用原始顺序
        ordered_points = src_points
    else:
        # 在上方点中，左边的是左上，右边的是右上
        top_points.sort(key=lambda p: p[0])
        # 在下方点中，左边的是左下，右边的是右下
        bottom_points.sort(key=lambda p: p[0])

        # 按照左上、右上、右下、左下的顺序排列
        ordered_points = np.array(
            [
                top_points[0],  # 左上
                top_points[1],  # 右上
                bottom_points[1],  # 右下
                bottom_points[0],  # 左下
            ],
            dtype=np.float32,
        )

    # Calculate the width and height of the corrected image
    width_top = np.linalg.norm(ordered_points[1] - ordered_points[0])
    width_bottom = np.linalg.norm(ordered_points[2] - ordered_points[3])
    width = max(int(width_top), int(width_bottom))

    height_left = np.linalg.norm(ordered_points[3] - ordered_points[0])
    height_right = np.linalg.norm(ordered_points[2] - ordered_points[1])
    height = max(int(height_left), int(height_right))

    # Define destination points for a rectangle
    dst_points = np.array(
        [[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32
    )

    # Calculate perspective transformation matrix
    matrix = cv2.getPerspectiveTransform(ordered_points, dst_points)

    # Apply perspective transformation
    corrected = cv2.warpPerspective(image, matrix, (width, height))

    return corrected


def histogram_equalization(image, clip_limit=3.0, tile_grid_size=(8, 8)):
    """直方图均衡化处理，支持彩色和灰度图像"""
    # 判断是彩色还是灰度图像
    if len(image.shape) == 3:
        # 彩色图像：在LAB色彩空间中对L通道进行均衡化
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # 对L通道进行CLAHE（限制对比度自适应直方图均衡化）
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        l_equalized = clahe.apply(l_channel)

        # 重新合并通道
        lab_equalized = cv2.merge([l_equalized, a_channel, b_channel])

        # 转换回BGR色彩空间
        result = cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2BGR)

        return result
    else:
        # 灰度图像：直接进行CLAHE
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(image)


def apply_white_balance(image, mode="color"):
    """
    统一的白平衡处理函数

    Args:
        image: 输入图像 (BGR格式)
        mode: 处理模式
            - "color": 彩色图像白平衡，使用加权目标和极值过滤
            - "grayscale": 灰度图像白平衡，使用简单目标和保守处理

    Returns:
        处理后的图像 (BGR格式)
    """
    # Convert BGR to RGB for PIL processing
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    # 分离RGB通道
    r, g, b = pil_image.split()
    r_array = np.array(r, dtype=np.float32)
    g_array = np.array(g, dtype=np.float32)
    b_array = np.array(b, dtype=np.float32)

    if mode == "color":
        # 彩色模式：使用robust mean和加权目标
        def get_robust_mean(channel_array):
            # 排除极值，只考虑中间范围的像素
            mask = (channel_array > 30) & (channel_array < 225)
            if np.sum(mask) > 0:
                return np.mean(channel_array[mask])
            else:
                return np.mean(channel_array)

        r_avg = get_robust_mean(r_array)
        g_avg = get_robust_mean(g_array)
        b_avg = get_robust_mean(b_array)

        # 使用 Rec.601 加权平均
        target = r_avg * 0.299 + g_avg * 0.587 + b_avg * 0.114

        # 因子限制范围
        factor_range = (0.8, 1.5)

    else:  # mode == "grayscale"
        # 灰度模式：使用简单mean和保守目标
        r_avg = np.mean(r_array)
        g_avg = np.mean(g_array)
        b_avg = np.mean(b_array)

        # 使用 Rec.601 加权平均
        target = r_avg * 0.299 + g_avg * 0.587 + b_avg * 0.114

        # 更保守的因子限制，保留更多细节
        factor_range = (0.85, 1.5)

    # 计算调整因子
    r_factor = target / r_avg if r_avg > 0 else 1
    g_factor = target / g_avg if g_avg > 0 else 1
    b_factor = target / b_avg if b_avg > 0 else 1

    # 应用因子限制
    r_factor = min(max(r_factor, factor_range[0]), factor_range[1])
    g_factor = min(max(g_factor, factor_range[0]), factor_range[1])
    b_factor = min(max(b_factor, factor_range[0]), factor_range[1])

    # 应用白平衡调整
    r_balanced = np.clip(r_array * r_factor, 0, 255).astype(np.uint8)
    g_balanced = np.clip(g_array * g_factor, 0, 255).astype(np.uint8)
    b_balanced = np.clip(b_array * b_factor, 0, 255).astype(np.uint8)

    # 重新构建图像
    r_img = Image.fromarray(r_balanced)
    g_img = Image.fromarray(g_balanced)
    b_img = Image.fromarray(b_balanced)
    balanced = Image.merge("RGB", (r_img, g_img, b_img))

    # Convert back to BGR for OpenCV
    final_array = np.array(balanced)
    return cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)


def lab_enhance(image, l_adjust=1.0, ab_adjust=1.0, equalization=False):
    """
    LAB色彩空间增强函数，统一处理亮度、色度调整和均衡化

    Args:
        image: 输入图像 (BGR格式)
        l_adjust: L通道(亮度)调整系数，1.0表示不调整
        ab_adjust: A和B通道(色度)调整系数，1.0表示不调整，>1.0增加饱和度
        equalization: 是否进行直方图均衡化

    Returns:
        处理后的图像 (BGR格式)
    """
    # 如果需要均衡化，先进行直方图均衡化
    if equalization:
        image = histogram_equalization(image)

    # 转换为LAB色彩空间
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # L通道(亮度)调整
    if l_adjust != 1.0:
        l_channel = np.clip(l_channel.astype(np.float32) * l_adjust, 0, 255).astype(
            np.uint8
        )

    # A和B通道(色度)调整
    if ab_adjust != 1.0:
        # A和B通道的值域是-128到127，需要特殊处理
        a_channel = np.clip(
            (a_channel.astype(np.float32) - 128) * ab_adjust + 128, 0, 255
        ).astype(np.uint8)
        b_channel = np.clip(
            (b_channel.astype(np.float32) - 128) * ab_adjust + 128, 0, 255
        ).astype(np.uint8)

    # 重新合并LAB通道
    lab_enhanced = cv2.merge([l_channel, a_channel, b_channel])

    # 转换回BGR色彩空间
    bgr_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    return bgr_enhanced


def process_color_image(image, mode="adjusted"):
    """
    统一的彩色图像处理函数

    Args:
        image: 输入图像 (BGR格式)
        mode: 处理模式
            - "original": 原色彩模式，仅做轻微调整
            - "adjusted": 调色模式，使用lab_enhance进行增强
            - "enhanced": 暴力上色模式，开启均衡化的强化处理

    Returns:
        处理后的图像 (BGR格式)
    """
    if mode == "original":
        # 原色彩模式：使用lab_enhance进行轻微调整
        return lab_enhance(
            image,
            l_adjust=1.1,  # 轻微提升亮度
            ab_adjust=1.02,  # 轻微提升色彩饱和度
            equalization=False,  # 不进行均衡化
        )

    elif mode == "enhanced":
        # 暴力上色模式：开启均衡化的强化处理
        # 先应用白平衡处理
        white_balanced_image = apply_white_balance(image, "color")

        # 然后使用lab_enhance进行强化增强
        return lab_enhance(
            white_balanced_image,
            l_adjust=1.3,  # 大幅提升亮度
            ab_adjust=1.25,  # 大幅增强色彩饱和度
            equalization=True,  # 开启均衡化
        )

    else:  # mode == "adjusted"
        # 调色模式：使用lab_enhance进行完整处理
        # 先应用白平衡处理
        white_balanced_image = apply_white_balance(image, "color")

        # 然后使用lab_enhance进行增强
        return lab_enhance(
            white_balanced_image,
            l_adjust=1.2,  # 提升亮度
            ab_adjust=1.15,  # 增强色彩饱和度
            equalization=False,  # 均衡化效果不好，也不进行均衡化
        )


def process_grayscale_image(image, detail_level="standard"):
    """
    统一的黑白图像处理函数

    Args:
        image: 输入图像 (BGR格式)
        detail_level: 细节级别
            - "minimal": 仅转换黑白（轻度CLAHE和高斯模糊）
            - "standard": 标准处理（未经均衡化）
            - "more": 较多细节（轻度CLAHE）
            - "most": 更多细节（中度CLAHE）
            - "extreme": 暴力细节（重度CLAHE）
            - "silhouette": 极简剪影（Otsu算法）

    Returns:
        处理后的图像 (BGR格式)
    """

    # 特殊处理：极简剪影效果（修正的Otsu算法）
    if detail_level == "silhouette":
        # 转换为LAB色彩空间
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)

        # 应用高斯模糊减少噪声影响
        L_blurred = cv2.GaussianBlur(L, (3, 3), 0)

        # 使用Otsu算法自动确定最佳阈值，然后提高阈值以保留更多细、浅的像素
        otsu_threshold, _ = cv2.threshold(
            L_blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        adjusted_threshold = (
            otsu_threshold * 1.15
        )  # 提高阈值15%以保留更多细节和浅色像素

        # 应用调整后的阈值
        _, L_binary = cv2.threshold(
            L_blurred, adjusted_threshold, 255, cv2.THRESH_BINARY
        )

        # 轻微形态学操作平滑边缘
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        L_final = cv2.morphologyEx(L_binary, cv2.MORPH_CLOSE, kernel)

        # 转换回3通道BGR格式
        return cv2.cvtColor(L_final, cv2.COLOR_GRAY2BGR)

    # 定义不同级别的处理参数
    params = {
        "minimal": {
            "use_clahe": True,
            "clip_limit": 1.5,
            "tile_grid_size": (8, 8),
            "use_minimal_processing": True,  # 特殊标记，只做轻度CLAHE和高斯模糊
        },
        "standard": {
            "use_clahe": False,
            "brightness": 1.1,
            "contrast": 1.2,
            "gamma": 0.9,
            "final_contrast": 1.3,
            "curve_strength": 1.5,
        },
        "more": {
            "use_clahe": True,
            "clip_limit": 2.0,
            "tile_grid_size": (8, 8),
            "brightness": 1.15,
            "contrast": 1.25,
            "gamma": 0.85,
            "final_contrast": 1.4,
            "curve_strength": 1.8,
        },
        "most": {
            "use_clahe": True,
            "clip_limit": 3.0,
            "tile_grid_size": (8, 8),
            "brightness": 1.1,
            "contrast": 1.15,
            "gamma": 0.95,
            "final_contrast": 1.2,
            "curve_strength": 1.3,
        },
        "extreme": {
            "use_clahe": True,
            "clip_limit": 4.0,
            "tile_grid_size": (6, 6),
            "brightness": 1.05,
            "contrast": 1.08,
            "gamma": 0.98,
            "final_contrast": 1.1,
            "curve_strength": 1.1,
        },
    }

    # 获取当前级别的参数
    p = params.get(detail_level, params["standard"])

    # 1. 先转换为灰度图像
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 特殊处理：仅转换黑白（minimal模式）
    if p.get("use_minimal_processing", False):
        # 轻度CLAHE处理
        clahe = cv2.createCLAHE(
            clipLimit=p["clip_limit"], tileGridSize=p["tile_grid_size"]
        )
        clahe_image = clahe.apply(gray_image)

        # 高斯模糊
        blurred_image = cv2.GaussianBlur(clahe_image, (3, 3), 0.5)

        # 转换回3通道BGR格式
        return cv2.cvtColor(blurred_image, cv2.COLOR_GRAY2BGR)

    # 2. CLAHE处理（非minimal模式）
    if p.get("use_clahe", False):
        clahe = cv2.createCLAHE(
            clipLimit=p["clip_limit"], tileGridSize=p["tile_grid_size"]
        )
        processed_image = clahe.apply(gray_image)
    else:
        processed_image = gray_image

    # 3. 转换为PIL格式进行后续处理
    pil_image = Image.fromarray(processed_image, mode="L")

    # 4. 亮度调整
    brightness_enhancer = ImageEnhance.Brightness(pil_image)
    brightened = brightness_enhancer.enhance(p["brightness"])

    # 5. 对比度调整
    contrast_enhancer = ImageEnhance.Contrast(brightened)
    contrasted = contrast_enhancer.enhance(p["contrast"])

    # 6. Gamma校正
    def gamma_correct(x):
        normalized = x / 255.0
        corrected = pow(normalized, p["gamma"])
        return int(corrected * 255)

    gamma_corrected = contrasted.point(gamma_correct)

    # 7. 最终对比度调整
    final_contrast_enhancer = ImageEnhance.Contrast(gamma_corrected)
    contrast_enhanced = final_contrast_enhancer.enhance(p["final_contrast"])

    # 8. S曲线调整
    def curve_adjust(x):
        normalized = x / 255.0
        strength = p["curve_strength"]
        if normalized < 0.5:
            enhanced = strength * normalized * normalized
        else:
            enhanced = 1 - strength * (1 - normalized) * (1 - normalized)
        return int(min(255, max(0, enhanced * 255)))

    curve_enhanced = contrast_enhanced.point(curve_adjust)

    # 9. 转换回3通道BGR格式
    final_array = np.array(curve_enhanced)
    result = cv2.cvtColor(final_array, cv2.COLOR_GRAY2BGR)

    return result


if __name__ == "__main__":
    # 从环境变量获取配置
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    print(f"Starting Flask app on {host}:{port}")
    if SCRIPT_NAME:
        print(f"Application will be served under: {SCRIPT_NAME}")

    app.run(host=host, port=port, debug=debug)
