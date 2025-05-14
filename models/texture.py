# models/texture.py
from PyQt5.QtGui import QImage, QPixmap

class Texture:
    """纹理类，管理地图的纹理数据"""
    
    def __init__(self):
        self.vegetation_textures = {}  # 植被纹理库
        self.terrain_textures = {}  # 地形纹理库
        self.load_default_textures()
        
    def load_default_textures(self):
        """加载默认纹理"""
        # 这里只是示例，实际项目中需要加载真实的纹理
        vegetation_types = ["森林", "草原", "沙漠", "雪地", "沼泽"]
        for veg_type in vegetation_types:
            self.vegetation_textures[veg_type] = None
        
        terrain_types = ["平原", "丘陵", "山地", "高山"]
        for terrain_type in terrain_types:
            self.terrain_textures[terrain_type] = None
    
    def load_texture(self, path):
        """从文件加载纹理"""
        try:
            image = QImage(path)
            return QPixmap.fromImage(image)
        except Exception as e:
            print(f"加载纹理失败: {e}")
            return None
    
    def get_texture_for_elevation(self, elevation):
        """根据海拔获取合适的纹理"""
        if elevation < 20:
            return self.terrain_textures.get("平原")
        elif elevation < 50:
            return self.terrain_textures.get("丘陵")
        elif elevation < 80:
            return self.terrain_textures.get("山地")
        else:
            return self.terrain_textures.get("高山")