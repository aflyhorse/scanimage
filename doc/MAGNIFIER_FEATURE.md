# Magnifier Feature Documentation

## Overview

A floating magnifier (loupe) feature has been added to help users precisely select corner points during image cropping. The magnifier displays a 3x zoomed view of the area around the cursor without blocking the current selection point.

## Features

### 1. Smart Positioning

- The magnifier automatically positions itself to avoid covering the current cursor/touch position
- Default position: top-right relative to the cursor
- Falls back to other positions if there's insufficient space:
  - If no space on right → positions on left
  - If no space on top → positions on bottom
- Maintains a 30px offset from the cursor for comfortable viewing

### 2. Visual Design

- **Size**: 150px diameter circular display
- **Zoom level**: 3x magnification
- **Border**: 3px blue border (#007bff) matching the app's primary color
- **Shadow**: Soft shadow for depth perception
- **Crosshair**: Red crosshair at the center to indicate the exact selection point
- **Non-interactive**: `pointer-events: none` ensures it doesn't interfere with clicking

### 3. Behavior

#### Mouse Support

- Automatically appears when hovering over the canvas during point selection
- Updates in real-time when dragging corner points
- Hides when:
  - Mouse leaves the canvas
  - Dragging ends (mouse up)
  - Not in selection mode

#### Touch Support

- Appears during touch-and-drag operations
- Updates smoothly during touch movement
- Hides when touch ends

#### Pointer Events

- Full support for modern pointer events API
- Unified handling for mouse, touch, and stylus input

### 4. Performance Optimization

- Uses `requestAnimationFrame` for smooth updates
- Image smoothing disabled for crisp pixel display
- Only active during the selection phase
- Minimal impact on drag performance

## Implementation Details

### CSS Classes

- `.magnifier`: Main container with circular mask
- `.magnifier canvas`: Internal canvas for rendering zoomed image
- `.magnifier::before` and `::after`: Crosshair markers

### JavaScript Variables

- `magnifier`: DOM element for the magnifier container
- `magnifierCanvas`: Internal canvas element
- `magnifierCtx`: 2D rendering context
- `magnifierZoom`: Zoom factor (default: 3)
- `magnifierSize`: Display size in pixels (default: 150)
- `magnifierOffset`: Distance from cursor (default: 30)

### Key Functions

- `initializeMagnifier()`: Creates and initializes the magnifier DOM structure
- `updateMagnifier(event)`: Updates magnifier position and content based on cursor position
- `positionMagnifier(event, rect)`: Smart positioning algorithm to avoid covering the cursor
- `hideMagnifier()`: Hides the magnifier

### Event Integration

- Integrated into existing `handleMouseMove()` during dragging
- Added new `handleCanvasHover()` for hover-only magnification
- Touch and pointer events automatically supported through unified event handling

## User Experience

### When Active

- Hover over the canvas → magnifier appears
- Click and drag a corner point → magnifier follows cursor
- Release → magnifier disappears

### Visual Feedback

- Clear 3x zoom shows pixel-level detail
- Red crosshair indicates exact selection point
- Blue border matches app's color scheme
- Always positioned for optimal visibility

## Browser Compatibility

- Works in all modern browsers supporting:
  - Canvas API
  - CSS transforms
  - Pointer events (with mouse/touch fallbacks)

## Future Enhancements (Potential)

- Adjustable zoom level (user preference)
- Toggle on/off option
- Different magnifier shapes (square, rectangle)
- Zoom level indicator
- Keyboard shortcut to toggle

## Testing Recommendations

1. Test on desktop with mouse input
2. Test on mobile/tablet with touch input
3. Test with stylus/pen input
4. Verify positioning in all canvas corners
5. Check performance with large images
6. Test during both point addition and dragging
