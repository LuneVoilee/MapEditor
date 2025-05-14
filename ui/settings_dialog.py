from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                           QGroupBox, QTabWidget, QWidget, QListWidget, QListWidgetItem,
                           QKeySequenceEdit, QGridLayout, QMessageBox)
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
        }
        
        # 加载当前快捷键设置
        self.current_shortcuts = {}
        self.load_shortcuts()
        
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
        
        # 将来可添加其他设置页
        # display_tab = self.create_display_tab()
        # tab_widget.addTab(display_tab, "显示")
        
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
    
    def load_shortcuts(self):
        """从设置加载快捷键配置"""
        self.settings.beginGroup("Shortcuts")
        
        # 加载所有快捷键设置，若没有则使用默认值
        for action_name, default_shortcut in self.default_shortcuts.items():
            shortcut_str = self.settings.value(action_name, default_shortcut.toString())
            self.current_shortcuts[action_name] = QKeySequence(shortcut_str)
        
        self.settings.endGroup()
    
    def save_shortcuts(self):
        """保存快捷键配置到设置"""
        self.settings.beginGroup("Shortcuts")
        
        for action_name, shortcut in self.current_shortcuts.items():
            self.settings.setValue(action_name, shortcut.toString())
        
        self.settings.endGroup()
        self.settings.sync()
    
    def reset_to_defaults(self):
        """重置所有设置为默认值"""
        # 重置快捷键
        for action_name, default_shortcut in self.default_shortcuts.items():
            self.current_shortcuts[action_name] = default_shortcut
            if action_name in self.shortcut_items:
                self.shortcut_items[action_name].shortcut_edit.setKeySequence(default_shortcut)
    
    def accept(self):
        """保存设置并关闭对话框"""
        self.save_shortcuts()
        self.settings_changed.emit()
        super().accept()
    
    def get_shortcut(self, action_name):
        """获取指定操作的快捷键"""
        if action_name in self.current_shortcuts:
            return self.current_shortcuts[action_name]
        return QKeySequence() 