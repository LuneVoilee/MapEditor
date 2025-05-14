# tools/brushes.py
import numpy as np
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QColor
class Brush:
    """笔刷基类"""
    
    def __init__(self, size=20, strength=10):
        self.size = size
        self.strength = strength
    
    def apply(self, map_canvas, position):
        """应用笔刷效果"""
        pass


class ProvinceBrush(Brush):
    """省份笔刷，用于绘制和编辑省份边界"""
    
    def __init__(self, size=20, strength=10, color=None):
        super().__init__(size, strength)
        self.color = color
    
    def apply(self, map_canvas, position):
        """应用省份笔刷效果"""
        x, y = position.x(), position.y()
        radius = self.size // 2
        
        # 找出笔刷范围内的点
        points = []
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                if (i - x) ** 2 + (j - y) ** 2 <= radius ** 2:
                    points.append((i, j))
        
        # 如果当前有活动的省份，将这些点添加到省份中
        if map_canvas.current_province:
            for point in points:
                map_canvas.current_province.add_point(*point)


class HeightBrush(Brush):
    """高程笔刷，用于修改地形高度"""
    
    def apply(self, map_canvas, position):
        """应用高程笔刷效果"""
        x, y = position.x(), position.y()
        radius = self.size // 2
        
        # 使用高斯分布增加细节
        for i in range(max(0, x - radius), min(map_canvas.heightmap.width, x + radius + 1)):
            for j in range(max(0, y - radius), min(map_canvas.heightmap.height, y + radius + 1)):
                dist = np.sqrt((i - x) ** 2 + (j - y) ** 2)
                if dist <= radius:
                    # 计算根据距离中心的距离而变化的强度
                    factor = 1 - (dist / radius) ** 2
                    value = int(self.strength * factor)
                    
                    # 更新高度值
                    current = map_canvas.heightmap.data[j, i]
                    new_value = max(0, min(255, current + value))
                    map_canvas.heightmap.data[j, i] = new_value


class ContinentBrush:
    def __init__(self, size, strength):
        self.size = size  # 笔刷半径
        self.strength = strength  # 笔刷强度
        # 预先计算笔刷形状掩码，避免每次应用时重复计算
        self._create_brush_mask()
        
    def _create_brush_mask(self):
        """预计算笔刷掩码以提高性能"""
        size = self.size
        # 创建足够大的矩阵以包含整个圆形笔刷
        y, x = np.ogrid[-size:size+1, -size:size+1]
        # 计算到中心的距离平方
        dist_sq = x*x + y*y
        # 创建圆形掩码 (True表示在圆内)
        self.mask = dist_sq <= size*size
        
    def apply(self, map_canvas, position):
        """高效应用大陆笔刷效果"""
        x, y = position.x(), position.y()
        size = self.size
        height, width = map_canvas.continent_mask.shape
        
        # 计算掩码在图上的位置
        y_min = max(0, y - size)
        y_max = min(height, y + size + 1)
        x_min = max(0, x - size)
        x_max = min(width, x + size + 1)
        
        # 计算掩码的对应切片
        mask_y_min = max(0, -(y - size))
        mask_y_max = mask_y_min + (y_max - y_min)
        mask_x_min = max(0, -(x - size))
        mask_x_max = mask_x_min + (x_max - x_min)
        
        # 应用笔刷掩码到大陆掩码
        mask_slice = self.mask[mask_y_min:mask_y_max, mask_x_min:mask_x_max]
        map_canvas.continent_mask[y_min:y_max, x_min:x_max] |= mask_slice
        
        # 一次性批量更新高程数据
        map_canvas.default_map.data[y_min:y_max, x_min:x_max][mask_slice] = 255
        
        # 返回修改的矩形区域，供调用者优化更新
        return (x_min, y_min, x_max - x_min, y_max - y_min)


class RiverBrush(Brush):
    """河流笔刷，用于绘制河流"""
    
    def apply(self, map_canvas, position):
        """应用河流笔刷效果"""
        x, y = position.x(), position.y()
        
        # 如果当前没有活动的河流，创建一个新河流
        if not map_canvas.rivers or map_canvas.is_drawing == False:
            map_canvas.rivers.append([(x, y)])
            map_canvas.is_drawing = True
        else:
            # 将新点添加到当前河流
            current_river = map_canvas.rivers[-1]
            
            # 添加一些随机扰动使河流看起来更自然
            noise_x = x + np.random.randint(-2, 3) if self.strength > 5 else x
            noise_y = y + np.random.randint(-2, 3) if self.strength > 5 else y
            
            current_river.append((noise_x, noise_y))
            
            # 根据高程图使河流自然流向低处
            # 这部分在实际应用中需要更复杂的算法