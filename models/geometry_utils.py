# models/geometry_utils.py
import shapely.geometry as sg
from shapely.validation import make_valid

def validate_and_fix_geometry(geometry):
    """
    验证并修复几何对象，解决拓扑异常问题
    
    参数:
        geometry: shapely几何对象
        
    返回:
        修复后的几何对象
    """
    if geometry is None:
        return None
        
    # 检查几何对象是否有效
    if not geometry.is_valid:
        try:
            # 使用shapely的make_valid函数修复几何对象
            fixed_geometry = make_valid(geometry)
            return fixed_geometry
        except Exception as e:
            print(f"几何修复失败: {e}")
            # 尝试使用buffer(0)方法修复
            try:
                return geometry.buffer(0)
            except:
                # 如果所有修复方法都失败，返回一个简化版本
                try:
                    return geometry.simplify(0.5, preserve_topology=False)
                except:
                    return None
    return geometry

def split_multi_geometries(geometry):
    """
    拆分多部件几何体为独立几何对象
    
    参数:
        geometry: 需要拆分的几何对象
        
    返回:
        独立几何对象的列表，已过滤无效和小面积部件
    """
    if not geometry:
        return []
    
    valid_geo = validate_and_fix_geometry(geometry)
    if not valid_geo:
        return []
    
    parts = []
    
    if valid_geo.geom_type.startswith('Multi'):
        parts = list(valid_geo.geoms)
    else:
        parts = [valid_geo]
    
    # 过滤无效和小面积部件
    min_area = 10  # 最小有效面积阈值
    return [
        part for part in parts 
        if part.is_valid and part.area >= min_area
    ]


def safe_difference(geom1, geom2):
    """
    安全地执行几何差集操作，处理可能的拓扑异常
    
    参数:
        geom1: 第一个几何对象
        geom2: 第二个几何对象
        
    返回:
        差集结果几何对象，如果操作失败则返回原始几何对象
    """
    if geom1 is None or geom2 is None:
        return geom1
        
    # 确保输入几何对象有效
    valid_geom1 = validate_and_fix_geometry(geom1)
    valid_geom2 = validate_and_fix_geometry(geom2)
    
    if valid_geom1 is None:
        return None
    
    if valid_geom2 is None:
        return valid_geom1
    
    try:
        # 尝试执行差集操作
        result = valid_geom1.difference(valid_geom2)
        return result
    except Exception as e:
        print(f"差集操作失败: {e}")
        # 如果差集失败，尝试使用其他方法
        try:
            # 使用缓冲区技术避免拓扑异常
            buffered1 = valid_geom1.buffer(0.01)
            buffered2 = valid_geom2.buffer(0.01)
            result = buffered1.difference(buffered2)
            return result.buffer(-0.01)  # 恢复原始大小
        except Exception as e:
            print(f"备用差集方法也失败: {e}")
            return valid_geom1  # 返回原始几何对象
