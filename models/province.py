# models/province.py
import numpy as np
from PyQt5.QtGui import QColor , QPainterPath , QPen , QImage , QPainter
from PyQt5.QtCore import Qt , QRectF
import shapely.geometry as sg
import matplotlib.colors as mcolors
import cv2

class Province:
    """省份类，用于存储和管理地图上的省份"""
    
    def __init__(self, name="未命名省份", color=None):
        self.name = name
        self.color = color if color else QColor.fromHsv(np.random.randint(0, 360), 200, 200)
        self.points = []  # 省份的点集
        self.boundary = []  # 省份边界
        self.texture_path = None  # 纹理路径
        self.elevation = 0  # 高程
        self._cached_path = None
        self.neighbors = set()  # 相邻省份
        self.boundary_polygon = None
        self.plot_indices = []  # 用于存储构成省份的地块索引
    @property
    def path(self):
        """获取省份的路径，使用缓存提高性能"""
        if not self._cached_path:
            # 只有当有足够的点时才创建路径
            if len(self.points) >= 3:
                self._cached_path = QPainterPath()
                
                # 对于大型路径，可以先简化点集
                if len(self.points) > 500:
                    # 使用本地简化而不是依赖shapely库
                    simplified_points = self._simplify_points(self.points, tolerance=2.0)
                else:
                    simplified_points = self.points
                
                # 创建路径
                self._cached_path.moveTo(simplified_points[0][0], simplified_points[0][1])
                
                # 批量添加线段而不是一个个添加
                for point in simplified_points[1:]:
                    self._cached_path.lineTo(point[0], point[1])
                
                self._cached_path.closeSubpath()
        
        return self._cached_path
    
    def _simplify_points(self, points, tolerance=2.0):
        """简化点集，使用Douglas-Peucker算法的简化版实现"""
        if len(points) <= 2:
            return points
        
        # 查找最大距离点
        dmax = 0
        index = 0
        end = len(points) - 1
        
        for i in range(1, end):
            d = self._point_line_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d
        
        # 如果最大距离大于公差，则递归简化
        if dmax > tolerance:
            # 递归简化前后两部分
            rec_results1 = self._simplify_points(points[:index+1], tolerance)
            rec_results2 = self._simplify_points(points[index:], tolerance)
            
            # 合并结果，删除重复点
            return rec_results1[:-1] + rec_results2
        else:
            # 如果最大距离小于公差，则将所有中间点删除
            return [points[0], points[end]]
    
    def _point_line_distance(self, point, line_start, line_end):
        """计算点到线段的垂直距离"""
        if line_start == line_end:
            return ((point[0] - line_start[0]) ** 2 + (point[1] - line_start[1]) ** 2) ** 0.5
        
        n = abs((line_end[1] - line_start[1]) * point[0] - 
                (line_end[0] - line_start[0]) * point[1] + 
                line_end[0] * line_start[1] - 
                line_end[1] * line_start[0])
        
        d = ((line_end[1] - line_start[1]) ** 2 + 
             (line_end[0] - line_start[0]) ** 2) ** 0.5
        
        return n / d
        
    def add_point(self, x, y):
        self.points.append((x, y))
        self._cached_path = None  # 路径变化时清除缓存
        
    def calculate_boundary(self):
        """计算省份边界"""
        if len(self.points) < 3:
            return
        # 计算边界算法 (简化版)
        self.boundary = self.points.copy()

    def finalize_shape(self):
        """完成省份形状，进行点的简化和多边形构建"""
        if len(self.points) < 3:
            return False
            
        # 确保闭合
        if self.points[0] != self.points[-1]:
            self.points.append(self.points[0])
            
        # 使用Douglas-Peucker算法简化点集
        line = sg.LineString(self.points)
        simplified_line = line.simplify(2.0, preserve_topology=True)
        self.points = list(simplified_line.coords)
        
        # 创建多边形
        try:
            polygon = sg.Polygon(self.points)
            
            # 导入几何验证工具
            from models.geometry_utils import validate_and_fix_geometry
            
            # 验证并修复几何对象
            self.boundary_polygon = validate_and_fix_geometry(polygon)
            
            if self.boundary_polygon is None or not self.boundary_polygon.is_valid:
                print("无法创建有效的省份多边形")
                return False
                
            # 更新点集以匹配修复后的多边形
            if hasattr(self.boundary_polygon, 'exterior') and self.boundary_polygon.exterior is not None:
                self.points = list(self.boundary_polygon.exterior.coords)
        except Exception as e:
            print(f"创建省份多边形时出错: {e}")
            return False
        
        # 清除缓存
        self._cached_path = None
        
        return True

    def intersects(self, other_province):
        """检查当前省份是否与另一个省份相交"""
        if not self.boundary_polygon or not other_province.boundary_polygon:
            return False
        return self.boundary_polygon.intersects(other_province.boundary_polygon)
    
    def subtract(self, other_province):
        """从当前省份中减去另一个省份的区域"""
        if not self.boundary_polygon or not other_province.boundary_polygon:
            return False
            
        if not self.intersects(other_province):
            return False
            
        # 导入安全差集操作函数
        from models.geometry_utils import safe_difference
        
        # 执行安全差集操作
        difference = safe_difference(self.boundary_polygon, other_province.boundary_polygon)
        
        if difference is None:
            return False
        
        # 处理多边形集合的情况
        if difference.geom_type == 'MultiPolygon':
            # 选择最大的多边形作为新边界
            largest = max(difference.geoms, key=lambda p: p.area)
            self.boundary_polygon = largest
        else:
            self.boundary_polygon = difference
            
        # 更新简化点集
        if hasattr(self.boundary_polygon, 'exterior') and self.boundary_polygon.exterior is not None:
            self.points = list(self.boundary_polygon.exterior.coords)
            self._cached_path = None
            return True
        else:
            return False

    def get_bounding_rect(self):
        """获取省份的边界矩形"""
        if not self.boundary_polygon:
            return None
        minx, miny, maxx, maxy = self.boundary_polygon.bounds
        return QRectF(minx, miny, maxx - minx, maxy - miny)
        
    def contains_point(self, x, y):
        """检查省份是否包含给定点"""
        if not self.boundary_polygon:
            return False
        return self.boundary_polygon.contains(sg.Point(x, y))

    def calculate_centroid(self):
        """计算省份的质心"""
        if not self.boundary_polygon:
            return None
        centroid = self.boundary_polygon.centroid
        return (centroid.x, centroid.y)

    def generate_color_palette(self, count=20):
        """生成美观且互相区分的颜色调色板"""
        # 使用HSV色彩空间生成均匀分布的色调
        colors = []
        for i in range(count):
            h = i / count
            s = 0.5 + np.random.uniform(-0.1, 0.1)  # 适中的饱和度
            v = 0.8 + np.random.uniform(-0.1, 0.1)  # 较高的亮度
            colors.append(QColor.fromHsvF(h, s, v))
        return colors

    def get_distinct_color(self, province):
        """为省份获取一个与邻居不同的颜色"""
        # 如果还没有生成颜色调色板，先生成一个
        if not hasattr(self, 'available_colors') or not self.available_colors:
            self.available_colors = self.generate_color_palette(20)
        
        # 收集邻居的颜色
        neighbor_colors = set()
        for neighbor_idx in province.neighbors:
            # 找到对应的省份
            for i, p in enumerate(self.provinces):
                if i == neighbor_idx:  # 如果使用索引作为ID
                    neighbor_colors.add(p.color.name())  # 使用颜色名称作为唯一标识
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

    def find_province_neighbors(self):
        """查找并更新所有省份之间的邻接关系"""
        for i, province in enumerate(self.provinces):
            province.neighbors.clear()
            
            for j, other in enumerate(self.provinces):
                if province.id != other.id and province.intersects(other):
                    province.neighbors.add(other.id)
                    other.neighbors.add(province.id)

    def handle_province_overlaps_raster(self, new_province):
        """使用栅格化方法处理省份重叠"""
        # 创建掩码图像
        mask = np.zeros((self.height(), self.width()), dtype=np.uint8)
        
        # 绘制新省份到掩码
        points = np.array([new_province.points], dtype=np.int32)
        cv2.fillPoly(mask, points, 255)
        
        # 处理每个现有省份
        for province in list(self.provinces):
            if province == new_province:
                continue
            
            # 创建该省份的掩码
            province_mask = np.zeros_like(mask)
            if len(province.points) > 2:
                points = np.array([province.points], dtype=np.int32)
                cv2.fillPoly(province_mask, points, 255)
                
                # 检查重叠
                overlap = cv2.bitwise_and(mask, province_mask)
                if np.any(overlap):
                    # 移除重叠区域
                    new_mask = cv2.bitwise_xor(province_mask, overlap)
                    
                    # 如果剩余面积太小，完全移除该省份
                    if np.sum(new_mask) < 1000:  # 阈值可调整
                        self.provinces.remove(province)
                    else:
                        # 重建省份边界
                        contours, _ = cv2.findContours(new_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            # 找到最大轮廓
                            largest = max(contours, key=cv2.contourArea)
                            # 更新省份点集
                            province.points = [tuple(p[0]) for p in largest]
                            province._cached_path = None

    