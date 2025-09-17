// 全局变量
let uploadedFilename = '';
let processedFilename = '';
let canvas = null;
let ctx = null;
let corners = [];
let isDragging = false;
let dragIndex = -1;
let canvasContainer = null;
let originalImageData = null;
let lastColorMode = 'color'; // 记住上次选择的输出模式

// API路径辅助函数
function getApiUrl(path) {
    const base = window.API_BASE || '';
    // 确保路径以/开头
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    return base + path;
}

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    initializeElements();
    setupEventListeners();
    loadLastColorMode(); // 加载上次的模式选择
});

function loadLastColorMode() {
    // 从本地存储读取上次的模式选择
    const savedMode = localStorage.getItem('scanimage-color-mode');
    if (savedMode && (savedMode === 'color' || savedMode === 'grayscale')) {
        lastColorMode = savedMode;
        const colorModeRadio = document.querySelector(`input[name="colorMode"][value="${savedMode}"]`);
        if (colorModeRadio) {
            colorModeRadio.checked = true;
        }
    }
}

function initializeElements() {
    canvas = document.getElementById('image-canvas');
    ctx = canvas.getContext('2d');

    // 创建canvas容器用于定位corner points
    canvasContainer = document.createElement('div');
    canvasContainer.className = 'canvas-container d-inline-block position-relative';
    canvas.parentNode.insertBefore(canvasContainer, canvas);
    canvasContainer.appendChild(canvas);
}

function setupEventListeners() {
    // 文件上传表单
    document.getElementById('upload-form').addEventListener('submit', handleFileUpload);

    // Canvas事件
    canvas.addEventListener('mousedown', handleCanvasMouseDown);

    // 全局鼠标事件（处理拖拽）
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Canvas特有事件
    canvas.addEventListener('mouseleave', handleMouseLeave);

    // 阻止默认的拖拽行为
    canvas.addEventListener('dragstart', (e) => e.preventDefault());

    // 处理按钮
    document.getElementById('process-btn').addEventListener('click', processImage);
    document.getElementById('reset-selection').addEventListener('click', resetSelection);

    // 旋转按钮
    document.getElementById('rotate-left').addEventListener('click', () => rotateImage(-90));
    document.getElementById('rotate-right').addEventListener('click', () => rotateImage(90));

    // 下载按钮
    document.getElementById('download-btn').addEventListener('click', downloadImage);

    // 重新开始按钮
    document.getElementById('start-over').addEventListener('click', startOver);
} async function handleFileUpload(event) {
    event.preventDefault();

    const fileInput = document.getElementById('image-input');
    const file = fileInput.files[0];

    if (!file) {
        showError('请选择一个图片文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showLoading(true);

    try {
        const response = await fetch(getApiUrl('/upload'), {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            uploadedFilename = result.filename;
            displayImageForSelection(result.image_data);
            showSection('selection-section');
        } else {
            showError(result.error || '上传失败');
        }
    } catch (error) {
        showError('上传失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function displayImageForSelection(imageData) {
    // 保存原始图片数据以供后续使用
    window.originalImageBase64 = imageData;

    const img = new Image();
    img.onload = function () {
        // 设置canvas大小
        const maxWidth = 800;
        const maxHeight = 600;

        let canvasWidth = img.width;
        let canvasHeight = img.height;

        // 缩放图片以适应显示区域
        if (canvasWidth > maxWidth || canvasHeight > maxHeight) {
            const widthRatio = maxWidth / canvasWidth;
            const heightRatio = maxHeight / canvasHeight;
            const ratio = Math.min(widthRatio, heightRatio);

            canvasWidth = canvasWidth * ratio;
            canvasHeight = canvasHeight * ratio;
        }

        canvas.width = canvasWidth;
        canvas.height = canvasHeight;

        // 绘制图片
        ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);

        // 保存原始图片数据用于重绘
        originalImageData = ctx.getImageData(0, 0, canvasWidth, canvasHeight);

        // 初始化四个角点
        initializeCorners();
    };
    img.src = 'data:image/png;base64,' + imageData;
}

function initializeCorners() {
    // 清空现有角点，让用户手动添加
    corners = [];

    // 清除现有的corner points
    const existingPoints = canvasContainer.querySelectorAll('.corner-point');
    existingPoints.forEach(point => point.remove());

    updateProcessButton();
}

function updateCornerPoints() {
    // 移除现有的corner points
    const existingPoints = canvasContainer.querySelectorAll('.corner-point');
    existingPoints.forEach(point => point.remove());

    // 创建新的corner points
    corners.forEach((corner, index) => {
        const point = document.createElement('div');
        point.className = 'corner-point';
        point.style.left = corner[0] + 'px';
        point.style.top = corner[1] + 'px';
        point.dataset.index = index;

        // 添加点击事件来启动拖拽
        point.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            isDragging = true;
            dragIndex = index;
            point.classList.add('dragging');
        });

        canvasContainer.appendChild(point);
    });
}

function handleCanvasMouseDown(event) {
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // 检查是否点击在已有corner point附近（作为备用方案）
    for (let i = 0; i < corners.length; i++) {
        const dx = x - corners[i][0];
        const dy = y - corners[i][1];
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance <= 12) {
            isDragging = true;
            dragIndex = i;
            const point = canvasContainer.querySelector(`[data-index="${i}"]`);
            if (point) point.classList.add('dragging');
            return;
        }
    }

    // 如果没有点击到现有点位，且角点数量少于4个，添加新点位
    if (corners.length < 4) {
        corners.push([x, y]);
        updateCornerPoints();
        drawSelection();
        updateProcessButton();
    }
}

function handleMouseMove(event) {
    if (isDragging && dragIndex >= 0) {
        const rect = canvas.getBoundingClientRect();
        let x = event.clientX - rect.left;
        let y = event.clientY - rect.top;

        // 网格吸附
        const gridSize = 5;
        x = Math.round(x / gridSize) * gridSize;
        y = Math.round(y / gridSize) * gridSize;

        // 确保坐标在canvas范围内
        x = Math.max(0, Math.min(canvas.width, x));
        y = Math.max(0, Math.min(canvas.height, y));

        corners[dragIndex] = [x, y];
        updateCornerPoints();
        drawSelection();
    }
}

function handleMouseUp(event) {
    if (isDragging) {
        isDragging = false;
        const draggingPoint = canvasContainer.querySelector('.dragging');
        if (draggingPoint) {
            draggingPoint.classList.remove('dragging');
        }
        dragIndex = -1;
        updateProcessButton();
    }
}

function handleMouseLeave() {
    // 鼠标离开canvas时停止拖拽
    if (isDragging) {
        isDragging = false;
        const draggingPoint = canvasContainer.querySelector('.dragging');
        if (draggingPoint) {
            draggingPoint.classList.remove('dragging');
        }
        dragIndex = -1;
    }
}

function drawSelection() {
    // 重绘原始图片
    if (originalImageData) {
        ctx.putImageData(originalImageData, 0, 0);
    }

    if (corners.length >= 2) {
        // 绘制选择区域
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.fillStyle = 'rgba(0, 123, 255, 0.1)';

        ctx.beginPath();
        ctx.moveTo(corners[0][0], corners[0][1]);
        for (let i = 1; i < corners.length; i++) {
            ctx.lineTo(corners[i][0], corners[i][1]);
        }

        // 如果有4个点，闭合区域并填充
        if (corners.length === 4) {
            ctx.closePath();
            ctx.fill();
        }
        ctx.stroke();

        // 绘制辅助线（从最后一个点到鼠标位置，如果正在添加新点）
        if (corners.length < 4 && corners.length > 0) {
            ctx.strokeStyle = 'rgba(0, 123, 255, 0.5)';
            ctx.setLineDash([5, 5]);
            // 这里可以添加到鼠标当前位置的线，但需要鼠标位置信息
            ctx.setLineDash([]);
        }
    }
}

function resetSelection() {
    corners = [];
    isDragging = false;
    dragIndex = -1;

    // 清除所有corner points
    const existingPoints = canvasContainer.querySelectorAll('.corner-point');
    existingPoints.forEach(point => point.remove());

    // 重新绘制原始图片
    if (originalImageData) {
        ctx.putImageData(originalImageData, 0, 0);
    }

    updateProcessButton();
}

function updateProcessButton() {
    const processBtn = document.getElementById('process-btn');
    processBtn.disabled = corners.length !== 4;
}

async function processImage() {
    if (corners.length !== 4) {
        showError('请选择四个角点');
        return;
    }

    const colorMode = document.querySelector('input[name="colorMode"]:checked').value;
    // 保存当前选择的模式
    lastColorMode = colorMode;
    localStorage.setItem('scanimage-color-mode', colorMode);

    // 直接使用canvas的尺寸和原始图片的尺寸计算缩放比例
    // 这里需要从displayImageForSelection函数获取原始图片尺寸
    const img = new Image();
    img.onload = async function () {
        const scaleX = img.naturalWidth / canvas.width;
        const scaleY = img.naturalHeight / canvas.height;

        const actualCorners = corners.map(corner => [
            corner[0] * scaleX,
            corner[1] * scaleY
        ]);

        showLoading(true);

        try {
            const response = await fetch(getApiUrl('/process'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: uploadedFilename,
                    corners: actualCorners,
                    color_mode: colorMode
                })
            });

            const result = await response.json();

            if (result.success) {
                processedFilename = result.processed_filename;
                displayProcessedImage(result.image_data);
                showSection('result-section');
            } else {
                showError(result.error || '处理失败');
            }
        } catch (error) {
            showError('处理失败: ' + error.message);
        } finally {
            showLoading(false);
        }
    };

    // 重新加载原始图片以获取正确的尺寸
    img.src = 'data:image/png;base64,' + window.originalImageBase64;
}

function displayProcessedImage(imageData) {
    const resultImg = document.getElementById('result-image');
    resultImg.src = 'data:image/png;base64,' + imageData;
}

async function rotateImage(angle) {
    if (!processedFilename) {
        showError('没有可旋转的图片');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(getApiUrl('/rotate'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: processedFilename,
                angle: angle
            })
        });

        const result = await response.json();

        if (result.success) {
            displayProcessedImage(result.image_data);
        } else {
            showError(result.error || '旋转失败');
        }
    } catch (error) {
        showError('旋转失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

function downloadImage() {
    if (!processedFilename) {
        showError('没有可下载的图片');
        return;
    }

    const link = document.createElement('a');
    link.href = getApiUrl('/download/' + processedFilename);
    link.download = processedFilename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function startOver() {
    // 重置所有状态
    uploadedFilename = '';
    processedFilename = '';
    corners = [];
    isDragging = false;
    dragIndex = -1;

    // 清除原始图片数据
    if (window.originalImageBase64) {
        delete window.originalImageBase64;
    }

    // 隐藏所有section，只显示upload section
    document.getElementById('selection-section').classList.add('d-none');
    document.getElementById('result-section').classList.add('d-none');
    document.getElementById('upload-section').classList.remove('d-none');

    // 重置表单但保持输出模式选择
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('image-input');
    fileInput.value = ''; // 清空文件选择

    // 恢复之前选择的输出模式
    const colorModeRadio = document.querySelector(`input[name="colorMode"][value="${lastColorMode}"]`);
    if (colorModeRadio) {
        colorModeRadio.checked = true;
    }

    // 清空错误信息
    clearErrors();
}

function showSection(sectionId) {
    // 隐藏所有section
    document.querySelectorAll('[id$="-section"]').forEach(section => {
        section.classList.add('d-none');
    });

    // 显示指定section
    document.getElementById(sectionId).classList.remove('d-none');
}

function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    if (show) {
        spinner.classList.remove('d-none');
    } else {
        spinner.classList.add('d-none');
    }
}

function showError(message) {
    const container = document.getElementById('error-container');
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    // 自动关闭错误消息
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

function clearErrors() {
    const container = document.getElementById('error-container');
    container.innerHTML = '';
}