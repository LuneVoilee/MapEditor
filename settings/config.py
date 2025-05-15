from PyQt5.QtCore import QSettings, QObject, pyqtSignal
from PyQt5.QtGui import QKeySequence

class AppSettings(QObject):
    """统一管理应用程序设置和快捷键"""
    
    # 设置变更信号
    settings_changed = pyqtSignal(str)  # 参数为变更的设置键名
    
    # 定义所有可配置项（包含默认值）
    SETTINGS_CONFIG = {
        'MapSettings/GridSize': {
            'default': 50,
            'type': int,
            'name': '栅格精度',
            'category': '地图设置'
        },
        'MapSettings/ShowGrid': {
            'default': True,
            'type': bool,
            'name': '显示网格',
            'category': '地图设置'
        },
        'Performance/EnablePerformanceMonitor': {
            'default': True,
            'type': bool,
            'name': '启用性能监控',
            'category': '性能'
        },
        'Shortcuts/Undo': {
            'default': QKeySequence("Ctrl+Z"),
            'type': 'key',
            'name': '撤销',
            'category': '快捷键'
        },
        'Shortcuts/Redo': {
            'default': QKeySequence("Ctrl+Y"),
            'type': 'key',
            'name': '重做',
            'category': '快捷键'
        },
        'Shortcuts/ShowGrid': {
            'default': QKeySequence("Ctrl+G"),
            'type': 'key',
            'name': '显示/隐藏网格',
            'category': '快捷键'
        },
        'Shortcuts/TogglePerformanceMonitor': {
            'default': QKeySequence("Ctrl+P"),
            'type': 'key',
            'name': '显示/隐藏性能监控',
            'category': '快捷键'
        }
        # 可以继续添加其他设置项...
    }

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MapEditor", "Settings")
        self.shortcut_actions = {}  # 存储快捷键对应的QAction
        self.map_controller = None
        
        # 检查是否是首次运行，若是则初始化默认设置
        if not self.settings.contains('AppInitialized'):
            self.initialize_default_settings()
            self.settings.setValue('AppInitialized', True)

    def initialize_default_settings(self):
        """初始化所有默认设置"""
        for key, config in self.SETTINGS_CONFIG.items():
            if not self.settings.contains(key):
                self.settings.setValue(key, config['default'])

    def set_map_controller(self, controller):
        """设置地图控制器引用"""
        self.map_controller = controller

    def get(self, key):
        """获取设置值"""
        config = self.SETTINGS_CONFIG.get(key)
        if not config:
            return None
        
        # 对于快捷键类型，需要特殊处理
        if config['type'] == 'key':
            value = self.settings.value(key, config['default'])
            # 如果存储的是字符串，需要转换为QKeySequence
            if isinstance(value, str):
                return QKeySequence(value)
            return value
            
        return self.settings.value(
            key, 
            config['default'],
            type=config['type']
        )

    def set(self, key, value):
        """保存设置值，并触发信号通知设置变更"""
        old_value = self.settings.value(key)
        
        # 如果值相同，不需要更新
        if old_value == value:
            return
            
        self.settings.setValue(key, value)
        
        # 触发设置变更信号
        self.settings_changed.emit(key)
        
        # 如果是快捷键设置，立即更新对应的快捷键
        if key.startswith('Shortcuts/') and key in self.shortcut_actions:
            self.shortcut_actions[key].setShortcut(value)

    def bind_shortcut(self, action, key):
        """Action绑定快捷键，并返回action以便链式调用"""
        self.shortcut_actions[key] = action
        action.setShortcut(self.get(key))
        return action

    def apply_all(self):
        """应用所有设置"""
        # 应用快捷键
        for key, action in self.shortcut_actions.items():
            shortcut = self.get(key)
            # 确保是QKeySequence类型
            if not isinstance(shortcut, QKeySequence):
                if isinstance(shortcut, str):
                    shortcut = QKeySequence(shortcut)
                else:
                    shortcut = QKeySequence()
            
            # 设置快捷键
            action.setShortcut(shortcut)
        
        # 应用其他设置
        if self.map_controller:
            self.map_controller.set_show_grid(self.get('MapSettings/ShowGrid'))
            
    def load_shortcut(self, shortcut_key):
        """加载快捷键设置"""
        return self.get(f'Shortcuts/{shortcut_key}')
        
    def add_dynamic_setting(self, key, default_value, value_type, name, category):
        """动态添加新的设置项"""
        if key not in self.SETTINGS_CONFIG:
            self.SETTINGS_CONFIG[key] = {
                'default': default_value,
                'type': value_type,
                'name': name,
                'category': category
            }
            # 如果设置不存在，初始化默认值
            if not self.settings.contains(key):
                self.settings.setValue(key, default_value) 