# ui/map_canvas.py
import numpy as np
from PyQt5.QtWidgets import QWidget, QPushButton, QHBoxLayout, QToolBar, QApplication, QColorDialog
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QImage, QCursor, QPixmap, QPainterPath
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QPoint, QTimer

from models.province import Province
from models.heightmap import HeightMap
from models.texture import Texture
import shapely.geometry as sg
from shapely.ops import polygonize, unary_union
import cv2
from tools.brushes import ContinentBrush
from tools.land_divider import LandDivider  # 新增:导入大陆分割工具

class MapCanvas(QWidget):
    """地图画布组件，处理地图的绘制和交互"""
    
    # 自定义信号
    tool_changed = pyqtSignal(str)
    map_changed = pyqtSignal()
    
    def generate_color_palette(self, count=20):
        """生成美观且互相区分的颜色调色板"""
        colors = []
        for i in range(count):
            h = i / count
            s = 0.5 + np.random.uniform(-0.1, 0.1)
            v = 0.8 + np.random.uniform(-0.1, 0.1)
            colors.append(QColor.fromHsvF(h, s, v))
        return colors
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        
        # 地图数据
        self.provinces = []  # 省份列表
        self.rivers = []  # 河流列表
        self.land_plots = []  # 大陆地块列表
        self.land_plots_selected = []  # 已选择的地块列表，用于构建省份
        self.continent_mask = np.zeros((800, 600), dtype=bool) # 大陆掩码，初始全为 False
        
        self.texture_manager = Texture()  # 纹理管理器
        
        # UI状态
        self.current_tool = "province"  # 当前工具
        self.brush_size = 20  # 笔刷大小
        self.brush_strength = 10  # 笔刷强度
        self.current_color = QColor(100, 150, 200)  # 当前颜色
        
        # 编辑状态
        self.is_drawing = False  # 是否正在绘制
        self.selected_province = None  # 当前选中的省份
        self.current_province = None  # 当前正在创建的省份
        
        # 文件操作
        self.current_file_path = None  # 当前文件路径
        
        # 历史记录（简单实现）
        self.history = []  # 操作历史
        self.history_index = -1  # 历史索引
        self.max_history = 20  # 最大历史记录数量
        
        # 笔刷绘制优化
        self.last_brush_position = None  # 上一次笔刷位置，用于线性插值
        
        self.setMouseTracking(True)  # 启用鼠标跟踪
        self.setFocusPolicy(Qt.StrongFocus)  # 可以获取键盘焦点
        
        self.default_map = HeightMap(800, 600)  # 高程图
        self.default_map_image = QImage()  # 新增：高程图离屏缓存
        self.update_default_map_image()  # 新增：初始化高程图缓存

        self.id = np.random.randint(10000, 99999)
        self.province_drawing_points = []

        # 初始化颜色调色板
        self.available_colors = self.generate_color_palette(20)
        
        self.blank_cursor = self.create_blank_cursor()
        
        # 初始化大陆分割工具
        self.land_divider = LandDivider()
        
        # 初始化省份编辑悬浮工具栏
        self.floating_toolbar = None
        self.show_province_toolbar_timer = QTimer(self)
        self.show_province_toolbar_timer.setSingleShot(True)
        self.show_province_toolbar_timer.timeout.connect(self.show_province_toolbar)

    def _get_land_polygon(self):
        if self.default_map is None or self.default_map.data is None:
            return None

        # Create a binary mask: 1 for land (elevation > 0), 0 for water
        land_mask = (self.default_map.data > 0).astype(np.uint8) * 255
        if np.sum(land_mask) == 0: # No land pixels
            return None

        # Find contours of land areas
        contours, hierarchy = cv2.findContours(land_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        polygons = []
        for contour in contours:
            if len(contour) >= 3: # A polygon needs at least 3 vertices
                # Squeeze the contour to remove redundant dimensions and convert to list of points
                points = contour.squeeze().tolist()
                # Ensure points is a list of coordinate pairs e.g. [[x1,y1], [x2,y2], ...]
                if isinstance(points, list) and len(points) >= 3:
                    if not isinstance(points[0], list):
                        # Handle cases where squeeze might result in a flat list for simple contours
                        # or a single point if contour was too small/degenerate after squeeze.
                        # This check might need refinement based on cv2.findContours output structure.
                        # For now, we assume it's a list of lists or can be skipped.
                        pass # Or try to reshape if a known pattern, otherwise skip
                    else:
                        try:
                            polygon = sg.Polygon(points)
                            if polygon.is_valid:
                                polygons.append(polygon)
                        except Exception: # Invalid polygon geometry (e.g., self-intersecting)
                            pass 
        
        if not polygons:
            return None
        
        # Combine all land polygons into a single MultiPolygon or Polygon
        land_geometry = unary_union(polygons)
        
        # Ensure it's a valid geometry
        if not land_geometry.is_valid:
            land_geometry = land_geometry.buffer(0) # Try to fix minor invalidities
        
        if land_geometry.is_valid and not land_geometry.is_empty:
            return land_geometry
        return None

    # 新增方法：更新高程图缓存
    def update_default_map_image(self):
        """将高程数据转换为QImage缓存"""
        self.default_map_image = QImage(
            self.default_map.width, 
            self.default_map.height, 
            QImage.Format_RGB32
        )
        
        for y in range(self.default_map.height):
            for x in range(self.default_map.width):
                elevation = self.default_map.data[y, x]
                # 颜色映射逻辑与原draw_heightmap一致
                if elevation > 0:
                    if elevation < 20: color = QColor(180, 210, 230)
                    elif elevation < 40: color = QColor(180, 220, 130)
                    elif elevation < 70: color = QColor(160, 190, 110)
                    elif elevation < 90: color = QColor(140, 160, 90)
                    else: color = QColor(220, 220, 220)
                else:
                    color = QColor(120, 172, 215)  # 水域背景色
                
                self.default_map_image.setPixelColor(x, y, color)

    def create_blank_cursor(self):
        pixmap = QPixmap(1, 1)
        pixmap.fill(Qt.transparent)
        return QCursor(pixmap)

    def paintEvent(self, event):
        """绘制地图"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景（水域）
        painter.fillRect(self.rect(), QColor(120, 172, 215))
        
        # 绘制高程图
        self.draw_heightmap(painter)
        
        # 绘制省份
        self.draw_provinces(painter)
        
        # 绘制河流
        self.draw_rivers(painter)

        # 绘制大陆地块
        self.draw_land_plots(painter)
        
        # 绘制当前工具的预览
        self.draw_tool_preview(painter)
        
    def draw_heightmap(self, painter):
        """绘制高程图"""
        painter.drawImage(0, 0, self.default_map_image)
        
    def draw_provinces(self, painter):
        """绘制省份"""
        # 绘制已完成的省份
        for province in self.provinces:
            if province.path:
                painter.fillPath(province.path, province.color)
                pen = QPen(Qt.black, 2)
                painter.setPen(pen)
                painter.drawPath(province.path)
                
                if province == self.selected_province:
                    highlight_pen = QPen(Qt.red, 3, Qt.DashLine)
                    painter.setPen(highlight_pen)
                    painter.drawPath(province.path)
        
        # 绘制正在创建的省份（通过高亮显示选中的地块）
        if self.current_province and hasattr(self.current_province, 'plot_indices'):
            highlight_pen = QPen(QColor(60, 60, 200, 220), 2, Qt.SolidLine)
            highlight_brush = QBrush(self.current_province.color)
            painter.setPen(highlight_pen)
            painter.setBrush(highlight_brush)
            
            for idx in self.current_province.plot_indices:
                if idx < len(self.land_plots):
                    plot_polygon = self.land_plots[idx]
                    if plot_polygon and plot_polygon.is_valid and plot_polygon.geom_type == 'Polygon':
                        q_path = QPainterPath()
                        exterior_coords = list(plot_polygon.exterior.coords)
                        if not exterior_coords:
                            continue
                        
                        q_path.moveTo(exterior_coords[0][0], exterior_coords[0][1])
                        for i in range(1, len(exterior_coords)):
                            q_path.lineTo(exterior_coords[i][0], exterior_coords[i][1])
                        q_path.closeSubpath()
                        
                        # 绘制内部孔洞 (如果存在)
                        for interior_ring in plot_polygon.interiors:
                            interior_coords = list(interior_ring.coords)
                            if not interior_coords:
                                continue
                            
                            # 开始新的子路径用于孔洞
                            q_path.moveTo(interior_coords[0][0], interior_coords[0][1])
                            for i in range(1, len(interior_coords)):
                                q_path.lineTo(interior_coords[i][0], interior_coords[i][1])
                            q_path.closeSubpath()
                        
                        q_path.setFillRule(Qt.OddEvenFill)  # 确保孔洞正确渲染
                        painter.drawPath(q_path)
        
        # 绘制正在创建的省份边界线（保留原有功能）
        if self.province_drawing_points and len(self.province_drawing_points) >= 2:
            # 只画黑线，不填充
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)
            
            # 绘制连接点的线段
            for i in range(len(self.province_drawing_points) - 1):
                p1 = self.province_drawing_points[i]
                p2 = self.province_drawing_points[i + 1]
                painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            
            # 如果起点和终点足够近，显示闭合提示
            if len(self.province_drawing_points) > 2:
                first = self.province_drawing_points[0]
                last = self.province_drawing_points[-1]
                dist = np.sqrt((first[0] - last[0])**2 + (first[1] - last[1])**2)
                if dist < 20:
                    # 显示闭合线
                    painter.drawLine(last[0], last[1], first[0], first[1])
                    
                    # 可选：显示一个圆圈表示可以闭合
                    painter.setPen(QPen(Qt.red, 2))
                    painter.drawEllipse(first[0]-5, first[1]-5, 10, 10)

    def draw_rivers(self, painter):
        """绘制河流"""
        pen = QPen(QColor(70, 130, 180), 3)
        painter.setPen(pen)
        
        for river in self.rivers:
            if len(river) < 2:
                continue
                
            for i in range(len(river) - 1):
                painter.drawLine(river[i][0], river[i][1], river[i + 1][0], river[i + 1][1])
    
    def draw_tool_preview(self, painter):
        """绘制当前工具的预览"""
        if not hasattr(self, 'mouse_pos') or self.mouse_pos is None:
            return
            
        x, y = self.mouse_pos.x(), self.mouse_pos.y()
        
        if self.current_tool == "province":
            # 绘制省份工具预览
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(self.current_color, Qt.SolidPattern))
            painter.drawEllipse(int(x - self.brush_size / 2), int(y - self.brush_size / 2), 
                               int(self.brush_size), int(self.brush_size))
        
        elif self.current_tool == "height":
            # 绘制高程工具预览
            pen = QPen(QColor(0, 0, 0, 100), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(200, 200, 200, 100)))
            painter.drawEllipse(int(x - self.brush_size / 2), int(y - self.brush_size / 2), 
                               int(self.brush_size), int(self.brush_size))
        
        elif self.current_tool == "river":
            # 绘制河流工具预览
            pen = QPen(QColor(70, 130, 180), 3)
            painter.setPen(pen)
            painter.drawEllipse(int(x - 5), int(y - 5), 10, 10)
        
        elif self.current_tool == "continent":
            # 绘制大陆工具预览
            pen = QPen(QColor(50, 50, 50, 150), 2)  # 使用独特颜色以便区分
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(150, 100, 50, 100)))  # 使用大地色调
            painter.drawEllipse(int(x - self.brush_size / 2), int(y - self.brush_size / 2), 
                               int(self.brush_size), int(self.brush_size))
        
        elif self.current_tool == "plot_select":
            # 绘制地块选择工具预览
            pen = QPen(QColor(50, 100, 200, 180), 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(100, 150, 250, 80)))
            painter.drawEllipse(int(x - self.brush_size / 2), int(y - self.brush_size / 2), 
                               int(self.brush_size), int(self.brush_size))
    
    def interpolate_brush_positions(self, start_pos, end_pos, brush_size):
        """在两点间插值生成中间点，确保笔触连续"""
        if start_pos is None or end_pos is None:
            return [end_pos] if end_pos else []
            
        x1, y1 = start_pos.x(), start_pos.y()
        x2, y2 = end_pos.x(), end_pos.y()
        
        # 计算两点间距离
        dist = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        
        # 如果距离小于笔刷大小的一半，不需要插值
        if dist < brush_size / 2:
            return [end_pos]
            
        # 计算需要插入的点数，确保相邻点间距不超过笔刷大小的一半
        steps = max(2, int(dist / (brush_size / 2)))
        
        # 生成插值点
        positions = []
        for i in range(1, steps + 1):
            t = i / steps
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t
            positions.append(QPoint(int(x), int(y)))
            
        return positions
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            
            if self.current_tool == "province":
                # 修改为涂抹选择地块
                # 检查是否有地块
                if not self.land_plots:
                    # 如果没有地块，尝试生成地块
                    land_geometry = self._get_land_polygon()
                    if land_geometry:
                        self.generate_land_plots()
                        
                # 创建新省份或使用当前选中的省份
                if not self.current_province:
                    self.current_province = Province(name=f"省份{len(self.provinces)}", color=self.get_new_province_color())
                    self.current_province.plot_indices = []  # 存储地块索引
                
                # 选择笔刷范围内的地块
                self.select_plots_in_brush(event.pos())
                
                # 启动悬浮工具栏计时器
                self.show_province_toolbar_timer.start(500)
            
            elif self.current_tool == "height":
                # 修改高程
                self.apply_height_brush(event.pos())
            
            elif self.current_tool == "river":
                # 开始绘制河流
                self.rivers.append([(event.x(), event.y())])
            
            elif self.current_tool == "continent":
                # 应用大陆笔刷
                continent_brush = ContinentBrush(size=self.brush_size, strength=self.brush_strength)
                
                # 获取修改的矩形区域并只更新该区域
                region = continent_brush.apply(self, event.pos())
                if region:
                    self.update_default_map_image_region(*region)
                    # 只更新被修改的区域
                    self.update(QRect(*region))
                    
                    # 记录当前位置用于后续插值
                    self.last_brush_position = event.pos()
                    return  # 提前返回，避免调用全局update()
            
            elif self.current_tool == "plot_select":
                # 选择地块
                if event.modifiers() & Qt.ControlModifier:
                    # Ctrl+点击取消选择地块
                    self.deselect_land_plot(event.pos())
                else:
                    # 点击选择地块
                    self.select_land_plot(event.pos())
            else:
                # 其他工具或没有特定工具时，尝试选择省份
                self.select_province(event.pos())
            
            self.update()
        
        # 右键点击可以直接选择省份，无论当前工具是什么
        elif event.button() == Qt.RightButton:
            self.select_province(event.pos())
            self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        self.mouse_pos = event.pos()
        
        if self.is_drawing:
            if self.current_tool == "province":
                # 省份工具现在是涂抹选择地块
                # 使用插值生成平滑路径
                if self.last_brush_position:
                    interpolated_positions = self.interpolate_brush_positions(
                        self.last_brush_position, event.pos(), self.brush_size)
                    
                    # 对每个插值点选择地块
                    for pos in interpolated_positions:
                        self.select_plots_in_brush(pos)
                else:
                    self.select_plots_in_brush(event.pos())
            
            elif self.current_tool == "height":
                self.apply_height_brush(event.pos())
            
            elif self.current_tool == "river":
                current_river = self.rivers[-1]
                current_river.append((event.x(), event.y()))

            elif self.current_tool == "continent" and self.is_drawing:
                # 使用插值生成平滑路径
                interpolated_positions = self.interpolate_brush_positions(
                    self.last_brush_position, event.pos(), self.brush_size)
                
                updated_regions = []
                continent_brush = ContinentBrush(size=self.brush_size, strength=self.brush_strength)
                
                # 对每个插值点应用笔刷
                for pos in interpolated_positions:
                    region = continent_brush.apply(self, pos)
                    if region:
                        updated_regions.append(region)
                
                # 合并所有更新区域为一个大区域
                if updated_regions:
                    x_min = min(r[0] for r in updated_regions)
                    y_min = min(r[1] for r in updated_regions)
                    x_max = max(r[0] + r[2] for r in updated_regions)
                    y_max = max(r[1] + r[3] for r in updated_regions)
                    
                    # 一次性更新合并后的区域
                    merged_region = (x_min, y_min, x_max - x_min, y_max - y_min)
                    self.update_default_map_image_region(*merged_region)
                    self.update(QRect(*merged_region))
                    
                    # 更新上次位置
                    self.last_brush_position = event.pos()
                    return  # 提前返回，避免调用全局update()
            
            elif self.current_tool == "plot_select" and self.is_drawing:
                # 拖动时继续选择地块
                if event.modifiers() & Qt.ControlModifier:
                    # Ctrl+拖动取消选择地块
                    self.deselect_land_plot(event.pos())
                else:
                    # 拖动选择地块
                    self.select_land_plot(event.pos())
        
        self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            self.last_brush_position = None  # 清除上次位置
            
            if self.current_tool == "province":
                # 结束省份绘制，添加当前省份到省份列表
                if self.current_province and hasattr(self.current_province, 'plot_indices') and self.current_province.plot_indices:
                    # 构建省份边界
                    self.finalize_province_from_plots()
                    self.provinces.append(self.current_province)
                    self.selected_province = self.current_province
                    # 更新当前省份为空，准备创建新省份
                    self.current_province = None
                    self.add_to_history()
            
            elif self.current_tool == "continent":
                # 大陆工具释放后添加到历史记录，但不立即进行分割
                self.add_to_history()
                
                # 注意：不像之前那样，这里不再调用全局的update_default_map_image
                # 那个操作现在在mousePressEvent和mouseMoveEvent中以局部方式处理
                
                # 仍然需要触发地图变化信号
                self.map_changed.emit()
            
            elif self.current_tool == "height" or self.current_tool == "river":
                # 高程和河流工具释放后记录历史
                self.add_to_history()
                self.update()
                self.map_changed.emit()
            
            elif self.current_tool == "plot_select":
                # 地块选择工具释放时不执行特殊操作
                pass
            
            self.update()
            self.map_changed.emit()

    def keyPressEvent(self, event):
        """键盘按键事件"""
        if event.key() == Qt.Key_Escape:
            # 如果正在绘制，取消绘制
            self.is_drawing = False
            
            # 如果有当前正在创建/编辑的省份，则取消
            if self.current_province:
                # 如果是编辑现有省份，恢复原来的状态
                if self.current_province in self.provinces:
                    # 这里可以加入恢复原始状态的代码
                    pass
                self.current_province = None
            
            self.update()
        
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            # 撤销操作
            self.undo()
        
        elif event.key() == Qt.Key_Y and event.modifiers() & Qt.ControlModifier:
            # 重做操作
            self.redo()
        
        elif event.key() == Qt.Key_E and self.selected_province:
            # E键编辑选中的省份
            if self.current_tool == "province" and not self.current_province:
                self.current_province = self.selected_province
                self.update()
        
        elif event.key() == Qt.Key_Delete and self.selected_province:
            # Delete键删除选中的省份
            self.provinces.remove(self.selected_province)
            self.selected_province = None
            self.update()
            self.map_changed.emit()
    
    # 修改apply_height_brush方法，添加局部更新逻辑
    def apply_height_brush(self, pos):
        x, y = pos.x(), pos.y()
        radius = self.brush_size // 2
        strength = self.brush_strength
        
        # 记录修改区域边界
        min_x = max(0, x - radius)
        max_x = min(self.width(), x + radius)
        min_y = max(0, y - radius)
        max_y = min(self.height(), y + radius)
        
        self.default_map.add_hill(x, y, radius, strength)
        
        # 只更新受影响区域的高程缓存
        for y_pix in range(min_y, max_y):
            for x_pix in range(min_x, max_x):
                elevation = self.default_map.data[y_pix, x_pix]
                # 颜色计算逻辑
                self.default_map_image.setPixelColor(x_pix, y_pix, elevation)
        
        # 请求局部重绘
        self.update(QRect(min_x, min_y, max_x - min_x, max_y - min_y))
    
    def set_tool(self, tool_name):
        """设置当前工具"""
        if tool_name not in ["province", "height", "river", "continent", "plot_select"]:
            print(f"未知工具: {tool_name}")
            return
            
        # 如果是从省份工具切换到其他工具，结束当前省份的编辑
        if self.current_tool == "province" and tool_name != "province" and self.current_province:
            # 如果当前省份有地块，则添加到省份列表
            if hasattr(self.current_province, 'plot_indices') and self.current_province.plot_indices:
                self.finalize_province_from_plots()
                # 如果是新建的省份，添加到列表
                if self.current_province not in self.provinces:
                    self.provinces.append(self.current_province)
                self.selected_province = self.current_province
                self.current_province = None
                self.add_to_history()
            
            # 安全地隐藏悬浮工具栏
            if hasattr(self, 'floating_toolbar') and self.floating_toolbar:
                try:
                    if self.floating_toolbar.isVisible():
                        self.floating_toolbar.hide()
                    self.floating_toolbar.deleteLater()
                except RuntimeError:
                    # 捕获对象已删除的错误
                    pass
                self.floating_toolbar = None
        
        self.current_tool = tool_name
        
        # 切换工具时清除一些状态
        if tool_name != "province":
            self.province_drawing_points = []
        
        # 如果切换到地块选择工具，确保已生成地块
        if tool_name == "plot_select" and not self.land_plots:
            land_geometry = self._get_land_polygon()
            if land_geometry:
                self.generate_land_plots()
        
        # 如果切换到省份工具，显示悬浮工具栏
        if tool_name == "province" and self.current_province:
            self.show_province_toolbar_timer.start(500)  # 延迟显示，避免频繁切换时闪烁
        
        self.tool_changed.emit(tool_name)
        self.update()
    
    def set_brush_size(self, size):
        """设置笔刷大小"""
        self.brush_size = size
        self.update()
    
    def set_brush_strength(self, strength):
        """设置笔刷强度"""
        self.brush_strength = strength
    
    def set_color(self, color):
        """设置当前颜色"""
        self.current_color = color
        self.update()
    
    def reset_map(self):
        """重置地图"""
        self.provinces = []
        self.default_map = HeightMap(self.width(), self.height())
        self.rivers = []
        self.selected_province = None
        self.current_file_path = None
        self.history = []
        self.history_index = -1
        self.update()
        self.map_changed.emit()
    
    def load_map(self, file_path):
        """加载地图"""
        # 在实际应用中实现加载逻辑
        pass
    
    def save_map(self, file_path):
        """保存地图"""
        # 在实际应用中实现保存逻辑
        pass
    
    def add_to_history(self):
        """添加当前状态到历史记录"""
        # 在实际应用中，应该深拷贝当前地图状态
        # 这里为简化只添加一个标记
        self.history = self.history[:self.history_index + 1]
        self.history.append("地图状态")
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        self.history_index = len(self.history) - 1
    
    def undo(self):
        """撤销操作"""
        if self.history_index > 0:
            self.history_index -= 1
            # 在实际应用中，应恢复到先前的状态
            self.update()
            self.map_changed.emit()
    
    def redo(self):
        """重做操作"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            # 在实际应用中，应恢复到后续的状态
            self.update()
            self.map_changed.emit()

    def _split_polygon_into_grid_plots(self, main_polygon, cell_size=50):
        """将一个多边形（或多个多边形）分割成基于网格的地块"""
        plots = []
        if not main_polygon or main_polygon.is_empty:
            return plots

        polygons_to_split = []
        if main_polygon.geom_type == 'Polygon':
            polygons_to_split.append(main_polygon)
        elif main_polygon.geom_type == 'MultiPolygon':
            polygons_to_split.extend(list(main_polygon.geoms))

        for poly_to_split in polygons_to_split:
            if not poly_to_split.is_valid or poly_to_split.is_empty:
                continue
            minx, miny, maxx, maxy = poly_to_split.bounds
            
            for x_start in np.arange(minx, maxx, cell_size):
                for y_start in np.arange(miny, maxy, cell_size):
                    cell = sg.box(x_start, y_start, x_start + cell_size, y_start + cell_size)
                    intersection = poly_to_split.intersection(cell)
                    
                    if not intersection.is_empty and intersection.is_valid:
                        if intersection.geom_type == 'Polygon' and intersection.area > 1e-6: # 最小面积阈值
                            plots.append(intersection)
                        elif intersection.geom_type == 'MultiPolygon':
                            for p_geom in intersection.geoms: # Changed variable name from p to p_geom
                                if p_geom.is_valid and p_geom.geom_type == 'Polygon' and p_geom.area > 1e-6:
                                    plots.append(p_geom)
        return plots

    def generate_land_plots(self, plot_cell_size=50):
        """生成大陆地块，使用自然分割方法"""
        self.land_plots = []  # 清除之前的地块
        self.land_plots_selected = []  # 清除已选择的地块
        
        land_geometry = self._get_land_polygon()
        if land_geometry:
            # 使用自然分割方法替代原来的网格分割
            try:
                # 尝试使用Voronoi分割方法
                self.land_plots = self.land_divider.divide_land_with_voronoi(land_geometry, n_divisions=30)
            except Exception as e:
                print(f"Voronoi分割失败: {e}")
                # 回退到栅格+分水岭方法
                try:
                    self.land_plots = self.land_divider.raster_based_division(land_geometry, n_divisions=30)
                except Exception as e:
                    print(f"栅格分水岭分割失败: {e}")
                    # 最后回退到原来的网格方法
                    self.land_plots = self._split_polygon_into_grid_plots(land_geometry, cell_size=plot_cell_size)
            
            self.update()  # 触发重绘
            self.map_changed.emit()  # 发出地图变化信号
            self.add_to_history()  # 记录历史，以便撤销
            
    def select_land_plot(self, pos):
        """选择点击位置处的地块"""
        x, y = pos.x(), pos.y()
        point = sg.Point(x, y)
        
        for plot in self.land_plots:
            if plot.contains(point):
                if plot not in self.land_plots_selected:
                    self.land_plots_selected.append(plot)
                    self.update()  # 触发重绘
                return True
        return False
    
    def deselect_land_plot(self, pos):
        """取消选择点击位置处的地块"""
        x, y = pos.x(), pos.y()
        point = sg.Point(x, y)
        
        for i, plot in enumerate(self.land_plots_selected):
            if plot.contains(point):
                self.land_plots_selected.pop(i)
                self.update()  # 触发重绘
                return True
        return False
    
    def create_province_from_selected_plots(self):
        """从选择的地块创建新省份"""
        if not self.land_plots_selected:
            return None
            
        # 合并所有选中的地块
        union_geom = unary_union(self.land_plots_selected)
        
        if union_geom.is_empty:
            return None
            
        # 创建新的省份对象
        province = Province(name="新省份", color=self.current_color)
        
        # 添加合并后多边形的边界点
        if union_geom.geom_type == 'Polygon':
            exterior_coords = list(union_geom.exterior.coords)
            province.points = exterior_coords
        elif union_geom.geom_type == 'MultiPolygon':
            # 如果是多个多边形，取最大的一个
            largest = max(union_geom.geoms, key=lambda p: p.area)
            exterior_coords = list(largest.exterior.coords)
            province.points = exterior_coords
            
        # 完成省份几何构建
        province.finalize_shape()
        
        # 清空已选择的地块
        self.land_plots_selected = []
        
        return province

    def draw_land_plots(self, painter):
        """绘制大陆地块"""
        if not self.land_plots:
            return
        
        # 收集所有已被分配到省份的地块索引
        allocated_plots = set()
        for province in self.provinces:
            if hasattr(province, 'plot_indices'):
                allocated_plots.update(province.plot_indices)
        
        # 如果有当前正在创建的省份，也将其地块加入到已分配列表中
        if self.current_province and hasattr(self.current_province, 'plot_indices'):
            allocated_plots.update(self.current_province.plot_indices)
        
        # 绘制未选择且未分配给任何省份的地块
        pen = QPen(QColor(80, 80, 80, 180), 1, Qt.DotLine)  # 设置地块边框颜色和样式
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)  # 地块不填充

        for i, plot_polygon in enumerate(self.land_plots):
            # 跳过已选择或已分配给省份的地块 (这里只跳过绘制填充色，边界线仍然绘制)
            if plot_polygon in self.land_plots_selected or i in allocated_plots:
                # 对于已分配地块，只绘制边界
                if plot_polygon and plot_polygon.is_valid and plot_polygon.geom_type == 'Polygon':
                    q_path = QPainterPath()
                    exterior_coords = list(plot_polygon.exterior.coords)
                    if not exterior_coords:
                        continue
                    
                    q_path.moveTo(exterior_coords[0][0], exterior_coords[0][1])
                    for j in range(1, len(exterior_coords)):
                        q_path.lineTo(exterior_coords[j][0], exterior_coords[j][1])
                    q_path.closeSubpath()
                    
                    # 只绘制边界，不填充
                    painter.drawPath(q_path)
                continue
            
            if plot_polygon and plot_polygon.is_valid and plot_polygon.geom_type == 'Polygon':
                q_path = QPainterPath()
                exterior_coords = list(plot_polygon.exterior.coords)
                if not exterior_coords:
                    continue
                
                q_path.moveTo(exterior_coords[0][0], exterior_coords[0][1])
                for j in range(1, len(exterior_coords)):
                    q_path.lineTo(exterior_coords[j][0], exterior_coords[j][1])
                q_path.closeSubpath()
                
                # 绘制内部孔洞 (如果存在)
                for interior_ring in plot_polygon.interiors:
                    interior_coords = list(interior_ring.coords)
                    if not interior_coords:
                        continue
                    
                    # 开始新的子路径用于孔洞
                    q_path.moveTo(interior_coords[0][0], interior_coords[0][1])
                    for j in range(1, len(interior_coords)):
                        q_path.lineTo(interior_coords[j][0], interior_coords[j][1])
                    q_path.closeSubpath()
                
                q_path.setFillRule(Qt.OddEvenFill)  # 确保孔洞正确渲染
                painter.drawPath(q_path)
        
        # 绘制已选择但还未分配给当前省份的地块
        if self.land_plots_selected:
            highlight_pen = QPen(QColor(60, 60, 200, 220), 2, Qt.SolidLine)
            highlight_brush = QBrush(QColor(100, 100, 220, 120))
            painter.setPen(highlight_pen)
            painter.setBrush(highlight_brush)
            
            for plot_polygon in self.land_plots_selected:
                if plot_polygon and plot_polygon.is_valid and plot_polygon.geom_type == 'Polygon':
                    q_path = QPainterPath()
                    exterior_coords = list(plot_polygon.exterior.coords)
                    if not exterior_coords:
                        continue
                    
                    q_path.moveTo(exterior_coords[0][0], exterior_coords[0][1])
                    for j in range(1, len(exterior_coords)):
                        q_path.lineTo(exterior_coords[j][0], exterior_coords[j][1])
                    q_path.closeSubpath()
                    
                    # 绘制内部孔洞 (如果存在)
                    for interior_ring in plot_polygon.interiors:
                        interior_coords = list(interior_ring.coords)
                        if not interior_coords:
                            continue
                        
                        # 开始新的子路径用于孔洞
                        q_path.moveTo(interior_coords[0][0], interior_coords[0][1])
                        for j in range(1, len(interior_coords)):
                            q_path.lineTo(interior_coords[j][0], interior_coords[j][1])
                        q_path.closeSubpath()
                    
                    q_path.setFillRule(Qt.OddEvenFill)  # 确保孔洞正确渲染
                    painter.drawPath(q_path)
    
    def zoom_in(self):
        """放大地图"""
        # 在实际应用中实现缩放逻辑
        pass
    
    def zoom_out(self):
        """缩小地图"""
        # 在实际应用中实现缩放逻辑
        pass

    def enterEvent(self, event):
        if self.current_tool in ["province", "height", "river"]:
            self.setCursor(self.blank_cursor)

    def handle_province_overlaps(self, new_province):
        """处理新省份与现有省份的重叠问题"""
        overlapped = False
        affected_provinces = []
        
        for province in self.provinces:
            if province != new_province and province.intersects(new_province):
                overlapped = True
                affected_provinces.append(province)
        
        if not overlapped:
            return
        
        # 处理重叠：新省份保持不变，修改旧省份
        for province in affected_provinces:
            original_polygon = province.boundary_polygon
            province.subtract(new_province)
            
            # 如果差集操作导致省份消失或变得很小，则删除它
            if (not province.boundary_polygon or 
                province.boundary_polygon.area < 100 or 
                not province.points or 
                len(province.points) < 3):
                self.provinces.remove(province)

    def find_province_neighbors(self):
        """查找并更新所有省份之间的邻接关系"""
        for i, province in enumerate(self.provinces):
            province.neighbors.clear()  # 清除旧的邻居关系
            
            for j, other in enumerate(self.provinces):
                if i != j and province.intersects(other):
                    # 由于Province类中没有id属性，使用列表索引代替
                    province.neighbors.add(j)
                    other.neighbors.add(i)

    def get_distinct_color(self, province):
        """为省份获取一个与邻居不同的颜色"""
        # 收集邻居的颜色
        neighbor_colors = set()
        for neighbor_idx in province.neighbors:
            # 找到对应的省份
            for i, p in enumerate(self.provinces):
                if i == neighbor_idx:
                    if hasattr(p, 'color'):
                        neighbor_colors.add(p.color.name())
                    break
        
        # 从可用颜色中选择一个未被邻居使用的颜色
        available = [c for c in self.available_colors if c.name() not in neighbor_colors]
        
        if available:
            return np.random.choice(available)
        else:
            # 如果所有颜色都被使用，生成一个新随机颜色
            h = np.random.random()
            s = 0.5 + np.random.uniform(-0.1, 0.1)
            v = 0.8 + np.random.uniform(-0.1, 0.1)
            return QColor.fromHsvF(h, s, v)

    def export_map_data(self, file_path):
        """导出地图数据，包含所有地块和省份信息
        
        导出格式为JSON，包含以下内容：
        1. 地图基本信息（宽度，高度）
        2. 大陆区域数据（高程数据）
        3. 所有分割的地块数据（坐标点列表）
        4. 省份数据（名称、颜色、所包含的地块索引）
        5. 河流数据
        """
        import json
        
        # 准备导出数据
        export_data = {
            "map_info": {
                "width": self.width(),
                "height": self.height(),
                "version": "1.0"
            },
            "heightmap": {
                "width": self.default_map.width,
                "height": self.default_map.height,
                # 将二维数组转换为一维列表
                "data": self.default_map.data.tolist()
            },
            "land_plots": [],
            "provinces": [],
            "rivers": []
        }
        
        # 导出地块数据
        for i, plot in enumerate(self.land_plots):
            if not plot.is_valid:
                continue
                
            plot_data = {
                "id": i,
                "exterior": [[p[0], p[1]] for p in list(plot.exterior.coords)],
                "interiors": [[[p[0], p[1]] for p in list(interior.coords)] for interior in plot.interiors],
                "area": plot.area,
                "province_id": -1  # 默认不属于任何省份
            }
            export_data["land_plots"].append(plot_data)
        
        # 导出省份数据
        for i, province in enumerate(self.provinces):
            if not province.boundary_polygon or not province.boundary_polygon.is_valid:
                continue
            
            # 检查是否有存储的地块索引
            contained_plots = []
            if hasattr(province, 'plot_indices') and province.plot_indices:
                contained_plots = [idx for idx in province.plot_indices if idx < len(self.land_plots)]
                # 更新地块所属省份
                for plot_idx in contained_plots:
                    if plot_idx < len(export_data["land_plots"]):
                        export_data["land_plots"][plot_idx]["province_id"] = i
            else:
                # 兼容旧方法：根据边界多边形查找包含的地块
                for j, plot in enumerate(self.land_plots):
                    if province.boundary_polygon.contains(plot) or province.boundary_polygon.overlaps(plot):
                        contained_plots.append(j)
                        export_data["land_plots"][j]["province_id"] = i  # 更新地块所属省份
            
            province_data = {
                "id": i,
                "name": province.name,
                "color": {
                    "r": province.color.red(),
                    "g": province.color.green(),
                    "b": province.color.blue(),
                    "a": province.color.alpha()
                },
                "boundary": [[p[0], p[1]] for p in province.points],
                "contained_plots": contained_plots
            }
            export_data["provinces"].append(province_data)
        
        # 导出河流数据
        for i, river in enumerate(self.rivers):
            if len(river) < 2:
                continue
                
            river_data = {
                "id": i,
                "points": [[p[0], p[1]] for p in river]
            }
            export_data["rivers"].append(river_data)
        
        # 写入文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出地图数据失败: {e}")
            return False
            
    def import_map_data(self, file_path):
        """导入地图数据，恢复所有地块和省份信息"""
        import json
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 验证版本
            version = import_data.get("map_info", {}).get("version", "")
            if version != "1.0":
                print(f"警告: 导入的地图数据版本({version})可能不兼容")
            
            # 恢复高程图
            heightmap_data = import_data.get("heightmap", {})
            if heightmap_data:
                width = heightmap_data.get("width", self.width())
                height = heightmap_data.get("height", self.height())
                data = heightmap_data.get("data", [])
                
                if data and width > 0 and height > 0:
                    # 重新创建高程图
                    self.default_map = HeightMap(width, height)
                    self.default_map.data = np.array(data)
                    self.update_default_map_image()
            
            # 清除现有数据
            self.land_plots = []
            self.provinces = []
            self.rivers = []
            
            # 恢复地块数据
            for plot_data in import_data.get("land_plots", []):
                exterior = plot_data.get("exterior", [])
                interiors = plot_data.get("interiors", [])
                
                if len(exterior) >= 3:
                    # 创建多边形
                    try:
                        polygon = sg.Polygon(exterior, holes=interiors)
                        if polygon.is_valid:
                            self.land_plots.append(polygon)
                    except Exception as e:
                        print(f"创建地块多边形失败: {e}")
            
            # 恢复省份数据
            for province_data in import_data.get("provinces", []):
                name = province_data.get("name", "未命名省份")
                color_data = province_data.get("color", {})
                color = QColor(
                    color_data.get("r", 0),
                    color_data.get("g", 0),
                    color_data.get("b", 0),
                    color_data.get("a", 255)
                )
                boundary = province_data.get("boundary", [])
                contained_plots = province_data.get("contained_plots", [])
                
                if len(boundary) >= 3:
                    province = Province(name=name, color=color)
                    province.points = boundary
                    
                    # 设置省份包含的地块索引
                    province.plot_indices = contained_plots
                    
                    if province.finalize_shape():
                        self.provinces.append(province)
            
            # 恢复河流数据
            for river_data in import_data.get("rivers", []):
                points = river_data.get("points", [])
                if len(points) >= 2:
                    self.rivers.append(points)
            
            self.update()
            self.map_changed.emit()
            return True
            
        except Exception as e:
            print(f"导入地图数据失败: {e}")
            return False

    def update_default_map_image_region(self, x, y, width, height):
        """局部更新高程图缓存，只更新指定矩形区域"""
        if not hasattr(self, 'default_map_image') or self.default_map_image is None:
            self.update_default_map_image()
            return
            
        # 确保区域在有效范围内
        x = max(0, x)
        y = max(0, y)
        width = min(self.default_map.width - x, width)
        height = min(self.default_map.height - y, height)
        
        if width <= 0 or height <= 0:
            return
            
        # 只更新指定区域的像素
        for j in range(y, y + height):
            for i in range(x, x + width):
                elevation = self.default_map.data[j, i]
                # 颜色映射逻辑
                if elevation > 0:
                    if elevation < 20: color = QColor(180, 210, 230)
                    elif elevation < 40: color = QColor(180, 220, 130)
                    elif elevation < 70: color = QColor(160, 190, 110)
                    elif elevation < 90: color = QColor(140, 160, 90)
                    else: color = QColor(220, 220, 220)
                else:
                    color = QColor(120, 172, 215)  # 水域背景色
                
                self.default_map_image.setPixelColor(i, j, color)

    def select_plots_in_brush(self, pos):
        """选择笔刷范围内的地块，添加到当前省份"""
        if not self.land_plots or not self.current_province:
            return
        
        x, y = pos.x(), pos.y()
        radius = self.brush_size / 2
        
        # 检查地块是否在笔刷范围内
        for i, plot in enumerate(self.land_plots):
            # 检查地块是否已经属于另一个省份
            is_in_other_province = False
            for p in self.provinces:
                if hasattr(p, 'plot_indices') and i in p.plot_indices:
                    is_in_other_province = True
                    break
                
            # 如果已经在当前省份或属于其他省份，跳过
            if hasattr(self.current_province, 'plot_indices') and (i in self.current_province.plot_indices or is_in_other_province):
                continue
            
            # 检查地块是否与笔刷相交
            # 简化：检查地块的外边界是否与笔刷圆相交
            for point in list(plot.exterior.coords):
                dist = np.sqrt((point[0] - x) ** 2 + (point[1] - y) ** 2)
                if dist <= radius:
                    # 将地块索引添加到当前省份
                    if not hasattr(self.current_province, 'plot_indices'):
                        self.current_province.plot_indices = []
                    self.current_province.plot_indices.append(i)
                    break

    def finalize_province_from_plots(self):
        """从选中的地块集合构建省份边界"""
        if not self.current_province or not hasattr(self.current_province, 'plot_indices') or not self.current_province.plot_indices:
            return False
        
        # 获取当前省份包含的所有地块
        province_plots = [self.land_plots[i] for i in self.current_province.plot_indices if i < len(self.land_plots)]
        if not province_plots:
            return False
        
        # 合并地块
        union_geom = unary_union(province_plots)
        
        if union_geom.is_empty:
            return False
        
        # 设置省份边界
        if union_geom.geom_type == 'Polygon':
            exterior_coords = list(union_geom.exterior.coords)
            self.current_province.points = exterior_coords
        elif union_geom.geom_type == 'MultiPolygon':
            # 如果是多个多边形，取最大的一个
            largest = max(union_geom.geoms, key=lambda p: p.area)
            exterior_coords = list(largest.exterior.coords)
            self.current_province.points = exterior_coords
        
        # 完成省份几何构建
        self.current_province.finalize_shape()
        self.current_province.boundary_polygon = union_geom
        
        return True

    def select_province(self, pos):
        """选择点击位置处的省份"""
        x, y = pos.x(), pos.y()
        
        for province in self.provinces:
            if province.contains_point(x, y):
                self.selected_province = province
                return True
        
        self.selected_province = None
        return False

    def get_new_province_color(self):
        """获取一个与已有省份不同的颜色"""
        # 收集已使用的颜色
        used_colors = set()
        for province in self.provinces:
            used_colors.add(province.color.name())
        
        # 从可用颜色中选择一个未被使用的颜色
        available = [c for c in self.available_colors if c.name() not in used_colors]
        
        if available:
            return np.random.choice(available)
        else:
            # 如果所有颜色都被使用，生成一个新随机颜色
            h = np.random.random()
            s = 0.5 + np.random.uniform(-0.1, 0.1)
            v = 0.8 + np.random.uniform(-0.1, 0.1)
            return QColor.fromHsvF(h, s, v)

    def show_province_toolbar(self):
        """显示省份编辑悬浮工具栏"""
        # 安全地清理现有工具栏
        if self.floating_toolbar == None:
            self.floating_toolbar = QWidget(self)
        
        if not self.current_province or self.current_tool != "province":
            return
        
        layout = QHBoxLayout(self.floating_toolbar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加完成按钮
        done_btn = QPushButton("✓ 完成")
        done_btn.setToolTip("完成当前省份编辑")
        done_btn.clicked.connect(self.finish_province_edit)
        layout.addWidget(done_btn)
        
        # 添加取消按钮
        cancel_btn = QPushButton("✗ 取消")
        cancel_btn.setToolTip("取消当前编辑")
        cancel_btn.clicked.connect(self.cancel_province_edit)
        layout.addWidget(cancel_btn)
        
        # 添加颜色选择按钮
        color_btn = QPushButton("调色")
        color_btn.setToolTip("更改当前省份颜色")
        color_btn.clicked.connect(self.change_province_color)
        layout.addWidget(color_btn)
        
        self.floating_toolbar.setLayout(layout)
        
        # 设置工具栏位置
        self.floating_toolbar.move(10, 10)
        self.floating_toolbar.show()

    def finish_province_edit(self):
        """完成当前省份编辑"""
        
        # 如果当前省份有地块，则添加到省份列表
        if hasattr(self.current_province, 'plot_indices') and self.current_province.plot_indices:
            self.finalize_province_from_plots()
            # 如果是新建的省份，添加到列表
            if self.current_province and self.current_province not in self.provinces:
                self.provinces.append(self.current_province)
            self.selected_province = self.current_province
            self.current_province = None
            self.add_to_history()
        
        # 安全地隐藏悬浮工具栏
        self.floating_toolbar.hide()
        self.floating_toolbar.deleteLater()
        self.floating_toolbar = None
        
        self.update()

    def cancel_province_edit(self):
        """取消当前省份编辑"""
        if self.current_province in self.provinces:
            # 如果是编辑现有省份，恢复原来的状态
            pass
        
        # 清除当前省份
        self.current_province = None
        
        # 安全地隐藏悬浮工具栏
        if hasattr(self, 'floating_toolbar') and self.floating_toolbar:
            try:
                if self.floating_toolbar.isVisible():
                    self.floating_toolbar.hide()
                self.floating_toolbar.deleteLater()
            except RuntimeError:
                # 捕获对象已删除的错误
                pass
            self.floating_toolbar = None
        
        self.update()

    def change_province_color(self):
        """更改当前省份颜色"""
        if not self.current_province:
            return
        
        # 打开颜色选择对话框
        color = QColorDialog.getColor(
            self.current_province.color, 
            self, 
            "选择省份颜色"
        )
        if color.isValid():
            self.current_province.color = color
            self.update()