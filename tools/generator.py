# tools/generators.py
import numpy as np
from PyQt5.QtGui import QColor

class TerrainGenerator:
    """地形生成器，用于生成各种地形特征"""
    
    @staticmethod
    def generate_heightmap(width, height, feature_size=10, octaves=6, persistence=0.5):
        """生成基于柏林噪声的高度图"""
        
        def noise(nx, ny, octaves=4):
            """简化的多重八度柏林噪声函数"""
            value = 0
            amplitude = 1.0
            frequency = 1.0
            max_value = 0
            
            for _ in range(octaves):
                value += amplitude * np.random.rand()
                max_value += amplitude
                amplitude *= persistence
                frequency *= 2
                
            return value / max_value
        
        # 初始化高度图
        heightmap = np.zeros((height, width), dtype=np.uint8)
        
        # 生成低频噪声作为基础
        for y in range(height):
            for x in range(width):
                nx = x / width - 0.5
                ny = y / height - 0.5
                
                # 距离中心的距离，用于创建岛屿形状
                d = 2 * np.sqrt(nx*nx + ny*ny)
                
                # 基于距离降低边缘高度
                value = (1 - d * 1.2) + noise(x / feature_size, y / feature_size, octaves)
                
                # 规范化并转换为0-255范围
                value = max(0, min(1, value))
                heightmap[y, x] = int(value * 255)
                
        return heightmap

    @staticmethod
    def generate_rivers(heightmap, count=5, min_length=10):
        """在高度图上生成河流"""
        height, width = heightmap.shape
        rivers = []
        
        for _ in range(count):
            # 从较高处开始河流
            # 在实际应用中，应该找到局部高点
            start_y = np.random.randint(height // 4, 3 * height // 4)
            start_x = np.random.randint(width // 4, 3 * width // 4)
            
            if heightmap[start_y, start_x] < 128:  # 跳过低海拔起点
                continue
                
            river = [(start_x, start_y)]
            current_x, current_y = start_x, start_y
            
            # 沿着下坡方向生成河流路径
            for _ in range(100):  # 最大步数限制
                # 查找周围8个方向
                neighbors = []
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                            
                        nx, ny = current_x + dx, current_y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            neighbors.append((nx, ny, heightmap[ny, nx]))
                
                if not neighbors:
                    break
                    
                # 选择高度最低的邻居
                next_x, next_y, _ = min(neighbors, key=lambda n: n[2])
                
                # 如果下一点不比当前点低，则结束河流
                if heightmap[next_y, next_x] >= heightmap[current_y, current_x]:
                    break
                    
                river.append((next_x, next_y))
                current_x, current_y = next_x, next_y
                
                # 如果到达边缘或水域，结束河流
                if current_x == 0 or current_x == width - 1 or current_y == 0 or current_y == height - 1 or heightmap[current_y, current_x] < 20:
                    break
            
            # 只保留足够长的河流
            if len(river) >= min_length:
                rivers.append(river)
                
        return rivers


class TextureGenerator:
    """纹理生成器，用于生成地形纹理"""
    
    @staticmethod
    def generate_texture_for_elevation(elevation):
        """根据海拔高度生成纹理"""
        if elevation < 20:
            # 水域
            r = np.random.randint(100, 130)
            g = np.random.randint(140, 180)
            b = np.random.randint(200, 230)
        elif elevation < 40:
            # 平原
            r = np.random.randint(140, 180)
            g = np.random.randint(180, 220)
            b = np.random.randint(100, 140)
        elif elevation < 70:
            # 丘陵
            r = np.random.randint(120, 160)
            g = np.random.randint(140, 180)
            b = np.random.randint(80, 120)
        elif elevation < 90:
            # 山地
            r = np.random.randint(100, 140)
            g = np.random.randint(110, 150)
            b = np.random.randint(70, 110)
        else:
            # 高山
            r = np.random.randint(200, 240)
            g = np.random.randint(200, 240)
            b = np.random.randint(200, 240)
            
        return QColor(r, g, b)