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
    processing_option = data.get("processing_option", "default")  # 新增处理选项

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
    processing_option = data.get("processing_option", "default")

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


def histogram_equalization(image):
    """直方图均衡化处理，支持彩色和灰度图像"""
    # 判断是彩色还是灰度图像
    if len(image.shape) == 3:
        # 彩色图像：在LAB色彩空间中对L通道进行均衡化
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # 对L通道进行CLAHE（限制对比度自适应直方图均衡化）
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_equalized = clahe.apply(l_channel)

        # 重新合并通道
        lab_equalized = cv2.merge([l_equalized, a_channel, b_channel])

        # 转换回BGR色彩空间
        result = cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2BGR)

        return result
    else:
        # 灰度图像：直接进行CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
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

        # 使用加权平均，给绿色通道更多权重（因为人眼对绿色最敏感）
        target = r_avg * 0.3 + g_avg * 0.5 + b_avg * 0.2

        # 因子限制范围
        factor_range = (0.8, 1.5)

    else:  # mode == "grayscale"
        # 灰度模式：使用简单mean和保守目标
        r_avg = np.mean(r_array)
        g_avg = np.mean(g_array)
        b_avg = np.mean(b_array)

        # 使用较为保守的目标值，保留更多原始色调信息
        target = (r_avg + g_avg + b_avg) / 3 * 1.05

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


def process_color_image(image, mode="adjusted"):
    """
    统一的彩色图像处理函数

    Args:
        image: 输入图像 (BGR格式)
        mode: 处理模式
            - "original": 原色彩模式，仅做轻微调整
            - "adjusted": 调色模式，包含均衡化、白平衡和增强

    Returns:
        处理后的图像 (BGR格式)
    """
    if mode == "original":
        # 原色彩模式：仅做透视矫正和适当的亮度调整
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # 仅做轻微的亮度和对比度调整
        brightness_enhancer = ImageEnhance.Brightness(pil_image)
        brightened = brightness_enhancer.enhance(1.1)  # 轻微提升亮度

        contrast_enhancer = ImageEnhance.Contrast(brightened)
        contrasted = contrast_enhancer.enhance(1.05)  # 轻微提升对比度

        # Convert back to BGR for OpenCV
        final_array = np.array(contrasted)
        return cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)

    else:  # mode == "adjusted"
        # 调色模式：完整的处理流程
        # 1. 先应用直方图均衡化
        equalized_image = histogram_equalization(image)

        # 2. 应用白平衡处理
        white_balanced_image = apply_white_balance(equalized_image, "color")

        # 3. 转换为PIL格式进行后续增强
        image_rgb = cv2.cvtColor(white_balanced_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # 4. 增强亮度调整
        brightness_enhancer = ImageEnhance.Brightness(pil_image)
        brightened = brightness_enhancer.enhance(1.2)

        # 5. 增强对比度
        contrast_enhancer = ImageEnhance.Contrast(brightened)
        enhanced = contrast_enhancer.enhance(1.25)

        # 6. 增强色彩饱和度
        color_enhancer = ImageEnhance.Color(enhanced)
        final = color_enhancer.enhance(1.15)

        # Convert back to BGR for OpenCV
        final_array = np.array(final)
        return cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)


def process_color(image):
    """彩色图像后处理：调色和白平衡，增强版本"""
    # 1. 先应用直方图均衡化
    equalized_image = histogram_equalization(image)

    # 2. 应用白平衡处理
    white_balanced_image = apply_white_balance(equalized_image, "color")

    # 3. 转换为PIL格式进行后续增强
    image_rgb = cv2.cvtColor(white_balanced_image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    # 4. 增强亮度调整
    brightness_enhancer = ImageEnhance.Brightness(pil_image)
    brightened = brightness_enhancer.enhance(1.1)

    # 5. 增强对比度
    contrast_enhancer = ImageEnhance.Contrast(brightened)
    enhanced = contrast_enhancer.enhance(1.15)

    # 6. 增强色彩饱和度
    color_enhancer = ImageEnhance.Color(enhanced)
    final = color_enhancer.enhance(1.1)

    # Convert back to BGR for OpenCV
    final_array = np.array(final)
    return cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)


def process_grayscale_image(image, detail_level="standard"):
    """
    统一的黑白图像处理函数

    Args:
        image: 输入图像 (BGR格式)
        detail_level: 细节级别
            - "standard": 标准处理（未经均衡化）
            - "more": 较多细节（轻度均衡化）
            - "most": 更多细节（中度均衡化）
            - "extreme": 暴力细节（重度均衡化）

    Returns:
        处理后的图像 (BGR格式)
    """
    # 定义不同级别的处理参数
    params = {
        "standard": {
            "use_equalization": False,
            "brightness": 1.1,
            "contrast": 1.2,
            "gamma": 0.9,
            "final_contrast": 1.3,
            "curve_strength": 1.5,
        },
        "more": {
            "use_equalization": True,
            "brightness": 1.15,
            "contrast": 1.25,
            "gamma": 0.85,
            "final_contrast": 1.4,
            "curve_strength": 1.8,
        },
        "most": {
            "use_equalization": True,
            "brightness": 1.1,
            "contrast": 1.15,
            "gamma": 0.95,
            "final_contrast": 1.2,
            "curve_strength": 1.3,
        },
        "extreme": {
            "use_equalization": True,
            "brightness": 1.05,
            "contrast": 1.08,
            "gamma": 0.98,
            "final_contrast": 1.1,
            "curve_strength": 1.1,
        },
    }

    # 获取当前级别的参数
    p = params.get(detail_level, params["standard"])

    # 1. 可选的直方图均衡化
    if p["use_equalization"]:
        processed_image = histogram_equalization(image)
        white_balanced_image = apply_white_balance(processed_image, "grayscale")
    else:
        # 标准模式：直接应用白平衡，不使用直方图均衡化
        white_balanced_image = apply_white_balance(image, "grayscale")

    # 2. 转换为PIL格式进行后续处理
    image_rgb = cv2.cvtColor(white_balanced_image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    # 3. 亮度调整
    brightness_enhancer = ImageEnhance.Brightness(pil_image)
    brightened = brightness_enhancer.enhance(p["brightness"])

    # 4. 对比度调整
    contrast_enhancer = ImageEnhance.Contrast(brightened)
    contrasted = contrast_enhancer.enhance(p["contrast"])

    # 5. 转换为灰度
    grayscale = contrasted.convert("L")

    # 6. Gamma校正
    def gamma_correct(x):
        normalized = x / 255.0
        corrected = pow(normalized, p["gamma"])
        return int(corrected * 255)

    gamma_corrected = grayscale.point(gamma_correct)

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
