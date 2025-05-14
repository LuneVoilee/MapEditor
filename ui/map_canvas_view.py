# ui/map_canvas_view.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QImage, QCursor, QPixmap, QPainterPath
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint, QTimer
import time

class MapCanvasView(QWidget):
    """地图画布视图组件，专注于地图的绘制和基本交互"""
    
    # 交互信号
    mouse_pressed = pyqtSignal(QPoint, Qt.MouseButton)
    mouse_moved = pyqtSignal(QPoint)
    mouse_released = pyqtSignal(QPoint, Qt.MouseButton)
    key_pressed = pyqtSignal(int)  # 键盘按键的键码
    
    def __init__(self, parent=None):
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
        
        # 缓存绘制内容
        self.map_cache = None  # 地图缓存
        self.heightmap_image = None  # 高程图缓存
        self.needs_redraw = True  # 是否需要重新绘制
        self.fast_update = False  # 是否使用快速更新模式
        
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
        self.draw_time = 0.0  # 绘制时间
        
        # 重绘定时器 - 防止频繁重绘
        self.redraw_timer = QTimer(self)
        self.redraw_timer.setSingleShot(True)
        self.redraw_timer.setInterval(100)  # 100ms防抖
        self.redraw_timer.timeout.connect(self.delayed_update)
    
    def create_blank_cursor(self):
        """创建空白光标"""
        pixmap = QPixmap(1, 1)
        pixmap.fill(Qt.transparent)
        return QCursor(pixmap)
    
    def set_controller(self, controller):
        """设置地图控制器"""
        self.controller = controller
        # 连接控制器信号
        self.controller.map_changed.connect(self.update_map)
        self.controller.tool_changed.connect(self.on_tool_changed)
    
    def update_map(self):
        """更新地图（标记需要重绘）"""
        self.needs_redraw = True
        self.update()
    
    def on_tool_changed(self, tool_name):
        """工具变更时的处理"""
        self.current_tool = tool_name
        
        # 根据工具类型设置光标
        if tool_name in ["province", "height", "river"]:
            self.setCursor(Qt.CrossCursor)
        elif tool_name == "plot_select":
            self.setCursor(Qt.ArrowCursor)
        elif tool_name == "pan":
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def paintEvent(self, event):
        """绘制地图"""
        # 性能监控
        start_time = time.time()
        
        # 开始绘制
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
        self.draw_heightmap(painter)
        
        # 在拖动或调整大小时使用简化绘制
        if not self.is_dragging_view and not self.optimized_drawing:
            # 绘制大陆地块 (可以考虑缓存)
            self.draw_land_plots(painter)
            
            # 绘制省份
            self.draw_provinces(painter)
            
            # 绘制河流
            self.draw_rivers(painter)
        else:
            # 如果有缓存的省份图像，仍然绘制它们（不需要重新计算路径）
            if hasattr(self, 'provinces_cache'):
                painter.resetTransform()
                painter.drawImage(0, 0, self.provinces_cache)
                painter.translate(self.offset_x, self.offset_y)
                painter.scale(self.scale_factor, self.scale_factor)
        
        # 绘制当前工具的预览 (总是实时绘制)
        if self.show_tool_preview and not self.is_dragging_view:
            self.draw_tool_preview(painter)
        
        # 性能监控
        self.draw_time = time.time() - start_time
        
    def draw_heightmap(self, painter):
        """绘制高程图 - 使用缓存提高性能"""
        if not hasattr(self.controller, 'default_map') or not self.controller.default_map:
            return
        
        # 获取高程图数据
        heightmap = self.controller.default_map
        
        # 检查是否已创建缓存图像或者需要更新
        if not self.heightmap_image or self.needs_redraw:
            # 创建高程图缓存
            try:
                width = min(heightmap.width, 2000)  # 限制最大尺寸，防止内存溢出
                height = min(heightmap.height, 2000)
                
                # 使用更高效的方式创建图像
                self.heightmap_image = QImage(width, height, QImage.Format_RGB32)
                
                # 使用NumPy批量处理像素，避免逐个像素设置
                # 获取高程数据
                elevation_data = heightmap.data
                
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
                        self.heightmap_image.setPixel(x, y, img_buffer[y, x])
                
                self.needs_redraw = False
            except Exception as e:
                print(f"绘制高程图错误: {e}")
                return
        
        # 使用缓存的高程图绘制
        if self.heightmap_image:
            # 使用更高效的方式绘制，避免缩放和变换导致的抗锯齿计算
            if self.optimized_drawing:
                painter.setRenderHint(QPainter.Antialiasing, False)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
            
            painter.drawImage(0, 0, self.heightmap_image)
    
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
    
    def draw_land_plots(self, painter):
        """绘制大陆地块"""
        if not hasattr(self.controller, 'land_plots') or not self.controller.land_plots:
            return
        
        # 检查是否需要更新地块缓存
        if self.needs_redraw or not hasattr(self, 'land_plots_cache'):
            # 创建缓存图像
            self.land_plots_cache = QImage(self.width(), self.height(), QImage.Format_ARGB32)
            self.land_plots_cache.fill(Qt.transparent)
            
            # 创建缓存图像的绘制器
            cache_painter = QPainter(self.land_plots_cache)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # 应用与主绘制器相同的变换
            cache_painter.translate(self.offset_x, self.offset_y)
            cache_painter.scale(self.scale_factor, self.scale_factor)
            
            # 设置地块样式
            plot_pen = QPen(QColor(100, 100, 100, 100), 1)
            plot_brush = QBrush(QColor(200, 200, 100, 50))
            selected_brush = QBrush(QColor(255, 200, 50, 100))
            
            # 只绘制范围内的地块，避免不必要的绘制
            view_rect = self.mapToScene(self.rect()).boundingRect()
            
            # 提前准备好QPainterPath对象，避免重复创建
            for i, plot in enumerate(self.controller.land_plots):
                if not plot or not hasattr(plot, 'exterior'):
                    continue
                
                # 检查地块是否在可见区域内（简单的边界框检查）
                if hasattr(plot, 'bounds'):
                    bounds = plot.bounds
                    if bounds[2] < view_rect.left() or bounds[0] > view_rect.right() or \
                       bounds[3] < view_rect.top() or bounds[1] > view_rect.bottom():
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
        
        # 绘制缓存的地块图像
        if hasattr(self, 'land_plots_cache'):
            painter.resetTransform()
            painter.drawImage(0, 0, self.land_plots_cache)
            
            # 恢复变换
            painter.resetTransform()
            painter.translate(self.offset_x, self.offset_y)
            painter.scale(self.scale_factor, self.scale_factor)
    
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
        if self.current_tool in ["province", "height", "continent"]:
            # 绘制笔刷圆圈
            brush_size = self.controller.brush_size if hasattr(self.controller, 'brush_size') else 20
            
            # 优化性能：拖动和调整大小时使用更简单的笔刷预览
            if self.optimized_drawing:
                brush_pen = QPen(QColor(200, 200, 200))
                brush_pen.setWidth(1)
                painter.setPen(brush_pen)
                painter.setBrush(Qt.NoBrush)
            else:
                brush_pen = QPen(QColor(200, 200, 200, 180))
                brush_pen.setWidth(2)
                painter.setPen(brush_pen)
                
                # 半透明填充
                brush_fill = QColor(230, 230, 250, 50)
                painter.setBrush(QBrush(brush_fill))
            
            # 确保将浮点坐标转换为整数
            x = int(map_x - brush_size/2)
            y = int(map_y - brush_size/2)
            width = int(brush_size)
            height = int(brush_size)
            
            painter.drawEllipse(x, y, width, height)
    
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
        self.heightmap_image = None
        
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