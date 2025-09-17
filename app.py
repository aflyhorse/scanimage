import os
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    """主页面 - 图片上传界面"""
    return render_template("index.html")


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

        # Post-processing based on color mode
        if color_mode == "grayscale":
            processed_image = process_grayscale(corrected_image)
        else:
            processed_image = process_color(corrected_image)

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


def process_color(image):
    """彩色图像后处理：调色和白平衡"""
    # Convert BGR to RGB for PIL processing
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    # Auto white balance using PIL
    # Simple white balance by stretching color channels
    r, g, b = pil_image.split()

    # Calculate the average and adjust
    r_avg = np.mean(np.array(r))
    g_avg = np.mean(np.array(g))
    b_avg = np.mean(np.array(b))

    # Target gray level
    target = (r_avg + g_avg + b_avg) / 3

    # Adjust each channel
    r_factor = target / r_avg if r_avg > 0 else 1
    g_factor = target / g_avg if g_avg > 0 else 1
    b_factor = target / b_avg if b_avg > 0 else 1

    # Apply factors with limits
    r_factor = min(max(r_factor, 0.5), 2.0)
    g_factor = min(max(g_factor, 0.5), 2.0)
    b_factor = min(max(b_factor, 0.5), 2.0)

    # Apply white balance
    r = Image.eval(r, lambda x: int(min(255, x * r_factor)))
    g = Image.eval(g, lambda x: int(min(255, x * g_factor)))
    b = Image.eval(b, lambda x: int(min(255, x * b_factor)))

    balanced = Image.merge("RGB", (r, g, b))

    # Enhance contrast and color
    enhancer = ImageEnhance.Contrast(balanced)
    enhanced = enhancer.enhance(1.2)

    color_enhancer = ImageEnhance.Color(enhanced)
    final = color_enhancer.enhance(1.1)

    # Convert back to BGR for OpenCV
    final_array = np.array(final)
    return cv2.cvtColor(final_array, cv2.COLOR_RGB2BGR)


def process_grayscale(image):
    """黑白图像后处理：通过白平衡、亮度对比度调整，再转为黑白"""
    # 首先进行彩色图像的白平衡和亮度调整
    # Convert BGR to RGB for PIL processing
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    # Auto white balance using PIL
    r, g, b = pil_image.split()

    # Calculate the average and adjust for white balance
    r_avg = np.mean(np.array(r))
    g_avg = np.mean(np.array(g))
    b_avg = np.mean(np.array(b))

    # Target gray level (slightly higher to make background whiter)
    target = max(r_avg, g_avg, b_avg) * 1.1  # 使背景更亮

    # Adjust each channel
    r_factor = target / r_avg if r_avg > 0 else 1
    g_factor = target / g_avg if g_avg > 0 else 1
    b_factor = target / b_avg if b_avg > 0 else 1

    # Apply factors with limits
    r_factor = min(max(r_factor, 0.8), 2.5)
    g_factor = min(max(g_factor, 0.8), 2.5)
    b_factor = min(max(b_factor, 0.8), 2.5)

    # Apply white balance
    r = Image.eval(r, lambda x: int(min(255, x * r_factor)))
    g = Image.eval(g, lambda x: int(min(255, x * g_factor)))
    b = Image.eval(b, lambda x: int(min(255, x * b_factor)))

    balanced = Image.merge("RGB", (r, g, b))

    # 增强亮度，使底色更接近白色
    brightness_enhancer = ImageEnhance.Brightness(balanced)
    brightened = brightness_enhancer.enhance(1.3)  # 提高亮度

    # 增强对比度
    contrast_enhancer = ImageEnhance.Contrast(brightened)
    contrasted = contrast_enhancer.enhance(1.6)  # 进一步提高对比度

    # 转换为灰度图像
    grayscale = contrasted.convert("L")

    # 进一步调整灰度图像的对比度和亮度
    # 使用PIL的point方法进行gamma校正，使背景更白
    def gamma_correct(x):
        # Gamma校正，使亮的部分更亮，暗的部分保持对比度
        normalized = x / 255.0
        corrected = pow(normalized, 0.75)  # 调整gamma值使对比更强
        return int(corrected * 255)

    gamma_corrected = grayscale.point(gamma_correct)

    # 再次增强对比度
    final_contrast_enhancer = ImageEnhance.Contrast(gamma_corrected)
    high_contrast = final_contrast_enhancer.enhance(1.8)  # 大幅提高对比度

    # 使用曲线调整进一步增强黑白对比
    def enhance_curve(x):
        # S曲线调整，增强明暗对比
        normalized = x / 255.0
        if normalized < 0.5:
            # 暗部更暗
            enhanced = 2 * normalized * normalized
        else:
            # 亮部更亮
            enhanced = 1 - 2 * (1 - normalized) * (1 - normalized)
        return int(min(255, max(0, enhanced * 255)))

    curve_enhanced = high_contrast.point(enhance_curve)

    # 转换回3通道BGR格式
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
