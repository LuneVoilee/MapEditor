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

    def generate_land_plots(self, heightmap, plot_cell_size=50):
        """基于高程图生成陆地地块
        
        Args:
            heightmap: HeightMap对象，包含高程数据
            plot_cell_size: 地块大小（像素）
            
        Returns:
            list: 地块几何对象列表
        """
        if heightmap is None or not hasattr(heightmap, 'data'):
            print("错误: 无法生成地块，未设置高程图")
            return []
        
        try:
            # 通过高程阈值过滤出陆地部分
            land_mask = heightmap.data > 0
            
            # 生成地块
            plot_geometries = self.generate_plots_from_mask(land_mask, plot_cell_size)
            
            return plot_geometries
            
        except Exception as e:
            print(f"生成地块时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def generate_plots_from_mask(self, land_mask, plot_cell_size=50):
        """从二值掩码生成地块
        
        Args:
            land_mask: 二值掩码，True表示陆地
            plot_cell_size: 地块大小
            
        Returns:
            list: 地块几何对象列表
        """
        import shapely.geometry as sg
        from shapely.ops import unary_union
        import cv2
        
        # 转换为OpenCV可处理的格式
        land_mask_cv = land_mask.astype(np.uint8) * 255
        
        if np.sum(land_mask_cv) == 0:  # 如果没有陆地
            return []
        
        # 使用OpenCV找到陆地区域
        contours, _ = cv2.findContours(land_mask_cv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # 创建陆地多边形
        land_polygons = []
        for contour in contours:
            if len(contour) >= 3:
                # 将OpenCV轮廓转换为Shapely多边形
                points = [(point[0][0], point[0][1]) for point in contour]
                if len(points) >= 3:
                    polygon = sg.Polygon(points)
                    if polygon.is_valid:
                        land_polygons.append(polygon)
        
        # 如果没有有效的陆地多边形，返回空列表
        if not land_polygons:
            return []
        
        # 合并所有陆地多边形
        land_geometry = unary_union(land_polygons)
        if not land_geometry.is_valid:
            land_geometry = land_geometry.buffer(0)  # 尝试修复几何无效性
        
        # 将区域划分为网格
        minx, miny, maxx, maxy = land_geometry.bounds
        
        grid_polygons = []
        
        # 生成网格多边形
        for x in range(int(minx), int(maxx), plot_cell_size):
            for y in range(int(miny), int(maxy), plot_cell_size):
                # 创建一个矩形单元格
                cell = sg.box(x, y, x + plot_cell_size, y + plot_cell_size)
                # 与陆地相交
                intersection = cell.intersection(land_geometry)
                if not intersection.is_empty and intersection.area > 0:
                    if intersection.geom_type == 'MultiPolygon':
                        # 如果是多个多边形，添加每个部分
                        for geom in intersection.geoms:
                            if geom.is_valid and geom.area > 0:
                                grid_polygons.append(geom)
                    else:
                        # 单个多边形
                        if intersection.is_valid and intersection.area > 0:
                            grid_polygons.append(intersection)
        
        return grid_polygons