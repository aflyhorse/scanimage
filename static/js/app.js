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
let currentColorMode = 'color'; // 当前处理的图像模式
let currentProcessingOption = 'adjusted'; // 当前处理选项
let debugMode = false; // 调试模式

// 状态保存变量
let savedState = {
    uploadedImage: null,        // 保存上传的图片数据
    selectedColorMode: 'color', // 保存选择的色彩模式
    cropCorners: [],           // 保存裁剪区域坐标(canvas坐标)
    actualCorners: [],         // 保存实际裁剪坐标(原始图片坐标)
    filename: ''               // 保存文件名
};

// 检测微信环境
function isWechat() {
    return /MicroMessenger/i.test(navigator.userAgent);
}

// 拖拽性能优化变量
let animationFrameId = null;
let smoothDragMode = true; // 流畅拖拽模式

// API路径辅助函数
function getApiUrl(path) {
    const base = window.API_BASE || '';
    // 确保路径以/开头
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    const fullUrl = base + path;
    console.log(`API URL: ${path} -> ${fullUrl}`);
    return fullUrl;
}

// 坐标转换辅助函数
function getCanvasCoordinates(event) {
    // 获取canvas的显示尺寸和位置
    const rect = canvas.getBoundingClientRect();

    // 计算缩放比例
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    // 获取事件的客户端坐标（支持鼠标和触摸事件）
    let clientX, clientY;
    if (event.touches && event.touches.length > 0) {
        // 触摸事件，使用第一个触点
        clientX = event.touches[0].clientX;
        clientY = event.touches[0].clientY;
    } else {
        // 鼠标事件
        clientX = event.clientX;
        clientY = event.clientY;
    }

    // 转换为canvas内部坐标
    const x = (clientX - rect.left) * scaleX;
    const y = (clientY - rect.top) * scaleY;

    // 确保坐标在canvas范围内
    const clampedX = Math.max(0, Math.min(canvas.width, x));
    const clampedY = Math.max(0, Math.min(canvas.height, y));

    // 调试信息
    if (debugMode) {
        console.log('坐标转换调试:', {
            canvasSize: { width: canvas.width, height: canvas.height },
            displaySize: { width: rect.width, height: rect.height },
            scale: { x: scaleX, y: scaleY },
            clientCoords: { x: clientX, y: clientY },
            rectOffset: { left: rect.left, top: rect.top },
            relativeCoords: { x: clientX - rect.left, y: clientY - rect.top },
            canvasCoords: { x: x, y: y },
            clampedCoords: { x: clampedX, y: clampedY }
        });
    }

    return [Math.round(clampedX), Math.round(clampedY)];
}

function getDisplayCoordinates(canvasX, canvasY) {
    // 获取canvas的显示尺寸
    const rect = canvas.getBoundingClientRect();

    // 计算缩放比例
    const scaleX = rect.width / canvas.width;
    const scaleY = rect.height / canvas.height;

    // 转换为显示坐标
    const displayX = canvasX * scaleX;
    const displayY = canvasY * scaleY;

    // 调试信息
    if (debugMode) {
        console.log('显示坐标转换调试:', {
            canvasCoords: { x: canvasX, y: canvasY },
            scale: { x: scaleX, y: scaleY },
            displayCoords: { x: displayX, y: displayY }
        });
    }

    return [Math.round(displayX), Math.round(displayY)];
}

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    initializeElements();
    setupEventListeners();
    loadLastColorMode(); // 加载上次的模式选择
    updateGrayscaleDescription(); // 初始化灰度处理选项描述
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

    // 添加调试信息显示
    if (debugMode) {
        createDebugInfoDisplay();
    }
}

function createDebugInfoDisplay() {
    // 创建调试信息显示区域
    const debugInfo = document.createElement('div');
    debugInfo.id = 'debug-info';
    debugInfo.style.cssText = `
        position: fixed;
        top: 10px;
        left: 10px;
        background: rgba(0,0,0,0.8);
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 12px;
        z-index: 1000;
        max-width: 300px;
    `;
    debugInfo.innerHTML = '<strong>坐标调试信息</strong><br>移动鼠标到画布上查看坐标';
    document.body.appendChild(debugInfo);

    // 添加鼠标移动监听，显示实时坐标
    canvas.addEventListener('mousemove', (event) => {
        if (!isDragging) {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const [canvasX, canvasY] = getCanvasCoordinates(event);

            debugInfo.innerHTML = `
                <strong>坐标调试信息</strong><br>
                Canvas尺寸: ${canvas.width} x ${canvas.height}<br>
                显示尺寸: ${Math.round(rect.width)} x ${Math.round(rect.height)}<br>
                缩放比例: ${scaleX.toFixed(3)} x ${scaleY.toFixed(3)}<br>
                鼠标位置: ${event.clientX - rect.left}, ${event.clientY - rect.top}<br>
                Canvas坐标: ${canvasX}, ${canvasY}<br>
                已选点数: ${corners.length}
            `;
        }
    });
}

function setupEventListeners() {
    console.log('Setting up event listeners...');

    // 文件上传表单
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
        console.log('Upload form event listener added');
    } else {
        console.error('Upload form not found!');
    }

    // Canvas事件
    canvas.addEventListener('mousedown', handleCanvasMouseDown);
    canvas.addEventListener('pointerdown', handleCanvasPointerDown); // 添加pointer支持

    // 触摸事件（手机端支持）
    canvas.addEventListener('touchstart', handleCanvasTouchStart);

    // 全局鼠标事件（处理拖拽）
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // 全局pointer事件（更好的拖拽支持）
    document.addEventListener('pointermove', handlePointerMove);
    document.addEventListener('pointerup', handlePointerUp);

    // 全局触摸事件（处理拖拽）
    document.addEventListener('touchmove', handleTouchMove);
    document.addEventListener('touchend', handleTouchEnd);

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

    // 处理选项变化监听 - 彩色选项自动触发重新处理
    document.querySelectorAll('input[name="colorProcessing"]').forEach(radio => {
        radio.addEventListener('change', () => {
            // 自动触发重新处理
            setTimeout(() => {
                reprocessImage();
            }, 100);
        });
    });

    // 黑白处理选项变化监听 - 自动触发重新处理
    document.querySelectorAll('input[name="grayscaleProcessing"]').forEach(radio => {
        radio.addEventListener('change', () => {
            updateGrayscaleDescription();
            // 自动触发重新处理
            setTimeout(() => {
                reprocessImage();
            }, 100);
        });
    });

    // 重新开始按钮
    document.getElementById('start-over').addEventListener('click', startOver);
    document.getElementById('start-over-step2').addEventListener('click', startOver);

    // 后退按钮
    document.getElementById('back-to-step2').addEventListener('click', backToStep2);
    document.getElementById('adjust-crop-bottom').addEventListener('click', backToStep2);

    // 色彩模式切换按钮
    document.getElementById('switch-to-color').addEventListener('click', () => switchColorMode('color'));
    document.getElementById('switch-to-grayscale').addEventListener('click', () => switchColorMode('grayscale'));
}

async function handleFileUpload(event) {
    console.log('handleFileUpload called', event);
    event.preventDefault();

    const fileInput = document.getElementById('image-input');
    const file = fileInput.files[0];

    console.log('Selected file:', file);
    console.log('API_BASE:', window.API_BASE);

    if (!file) {
        showError('请选择一个图片文件');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // 添加扩图选项
    const expandImageCheckbox = document.getElementById('expand-image');
    if (expandImageCheckbox && expandImageCheckbox.checked) {
        formData.append('expandImage', 'on');
    }

    showLoading(true);

    try {
        const response = await fetch(getApiUrl('/upload'), {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            uploadedFilename = result.filename;

            // 保存当前状态
            const colorModeElement = document.querySelector('input[name="colorMode"]:checked');
            savedState.uploadedImage = result.image_data;
            savedState.selectedColorMode = colorModeElement ? colorModeElement.value : 'color';
            savedState.filename = result.filename;
            savedState.cropCorners = []; // 重置裁剪区域
            savedState.actualCorners = []; // 重置实际坐标

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

        // 将canvas内部坐标转换为显示坐标
        const [displayX, displayY] = getDisplayCoordinates(corner[0], corner[1]);
        point.style.left = displayX + 'px';
        point.style.top = displayY + 'px';
        point.dataset.index = index;

        // 添加鼠标点击事件来启动拖拽
        point.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            isDragging = true;
            dragIndex = index;
            point.classList.add('dragging');

            if (debugMode) {
                console.log(`Corner point ${index} mousedown 事件触发`);
            }
        });

        // 添加pointer events支持（更好的拖拽体验）
        point.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            isDragging = true;
            dragIndex = index;
            point.classList.add('dragging');

            // 设置pointer capture，确保后续事件不会丢失
            if (point.setPointerCapture) {
                try {
                    point.setPointerCapture(e.pointerId);
                } catch (err) {
                    if (debugMode) {
                        console.log('设置pointer capture失败:', err.message);
                    }
                }
            }

            if (debugMode) {
                console.log(`Corner point ${index} pointerdown 事件触发, pointerId: ${e.pointerId}`);
            }
        });

        // 添加触摸事件来启动拖拽
        point.addEventListener('touchstart', (e) => {
            e.preventDefault();
            e.stopPropagation();
            isDragging = true;
            dragIndex = index;
            point.classList.add('dragging');

            if (debugMode) {
                console.log(`Corner point ${index} touchstart 事件触发`);
            }
        });

        canvasContainer.appendChild(point);
    });
}

function handleCanvasMouseDown(event) {
    event.preventDefault();
    const [x, y] = getCanvasCoordinates(event);

    // 检查是否点击在已有corner point附近（扩大检测范围以提高可用性）
    let closestIndex = -1;
    let closestDistance = Infinity;

    for (let i = 0; i < corners.length; i++) {
        const dx = x - corners[i][0];
        const dy = y - corners[i][1];
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance <= 20 && distance < closestDistance) { // 扩大检测范围到20像素
            closestDistance = distance;
            closestIndex = i;
        }
    }

    if (closestIndex >= 0) {
        // 开始拖拽最近的corner point
        isDragging = true;
        dragIndex = closestIndex;
        const point = canvasContainer.querySelector(`[data-index="${closestIndex}"]`);
        if (point) {
            point.classList.add('dragging');
            // 设置pointer capture（如果支持且是pointer事件）
            if (point.setPointerCapture && event.pointerId) {
                try {
                    point.setPointerCapture(event.pointerId);
                } catch (e) {
                    if (debugMode) {
                        console.log('设置pointer capture失败:', e.message);
                    }
                }
            }
        }

        if (debugMode) {
            console.log(`开始拖拽角点 ${closestIndex}, 距离: ${closestDistance.toFixed(1)}`);
        }
        return;
    }

    // 如果没有点击到现有点位，且角点数量少于4个，添加新点位
    if (corners.length < 4) {
        corners.push([x, y]);
        updateCornerPoints();
        drawSelection();
        updateProcessButton();

        if (debugMode) {
            console.log(`添加新角点: (${x}, ${y}), 总数: ${corners.length}`);
        }
    }
}

function handleMouseMove(event) {
    if (isDragging && dragIndex >= 0) {
        // 确保拖拽的corner point仍然存在
        if (dragIndex >= corners.length) {
            console.warn('拖拽索引超出范围，停止拖拽');
            isDragging = false;
            dragIndex = -1;
            return;
        }

        const [x, y] = getCanvasCoordinates(event);

        // 实时更新corner point的DOM位置（不使用网格吸附，确保流畅）
        const point = canvasContainer.querySelector(`[data-index="${dragIndex}"]`);
        if (point) {
            const [displayX, displayY] = getDisplayCoordinates(x, y);
            point.style.left = displayX + 'px';
            point.style.top = displayY + 'px';
        } else {
            console.warn('找不到对应的corner point DOM元素');
        }

        // 使用requestAnimationFrame来节流canvas重绘
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }

        animationFrameId = requestAnimationFrame(() => {
            // 确保坐标在canvas范围内
            const clampedX = Math.max(0, Math.min(canvas.width, x));
            const clampedY = Math.max(0, Math.min(canvas.height, y));

            // 更新corners数组
            if (dragIndex >= 0 && dragIndex < corners.length) {
                corners[dragIndex] = [clampedX, clampedY];

                // 重绘选择区域
                drawSelection();
            }
        });

        if (debugMode) {
            console.log(`拖拽移动: 角点${dragIndex} -> (${x.toFixed(1)}, ${y.toFixed(1)})`);
        }
    }
}

function handleMouseUp(event) {
    if (isDragging) {
        isDragging = false;
        const draggingPoint = canvasContainer.querySelector('.dragging');
        if (draggingPoint) {
            draggingPoint.classList.remove('dragging');
        }

        // 在拖拽结束时应用网格吸附（根据模式设置）
        if (dragIndex >= 0 && dragIndex < corners.length) {
            const corner = corners[dragIndex];
            let finalX = corner[0];
            let finalY = corner[1];

            // 只在非流畅模式下应用网格吸附
            if (!smoothDragMode) {
                const gridSize = 5;
                finalX = Math.round(corner[0] / gridSize) * gridSize;
                finalY = Math.round(corner[1] / gridSize) * gridSize;
            }

            // 确保坐标在canvas范围内
            const clampedX = Math.max(0, Math.min(canvas.width, finalX));
            const clampedY = Math.max(0, Math.min(canvas.height, finalY));

            corners[dragIndex] = [clampedX, clampedY];

            // 更新最终位置
            updateCornerPoints();
            drawSelection();

            if (debugMode) {
                console.log(`拖拽结束: 角点${dragIndex} 最终位置 (${clampedX}, ${clampedY})`);
            }
        }

        dragIndex = -1;
        updateProcessButton();

        // 清理动画帧
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
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

// 触摸事件处理函数
function handleCanvasTouchStart(event) {
    event.preventDefault(); // 防止页面滚动

    // 将触摸事件转换为鼠标事件的格式
    const touch = event.touches[0];
    const mouseEvent = {
        clientX: touch.clientX,
        clientY: touch.clientY,
        preventDefault: () => { },
        touches: event.touches
    };

    handleCanvasMouseDown(mouseEvent);
}

function handleTouchMove(event) {
    if (isDragging && dragIndex >= 0) {
        event.preventDefault(); // 防止页面滚动

        const touch = event.touches[0];
        const mouseEvent = {
            clientX: touch.clientX,
            clientY: touch.clientY,
            touches: event.touches
        };

        handleMouseMove(mouseEvent);
    }
}

function handleTouchEnd(event) {
    if (isDragging) {
        event.preventDefault();

        const mouseEvent = {
            preventDefault: () => { }
        };

        handleMouseUp(mouseEvent);
    }
}

// Pointer事件处理函数（统一处理鼠标和触摸，更好的拖拽体验）
function handleCanvasPointerDown(event) {
    // 将pointer事件转换为通用格式
    const unifiedEvent = {
        clientX: event.clientX,
        clientY: event.clientY,
        preventDefault: () => event.preventDefault(),
        pointerId: event.pointerId
    };

    handleCanvasMouseDown(unifiedEvent);
}

function handlePointerMove(event) {
    if (isDragging && dragIndex >= 0) {
        // 将pointer事件转换为通用事件格式
        const unifiedEvent = {
            clientX: event.clientX,
            clientY: event.clientY,
            preventDefault: () => event.preventDefault()
        };

        handleMouseMove(unifiedEvent);
    }
}

function handlePointerUp(event) {
    if (isDragging) {
        // 释放pointer capture
        const draggingPoint = canvasContainer.querySelector('.dragging');
        if (draggingPoint && draggingPoint.releasePointerCapture && event.pointerId) {
            try {
                draggingPoint.releasePointerCapture(event.pointerId);
            } catch (e) {
                // 忽略释放捕获时的错误
                if (debugMode) {
                    console.log('释放pointer capture时发生错误:', e.message);
                }
            }
        }

        const unifiedEvent = {
            preventDefault: () => event.preventDefault()
        };

        handleMouseUp(unifiedEvent);
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

        // 调试模式：在canvas上绘制小圆圈标记每个角点的精确位置
        if (debugMode) {
            ctx.fillStyle = '#ff0000';
            corners.forEach((corner, index) => {
                ctx.beginPath();
                ctx.arc(corner[0], corner[1], 3, 0, 2 * Math.PI);
                ctx.fill();

                // 添加角点编号
                ctx.fillStyle = '#ffffff';
                ctx.font = '12px Arial';
                ctx.fillText(index + 1, corner[0] + 5, corner[1] - 5);
                ctx.fillStyle = '#ff0000';
            });
        }

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
    const processIcon = processBtn.querySelector('.bi-gear') || processBtn.querySelector('[data-bs-icon="gear"]');

    if (corners.length === 0) {
        // 没有选择任何角点，按钮变为"处理全图"
        processBtn.disabled = false;
        if (processIcon) {
            processBtn.innerHTML = processBtn.innerHTML.replace(/开始处理|处理全图/, '处理全图');
        } else {
            // 如果没有找到图标，直接替换文本
            processBtn.textContent = processBtn.textContent.replace(/开始处理|处理全图/, '处理全图');
        }
    } else if (corners.length === 4) {
        // 选择了4个角点，按钮变为"开始处理"
        processBtn.disabled = false;
        if (processIcon) {
            processBtn.innerHTML = processBtn.innerHTML.replace(/开始处理|处理全图/, '开始处理');
        } else {
            processBtn.textContent = processBtn.textContent.replace(/开始处理|处理全图/, '开始处理');
        }
    } else {
        // 选择了1-3个角点，按钮禁用
        processBtn.disabled = true;
        if (processIcon) {
            processBtn.innerHTML = processBtn.innerHTML.replace(/开始处理|处理全图/, '开始处理');
        } else {
            processBtn.textContent = processBtn.textContent.replace(/开始处理|处理全图/, '开始处理');
        }
    }
}

async function processImage() {
    // 验证条件：要么有4个角点，要么没有角点（处理全图）
    if (corners.length !== 0 && corners.length !== 4) {
        showError('请选择四个角点或不选择任何区域直接处理全图');
        return;
    }

    const colorMode = document.querySelector('input[name="colorMode"]:checked').value;
    // 保存当前选择的模式
    lastColorMode = colorMode;
    currentColorMode = colorMode;
    localStorage.setItem('scanimage-color-mode', colorMode);

    // 保存裁剪区域坐标到状态
    savedState.cropCorners = [...corners];

    // 如果没有选择角点，直接发送null给后端
    if (corners.length === 0) {
        // 保存实际坐标为空数组
        savedState.actualCorners = [];

        showLoading(true);

        try {
            const response = await fetch(getApiUrl('/process'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: uploadedFilename,
                    corners: null, // 发送null表示处理全图
                    color_mode: colorMode,
                    processing_option: 'adjusted'
                })
            });

            const result = await response.json();

            if (result.success) {
                processedFilename = result.processed_filename;
                currentProcessingOption = 'adjusted';
                displayProcessedImage(result.image_data);
                setupProcessingOptions(colorMode);
                showSection('result-section');
            } else {
                showError(result.error || '处理失败');
            }
        } catch (error) {
            showError('处理失败: ' + error.message);
        } finally {
            showLoading(false);
        }
        return;
    }

    // 有4个角点的情况，原有逻辑
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

        // 保存实际坐标（原始图片尺寸）用于重新处理
        savedState.actualCorners = actualCorners;

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
                    color_mode: colorMode,
                    processing_option: 'adjusted'
                })
            });

            const result = await response.json();

            if (result.success) {
                processedFilename = result.processed_filename;
                currentProcessingOption = 'adjusted';
                displayProcessedImage(result.image_data);
                setupProcessingOptions(colorMode);
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

function setupProcessingOptions(colorMode) {
    // 显示对应的处理选项
    const colorOptions = document.getElementById('color-processing-options');
    const grayscaleOptions = document.getElementById('grayscale-processing-options');

    if (colorMode === 'color') {
        colorOptions.classList.remove('d-none');
        grayscaleOptions.classList.add('d-none');
        // 重置选项为自动调色默认值
        document.getElementById('color-adjusted').checked = true;
        currentProcessingOption = 'adjusted';
    } else {
        colorOptions.classList.add('d-none');
        grayscaleOptions.classList.remove('d-none');
        // 重置为标准灰度处理选项
        const standardOption = document.querySelector('input[name="grayscaleProcessing"][value="standard"]');
        if (standardOption) {
            standardOption.checked = true;
        }
        currentProcessingOption = 'standard';
    }

    // 更新色彩模式切换按钮状态
    updateColorModeButtons(colorMode);
}

// 更新灰度处理选项描述
function updateGrayscaleDescription() {
    const selectedOption = document.querySelector('input[name="grayscaleProcessing"]:checked');
    const description = document.getElementById('grayscale-description');

    if (selectedOption && description) {
        const descriptions = {
            'minimal': '仅转换黑白：轻度处理，保持原始色调和层次',
            'standard': '标准灰度处理，平衡的细节保留和对比度',
            'more': '保留更多细节，增强纹理和层次感',
            'most': '最大程度保留细节，适合复杂文档',
            'extreme': '极致细节增强，适合淡色或低对比度文档',
            'silhouette': '极简剪影：高对比度二值化处理，突出轮廓'
        };

        description.textContent = descriptions[selectedOption.value] || '标准灰度处理';
    }
}

async function reprocessImage() {
    if (!uploadedFilename) {
        showError('无法重新处理，请重新开始流程');
        return;
    }

    // 获取当前选择的处理选项
    let processingOption = 'adjusted';
    if (currentColorMode === 'color') {
        const selectedOption = document.querySelector('input[name="colorProcessing"]:checked');
        processingOption = selectedOption ? selectedOption.value : 'adjusted';
    } else {
        // 黑白模式使用灰度处理选项
        const selectedOption = document.querySelector('input[name="grayscaleProcessing"]:checked');
        processingOption = selectedOption ? selectedOption.value : 'standard';
    }

    // 重新加载原始图片以计算尺寸
    const img = new Image();
    img.onload = async function () {
        let actualCorners = [];

        // 只有当有选择角点时才计算实际坐标
        if (corners.length === 4) {
            const scaleX = img.naturalWidth / canvas.width;
            const scaleY = img.naturalHeight / canvas.height;

            actualCorners = corners.map(corner => [
                corner[0] * scaleX,
                corner[1] * scaleY
            ]);
        }

        showResultLoading(true);

        try {
            const response = await fetch(getApiUrl('/reprocess'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: uploadedFilename,
                    corners: actualCorners,
                    color_mode: currentColorMode,
                    processing_option: processingOption,
                    processed_filename: processedFilename
                })
            });

            const result = await response.json();

            if (result.success) {
                currentProcessingOption = processingOption;
                displayProcessedImage(result.image_data);
            } else {
                showError(result.error || '重新处理失败');
            }
        } catch (error) {
            showError('重新处理失败: ' + error.message);
        } finally {
            showResultLoading(false);
        }
    };

    img.src = 'data:image/png;base64,' + window.originalImageBase64;
}

function displayProcessedImage(imageData) {
    const resultImg = document.getElementById('result-image');
    resultImg.src = 'data:image/png;base64,' + imageData;

    // 在微信环境下更新下载按钮
    if (isWechat()) {
        const downloadBtn = document.getElementById('download-btn');
        downloadBtn.innerHTML = '微信客户端请长按图片保存';
        downloadBtn.className = 'btn btn-info';
        downloadBtn.style.cursor = 'default';
    }
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
    currentColorMode = 'color';
    currentProcessingOption = 'adjusted';

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

    // 重置处理选项 - 自动调色为默认
    document.getElementById('color-adjusted').checked = true;

    // 重置细节级别显示
    updateDetailLevelDisplay();

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

function showResultLoading(show) {
    const resultLoading = document.getElementById('result-loading');
    const resultImage = document.getElementById('result-image');
    if (show) {
        resultLoading.classList.remove('d-none');
        // 可选：让图片稍微半透明显示处理中状态
        resultImage.style.opacity = '0.6';
    } else {
        resultLoading.classList.add('d-none');
        resultImage.style.opacity = '1';
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

function showInfo(message) {
    const container = document.getElementById('error-container');
    const alert = document.createElement('div');
    alert.className = 'alert alert-info alert-dismissible fade show';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    // 自动关闭信息消息
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 3000);
}

function clearErrors() {
    const container = document.getElementById('error-container');
    container.innerHTML = '';
}

// 后退到步骤2 - 调整裁剪区域
function backToStep2() {
    if (!savedState.uploadedImage) {
        showError('没有保存的图片数据，请重新上传');
        return;
    }

    // 恢复图片显示
    displayImageForSelection(savedState.uploadedImage);

    // 显示步骤2
    showSection('selection-section');

    // 恢复裁剪区域（如果有的话）需要在图片加载完成后
    if (savedState.cropCorners && savedState.cropCorners.length === 4) {
        // 使用setTimeout确保图片已经加载完成
        setTimeout(() => {
            corners = [...savedState.cropCorners];
            drawSelection();
            updateCornerPoints(); // 显示可拖拽的角点
            updateProcessButton();
        }, 100);
    }

    // 清空错误信息
    clearErrors();
}

// 切换色彩模式（在步骤3中使用）
async function switchColorMode(targetMode) {
    if (!processedFilename) {
        showError('没有处理过的图片，无法切换色彩模式');
        return;
    }

    // 允许没有裁剪区域的情况（全图处理）
    if (!savedState.actualCorners) {
        savedState.actualCorners = [];
    }

    // 更新当前色彩模式
    currentColorMode = targetMode;

    // 更新按钮状态
    updateColorModeButtons(targetMode);

    // 根据新的模式重新处理图片
    showResultLoading(true);

    try {
        const response = await fetch(getApiUrl('/reprocess'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: savedState.filename,
                corners: savedState.actualCorners,
                color_mode: targetMode,
                processing_option: getCurrentProcessingOption(targetMode),
                processed_filename: processedFilename
            })
        });

        const result = await response.json();

        if (result.success) {
            processedFilename = result.processed_filename;
            displayProcessedImage(result.image_data);
            setupProcessingOptions(targetMode);
        } else {
            showError(result.error || '重新处理失败');
        }
    } catch (error) {
        showError('重新处理失败: ' + error.message);
    } finally {
        showResultLoading(false);
    }
}

// 更新色彩模式按钮状态
function updateColorModeButtons(activeMode) {
    const colorBtn = document.getElementById('switch-to-color');
    const grayscaleBtn = document.getElementById('switch-to-grayscale');

    if (activeMode === 'color') {
        colorBtn.classList.remove('btn-outline-info');
        colorBtn.classList.add('btn-info');
        grayscaleBtn.classList.remove('btn-secondary');
        grayscaleBtn.classList.add('btn-outline-secondary');
    } else {
        colorBtn.classList.remove('btn-info');
        colorBtn.classList.add('btn-outline-info');
        grayscaleBtn.classList.remove('btn-outline-secondary');
        grayscaleBtn.classList.add('btn-secondary');
    }
}

// 获取当前处理选项
function getCurrentProcessingOption(colorMode) {
    if (colorMode === 'color') {
        const checkedOption = document.querySelector('input[name="colorProcessing"]:checked');
        return checkedOption ? checkedOption.value : 'adjusted';
    } else {
        const checkedOption = document.querySelector('input[name="grayscaleProcessing"]:checked');
        return checkedOption ? checkedOption.value : 'standard';
    }
}