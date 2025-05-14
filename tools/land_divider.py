# tools/land_divider.py
import numpy as np
from scipy.spatial import Voronoi
import shapely.geometry as sg
from shapely.ops import unary_union, polygonize
import random
import cv2

class LandDivider:
    """大陆区域分割工具类，用于将大陆多边形分割成自然的小块"""
    
    def __init__(self):
        pass
        
    def perturb_grid_points(self, bounds, n_points_x, n_points_y, noise_factor=0.4):
        """生成带随机扰动的网格点，使生成的Voronoi图更自然"""
        minx, miny, maxx, maxy = bounds
        width = maxx - minx
        height = maxy - miny
        
        # 计算网格间距
        x_step = width / (n_points_x - 1) if n_points_x > 1 else width
        y_step = height / (n_points_y - 1) if n_points_y > 1 else height
        
        # 生成网格点并添加随机扰动
        points = []
        for i in range(n_points_x):
            for j in range(n_points_y):
                x = minx + i * x_step
                y = miny + j * y_step
                
                # 添加随机扰动，但保持在边界内
                dx = (random.random() - 0.5) * 2 * noise_factor * x_step
                dy = (random.random() - 0.5) * 2 * noise_factor * y_step
                
                x = max(minx, min(maxx, x + dx))
                y = max(miny, min(maxy, y + dy))
                
                points.append((x, y))
        
        # 在多边形内部再随机添加一些点，以增加变化
        for _ in range(int(n_points_x * n_points_y * 0.5)):
            x = minx + random.random() * width
            y = miny + random.random() * height
            points.append((x, y))
            
        return np.array(points)
    
    def generate_random_points_in_polygon(self, polygon, n_points):
        """在多边形内部生成随机点"""
        if not polygon or polygon.is_empty:
            return np.array([])
            
        minx, miny, maxx, maxy = polygon.bounds
        points = []
        
        while len(points) < n_points:
            # 生成随机点
            x = minx + random.random() * (maxx - minx)
            y = miny + random.random() * (maxy - miny)
            point = sg.Point(x, y)
            
            # 检查点是否在多边形内
            if polygon.contains(point):
                points.append((x, y))
                
        return np.array(points)
    
    def divide_land_with_voronoi(self, land_polygon, n_divisions=20):
        """使用Voronoi图将大陆多边形分割成自然的小块
        
        Args:
            land_polygon: shapely.geometry.Polygon 大陆多边形
            n_divisions: int 大致分割数量
        
        Returns:
            list of shapely.geometry.Polygon 分割后的多边形列表
        """
        if not land_polygon or land_polygon.is_empty:
            return []
            
        # 估算每个轴上应有的点数
        area = land_polygon.area
        width = land_polygon.bounds[2] - land_polygon.bounds[0]
        height = land_polygon.bounds[3] - land_polygon.bounds[1]
        aspect_ratio = width / height if height > 0 else 1
        
        # 计算合适的x,y方向点数，保持点分布均衡
        n_points_x = int(np.sqrt(n_divisions * aspect_ratio))
        n_points_y = int(n_divisions / n_points_x)
        
        # 确保至少有2x2的点
        n_points_x = max(2, n_points_x)
        n_points_y = max(2, n_points_y)
        
        # 方法1：使用网格点加扰动
        # points = self.perturb_grid_points(land_polygon.bounds, n_points_x, n_points_y)
        
        # 方法2：在多边形内随机生成点
        points = self.generate_random_points_in_polygon(land_polygon, n_divisions)
        
        if len(points) < 4:
            # 如果点太少，无法生成足够的Voronoi区域
            return [land_polygon]
            
        # 计算Voronoi图
        vor = Voronoi(points)
        
        # 将Voronoi区域转换为shapely多边形并裁剪到原多边形范围内
        regions_polygons = []
        
        for region_idx in vor.point_region:
            region = vor.regions[region_idx]
            if -1 in region or len(region) < 3:
                continue  # 跳过无界区域或点不足的区域
                
            # 构建区域多边形
            polygon_vertices = [vor.vertices[i] for i in region]
            if len(polygon_vertices) < 3:
                continue
                
            region_polygon = sg.Polygon(polygon_vertices)
            
            # 与原始多边形相交，确保区域在多边形内
            intersection = region_polygon.intersection(land_polygon)
            
            if not intersection.is_empty:
                if intersection.geom_type == 'Polygon':
                    if intersection.area > 1e-6:  # 忽略非常小的多边形
                        regions_polygons.append(intersection)
                elif intersection.geom_type == 'MultiPolygon':
                    for poly in intersection.geoms:
                        if poly.area > 1e-6:
                            regions_polygons.append(poly)
        
        # 如果提取的区域太少，回退到简单的网格分割
        if len(regions_polygons) < n_divisions / 4:
            print(f"Voronoi分割生成的区域太少({len(regions_polygons)})，回退到网格分割")
            return self._fallback_grid_division(land_polygon, n_divisions)
            
        return regions_polygons
    
    def _fallback_grid_division(self, land_polygon, n_divisions):
        """回退方法：使用简单的网格分割"""
        minx, miny, maxx, maxy = land_polygon.bounds
        width = maxx - minx
        height = maxy - miny
        
        # 计算网格大小
        aspect_ratio = width / height if height > 0 else 1
        n_cols = int(np.sqrt(n_divisions * aspect_ratio))
        n_rows = int(n_divisions / n_cols)
        
        n_cols = max(2, n_cols)
        n_rows = max(2, n_rows)
        
        cell_width = width / n_cols
        cell_height = height / n_rows
        
        # 生成网格单元并与原始多边形相交
        grid_cells = []
        
        for i in range(n_cols):
            for j in range(n_rows):
                # 创建略有随机扰动的网格单元
                cell_minx = minx + i * cell_width
                cell_miny = miny + j * cell_height
                cell_maxx = cell_minx + cell_width
                cell_maxy = cell_miny + cell_height
                
                # 添加一些随机扰动
                distort_factor = 0.15  # 扰动因子
                dx1 = (random.random() - 0.5) * 2 * distort_factor * cell_width
                dy1 = (random.random() - 0.5) * 2 * distort_factor * cell_height
                dx2 = (random.random() - 0.5) * 2 * distort_factor * cell_width
                dy2 = (random.random() - 0.5) * 2 * distort_factor * cell_height
                dx3 = (random.random() - 0.5) * 2 * distort_factor * cell_width
                dy3 = (random.random() - 0.5) * 2 * distort_factor * cell_height
                dx4 = (random.random() - 0.5) * 2 * distort_factor * cell_width
                dy4 = (random.random() - 0.5) * 2 * distort_factor * cell_height
                
                # 创建单元格四个角的坐标
                p1 = (cell_minx + dx1, cell_miny + dy1)
                p2 = (cell_maxx + dx2, cell_miny + dy2)
                p3 = (cell_maxx + dx3, cell_maxy + dy3)
                p4 = (cell_minx + dx4, cell_maxy + dy4)
                
                cell = sg.Polygon([p1, p2, p3, p4])
                
                # 与原始多边形相交
                intersection = cell.intersection(land_polygon)
                
                if not intersection.is_empty:
                    if intersection.geom_type == 'Polygon':
                        if intersection.area > 1e-6:
                            grid_cells.append(intersection)
                    elif intersection.geom_type == 'MultiPolygon':
                        for poly in intersection.geoms:
                            if poly.area > 1e-6:
                                grid_cells.append(poly)
        
        return grid_cells

    def raster_based_division(self, land_polygon, n_divisions=20):
        """使用栅格化结合分水岭算法实现更自然的区域分割"""
        if not land_polygon or land_polygon.is_empty:
            return []
            
        # 栅格化参数
        width, height = 800, 600
        minx, miny, maxx, maxy = land_polygon.bounds
        scale_x = width / (maxx - minx)
        scale_y = height / (maxy - miny)
        
        # 创建掩码图像
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # 栅格化多边形
        points = []
        if land_polygon.geom_type == 'Polygon':
            exterior_coords = list(land_polygon.exterior.coords)
            points = [[(int((p[0] - minx) * scale_x), int((p[1] - miny) * scale_y)) 
                     for p in exterior_coords]]
            cv2.fillPoly(mask, np.array(points, dtype=np.int32), 255)
        
        # 确保掩码非空
        if np.sum(mask) == 0:
            return [land_polygon]
            
        # 在掩码上随机放置标记点作为分水岭种子
        markers = np.zeros_like(mask, dtype=np.int32)
        n_markers = min(n_divisions, 100)  # 限制最大种子数
        
        # 寻找可能的种子位置
        y_indices, x_indices = np.where(mask > 0)
        if len(y_indices) < n_markers:
            return [land_polygon]
            
        # 随机选择种子位置
        indices = np.random.choice(len(y_indices), size=n_markers, replace=False)
        for i, idx in enumerate(indices):
            markers[y_indices[idx], x_indices[idx]] = i + 1
            
        # 应用距离变换和分水岭算法
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        dist = cv2.normalize(dist, None, 0, 1.0, cv2.NORM_MINMAX)
        dist = (255 * dist).astype(np.uint8)
        
        # 反转距离变换，使边界处为高点
        dist = 255 - dist
        
        # 应用分水岭算法
        watershed_result = cv2.watershed(cv2.cvtColor(dist, cv2.COLOR_GRAY2BGR), markers)
        
        # 从分水岭结果创建多边形
        regions_polygons = []
        for marker_id in range(1, n_markers + 1):
            # 提取每个区域
            region_mask = np.zeros_like(mask, dtype=np.uint8)
            region_mask[watershed_result == marker_id] = 255
            
            # 找到区域轮廓
            contours, _ = cv2.findContours(region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if len(contour) >= 3:  # 至少需要3个点形成多边形
                    # 转换回原始坐标系
                    points = []
                    for point in contour:
                        x = point[0][0] / scale_x + minx
                        y = point[0][1] / scale_y + miny
                        points.append((x, y))
                    
                    if len(points) >= 3:
                        try:
                            poly = sg.Polygon(points)
                            if poly.is_valid and poly.area > 1e-6:
                                # 与原始多边形相交以确保边界准确
                                intersection = poly.intersection(land_polygon)
                                if not intersection.is_empty:
                                    if intersection.geom_type == 'Polygon':
                                        regions_polygons.append(intersection)
                                    elif intersection.geom_type == 'MultiPolygon':
                                        regions_polygons.extend(list(intersection.geoms))
                        except Exception:
                            continue
        
        # 如果区域太少，回退到Voronoi方法
        if len(regions_polygons) < n_divisions / 4:
            return self.divide_land_with_voronoi(land_polygon, n_divisions)
            
        return regions_polygons 