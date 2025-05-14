import json
import os
import pickle
import numpy as np
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QObject, pyqtSignal
import shapely.geometry as sg
from shapely.geometry import mapping, shape
import cv2

from models.province import Province
from models.heightmap import HeightMap
from models.texture import Texture
from ui.history.history_manager import HistoryManager
from ui.history.map_state import MapState

class MapController(QObject):
    """地图控制器，负责处理地图数据操作和工具逻辑
    
    该类是地图编辑器的核心，管理所有地图数据（高程、省份、河流等），
    提供工具逻辑实现，并通过信号机制与视图层（MapCanvasView）通信。
    作为MVC架构中的控制器，它将数据模型与用户界面分离。
    """
    
    # 自定义信号
    tool_changed = pyqtSignal(str)  # 工具变更信号
    map_changed = pyqtSignal()  # 地图数据变更信号
    selection_changed = pyqtSignal(Province)  # 选中省份变更信号
    
    def __init__(self, parent=None):
        """初始化地图控制器
        
        Args:
            parent: 父QObject
        """
        super().__init__(parent)
        
        # 地图数据
        self.provinces = []  # 省份列表
        self.rivers = []  # 河流列表
        self.land_plots = []  # 大陆地块列表
        self.land_plots_selected = []  # 已选择的地块列表，用于构建省份
        self.continent_mask = None  # 大陆掩码
        
        # 初始化高程图
        self.default_map = HeightMap(800, 600)
        
        # 工具状态
        self.current_tool = "province"  # 当前工具
        self.brush_size = 20  # 笔刷大小
        self.brush_strength = 10  # 笔刷强度
        self.current_color = QColor(100, 150, 200)  # 当前颜色
        
        # 编辑状态
        self.selected_province = None  # 当前选中的省份
        self.current_province = None  # 当前正在创建的省份
        
        # 文件操作
        self.current_file_path = None  # 当前文件路径
        
        # 历史记录管理
        self.history_manager = HistoryManager(max_history=50)
        self.add_to_history()  # 保存初始状态
    
    def add_to_history(self):
        """添加当前状态到历史记录，用于撤销/重做功能"""
        state = MapState()
        
        # 省份数据
        state.provinces = []
        for province in self.provinces:
            province_data = {
                'name': province.name,
                'color': QColor(province.color),
                'points': province.points.copy() if province.points else [],
                'plot_indices': province.plot_indices.copy() if hasattr(province, 'plot_indices') else [],
                'boundary_polygon': None if province.boundary_polygon is None else province.boundary_polygon
            }
            state.provinces.append(province_data)
        
        # 河流数据
        state.rivers = self.rivers.copy()
        
        # 地块数据
        state.land_plots = []
        for plot in self.land_plots:
            if plot and hasattr(plot, 'is_valid') and plot.is_valid:
                state.land_plots.append(plot.wkt)
        
        # 高程图数据
        if self.default_map and hasattr(self.default_map, 'data'):
            state.heightmap_data = self.default_map.data.copy()
        
        # 保存状态
        self.history_manager.add_state(state)
    
    def undo(self):
        """撤销操作，返回到上一个历史状态
        
        Returns:
            bool: 是否成功撤销
        """
        if not self.history_manager.can_undo():
            return False
        
        # 获取上一个状态
        state = self.history_manager.undo()
        if state:
            self._apply_state(state)
            return True
        
        return False
    
    def redo(self):
        """重做操作，恢复到下一个历史状态
        
        Returns:
            bool: 是否成功重做
        """
        if not self.history_manager.can_redo():
            return False
        
        # 获取下一个状态
        state = self.history_manager.redo()
        if state:
            self._apply_state(state)
            return True
        
        return False
    
    def _apply_state(self, state):
        """应用历史状态
        
        Args:
            state: 要应用的MapState对象
        """
        # 恢复省份
        self.provinces = []
        for province_data in state.provinces:
            province = Province(name=province_data['name'], color=province_data['color'])
            province.points = province_data['points']
            province.plot_indices = province_data['plot_indices']
            
            # 重新创建boundary_polygon
            if province_data['boundary_polygon']:
                province.boundary_polygon = province_data['boundary_polygon']
            
            # 重建路径缓存
            province._cached_path = None
            province.finalize_shape()
            
            self.provinces.append(province)
        
        # 恢复河流
        self.rivers = state.rivers.copy()
        
        # 恢复地块
        self.land_plots = []
        for plot_wkt in state.land_plots:
            self.land_plots.append(sg.loads(plot_wkt))
        
        # 恢复高程图数据
        if state.heightmap_data is not None and self.default_map:
            self.default_map.data = state.heightmap_data.copy()
        
        # 发送地图已更改信号
        self.map_changed.emit()
    
    def set_tool(self, tool_name):
        """设置当前工具
        
        Args:
            tool_name: 工具名称
        """
        # 检查是否是有效的工具名称
        valid_tools = ["select", "province", "height", "river", "continent", "plot_select"]
        if tool_name in valid_tools:
            self.current_tool = tool_name
            # 发出工具变更信号
            self.tool_changed.emit(tool_name)
        else:
            print(f"警告: 未知的工具名称 '{tool_name}'")
    
    def set_brush_size(self, size):
        """设置笔刷大小
        
        Args:
            size: 笔刷大小（像素）
        """
        self.brush_size = size
    
    def set_brush_strength(self, strength):
        """设置笔刷强度
        
        Args:
            strength: 笔刷强度值
        """
        self.brush_strength = strength
    
    def set_color(self, color):
        """设置当前颜色
        
        Args:
            color: QColor对象
        """
        self.current_color = color
    
    def select_province(self, pos):
        """选择省份
        
        Args:
            pos: 鼠标位置（QPoint）
            
        Returns:
            bool: 是否选中了省份
        """
        x, y = pos.x(), pos.y()
        for province in self.provinces:
            if province.contains_point(x, y):
                self.selected_province = province
                self.selection_changed.emit(province)
                return True
        
        self.selected_province = None
        self.selection_changed.emit(None)
        return False
    
    def create_new_province(self):
        """创建新省份
        
        Returns:
            Province: 新创建的省份对象
        """
        # 随机生成颜色
        h = np.random.random()
        s = 0.5 + np.random.uniform(-0.1, 0.1)
        v = 0.8 + np.random.uniform(-0.1, 0.1)
        color = QColor.fromHsvF(h, s, v)
        
        # 创建新省份
        province = Province(name=f"省份{len(self.provinces)}", color=color)
        province.plot_indices = []
        
        self.current_province = province
        
        return province
    
    def add_province(self, province):
        """添加省份到地图
        
        Args:
            province: 要添加的Province对象
            
        Returns:
            bool: 是否成功添加
        """
        if province and province not in self.provinces:
            self.provinces.append(province)
            self.add_to_history()
            self.map_changed.emit()
            return True
        return False
    
    def delete_province(self, province):
        """从地图中删除省份"""
        if province in self.provinces:
            self.provinces.remove(province)
            if self.selected_province == province:
                self.selected_province = None
                self.selection_changed.emit(None)
            
            self.add_to_history()
            self.map_changed.emit()
            return True
        return False
    
    def reset_map(self):
        """重置地图"""
        self.provinces = []
        self.rivers = []
        self.land_plots = []
        self.land_plots_selected = []
        self.default_map = HeightMap(800, 600)
        
        self.selected_province = None
        self.current_province = None
        
        self.add_to_history()
        self.map_changed.emit()
    
    def select_plots_in_brush(self, pos, is_adding=True):
        """在笔刷范围内选择地块"""
        if not self.land_plots:
            return False
        
        x, y = pos.x(), pos.y()
        changed = False
        
        # 计算笔刷半径
        radius = self.brush_size / 2
        
        # 遍历所有地块
        for i, plot in enumerate(self.land_plots):
            if plot and hasattr(plot, 'contains') and plot.contains(sg.Point(x, y)) or \
               plot and hasattr(plot, 'centroid') and plot.centroid.buffer(radius).contains(sg.Point(x, y)):
                # 添加到选择列表（如果是添加模式）
                if is_adding and i not in self.land_plots_selected:
                    self.land_plots_selected.append(i)
                    changed = True
                # 从选择列表移除（如果是移除模式）
                elif not is_adding and i in self.land_plots_selected:
                    self.land_plots_selected.remove(i)
                    changed = True
        
        if changed:
            self.map_changed.emit()
        
        return changed
    
    def finalize_province_from_plots(self):
        """从选定的地块创建省份"""
        if not self.current_province or not self.land_plots_selected:
            return False
        
        # 收集选定地块
        selected_plots = [self.land_plots[i] for i in self.land_plots_selected if i < len(self.land_plots)]
        if not selected_plots:
            return False
        
        # 合并地块为一个多边形
        try:
            from shapely.ops import unary_union
            union = unary_union(selected_plots)
            
            if union.is_empty:
                return False
            
            # 更新省份信息
            self.current_province.boundary_polygon = union
            self.current_province.plot_indices = self.land_plots_selected.copy()
            
            # 提取外部边界作为点集
            if hasattr(union, 'exterior') and union.exterior:
                self.current_province.points = list(union.exterior.coords)
            
            # 清空路径缓存
            self.current_province._cached_path = None
            
            # 将省份添加到列表
            if self.current_province not in self.provinces:
                self.provinces.append(self.current_province)
            
            # 清空选择的地块列表
            self.land_plots_selected = []
            
            # 保存历史状态
            self.add_to_history()
            self.map_changed.emit()
            
            return True
        except Exception as e:
            print(f"创建省份失败: {e}")
            return False
    
    def save_map(self, file_path):
        """保存地图到文件
        
        Args:
            file_path: 保存路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 创建要保存的数据字典
            data = {
                'provinces': [],
                'rivers': self.rivers,
                'heightmap': self.default_map.data.tolist() if self.default_map is not None else None,
                'version': '1.0'
            }
            
            # 处理省份数据
            for province in self.provinces:
                province_data = {
                    'name': province.name,
                    'color': province.color.name(),
                    'points': province.points,
                    'plot_indices': province.plot_indices
                }
                
                # 处理边界多边形（转换为WKT格式）
                if province.boundary_polygon and hasattr(province.boundary_polygon, 'wkt'):
                    province_data['boundary_polygon'] = province.boundary_polygon.wkt
                else:
                    province_data['boundary_polygon'] = None
                
                data['provinces'].append(province_data)
            
            # 处理地块数据
            data['land_plots'] = []
            for plot in self.land_plots:
                if plot and hasattr(plot, 'wkt'):
                    data['land_plots'].append(plot.wkt)
            
            # 保存数据
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            
            # 更新当前文件路径
            self.current_file_path = file_path
            
            return True
        except Exception as e:
            print(f"保存地图失败: {e}")
            return False
    
    def load_map(self, file_path):
        """从文件加载地图
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            # 打开文件
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            # 重置当前状态
            self.reset_map()
            
            # 加载高程图数据
            if 'heightmap' in data and data['heightmap'] is not None:
                height_data = np.array(data['heightmap'])
                if self.default_map is None:
                    self.default_map = HeightMap(height_data.shape[1], height_data.shape[0])
                self.default_map.data = height_data
            
            # 加载河流数据
            if 'rivers' in data:
                self.rivers = data['rivers']
            
            # 加载地块数据
            if 'land_plots' in data:
                self.land_plots = []
                for plot_wkt in data['land_plots']:
                    try:
                        plot = sg.loads(plot_wkt)
                        if plot and plot.is_valid:
                            self.land_plots.append(plot)
                    except Exception as e:
                        print(f"加载地块失败: {e}")
            
            # 加载省份数据
            if 'provinces' in data:
                for province_data in data['provinces']:
                    try:
                        # 创建省份对象
                        province = Province(
                            name=province_data['name'],
                            color=QColor(province_data['color'])
                        )
                        
                        # 设置点集和地块索引
                        province.points = province_data['points']
                        province.plot_indices = province_data['plot_indices']
                        
                        # 加载边界多边形
                        if 'boundary_polygon' in province_data and province_data['boundary_polygon']:
                            province.boundary_polygon = sg.loads(province_data['boundary_polygon'])
                        
                        # 重建路径缓存
                        province._cached_path = None
                        
                        # 添加到省份列表
                        self.provinces.append(province)
                    except Exception as e:
                        print(f"加载省份失败: {e}")
            
            # 更新当前文件路径
            self.current_file_path = file_path
            
            # 触发地图更新
            self.map_changed.emit()
            
            return True
        except Exception as e:
            print(f"加载地图失败: {e}")
            return False
    
    def export_map_data(self, file_path):
        """导出地图数据为JSON格式
        
        Args:
            file_path: 导出文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            # 创建要导出的数据字典
            export_data = {
                'provinces': [],
                'rivers': [],
                'heightmap': {
                    'width': self.default_map.width if self.default_map else 800,
                    'height': self.default_map.height if self.default_map else 600,
                    'data': self.default_map.data.tolist() if self.default_map is not None else []
                },
                'version': '1.0'
            }
            
            # 处理省份数据
            for province in self.provinces:
                province_data = {
                    'name': province.name,
                    'color': province.color.name(),
                }
                
                # 将边界多边形转换为GeoJSON格式
                if province.boundary_polygon:
                    province_data['geometry'] = mapping(province.boundary_polygon)
                
                export_data['provinces'].append(province_data)
            
            # 处理河流数据
            for river in self.rivers:
                river_data = {
                    'points': river
                }
                export_data['rivers'].append(river_data)
            
            # 处理地块数据
            export_data['land_plots'] = []
            for plot in self.land_plots:
                if plot and plot.is_valid:
                    plot_data = mapping(plot)
                    export_data['land_plots'].append(plot_data)
            
            # 写入JSON文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"导出地图数据失败: {e}")
            return False
    
    def import_map_data(self, file_path):
        """从JSON文件导入地图数据
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            bool: 导入是否成功
        """
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 重置当前状态
            self.reset_map()
            
            # 导入高程图数据
            if 'heightmap' in import_data:
                heightmap_data = import_data['heightmap']
                if 'data' in heightmap_data and heightmap_data['data']:
                    height_data = np.array(heightmap_data['data'])
                    width = heightmap_data.get('width', height_data.shape[1])
                    height = heightmap_data.get('height', height_data.shape[0])
                    self.default_map = HeightMap(width, height)
                    self.default_map.data = height_data
            
            # 导入河流数据
            if 'rivers' in import_data:
                for river_data in import_data['rivers']:
                    if 'points' in river_data:
                        self.rivers.append(river_data['points'])
            
            # 导入地块数据
            if 'land_plots' in import_data:
                for plot_data in import_data['land_plots']:
                    try:
                        plot = shape(plot_data)
                        if plot and plot.is_valid:
                            self.land_plots.append(plot)
                    except Exception as e:
                        print(f"导入地块失败: {e}")
            
            # 导入省份数据
            if 'provinces' in import_data:
                for province_data in import_data['provinces']:
                    try:
                        # 创建省份对象
                        province = Province(
                            name=province_data['name'], 
                            color=QColor(province_data['color'])
                        )
                        
                        # 导入几何数据
                        if 'geometry' in province_data:
                            try:
                                province.boundary_polygon = shape(province_data['geometry'])
                                if province.boundary_polygon and hasattr(province.boundary_polygon, 'exterior'):
                                    province.points = list(province.boundary_polygon.exterior.coords)
                            except Exception as e:
                                print(f"导入省份几何数据失败: {e}")
                        
                        # 重建路径缓存
                        province._cached_path = None
                        
                        # 添加到省份列表
                        self.provinces.append(province)
                    except Exception as e:
                        print(f"导入省份失败: {e}")
            
            # 触发地图更新
            self.map_changed.emit()
            
            return True
        except Exception as e:
            print(f"导入地图数据失败: {e}")
            return False
    
    def generate_land_plots(self, plot_cell_size=50):
        """生成陆地地块"""
        if not self.default_map:
            print("错误: 无法生成地块，未设置高程图")
            return False
        
        try:
            # 从高程图生成地块
            print("正在生成地块...")
            
            # 通过高程阈值过滤出陆地部分
            land_mask = self.default_map.data > 0
            
            # 生成地块
            plot_geometries = self._generate_plots_from_mask(land_mask, plot_cell_size)
            
            # 设置地块
            self.land_plots = plot_geometries
            self.land_plots_selected = set()  # 清空选择
            
            # 通知视图更新
            self.map_changed.emit()
            
            return True
            
        except Exception as e:
            print(f"生成地块时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_plots_from_mask(self, land_mask, plot_cell_size=50):
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