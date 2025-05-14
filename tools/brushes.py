# tools/brushes.py
import numpy as np
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QColor
class Brush:
    """笔刷基类，所有具体笔刷工具的抽象基类"""
    
    def __init__(self, size=20, strength=10):
        """初始化笔刷
        
        Args:
            size: 笔刷大小（直径）
            strength: 笔刷强度，影响效果的程度
        """
        self.size = size
        self.strength = strength
    
    def apply(self, map_controller, position):
        """应用笔刷效果（抽象方法，由子类实现）
        
        Args:
            map_controller: 地图控制器实例
            position: 应用位置（QPoint）
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        pass


class ProvinceBrush(Brush):
    """省份笔刷，用于绘制和编辑省份边界"""
    
    def __init__(self, size=20, strength=10, color=None):
        """初始化省份笔刷
        
        Args:
            size: 笔刷大小
            strength: 笔刷强度
            color: 省份颜色
        """
        super().__init__(size, strength)
        self.color = color
        self.last_position = None
        
        # 创建Qt笔刷和画笔
        from PyQt5.QtGui import QBrush, QColor, QPen
        from PyQt5.QtCore import Qt
        
        # 使用半透明颜色
        brush_color = QColor(200, 200, 200, 150) if color is None else QColor(color)
        brush_color.setAlpha(150)
        self.qt_brush = QBrush(brush_color)
        self.qt_pen = QPen(Qt.NoPen)
    
    def apply(self, map_controller, position):
        """应用省份笔刷效果，向当前省份添加点
        
        Args:
            map_controller: 地图控制器实例
            position: 应用位置（QPoint）
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        from PyQt5.QtGui import QPainter, QImage, QPainterPath, QColor
        from PyQt5.QtCore import QPointF, Qt
        import numpy as np
        
        x, y = position.x(), position.y()
        size = self.size
        radius = size // 2
        
        # 如果当前没有活动的省份，不执行任何操作
        if not hasattr(map_controller, 'current_province') or map_controller.current_province is None:
            return None
        
        # 计算绘制区域
        x_min = max(0, x - radius)
        y_min = max(0, y - radius)
        width = radius * 2
        height = radius * 2
        
        # 创建临时图像
        temp_image = QImage(width, height, QImage.Format_ARGB32)
        temp_image.fill(Qt.transparent)
        
        # 创建绘制器
        painter = QPainter(temp_image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.qt_pen)
        painter.setBrush(self.qt_brush)
        
        # 绘制圆形
        ellipse_center = QPointF(radius, radius)
        painter.drawEllipse(ellipse_center, radius, radius)
        painter.end()
        
        # 收集笔刷范围内的点
        points = []
        for i in range(width):
            for j in range(height):
                # 检查像素是否非透明
                if temp_image.pixelColor(i, j).alpha() > 0:
                    # 转换为地图坐标
                    map_x = x_min + i
                    map_y = y_min + j
                    points.append((map_x, map_y))
        
        # 如果当前有活动的省份，将这些点添加到省份中
        for point in points:
            map_controller.current_province.add_point(*point)
        
        # 如果插值绘制开启，且有上一个位置
        if self.last_position is not None:
            last_x, last_y = self.last_position.x(), self.last_position.y()
            dist = np.sqrt((x - last_x)**2 + (y - last_y)**2)
            
            # 如果距离较大，进行插值
            if dist > size / 3:
                # 计算需要插值的点数
                steps = max(2, int(dist / (size / 6)))
                
                # 执行插值
                for step in range(1, steps):
                    t = step / steps
                    ix = int(last_x + (x - last_x) * t)
                    iy = int(last_y + (y - last_y) * t)
                    
                    # 在插值点创建小号笔刷
                    interp_size = max(int(size * 0.8), 10)  # 略小的笔刷
                    interp_radius = interp_size // 2
                    
                    # 计算区域
                    ix_min = max(0, ix - interp_radius)
                    iy_min = max(0, iy - interp_radius)
                    
                    # 创建临时插值图像
                    interp_image = QImage(interp_size, interp_size, QImage.Format_ARGB32)
                    interp_image.fill(Qt.transparent)
                    
                    # 创建绘制器
                    interp_painter = QPainter(interp_image)
                    interp_painter.setRenderHint(QPainter.Antialiasing, True)
                    interp_painter.setPen(self.qt_pen)
                    interp_painter.setBrush(self.qt_brush)
                    
                    # 绘制圆形
                    interp_center = QPointF(interp_radius, interp_radius)
                    interp_painter.drawEllipse(interp_center, interp_radius, interp_radius)
                    interp_painter.end()
                    
                    # 收集点
                    for i in range(interp_size):
                        for j in range(interp_size):
                            if interp_image.pixelColor(i, j).alpha() > 0:
                                map_x = ix_min + i
                                map_y = iy_min + j
                                map_controller.current_province.add_point(map_x, map_y)
        
        # 更新最后位置
        self.last_position = position
        
        # 发送地图已更改信号
        map_controller.map_changed.emit()
        
        # 返回修改区域
        return (x_min, y_min, width, height)


class HeightBrush(Brush):
    """高程笔刷，用于修改地形高度、创建山脉和水域"""
    
    def __init__(self, size=20, strength=10):
        """初始化高程笔刷
        
        Args:
            size: 笔刷大小
            strength: 笔刷强度，正值增加高度，负值降低高度
        """
        super().__init__(size, strength)
        self.last_position = None  # 用于线性插值
        
        # 创建Qt渐变笔刷
        from PyQt5.QtGui import QRadialGradient, QBrush, QColor, QPen
        from PyQt5.QtCore import Qt, QPointF
        
        # 创建径向渐变，从中心到边缘强度递减
        self.gradient = QRadialGradient()
        # 设置渐变颜色
        self.gradient.setColorAt(0, QColor(255, 255, 255, 255))  # 中心最强
        self.gradient.setColorAt(1, QColor(255, 255, 255, 0))    # 边缘最弱
        
        self.qt_brush = QBrush(self.gradient)
        self.qt_pen = QPen(Qt.NoPen)  # 无边框
    
    def apply(self, map_controller, position):
        """应用高程笔刷效果，修改地形高度
        
        Args:
            map_controller: 地图控制器实例
            position: 应用位置（QPoint）
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        from PyQt5.QtGui import QPainter, QImage, QRadialGradient
        from PyQt5.QtCore import QPointF, QRect, Qt
        import numpy as np
        
        x, y = position.x(), position.y()
        size = self.size
        radius = size // 2
        strength = self.strength
        
        # 获取高程图
        default_map = map_controller.default_map
        if default_map is None or not hasattr(default_map, 'data'):
            return None
        
        height, width = default_map.data.shape
        
        # 计算笔刷范围
        x_min = max(0, x - radius)
        y_min = max(0, y - radius)
        x_max = min(width, x + radius + 1)
        y_max = min(height, y + radius + 1)
        rect_width = x_max - x_min
        rect_height = y_max - y_min
        
        # 如果范围无效，直接返回
        if rect_width <= 0 or rect_height <= 0:
            return None
        
        # 如果有上一个位置，执行插值
        if self.last_position is not None:
            last_x, last_y = self.last_position.x(), self.last_position.y()
            dist = np.sqrt((x - last_x)**2 + (y - last_y)**2)
            
            # 如果距离较大，添加中间点
            if dist > size / 4:
                num_points = max(2, int(dist / (size / 8)))
                for i in range(1, num_points):
                    t = i / num_points
                    ix = int(last_x + (x - last_x) * t)
                    iy = int(last_y + (y - last_y) * t)
                    # 创建并应用单点笔刷
                    self._apply_at_point(map_controller, ix, iy, strength)
        
        # 应用当前点的笔刷
        modified_rect = self._apply_at_point(map_controller, x, y, strength)
        
        # 记录当前位置
        self.last_position = position
        
        # 发送地图已更改信号
        map_controller.map_changed.emit()
        
        return (x_min, y_min, rect_width, rect_height)
    
    def _apply_at_point(self, map_controller, x, y, strength):
        """在特定点应用高程修改
        
        Args:
            map_controller: 地图控制器实例
            x, y: 应用点坐标
            strength: 应用强度
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        from PyQt5.QtGui import QPainter, QImage, QRadialGradient, QColor
        from PyQt5.QtCore import QPointF, Qt
        import numpy as np
        
        size = self.size
        radius = size // 2
        default_map = map_controller.default_map
        height, width = default_map.data.shape
        
        # 计算笔刷范围
        x_min = max(0, x - radius)
        y_min = max(0, y - radius)
        x_max = min(width, x + radius + 1)
        y_max = min(height, y + radius + 1)
        rect_width = x_max - x_min
        rect_height = y_max - y_min
        
        # 创建临时图像
        temp_image = QImage(rect_width, rect_height, QImage.Format_ARGB32)
        temp_image.fill(Qt.transparent)
        
        # 设置渐变中心点
        self.gradient.setCenter(QPointF(x - x_min, y - y_min))
        self.gradient.setRadius(radius)
        self.gradient.setFocalPoint(QPointF(x - x_min, y - y_min))
        
        # 创建绘制器并绘制
        painter = QPainter(temp_image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.qt_pen)
        painter.setBrush(self.qt_brush)
        
        # 绘制圆形
        painter.drawEllipse(QPointF(x - x_min, y - y_min), radius, radius)
        painter.end()
        
        # 应用高程变化
        for py in range(rect_height):
            for px in range(rect_width):
                alpha = temp_image.pixelColor(px, py).alpha()
                if alpha > 0:
                    map_x = x_min + px
                    map_y = y_min + py
                    
                    # 根据透明度计算强度
                    factor = alpha / 255.0
                    value = int(strength * factor)
                    
                    # 更新高度值
                    current = default_map.data[map_y, map_x]
                    new_value = max(0, min(255, current + value))
                    default_map.data[map_y, map_x] = new_value
        
        return (x_min, y_min, rect_width, rect_height)


class ContinentBrush:
    """大陆笔刷，用于绘制大陆轮廓，使用Qt绘制实现连续平滑的轮廓线
    
    该笔刷会同时影响地图的大陆掩码和高程数据，用于快速创建基本地形。
    添加了线性插值以确保笔画连续性，即使鼠标移动较快。
    """
    def __init__(self, size, strength):
        """初始化大陆笔刷
        
        Args:
            size: 笔刷大小（直径）
            strength: 笔刷强度，影响大陆高度
        """
        self.size = size  # 笔刷半径
        self.strength = strength  # 笔刷强度
        self.last_position = None  # 记录上一次位置，用于线性插值
        # 创建Qt笔刷对象
        from PyQt5.QtGui import QBrush, QColor, QPen, QPainterPath
        from PyQt5.QtCore import Qt
        self.qt_brush = QBrush(QColor(255, 255, 255))
        self.qt_pen = QPen(Qt.NoPen)  # 无边框
        
    def apply(self, map_controller, position):
        """应用大陆笔刷效果，绘制大陆并设置高程数据
        
        使用Qt绘制实现平滑连续的笔画，并通过线性插值确保即使鼠标移动较快时绘制也不会中断。
        
        Args:
            map_controller: 地图控制器实例
            position: 应用位置（QPoint）
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        from PyQt5.QtGui import QPainter, QImage, QColor, QPainterPath
        from PyQt5.QtCore import QPoint, QRect, Qt
        import numpy as np
        
        x, y = position.x(), position.y()
        size = self.size
        radius = size // 2
        
        # 检查并初始化continent_mask（如果不存在）
        if not hasattr(map_controller, 'continent_mask') or map_controller.continent_mask is None:
            # 根据default_map的大小创建大陆掩码
            height, width = map_controller.default_map.data.shape
            map_controller.continent_mask = np.zeros((height, width), dtype=bool)
        
        height, width = map_controller.continent_mask.shape
        
        # 计算笔刷绘制范围
        x_min = max(0, x - radius)
        y_min = max(0, y - radius)
        x_max = min(width, x + radius + 1)
        y_max = min(height, y + radius + 1)
        rect_width = x_max - x_min
        rect_height = y_max - y_min
        
        # 如果范围无效，直接返回
        if rect_width <= 0 or rect_height <= 0:
            return (0, 0, 0, 0)
            
        # 如果有上一个位置，执行插值以确保连续绘制
        if self.last_position is not None:
            last_x, last_y = self.last_position.x(), self.last_position.y()
            dist = np.sqrt((x - last_x)**2 + (y - last_y)**2)
            
            # 如果距离较大，进行插值
            if dist > size / 4:
                # 创建路径，用于连接点
                path = QPainterPath()
                path.moveTo(last_x, last_y)
                path.lineTo(x, y)
                
                # 计算包含路径的矩形区域
                path_rect = path.boundingRect()
                path_x = max(0, int(path_rect.x() - radius))
                path_y = max(0, int(path_rect.y() - radius))
                path_width = min(width - path_x, int(path_rect.width() + radius * 2))
                path_height = min(height - path_y, int(path_rect.height() + radius * 2))
                
                # 只有在有效范围内才进行绘制
                if path_width > 0 and path_height > 0:
                    # 创建临时图像进行绘制
                    temp_image = QImage(path_width, path_height, QImage.Format_ARGB32)
                    temp_image.fill(Qt.transparent)
                    
                    painter = QPainter(temp_image)
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    
                    # 创建笔刷路径
                    painter.setPen(self.qt_pen)
                    painter.setBrush(self.qt_brush)
                    
                    # 在路径上绘制圆形笔刷
                    for i in range(1, 11):  # 将路径分成10段
                        t = i / 10.0
                        ix = int(last_x + (x - last_x) * t)
                        iy = int(last_y + (y - last_y) * t)
                        # 绘制偏移后的圆形
                        ellipse_x = ix - path_x - radius
                        ellipse_y = iy - path_y - radius
                        painter.drawEllipse(ellipse_x, ellipse_y, size, size)
                    
                    painter.end()
                    
                    # 将临时图像的内容复制到continent_mask
                    for py in range(path_height):
                        for px in range(path_width):
                            # 检查像素是否为白色（非透明部分）
                            if temp_image.pixelColor(px, py).alpha() > 0:
                                map_x = path_x + px
                                map_y = path_y + py
                                if 0 <= map_x < width and 0 <= map_y < height:
                                    map_controller.continent_mask[map_y, map_x] = True
                                    map_controller.default_map.data[map_y, map_x] = 255
        
        # 创建当前位置的临时图像
        temp_image = QImage(rect_width, rect_height, QImage.Format_ARGB32)
        temp_image.fill(Qt.transparent)
        
        painter = QPainter(temp_image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # 设置笔刷
        painter.setPen(self.qt_pen)
        painter.setBrush(self.qt_brush)
        
        # 绘制圆形
        ellipse_x = x - x_min - radius
        ellipse_y = y - y_min - radius
        painter.drawEllipse(ellipse_x, ellipse_y, size, size)
        
        painter.end()
        
        # 将临时图像转换为掩码和高度数据
        for py in range(rect_height):
            for px in range(rect_width):
                if temp_image.pixelColor(px, py).alpha() > 0:
                    map_x = x_min + px
                    map_y = y_min + py
                    map_controller.continent_mask[map_y, map_x] = True
                    map_controller.default_map.data[map_y, map_x] = 255
        
        # 记录当前位置，供下次使用
        self.last_position = position
        
        # 发送地图更新信号
        map_controller.map_changed.emit()
        
        # 返回修改区域
        return (x_min, y_min, rect_width, rect_height)


class RiverBrush(Brush):
    """河流笔刷，用于绘制河流路径"""
    
    def __init__(self, size=20, strength=10):
        """初始化河流笔刷
        
        Args:
            size: 笔刷大小（河流宽度）
            strength: 笔刷强度（影响河流的曲折度）
        """
        super().__init__(size, strength)
        # 创建Qt笔刷和画笔
        from PyQt5.QtGui import QPen, QBrush, QColor
        from PyQt5.QtCore import Qt
        
        # 河流使用蓝色笔
        self.qt_pen = QPen(QColor(70, 130, 180), 3)  # 蓝色
        self.qt_pen.setCapStyle(Qt.RoundCap)
        self.qt_pen.setJoinStyle(Qt.RoundJoin)
        self.qt_brush = QBrush(Qt.NoBrush)  # 无填充
    
    def apply(self, map_controller, position):
        """应用河流笔刷效果，绘制河流
        
        Args:
            map_controller: 地图控制器实例
            position: 应用位置（QPoint）
            
        Returns:
            修改区域的元组 (x, y, width, height) 或 None
        """
        from PyQt5.QtGui import QPainter, QImage, QPainterPath
        from PyQt5.QtCore import QPoint, QRect, Qt
        import numpy as np
        
        x, y = position.x(), position.y()
        
        # 确保rivers列表存在
        if not hasattr(map_controller, 'rivers') or map_controller.rivers is None:
            map_controller.rivers = []
        
        # 如果当前没有活动的河流，创建一个新河流
        if not map_controller.rivers or not hasattr(map_controller, 'is_drawing') or map_controller.is_drawing == False:
            map_controller.rivers.append([(x, y)])
            map_controller.is_drawing = True
            # 创建新河流时无需绘制
            map_controller.map_changed.emit()
            return None
        
        # 获取当前河流
        current_river = map_controller.rivers[-1]
        
        # 添加一些随机扰动，使河流更自然
        noise_x = x
        noise_y = y
        if self.strength > 5:
            noise_x += np.random.randint(-2, 3)
            noise_y += np.random.randint(-2, 3)
        
        # 如果河流中已有点，获取最后一个点
        if len(current_river) > 0:
            last_x, last_y = current_river[-1]
            
            # 计算河流段的包围盒
            min_x = min(last_x, noise_x)
            min_y = min(last_y, noise_y)
            width = abs(noise_x - last_x) + 6  # 添加边距
            height = abs(noise_y - last_y) + 6  # 添加边距
            
            # 创建临时图像展示修改区域
            temp_image = QImage(width, height, QImage.Format_ARGB32)
            temp_image.fill(Qt.transparent)
            
            # 创建路径
            path = QPainterPath()
            path.moveTo(last_x - min_x + 3, last_y - min_y + 3)  # 加3是边距偏移
            path.lineTo(noise_x - min_x + 3, noise_y - min_y + 3)
            
            # 绘制路径
            painter = QPainter(temp_image)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(self.qt_pen)
            painter.setBrush(self.qt_brush)
            painter.drawPath(path)
            painter.end()
        
        # 将新点添加到当前河流
        current_river.append((noise_x, noise_y))
        
        # 发送地图已更改信号
        map_controller.map_changed.emit()
        
        # 返回修改区域，如果是第一个点则返回None
        if len(current_river) <= 1:
            return None
        else:
            last_x, last_y = current_river[-2]
            return (min(last_x, noise_x) - 3, min(last_y, noise_y) - 3, abs(noise_x - last_x) + 6, abs(noise_y - last_y) + 6)