from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                           QGroupBox, QTabWidget, QWidget, QListWidget, QListWidgetItem,
                           QKeySequenceEdit, QGridLayout, QMessageBox, QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QSettings, pyqtSignal
from PyQt5.QtGui import QKeySequence

class ShortcutItem(QWidget):
    """自定义快捷键编辑项"""
    
    shortcut_changed = pyqtSignal(str, QKeySequence)
    
    def __init__(self, action_name, shortcut, parent=None):
        super().__init__(parent)
        self.action_name = action_name
        
        # 创建布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # 添加操作名称标签
        self.name_label = QLabel(action_name)
        layout.addWidget(self.name_label)
        
        # 添加快捷键编辑器
        self.shortcut_edit = QKeySequenceEdit(shortcut)
        self.shortcut_edit.editingFinished.connect(self.on_shortcut_changed)
        layout.addWidget(self.shortcut_edit)
        
        # 设置伸展因子
        layout.setStretch(0, 1)
        layout.setStretch(1, 0)
    
    def on_shortcut_changed(self):
        """快捷键变更事件处理"""
        self.shortcut_changed.emit(self.action_name, self.shortcut_edit.keySequence())
    
    def get_shortcut(self):
        """获取当前设置的快捷键"""
        return self.shortcut_edit.keySequence()

class SettingsDialog(QDialog):
    """设置对话框"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(500, 400)
        self.settings = QSettings("MapEditor", "Settings")
        
        # 定义默认快捷键
        self.default_shortcuts = {
            "撤销": QKeySequence("Ctrl+Z"),
            "重做": QKeySequence("Ctrl+Y"),
            "打开": QKeySequence("Ctrl+O"),
            "保存": QKeySequence("Ctrl+S"),
            "新建": QKeySequence("Ctrl+N"),
            "导出": QKeySequence("Ctrl+E"),
            "退出": QKeySequence("Alt+F4"),
            "性能监控": QKeySequence("Ctrl+P"),
        }
        
        # 默认设置
        self.default_settings = {
            "GridSize": 50,  # 默认栅格精度为50
            "EnablePerformanceMonitor": True,  # 默认启用性能监控
        }
        
        # 加载当前快捷键设置
        self.current_shortcuts = {}
        self.load_shortcuts()
        
        # 加载当前栅格设置
        self.current_settings = {}
        self.load_settings()
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化UI组件"""
        main_layout = QVBoxLayout(self)
        
        # 创建选项卡控件
        tab_widget = QTabWidget()
        
        # 创建快捷键设置页
        shortcuts_tab = self.create_shortcuts_tab()
        tab_widget.addTab(shortcuts_tab, "快捷键")
        
        # 创建地图设置页
        map_tab = self.create_map_tab()
        tab_widget.addTab(map_tab, "地图")
        
        # 创建性能设置页
        view_tab = self.create_view_tab()
        tab_widget.addTab(view_tab, "界面")
        
        main_layout.addWidget(tab_widget)
        
        # 创建底部按钮
        button_layout = QHBoxLayout()
        
        reset_button = QPushButton("恢复默认")
        reset_button.clicked.connect(self.reset_to_defaults)
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(reset_button)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
    
    def create_shortcuts_tab(self):
        """创建快捷键设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明标签
        help_label = QLabel("点击快捷键字段并按下所需的组合键来修改快捷键")
        layout.addWidget(help_label)
        
        # 快捷键列表
        self.shortcut_items = {}
        shortcuts_group = QGroupBox("快捷键")
        shortcuts_layout = QVBoxLayout()
        
        # 添加所有操作的快捷键编辑项
        for action_name, shortcut in self.current_shortcuts.items():
            item = ShortcutItem(action_name, shortcut)
            item.shortcut_changed.connect(self.on_shortcut_changed)
            shortcuts_layout.addWidget(item)
            self.shortcut_items[action_name] = item
        
        shortcuts_group.setLayout(shortcuts_layout)
        layout.addWidget(shortcuts_group)
        
        return widget
    
    def create_map_tab(self):
        """创建地图设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 栅格设置组
        grid_group = QGroupBox("栅格设置")
        grid_layout = QGridLayout()
        
        # 栅格精度设置
        grid_size_label = QLabel("栅格精度:")
        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(1, 500)  # 设置精度范围
        self.grid_size_spin.setValue(self.current_settings["GridSize"])
        self.grid_size_spin.setSingleStep(5)
        self.grid_size_spin.valueChanged.connect(self.on_grid_size_changed)
        
        grid_size_help = QLabel("较小的值会生成更多更细的地块，较大的值会生成更少更粗的地块")
        grid_size_help.setWordWrap(True)
        
        # 添加显示网格选项
        self.show_grid_checkbox = QCheckBox("显示网格")
        self.show_grid_checkbox.setChecked(self.current_settings.get("ShowGrid", True))
        self.show_grid_checkbox.toggled.connect(self.on_show_grid_toggled)
        
        grid_layout.addWidget(grid_size_label, 0, 0)
        grid_layout.addWidget(self.grid_size_spin, 0, 1)
        grid_layout.addWidget(grid_size_help, 1, 0, 1, 2)
        grid_layout.addWidget(self.show_grid_checkbox, 2, 0, 1, 2)
        
        grid_group.setLayout(grid_layout)
        layout.addWidget(grid_group)
        
        # 添加一些填充空间
        layout.addStretch()
        
        return widget
    
    def create_view_tab(self):
        """创建界面设置页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 性能监控设置组
        perf_group = QGroupBox("性能监控")
        perf_layout = QVBoxLayout()
        
        # 启用性能监控选项
        self.enable_perf_checkbox = QCheckBox("启用性能监控")
        self.enable_perf_checkbox.setChecked(self.current_settings.get("EnablePerformanceMonitor", self.default_settings["EnablePerformanceMonitor"]))
        self.enable_perf_checkbox.toggled.connect(self.on_perf_monitor_toggled)
        
        perf_layout.addWidget(self.enable_perf_checkbox)

        
        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)
        
        # 添加一些填充空间
        layout.addStretch()
        
        return widget
    
    def on_shortcut_changed(self, action_name, shortcut):
        """快捷键变更事件处理"""
        # 检查快捷键冲突
        for name, item in self.shortcut_items.items():
            if name != action_name and item.get_shortcut() == shortcut and not shortcut.isEmpty():
                QMessageBox.warning(
                    self, 
                    "快捷键冲突", 
                    f"快捷键 '{shortcut.toString()}' 已被 '{name}' 使用"
                )
                # 重置为原来的快捷键
                self.shortcut_items[action_name].shortcut_edit.setKeySequence(
                    self.current_shortcuts[action_name]
                )
                return
        
        # 更新当前快捷键
        self.current_shortcuts[action_name] = shortcut
    
    def on_grid_size_changed(self, value):
        """栅格精度变更处理"""
        self.current_settings["GridSize"] = value
    
    def on_perf_monitor_toggled(self, checked):
        """性能监控启用状态变更处理"""
        self.current_settings["EnablePerformanceMonitor"] = checked
    
    def on_show_grid_toggled(self, checked):
        """网格显示状态变更处理"""
        self.current_settings["ShowGrid"] = checked
    
    def load_shortcuts(self):
        """从设置加载快捷键配置"""
        self.settings.beginGroup("Shortcuts")
        
        # 加载所有快捷键设置，若没有则使用默认值
        for action_name, default_shortcut in self.default_shortcuts.items():
            shortcut_str = self.settings.value(action_name, default_shortcut.toString())
            self.current_shortcuts[action_name] = QKeySequence(shortcut_str)
        
        self.settings.endGroup()
    
    def load_settings(self):
        """加载其他设置"""
        self.settings.beginGroup("MapSettings")
        
        # 加载栅格精度设置
        self.current_settings["GridSize"] = int(self.settings.value("GridSize", self.default_settings["GridSize"]))
        
        # 加载显示网格设置
        self.current_settings["ShowGrid"] = self.settings.value("ShowGrid", "true") == "true"
        
        self.settings.endGroup()
        
        self.settings.beginGroup("Performance")
        
        # 加载性能监控设置
        self.current_settings["EnablePerformanceMonitor"] = self.settings.value(
            "EnablePerformanceMonitor", 
            self.default_settings["EnablePerformanceMonitor"],
            type=bool
        )
        
        self.settings.endGroup()
    
    def save_shortcuts(self):
        """保存快捷键配置到设置"""
        self.settings.beginGroup("Shortcuts")
        
        for action_name, shortcut in self.current_shortcuts.items():
            self.settings.setValue(action_name, shortcut.toString())
        
        self.settings.endGroup()
    
    def save_settings(self):
        """保存其他设置"""
        self.settings.beginGroup("MapSettings")
        
        # 保存栅格精度设置
        self.settings.setValue("GridSize", self.current_settings["GridSize"])
        
        # 保存显示网格设置
        self.settings.setValue("ShowGrid", str(self.current_settings["ShowGrid"]).lower())
        
        self.settings.endGroup()
        
        self.settings.beginGroup("Performance")
        
        # 保存性能监控设置
        self.settings.setValue("EnablePerformanceMonitor", self.current_settings["EnablePerformanceMonitor"])
        
        self.settings.endGroup()
        self.settings.sync()
    
    def reset_to_defaults(self):
        """重置所有设置为默认值"""
        # 重置快捷键
        for action_name, default_shortcut in self.default_shortcuts.items():
            self.current_shortcuts[action_name] = default_shortcut
            if action_name in self.shortcut_items:
                self.shortcut_items[action_name].shortcut_edit.setKeySequence(default_shortcut)
        
        # 重置栅格设置
        self.current_settings["GridSize"] = self.default_settings["GridSize"]
        self.grid_size_spin.setValue(self.default_settings["GridSize"])
        
        # 重置性能监控设置
        self.current_settings["EnablePerformanceMonitor"] = self.default_settings["EnablePerformanceMonitor"]
        self.enable_perf_checkbox.setChecked(self.default_settings["EnablePerformanceMonitor"])
        
        # 重置显示网格设置
        self.current_settings["ShowGrid"] = self.default_settings["ShowGrid"]
        self.show_grid_checkbox.setChecked(self.default_settings["ShowGrid"])
    
    def accept(self):
        """保存设置并关闭对话框"""
        self.save_shortcuts()
        self.save_settings()
        self.settings_changed.emit()
        super().accept()
    
    def get_shortcut(self, action_name):
        """获取指定操作的快捷键
        
        Args:
            action_name: 操作名称
        
        Returns:
            QKeySequence: 快捷键序列
        """
        return self.current_shortcuts.get(action_name, QKeySequence())
    
    def get_grid_size(self):
        """获取栅格精度设置
        
        Returns:
            int: 栅格精度
        """
        return self.current_settings.get("GridSize", self.default_settings["GridSize"])
    
    def is_performance_monitor_enabled(self):
        """获取性能监控启用状态
        
        Returns:
            bool: 是否启用性能监控
        """
        return self.current_settings.get("EnablePerformanceMonitor", self.default_settings["EnablePerformanceMonitor"])
    
    def is_show_grid_enabled(self):
        """返回是否显示网格"""
        return self.current_settings.get("ShowGrid", True) 