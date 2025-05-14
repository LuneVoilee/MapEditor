import copy
import numpy as np
from PyQt5.QtGui import QColor
import shapely.geometry as sg

class MapState:
    """地图状态类，用于保存地图的当前状态供历史记录使用"""
    
    def __init__(self):
        self.provinces = []  # 省份列表的深拷贝
        self.rivers = []  # 河流列表的深拷贝
        self.land_plots = []  # 地块列表的深拷贝
        self.heightmap_data = None  # 高程图数据的深拷贝
    
    @staticmethod
    def from_map_controller(controller):
        """从MapController创建当前状态的快照
        
        Args:
            controller: MapController实例
            
        Returns:
            MapState: 当前地图状态的快照
        """
        state = MapState()
        
        # 保存省份信息
        state.provinces = []
        for province in controller.provinces:
            # 创建省份的深拷贝
            province_copy = {
                'name': province.name,
                'color': QColor(province.color),
                'points': copy.deepcopy(province.points),
                'plot_indices': copy.deepcopy(province.plot_indices) if hasattr(province, 'plot_indices') else [],
                # 注意：boundary_polygon不能直接深拷贝，需要重新创建
                'boundary_polygon': None if province.boundary_polygon is None else sg.Polygon(province.boundary_polygon)
            }
            state.provinces.append(province_copy)
        
        # 保存河流信息（河流是点列表的列表）
        state.rivers = copy.deepcopy(controller.rivers)
        
        # 保存地块信息（保存为WKT字符串，因为shapely对象不能直接深拷贝）
        state.land_plots = []
        for plot in controller.land_plots:
            if plot and plot.is_valid:
                state.land_plots.append(plot.wkt)
        
        # 保存高程图数据
        if controller.default_map and hasattr(controller.default_map, 'data'):
            state.heightmap_data = controller.default_map.data.copy()
        
        return state
    
    def apply_to_map_controller(self, controller):
        """将保存的状态应用到MapController
        
        Args:
            controller: MapController实例
        """
        from models.province import Province
        
        # 恢复省份
        controller.provinces = []
        for province_data in self.provinces:
            province = Province(name=province_data['name'], color=province_data['color'])
            province.points = province_data['points']
            province.plot_indices = province_data['plot_indices']
            
            # 重新创建boundary_polygon
            if province_data['boundary_polygon']:
                province.boundary_polygon = sg.loads(province_data['boundary_polygon'].wkt)
            
            # 重建路径缓存
            province._cached_path = None
            province.finalize_shape()
            
            controller.provinces.append(province)
        
        # 恢复河流
        controller.rivers = copy.deepcopy(self.rivers)
        
        # 恢复地块
        controller.land_plots = []
        for plot_wkt in self.land_plots:
            controller.land_plots.append(sg.loads(plot_wkt))
        
        # 恢复高程图数据
        if self.heightmap_data is not None and controller.default_map:
            controller.default_map.data = self.heightmap_data.copy()
        
        # 发送地图更新信号
        controller.map_changed.emit() 