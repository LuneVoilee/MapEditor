# ui/map_canvas_view.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QImage, QCursor, QPixmap, QPainterPath
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint, QTimer
import time
import typing
from tools.performance.performance_monitor import StaticMonitor

class MapCanvasView(QWidget):
    """地图画布视图组件，专注于地图的绘制和基本交互
    
    该类是地图编辑器的视图层，负责地图内容的可视化呈现和用户交互捕获。
    它不直接操作地图数据，而是通过信号将用户交互传递给MapController，
    并根据MapController的数据更新视图。这种分离使界面逻辑与数据处理逻辑解耦，
    提高了代码的模块化和可维护性。
    """
    
    # 交互信号
    mouse_pressed = pyqtSignal(QPoint, Qt.MouseButton)  # 鼠标按下信号
    mouse_moved = pyqtSignal(QPoint)  # 鼠标移动信号
    mouse_released = pyqtSignal(QPoint, Qt.MouseButton)  # 鼠标释放信号
    key_pressed = pyqtSignal(int)  # 键盘按键的键码
    
    def __init__(self, parent=None):
        """初始化地图画布视图
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        
        # 视图状态
        self.scale_factor = 1.0  # 缩放比例
        self.offset_x = 0  # 水平偏移
        self.offset_y = 0  # 垂直偏移
        self.is_dragging_view = False  # 是否正在拖拽视图
        self.last_drag_pos = None  # 上次拖拽位置
        
        # 工具相关
        self.current_tool = "province"  # 当前工具
        self.brush_size = 20  # 笔刷大小
        self.show_tool_preview = True  # 是否显示工具预览
        
        # 临时绘制层 - 用于笔刷操作
        self.temp_drawing_layer = None  # 临时绘制层
        self.is_drawing = False  # 是否正在绘制
        self.drawing_tool = None  # 当前绘制工具
        self.stroke_path = None  # 当前笔划路径
        
        # 缓存绘制内容
        self.map_cache = None  # 地图缓存
        self.default_map_image = None  # 高程图缓存
        self.needs_redraw = True  # 是否需要重新绘制
        self.fast_update = False  # 是否使用快速更新模式
        
        # 缓存版本跟踪
        self.land_plots_version = -1  # 地块版本号，用于检测变化
        
        # 交互设置
        self.setMouseTracking(True)  # 启用鼠标跟踪
        self.setFocusPolicy(Qt.StrongFocus)  # 可以获取键盘焦点
        
        # 空白光标（用于特定工具如绘图工具）
        self.blank_cursor = self.create_blank_cursor()
        
        # 默认背景色
        self.background_color = QColor(120, 172, 215)  # 水域蓝色
        
        # 绘制性能优化
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)  # 禁用系统背景
        self.optimized_drawing = False  # 优化绘制标志
        
        # 性能监控
        self.draw_time = 0.0
        
        # 重绘定时器 - 防止频繁重绘
        self.redraw_timer = QTimer(self)
        self.redraw_timer.setSingleShot(True)
        self.redraw_timer.setInterval(100)  # 100ms防抖
        self.redraw_timer.timeout.connect(self.delayed_update)
    
    def create_blank_cursor(self):
        """创建空白光标，用于隐藏鼠标
        
        Returns:
            QCursor: 透明光标对象
        """
        # 创建1x1像素的透明光标，完全隐藏鼠标
        pixmap = QPixmap(1, 1)
        pixmap.fill(Qt.transparent)
        return QCursor(pixmap, 0, 0)  # 设置热点为左上角
    
    def set_controller(self, controller):
        """设置地图控制器
        
        将视图与控制器连接，建立信号和槽的连接关系，
        使视图能够响应控制器的数据变化。
        
        Args:
            controller: MapController实例
        """
        self.controller = controller
        # 连接控制器信号
        self.controller.map_changed.connect(self.update_map)
        self.controller.tool_changed.connect(self.on_tool_changed)

    def update(self,*args):
        StaticMonitor.update_frame()
        super().update(*args)

    def update_map(self):
        """更新地图（标记需要重绘）
        
        当地图数据变化时，该方法被调用，标记视图需要重绘
        """
        self.needs_redraw = True
        # 强制更新地块缓存版本号，确保重绘时更新
        if hasattr(self, 'controller') and hasattr(self.controller, 'land_plots'):
            self.land_plots_version = -1  # 重置版本号以强制更新缓存
            
        self.update()

    
    def on_tool_changed(self, tool_name):
        """工具变更时的处理
        
        根据选择的工具类型设置相应的光标和工具预览状态
        
        Args:
            tool_name: 工具名称
        """
        self.current_tool = tool_name
        
        # 根据工具类型设置光标
        if tool_name in ["province", "height", "continent", "river"]:
            # 使用空白光标，让工具预览图标充当鼠标
            self.setCursor(self.blank_cursor)
            # 确保工具预览显示
            self.show_tool_preview = True
            # 立即更新视图，显示工具预览
            self.update()
        elif tool_name == "plot_select":
            self.setCursor(Qt.ArrowCursor)
            self.show_tool_preview = False
        elif tool_name == "pan":
            self.setCursor(Qt.OpenHandCursor)
            self.show_tool_preview = False
        else:
            self.setCursor(Qt.ArrowCursor)
            self.show_tool_preview = False
    
    def start_brush_stroke(self, tool_type, position, size):
        """开始笔刷绘制，初始化临时绘制层"""
        from PyQt5.QtGui import QImage, QPainter, QPainterPath, QPen, QBrush, QColor, QRadialGradient
        from PyQt5.QtCore import Qt, QPointF
        
        # 如果已经有绘制层，先清理
        if self.temp_drawing_layer is not None:
            self.temp_drawing_layer = None
        
        # 获取当前视图大小并创建临时绘制层
        if self.controller and hasattr(self.controller, 'default_map'):
            # 使用地图的实际大小
            height, width = self.controller.default_map.data.shape
            self.temp_drawing_layer = QImage(width, height, QImage.Format_ARGB32)
            self.temp_drawing_layer.fill(Qt.transparent)
            
            # 创建笔划路径
            self.stroke_path = QPainterPath()
            
            # 转换位置到地图坐标
            x, y = position.x(), position.y()
            
            # 记录初始点
            self.stroke_path.moveTo(x, y)
            
            # 绘制初始点
            painter = QPainter(self.temp_drawing_layer)
            painter.setRenderHint(QPainter.Antialiasing, True)
            
            # 设置笔刷样式（根据工具类型）
            if tool_type == "continent":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 255, 150)))
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
            elif tool_type == "height":
                # 创建径向渐变
                gradient = QRadialGradient(QPointF(x, y), size/2)
                gradient.setColorAt(0, QColor(255, 255, 255, 200))
                gradient.setColorAt(1, QColor(255, 255, 255, 0))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
            elif tool_type == "river":
                painter.setPen(QPen(QColor(70, 130, 180, 200), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.setBrush(Qt.NoBrush)
                # 对于河流绘制一个起始点
                painter.drawPoint(QPointF(x, y))
            else:  # 默认为province工具
                color = QColor(200, 200, 200, 150)
                if hasattr(self.controller, 'current_color') and self.controller.current_color:
                    color = QColor(self.controller.current_color)
                    color.setAlpha(150)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
            
            painter.end()
            
            # 标记正在绘制状态
            self.is_drawing = True
            self.drawing_tool = tool_type
            
            # 更新视图
            self.update()
            
            return True
        
        return False
    
    def continue_brush_stroke(self, position, size):
        """继续笔刷绘制，更新临时绘制层"""
        if not self.is_drawing or self.temp_drawing_layer is None:
            return False
        
        from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QRadialGradient
        from PyQt5.QtCore import Qt, QPointF, QLineF
        
        # 转换位置到地图坐标
        x, y = position.x(), position.y()
        
        # 获取上一个点
        last_point = self.stroke_path.currentPosition()
        
        # 添加新点到路径
        self.stroke_path.lineTo(x, y)
        
        # 计算点之间的距离
        import math
        distance = math.sqrt((x - last_point.x())**2 + (y - last_point.y())**2)
        
        # 绘制到临时层
        painter = QPainter(self.temp_drawing_layer)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 根据工具类型设置笔刷样式
        if self.drawing_tool == "continent":
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 128)))
            
            # 如果距离较大，添加中间点
            if distance > size/4:
                steps = max(1, int(distance/(size/8)))
                for i in range(1, steps+1):
                    t = i / steps
                    ix = last_point.x() + (x - last_point.x()) * t
                    iy = last_point.y() + (y - last_point.y()) * t
                    painter.drawEllipse(QPointF(ix, iy), size/2, size/2)
            else:
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
                
        elif self.drawing_tool == "height":
            gradient = QRadialGradient(QPointF(x, y), size/2)
            gradient.setColorAt(0, QColor(255, 255, 255, 200))
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(gradient))
            
            # 如果距离较大，添加中间点
            if distance > size/4:
                steps = max(1, int(distance/(size/8)))
                for i in range(1, steps+1):
                    t = i / steps
                    ix = last_point.x() + (x - last_point.x()) * t
                    iy = last_point.y() + (y - last_point.y()) * t
                    
                    # 每个中间点使用新的渐变
                    mid_gradient = QRadialGradient(QPointF(ix, iy), size/2)
                    mid_gradient.setColorAt(0, QColor(255, 255, 255, 200))
                    mid_gradient.setColorAt(1, QColor(255, 255, 255, 0))
                    painter.setBrush(QBrush(mid_gradient))
                    
                    painter.drawEllipse(QPointF(ix, iy), size/2, size/2)
            else:
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
                
        elif self.drawing_tool == "river":
            painter.setPen(QPen(QColor(70, 130, 180, 200), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            
            # 绘制线段
            painter.drawLine(QLineF(last_point, QPointF(x, y)))
            
        else:  # 默认为province工具
            color = QColor(200, 200, 200, 128)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            
            # 如果距离较大，添加中间点
            if distance > size/4:
                steps = max(1, int(distance/(size/8)))
                for i in range(1, steps+1):
                    t = i / steps
                    ix = last_point.x() + (x - last_point.x()) * t
                    iy = last_point.y() + (y - last_point.y()) * t
                    painter.drawEllipse(QPointF(ix, iy), size/2, size/2)
            else:
                painter.drawEllipse(QPointF(x, y), size/2, size/2)
        
        painter.end()
        
        # 更新视图
        self.update()
        
        return True
    
    def finish_brush_stroke(self):
        """完成笔刷绘制，处理数据更新"""
        if not self.is_drawing or self.temp_drawing_layer is None:
            return False
        
        import numpy as np
        import cv2
        from PyQt5.QtGui import QImage
        
        # 获取临时层数据
        temp_image = self.temp_drawing_layer
        
        # 转换为OpenCV格式进行处理
        width = temp_image.width()
        height = temp_image.height()
        
        # 创建NumPy数组存储图像数据
        buffer = temp_image.constBits()
        buffer.setsize(temp_image.byteCount())
        
        # 将QImage转换为NumPy数组(RGBA格式)
        img_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
        
        # 根据工具类型处理数据
        if self.controller is not None:
            if self.drawing_tool == "continent":
                # 使用alpha通道创建掩码（非零的alpha表示被笔刷绘制的区域）
                mask = img_array[:, :, 3] > 0
                
                # 确保controller有continent_mask属性
                if not hasattr(self.controller, 'continent_mask') or self.controller.continent_mask is None:
                    self.controller.continent_mask = np.zeros((height, width), dtype=bool)
                
                # 更新大陆掩码和高程数据
                self.controller.continent_mask |= mask
                self.controller.default_map.data[mask] = 255
                
            elif self.drawing_tool == "height":
                # 获取alpha通道作为强度因子
                strength_factor = img_array[:, :, 3].astype(np.float32) / 255.0
                
                # 使用笔刷强度进行加权
                brush_strength = self.controller.brush_strength
                height_change = strength_factor * brush_strength
                
                # 应用高程变化
                valid_mask = strength_factor > 0
                
                # 更新高程数据
                current_heights = self.controller.default_map.data
                new_heights = np.clip(current_heights + height_change, 0, 255)
                
                # 只更新掩码内的像素
                self.controller.default_map.data[valid_mask] = new_heights[valid_mask]
                
            elif self.drawing_tool == "river":
                # 提取笔划路径
                path_pixels = img_array[:, :, 3] > 0
                
                # 使用骨架化算法提取路径中心线
                path_pixels_u8 = path_pixels.astype(np.uint8) * 255
                skeleton = cv2.ximgproc.thinning(path_pixels_u8)
                
                # 找到非零点
                river_points = np.column_stack(np.where(skeleton > 0))
                
                # 按照路径排序（可选步骤，需要更复杂的算法）
                # 这里简化为按y坐标排序
                river_points = river_points[np.argsort(river_points[:, 0])]
                
                # 创建河流点列表
                river_path = [(int(point[1]), int(point[0])) for point in river_points]
                
                # 如果没有足够的点，使用原始路径
                if len(river_path) < 2:
                    # 回退到简单方法：使用笔划中的任何有效点
                    all_points = np.column_stack(np.where(path_pixels))
                    # 采样一些点减少数量
                    sample_step = max(1, len(all_points) // 20)
                    sampled_points = all_points[::sample_step]
                    river_path = [(int(point[1]), int(point[0])) for point in sampled_points]
                
                # 添加到河流列表
                if hasattr(self.controller, 'rivers'):
                    if len(river_path) > 1:
                        self.controller.rivers.append(river_path)
                        self.controller.is_drawing = False
                
            elif self.drawing_tool == "province":
                # 提取被笔刷覆盖的点
                province_pixels = img_array[:, :, 3] > 0
                
                # 找到所有非零点
                province_points = np.column_stack(np.where(province_pixels))
                
                # 添加点到当前省份
                if hasattr(self.controller, 'current_province') and self.controller.current_province is not None:
                    for point in province_points:
                        # 注意坐标系转换：NumPy是(y,x)，而省份点是(x,y)
                        self.controller.current_province.add_point(int(point[1]), int(point[0]))
            
            # 发送地图更改信号
            self.controller.map_changed.emit()
        
        # 清理绘制状态
        self.is_drawing = False
        self.drawing_tool = None
        self.stroke_path = None
        self.temp_drawing_layer = None
        
        # 更新视图
        self.needs_redraw = True
        self.update()
        
        return True
    
    def paintEvent(self, event):
        """绘制事件处理
        
        绘制地图内容、工具预览等
        
        Args:
            event: 绘制事件
        """

        
        # 创建绘制器
        painter = QPainter(self)
        
        # 优化性能：缩放和拖拽时禁用抗锯齿和高质量渲染
        if self.optimized_drawing or self.is_dragging_view:
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        else:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 绘制背景
        painter.fillRect(self.rect(), self.background_color)
        
        # 应用变换（缩放和平移）
        painter.translate(self.offset_x, self.offset_y)
        painter.scale(self.scale_factor, self.scale_factor)
        
        # 绘制高程图
        self.draw_default_map(painter)
        
        # 绘制栅格化地块 - 始终绘制，不受优化模式影响
        self.draw_land_plots(painter)
        
        # 在拖动或调整大小时使用简化绘制
        if not self.is_dragging_view and not self.optimized_drawing:
            # 绘制省份
            self.draw_provinces(painter)
            
            # 绘制河流
            self.draw_rivers(painter)
            
            # 绘制临时笔刷层
            if self.is_drawing and self.temp_drawing_layer is not None:
                painter.drawImage(0, 0, self.temp_drawing_layer)
        else:
            # 如果有缓存的省份图像，仍然绘制它们（不需要重新计算路径）
            if hasattr(self, 'provinces_cache'):
                painter.resetTransform()
                painter.drawImage(0, 0, self.provinces_cache)
                painter.translate(self.offset_x, self.offset_y)
                painter.scale(self.scale_factor, self.scale_factor)
        
        # 绘制当前工具的预览 (只有当未在绘制状态时才显示)
        if self.show_tool_preview and not self.is_dragging_view and not self.is_drawing:
            self.draw_tool_preview(painter)
        
        # 绘制可绘制区域的黑框边界
        if hasattr(self.controller, 'default_map') and self.controller.default_map:
            # 保存当前状态
            painter.save()
            # 重置变换，确保按原始尺寸绘制边框
            painter.resetTransform()
            # 将坐标系移动到画布左上角
            painter.translate(self.offset_x, self.offset_y)
            # 应用缩放
            painter.scale(self.scale_factor, self.scale_factor)
            
            # 获取地图尺寸
            width = self.controller.default_map.width
            height = self.controller.default_map.height
            
            # 设置黑色画笔绘制边框
            painter.setPen(QPen(QColor(0, 0, 0), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(0, 0, width, height)
            
            # 恢复之前的画笔状态
            painter.restore()
        
        # 结束绘制
        painter.end()
        self.needs_redraw = False

        
    @StaticMonitor.monitor("绘制底图")
    def draw_default_map(self, painter):
        """绘制底图"""
        if not hasattr(self.controller, 'default_map') or not self.controller.default_map:
            return
        
        # 获取高程图数据
        default_map = self.controller.default_map
        
        # 检查是否已创建缓存图像或者需要更新
        if not self.default_map_image or self.needs_redraw:
            # 创建高程图缓存
            try:
                width = min(default_map.width, 2000)  # 限制最大尺寸，防止内存溢出
                height = min(default_map.height, 2000)
                
                # 使用更高效的方式创建图像
                self.default_map_image = QImage(width, height, QImage.Format_RGB32)
                
                # 使用NumPy批量处理像素，避免逐个像素设置
                # 获取高程数据
                elevation_data = default_map.data
                
                # 预先定义颜色映射
                color_map = {
                    0: QColor(120, 172, 215).rgb(),  # 水域
                    1: QColor(180, 210, 230).rgb(),  # 低地 (<20)
                    2: QColor(180, 220, 130).rgb(),  # 平原 (20-40)
                    3: QColor(160, 190, 110).rgb(),  # 丘陵 (40-70)
                    4: QColor(140, 160, 90).rgb(),   # 高地 (70-90)
                    5: QColor(220, 220, 220).rgb()   # 山地 (>90)
                }
                
                # 创建一个缓冲区来存储颜色值
                img_buffer = np.zeros((height, width), dtype=np.uint32)
                
                # 根据高程批量设置颜色
                img_buffer[elevation_data <= 0] = color_map[0]
                img_buffer[(elevation_data > 0) & (elevation_data < 20)] = color_map[1]
                img_buffer[(elevation_data >= 20) & (elevation_data < 40)] = color_map[2]
                img_buffer[(elevation_data >= 40) & (elevation_data < 70)] = color_map[3]
                img_buffer[(elevation_data >= 70) & (elevation_data < 90)] = color_map[4]
                img_buffer[elevation_data >= 90] = color_map[5]
                
                # 将缓冲区数据复制到QImage
                for y in range(height):
                    for x in range(width):
                        self.default_map_image.setPixel(x, y, int(img_buffer[y, x]))
            except Exception as e:
                print(f"绘制高程图错误: {e}")
                return
        
        # 使用缓存的高程图绘制
        if self.default_map_image:
            # 使用更高效的方式绘制，避免缩放和变换导致的抗锯齿计算
            if self.optimized_drawing:
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            
            painter.drawImage(0, 0, self.default_map_image)
    
    @StaticMonitor.monitor("绘制省份")
    def draw_provinces(self, painter):
        """绘制省份"""
        if not hasattr(self.controller, 'provinces'):
            return
        
        # 检查是否需要更新省份缓存图像
        if self.needs_redraw or not hasattr(self, 'provinces_cache'):
            # 根据当前视图大小创建缓存图像
            self.provinces_cache = QImage(self.width(), self.height(), QImage.Format_ARGB32)
            self.provinces_cache.fill(Qt.transparent)
            
            # 创建缓存图像的绘制器
            cache_painter = QPainter(self.provinces_cache)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # 应用与主绘制器相同的变换
            cache_painter.translate(self.offset_x, self.offset_y)
            cache_painter.scale(self.scale_factor, self.scale_factor)
            
            # 绘制所有省份到缓存图像
            for province in self.controller.provinces:
                if hasattr(province, 'path') and province.path:
                    cache_painter.fillPath(province.path, province.color)
                    
                    # 绘制边框
                    border_pen = QPen(QColor(0, 0, 0), 1)
                    cache_painter.setPen(border_pen)
                    cache_painter.drawPath(province.path)
            
            cache_painter.end()
            
            # 标记为已缓存
            self.provinces_cached = True
        
        # 如果有选中的省份，我们需要在实时绘制中处理它
        selected_province = None if not hasattr(self.controller, 'selected_province') else self.controller.selected_province
        
        # 绘制缓存的省份图像
        if hasattr(self, 'provinces_cache'):
            painter.resetTransform()  # 重置变换以便准确绘制缓存图像
            painter.drawImage(0, 0, self.provinces_cache)
            
            # 恢复变换以便绘制选中的省份
            painter.resetTransform()
            painter.translate(self.offset_x, self.offset_y)
            painter.scale(self.scale_factor, self.scale_factor)
        
        # 绘制当前选中的省份（高亮）- 这需要实时绘制
        if selected_province and hasattr(selected_province, 'path') and selected_province.path:
            # 使用半透明高亮色
            highlight_color = QColor(255, 255, 0, 100)
            painter.fillPath(selected_province.path, highlight_color)
            
            # 绘制粗边框
            highlight_pen = QPen(QColor(255, 200, 0), 2)
            painter.setPen(highlight_pen)
            painter.drawPath(selected_province.path)
    
    def draw_rivers(self, painter):
        """绘制河流"""
        if not hasattr(self.controller, 'rivers'):
            return
        
        # 设置河流样式
        river_pen = QPen(QColor(70, 130, 180), 3)
        river_pen.setCapStyle(Qt.RoundCap)
        river_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(river_pen)
        
        # 绘制所有河流
        for river in self.controller.rivers:
            if len(river) < 2:
                continue
            
            # 创建河流路径
            path = QPainterPath()
            path.moveTo(river[0][0], river[0][1])
            
            for point in river[1:]:
                path.lineTo(point[0], point[1])
            
            # 绘制路径
            painter.drawPath(path)
    
    @StaticMonitor.monitor("绘制栅格化地块")
    def draw_land_plots(self, painter):
        """绘制栅格化地块"""
        if not hasattr(self.controller, 'land_plots') or not self.controller.land_plots:
            return
        
        # 计算当前land_plots的版本号或标识
        current_plots_length = len(self.controller.land_plots)
        current_plots_selected = [] if not hasattr(self.controller, 'land_plots_selected') else self.controller.land_plots_selected.copy()
        
        # 检查是否需要更新地块缓存 - 增加检查land_plots变化的逻辑
        if (self.needs_redraw or 
            not hasattr(self, 'land_plots_cache') or 
            self.land_plots_version != current_plots_length or
            hasattr(self, 'last_plots_selected') and self.last_plots_selected != current_plots_selected):
            
            # 更新版本号或标识
            self.land_plots_version = current_plots_length
            self.last_plots_selected = current_plots_selected.copy()
            
            # 创建缓存图像 - 使用地图实际尺寸
            if hasattr(self.controller, 'default_map') and self.controller.default_map:
                cache_width = self.controller.default_map.width
                cache_height = self.controller.default_map.height
            else:
                print("绘制网格时，无法找到 default_map")
                return

            
            # 创建与地图相同尺寸的缓存
            self.land_plots_cache = QImage(cache_width, cache_height, QImage.Format_ARGB32)
            self.land_plots_cache.fill(Qt.transparent)
            
            # 创建缓存图像的绘制器
            cache_painter = QPainter(self.land_plots_cache)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # 设置地块样式
            plot_pen = QPen(QColor(100, 100, 100, 100), 1)
            plot_brush = QBrush(QColor(200, 200, 100, 50))
            selected_brush = QBrush(QColor(255, 200, 50, 100))
            
            # 绘制所有地块
            for i, plot in enumerate(self.controller.land_plots):
                if not plot or not hasattr(plot, 'exterior'):
                    continue
                
                # 创建地块路径
                path = QPainterPath()
                exterior_coords = list(plot.exterior.coords)
                
                # 简化复杂地块
                if len(exterior_coords) > 100:
                    # 简化点集但保留形状
                    step = max(1, len(exterior_coords) // 100)
                    simplified_coords = exterior_coords[::step]
                    # 确保闭合
                    if simplified_coords[0] != simplified_coords[-1]:
                        simplified_coords.append(simplified_coords[0])
                else:
                    simplified_coords = exterior_coords
                
                # 绘制简化后的地块
                path.moveTo(simplified_coords[0][0], simplified_coords[0][1])
                for coord in simplified_coords[1:]:
                    path.lineTo(coord[0], coord[1])
                
                # 检查是否是选中的地块
                is_selected = False
                if hasattr(self.controller, 'land_plots_selected'):
                    is_selected = i in self.controller.land_plots_selected
                
                # 设置填充和边框
                cache_painter.setPen(plot_pen)
                cache_painter.setBrush(selected_brush if is_selected else plot_brush)
                
                # 绘制地块
                cache_painter.drawPath(path)
            
            cache_painter.end()
        
        # 绘制缓存的地块图像 - 使用已有的画布变换
        if self.land_plots_cache:
            # 直接使用当前painter的变换状态（已经包含scale和translate）
            painter.drawImage(0, 0, self.land_plots_cache)

    def draw_tool_preview(self, painter):
        """绘制当前工具的预览"""
        # 获取鼠标位置
        cursor_pos = self.mapFromGlobal(QCursor.pos())
        
        # 如果鼠标不在窗口内，不绘制预览
        if not self.rect().contains(cursor_pos):
            return
        
        # 转换为地图坐标
        map_x = (cursor_pos.x() - self.offset_x) / self.scale_factor
        map_y = (cursor_pos.y() - self.offset_y) / self.scale_factor
        
        # 根据当前工具绘制预览
        if self.current_tool in ["province", "height", "continent", "river"]:
            # 绘制笔刷圆圈
            brush_size = self.controller.brush_size if hasattr(self.controller, 'brush_size') else 20
            
            # 优化性能：拖动和调整大小时使用更简单的笔刷预览
            if self.optimized_drawing:
                brush_pen = QPen(QColor(200, 200, 200))
                brush_pen.setWidth(1)
                painter.setPen(brush_pen)
                painter.setBrush(Qt.NoBrush)
            else:
                if self.current_tool == "province":
                    brush_color = QColor(200, 200, 200, 120)
                    brush_pen = QPen(QColor(150, 150, 150, 180), 1)
                elif self.current_tool == "height":
                    brush_color = QColor(100, 255, 100, 120)
                    brush_pen = QPen(QColor(80, 200, 80, 180), 1)
                elif self.current_tool == "continent":
                    brush_color = QColor(255, 255, 255, 120)
                    brush_pen = QPen(QColor(200, 200, 200, 180), 1)
                elif self.current_tool == "river":
                    brush_color = QColor(100, 150, 255, 120)
                    brush_pen = QPen(QColor(70, 130, 180, 180), 1)
                else:
                    brush_color = QColor(230, 230, 250, 50)
                    brush_pen = QPen(QColor(200, 200, 200, 180), 1)
                
                painter.setPen(brush_pen)
                painter.setBrush(QBrush(brush_color))
            
            # 确保将浮点坐标转换为整数
            x = int(map_x - brush_size/2)
            y = int(map_y - brush_size/2)
            width = int(brush_size)
            height = int(brush_size)
            
            # 绘制笔刷预览
            painter.drawEllipse(x, y, width, height)
            
            # 绘制中心点以提高精确度
            if not self.optimized_drawing:
                center_pen = QPen(QColor(255, 255, 255, 200), 1, Qt.SolidLine)
                painter.setPen(center_pen)
                painter.drawPoint(int(map_x), int(map_y))
                
                # 绘制十字线
                painter.drawLine(int(map_x-3), int(map_y), int(map_x+3), int(map_y))
                painter.drawLine(int(map_x), int(map_y-3), int(map_x), int(map_y+3))
        
    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        # 转换为相对于缩放和平移后的坐标
        map_pos = self.map_to_scene(event.pos())
        
        # 中键拖动画布
        if event.button() == Qt.MiddleButton:
            self.is_dragging_view = True
            self.last_drag_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            # 开启性能优化模式
            self.optimized_drawing = True
            return
        
        # 如果按下左键，开始笔刷操作
        if event.button() == Qt.LeftButton and not self.is_drawing:
            # 获取当前工具和笔刷大小
            tool = self.current_tool
            brush_size = self.controller.brush_size if hasattr(self.controller, 'brush_size') else 20
            
            # 检查当前是否处于地块选择模式
            in_plot_selection_mode = hasattr(self.controller, 'land_plots') and len(self.controller.land_plots) > 0
            
            # 检查工具类型，开始相应的笔刷操作，但当处于地块选择模式时禁用绘制工具
            if tool in ["continent", "height", "river", "province"] and not in_plot_selection_mode:
                # 开始笔刷绘制
                # 确保鼠标真正隐藏
                self.setCursor(self.blank_cursor)
                self.start_brush_stroke(tool, map_pos, brush_size)
                return
        
        # 将事件转发给控制器
        self.mouse_pressed.emit(map_pos, event.button())
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        # 如果是拖拽视图
        if self.is_dragging_view and self.last_drag_pos:
            delta = event.pos() - self.last_drag_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_drag_pos = event.pos()
            # 设置快速绘制模式
            self.fast_update = True
            self.update()
            return
        
        # 转换为相对于缩放和平移后的坐标
        map_pos = self.map_to_scene(event.pos())
        
        # 如果正在绘制，继续笔刷操作
        if self.is_drawing and (event.buttons() & Qt.LeftButton):
            brush_size = self.controller.brush_size if hasattr(self.controller, 'brush_size') else 20
            self.continue_brush_stroke(map_pos, brush_size)
            return
        
        # 如果显示工具预览，需要立即更新视图以显示笔刷在新位置
        if self.show_tool_preview and self.current_tool in ["province", "height", "continent", "river"]:
            # 仅更新鼠标周围的区域以提高性能
            brush_size = self.controller.brush_size if hasattr(self.controller, 'brush_size') else 20
            # 计算屏幕坐标中的区域
            screen_x = int(event.pos().x())
            screen_y = int(event.pos().y())
            screen_radius = int(brush_size * self.scale_factor) + 10  # 添加边距
            # 更新区域
            update_rect = QRect(screen_x - screen_radius, screen_y - screen_radius,
                               screen_radius * 2, screen_radius * 2)
            self.update(update_rect)
        
        # 将事件转发给控制器
        self.mouse_moved.emit(map_pos)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件处理"""
        # 如果是结束拖拽视图
        if event.button() == Qt.MiddleButton and self.is_dragging_view:
            self.is_dragging_view = False
            self.setCursor(Qt.ArrowCursor)
            # 关闭性能优化模式，完整绘制
            self.optimized_drawing = False
            self.needs_redraw = True
            self.update()
            return
        
        # 如果是结束笔刷操作
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.finish_brush_stroke()
            return
        
        # 转换为相对于缩放和平移后的坐标
        map_pos = self.map_to_scene(event.pos())
        
        # 将事件转发给控制器
        self.mouse_released.emit(map_pos, event.button())
    
    def keyPressEvent(self, event):
        """键盘按下事件处理"""
        # 将事件转发给控制器
        self.key_pressed.emit(event.key())
        
        # 处理一些通用键盘快捷键
        if event.key() == Qt.Key_Space:
            # 空格键临时切换到平移工具
            self.previous_tool = self.current_tool
            self.current_tool = "pan"
            self.setCursor(Qt.OpenHandCursor)
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            # 放大
            self.zoom_in()
        elif event.key() == Qt.Key_Minus:
            # 缩小
            self.zoom_out()
    
    def keyReleaseEvent(self, event):
        """键盘释放事件处理"""
        if event.key() == Qt.Key_Space and hasattr(self, 'previous_tool'):
            # 恢复之前的工具
            self.current_tool = self.previous_tool
            self.on_tool_changed(self.current_tool)
    
    def wheelEvent(self, event):
        """鼠标滚轮事件处理（缩放）"""
        zoom_in_factor = 1.1  # 降低缩放步长，减少卡顿
        zoom_out_factor = 1 / zoom_in_factor
        
        # 获取鼠标位置（相对于窗口）
        cursor_pos = event.pos()
        
        # 计算鼠标位置相对于场景的坐标
        old_scene_pos = self.map_to_scene(cursor_pos)
        
        # 根据滚轮方向缩放
        if event.angleDelta().y() > 0:
            # 放大
            self.scale_factor *= zoom_in_factor
        else:
            # 缩小
            self.scale_factor *= zoom_out_factor
        
        # 限制缩放范围
        self.scale_factor = max(0.1, min(5.0, self.scale_factor))
        
        # 重新计算鼠标位置相对于场景的坐标
        new_scene_pos = self.map_to_scene(cursor_pos)
        
        # 调整偏移，使鼠标下的点在缩放前后位置一致
        delta_scene = new_scene_pos - old_scene_pos
        self.offset_x += delta_scene.x() * self.scale_factor
        self.offset_y += delta_scene.y() * self.scale_factor
        
        # 设置快速更新模式
        self.fast_update = True
        self.update()
    
    def map_to_scene(self, pos):
        """将窗口坐标转换为场景坐标"""
        return QPoint(
            int((pos.x() - self.offset_x) / self.scale_factor),
            int((pos.y() - self.offset_y) / self.scale_factor)
        )
    
    def scene_to_map(self, scene_pos):
        """将场景坐标转换为窗口坐标"""
        return QPoint(
            int(scene_pos.x() * self.scale_factor + self.offset_x),
            int(scene_pos.y() * self.scale_factor + self.offset_y)
        )
    
    def zoom_in(self):
        """放大地图"""
        zoom_factor = 1.2
        center = QPoint(self.width() / 2, self.height() / 2)
        
        # 计算中心点相对于场景的坐标
        old_center_scene = self.map_to_scene(center)
        
        # 增加缩放因子
        self.scale_factor *= zoom_factor
        
        # 限制缩放范围
        self.scale_factor = min(5.0, self.scale_factor)
        
        # 重新计算中心点相对于场景的坐标
        new_center_scene = self.map_to_scene(center)
        
        # 调整偏移
        delta_scene = new_center_scene - old_center_scene
        self.offset_x += delta_scene.x() * self.scale_factor
        self.offset_y += delta_scene.y() * self.scale_factor
        
        self.update()
    
    def zoom_out(self):
        """缩小地图"""
        zoom_factor = 1 / 1.2
        center = QPoint(self.width() / 2, self.height() / 2)
        
        # 计算中心点相对于场景的坐标
        old_center_scene = self.map_to_scene(center)
        
        # 减小缩放因子
        self.scale_factor *= zoom_factor
        
        # 限制缩放范围
        self.scale_factor = max(0.1, self.scale_factor)
        
        # 重新计算中心点相对于场景的坐标
        new_center_scene = self.map_to_scene(center)
        
        # 调整偏移
        delta_scene = new_center_scene - old_center_scene
        self.offset_x += delta_scene.x() * self.scale_factor
        self.offset_y += delta_scene.y() * self.scale_factor
        
        self.update()
    
    def reset_view(self):
        """重置视图（缩放和平移）"""
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update()
    
    def resizeEvent(self, event):
        """窗口大小变化事件，优化重绘性能"""
        # 标记优化绘制模式
        self.optimized_drawing = True
        
        # 标记需要重绘，但不立即执行
        self.needs_redraw = True
        
        # 清除所有缓存图像
        if hasattr(self, 'provinces_cache'):
            delattr(self, 'provinces_cache')
        
        if hasattr(self, 'land_plots_cache'):
            delattr(self, 'land_plots_cache')
        
        if hasattr(self, 'rivers_cache'):
            delattr(self, 'rivers_cache')
        
        # 清除高程图缓存
        self.default_map_image = None
        
        # 延长防抖动重绘间隔到300ms，进一步减少频繁重绘
        self.redraw_timer.setInterval(300)
        
        # 使用防抖动重绘
        if self.redraw_timer.isActive():
            self.redraw_timer.stop()
        self.redraw_timer.start()
        
        # 调用基类方法
        super().resizeEvent(event)
    
    def delayed_update(self):
        """延迟更新，减少频繁重绘"""
        # 关闭优化绘制模式
        self.optimized_drawing = False
        self.update() 