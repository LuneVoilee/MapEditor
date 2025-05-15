# models/heightmap.py
import numpy as np
from scipy import ndimage

class DefaultMap:
    """底图类，用于绘制地图"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.data = np.zeros((height, width), dtype=np.float32)
        
    def apply_brush(self, x, y, size, strength, add=True):
        """应用笔刷修改高程
        
        Args:
            x: 笔刷中心X坐标
            y: 笔刷中心Y坐标
            size: 笔刷大小（直径）
            strength: 笔刷强度
            add: 是否添加高程（True）或降低高程（False）
        """
        # 计算笔刷影响区域
        radius = size // 2
        x1 = max(0, x - radius)
        y1 = max(0, y - radius)
        x2 = min(self.width, x + radius)
        y2 = min(self.height, y + radius)
        
        # 在影响区域应用高程变化
        for py in range(y1, y2):
            for px in range(x1, x2):
                # 计算到中心的距离
                dist = np.sqrt((px - x) ** 2 + (py - y) ** 2)
                
                # 如果在笔刷范围内
                if dist <= radius:
                    # 根据距离计算影响强度
                    intensity = (1 - dist / radius) * strength
                    
                    # 应用高程变化
                    if add:
                        self.data[py, px] += intensity
                    else:
                        self.data[py, px] = max(0, self.data[py, px] - intensity)
    
    def generate_random_terrain(self, seed=None, noise_scale=100.0, smoothing=2, land_ratio=0.6):
        """生成随机地形
        
        Args:
            seed: 随机种子
            noise_scale: 噪声缩放
            smoothing: 平滑程度
            land_ratio: 陆地占比
        """
        if seed is not None:
            np.random.seed(seed)
        
        # 生成随机噪声
        noise = np.random.rand(self.height, self.width)
        
        # 应用高斯滤波平滑噪声
        smoothed = ndimage.gaussian_filter(noise, sigma=smoothing)
        
        # 缩放噪声
        self.data = smoothed * noise_scale
        
        # 调整高程，使一定比例的区域成为陆地
        threshold = np.percentile(self.data, (1 - land_ratio) * 100)
        self.data[self.data < threshold] = 0
        
        # 归一化陆地高程到[1, 100]范围
        if np.max(self.data) > 0:
            land_mask = self.data > 0
            self.data[land_mask] = 1 + 99 * (self.data[land_mask] - threshold) / (np.max(self.data) - threshold)
        
        return self

    def add_hill(self, x, y, radius, height):
        """添加山丘"""
        x, y = int(x), int(y)
        for i in range(max(0, x - radius), min(self.width, x + radius + 1)):
            for j in range(max(0, y - radius), min(self.height, y + radius + 1)):
                dist = np.sqrt((i - x) ** 2 + (j - y) ** 2)
                if dist <= radius:
                    h = height * (1 - dist / radius)
                    self.data[j, i] = min(255, max(0, int(self.data[j, i] + h)))
    
    def add_range(self, x1, y1, x2, y2, width, height):
        """添加山脉"""
        # 简单实现山脉的添加
        points = self._line(x1, y1, x2, y2)
        for x, y in points:
            self.add_hill(x, y, width, height)
    
    def _line(self, x1, y1, x2, y2):
        """使用Bresenham算法生成一条线上的点"""
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
                
        return points