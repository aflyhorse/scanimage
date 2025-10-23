# Aspect Ratio Adjustment Feature

## 功能概述

在处理结果页面添加了纵横比微调功能，允许用户通过滑动条调整输出图片的纵横比例。

## 功能特性

### 1. 调整范围

- **向左滑动**：纵向拉伸，最大 30%
- **中间位置**：不做调整（默认）
- **向右滑动**：横向拉伸，最大 30%

### 2. 实时预览

- 滑动时显示当前调整百分比
- 使用防抖技术（150ms），避免频繁重绘
- 基于客户端的原始处理结果进行调整，无需重新请求服务器

### 3. 智能状态管理

- 保存原始处理结果 (`originalProcessedImageData`)
- 每次处理、旋转或切换色彩模式后自动重置滑条
- 调整时基于原始图片计算，避免累积误差
- 反复左右调整不会导致图片越来越大

### 4. 响应式设计

- 桌面端：滑条与旋转按钮在同一行
- 窄屏（手机）：滑条自动换行，保持良好的操作体验

## 技术实现

### HTML 结构

```html
<div class="aspect-ratio-control">
    <label>纵横比:</label>
    <input type="range" id="aspect-ratio-slider" min="-30" max="30" value="0">
    <span id="aspect-ratio-value">0%</span>
</div>
```

### 关键变量

- `originalProcessedImageData`: 保存未调整纵横比的原始处理结果
- `currentAspectRatio`: 当前纵横比调整值（-30 到 30）
- `aspectRatioAdjustTimeout`: 防抖定时器

### 核心函数

#### `handleAspectRatioChange(event)`

处理滑条变化事件：

- 更新显示的百分比和颜色标识
- 使用 150ms 防抖，避免频繁调整
- 调用 `applyAspectRatioAdjustment()` 应用调整

#### `applyAspectRatioAdjustment(percentage)`

应用纵横比调整：

- 基于 `originalProcessedImageData` 创建临时 canvas
- 根据百分比计算新的宽度或高度
- 使用 canvas API 绘制调整后的图像
- 转换为 base64 并更新显示

#### `resetAspectRatioSlider()`

重置滑条状态：

- 在每次处理、旋转、切换模式后调用
- 将滑条值设为 0
- 重置显示文本和颜色

### 计算逻辑

```javascript
if (percentage > 0) {
    // 正值：横向拉伸
    newWidth = originalWidth * (1 + percentage / 100);
    newHeight = originalHeight; // 保持不变
} else if (percentage < 0) {
    // 负值：纵向拉伸
    newWidth = originalWidth; // 保持不变
    newHeight = originalHeight * (1 + Math.abs(percentage) / 100);
}
```

### 防抖机制

```javascript
if (aspectRatioAdjustTimeout) {
    clearTimeout(aspectRatioAdjustTimeout);
}
aspectRatioAdjustTimeout = setTimeout(() => {
    applyAspectRatioAdjustment(value);
}, 150);
```

## 用户界面

### 视觉反馈

- **灰色徽章**（0%）：无调整
- **蓝色徽章**（横向+N%）：横向拉伸
- **黄色徽章**（纵向+N%）：纵向拉伸

### 布局适配

- 使用 `flex-wrap` 和 `gap-2` 实现自适应布局
- 窄屏下滑条控件独占一行，宽度自适应
- 滑条最大宽度限制为 200px（手机端）

## 性能优化

1. **客户端处理**：使用 Canvas API 在客户端进行纵横比调整，无需服务器参与
2. **防抖延迟**：150ms 防抖避免滑动时频繁重绘
3. **基于原图**：始终基于 `originalProcessedImageData` 计算，避免累积误差
4. **按需更新**：仅在值变化时更新，值为 0 时直接显示原图

## 使用场景

### 适用情况

- 扫描的文档纵横比略有偏差
- 拍摄角度导致的轻微变形
- 需要微调宽高比以适应特定用途

### 典型工作流

1. 用户上传并处理图片
2. 查看结果，发现纵横比略有偏差
3. 拖动滑条进行微调
4. 实时预览调整效果
5. 满意后下载图片

## 兼容性

- ✅ 与旋转功能完全兼容
- ✅ 与色彩模式切换完全兼容
- ✅ 与处理选项切换完全兼容
- ✅ 支持移动端触摸滑动
- ✅ 支持所有现代浏览器

## 注意事项

1. **不影响服务器文件**：调整仅在客户端进行，不修改服务器上的处理结果
2. **下载时应用**：下载按钮下载的是当前显示的（已调整的）图片
3. **自动重置**：任何新的处理操作都会重置滑条到中间位置
4. **无累积效应**：反复调整不会产生累积放大效果

## 未来增强

可能的改进方向：

- 添加数字输入框精确控制百分比
- 支持自由比例调整（独立控制宽高）
- 添加常用比例快捷按钮（如 A4、16:9 等）
- 保存用户偏好的调整值
