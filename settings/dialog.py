from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, 
                             QFormLayout, QCheckBox, QSpinBox, QDialogButtonBox,
                             QLabel, QHBoxLayout, QPushButton)
from PyQt5.QtGui import QKeySequence, QKeyEvent, QFont
from PyQt5.QtCore import Qt, pyqtSignal
from .config import AppSettings

class KeySequenceEdit(QWidget):
    """自定义快捷键编辑控件"""
    
    keySequenceChanged = pyqtSignal(QKeySequence)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 定义样式常量
        self.NORMAL_STYLE = "padding: 2px 5px; border: 1px solid #999; background-color: #f8f8f8; color: #000000;"
        self.FOCUS_STYLE = "padding: 2px 5px; border: 1px solid #3c7fb1; background-color: #f0f0f0; color: #000000;"
        self.ACTIVE_STYLE = "padding: 2px 5px; border: 1px solid #3c7fb1; background-color: #e6f0fa; color: #000000;"
        self.INACTIVE_STYLE = "padding: 2px 5px; border: 1px solid #999; background-color: #e6f0fa; color: #000000;"
        
        self.key_label = QLabel("按下快捷键...")
        self.key_label.setMinimumWidth(120)
        # 设置边框和背景色，让它看起来像输入框
        self.key_label.setStyleSheet(self.NORMAL_STYLE)
        
        self.clear_button = QPushButton("清除")
        self.clear_button.setMaximumWidth(60)
        
        self.layout.addWidget(self.key_label)
        self.layout.addWidget(self.clear_button)
        
        self.current_sequence = QKeySequence()
        self.clear_button.clicked.connect(self.clear_sequence)
        
        # 设置焦点策略，使控件可以接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        
    def setKeySequence(self, sequence):
        """设置快捷键序列"""
        if isinstance(sequence, QKeySequence):
            self.current_sequence = sequence
            if sequence.isEmpty():
                self.key_label.setText("按下快捷键...")
                self.key_label.setStyleSheet(self.NORMAL_STYLE)
            else:
                self.key_label.setText(sequence.toString())
                # 设置一个特殊的样式，表示已设置快捷键
                self.key_label.setStyleSheet(self.ACTIVE_STYLE)
            self.keySequenceChanged.emit(self.current_sequence)
        
    def keySequence(self):
        """获取当前快捷键序列"""
        return self.current_sequence
    
    def clear_sequence(self):
        """清除快捷键"""
        self.setKeySequence(QKeySequence())
        
    def focusInEvent(self, event):
        """获得焦点时的处理"""
        super().focusInEvent(event)
        if self.current_sequence.isEmpty():
            self.key_label.setText("请按下快捷键组合...")
        self.key_label.setStyleSheet(self.FOCUS_STYLE)
        
    def focusOutEvent(self, event):
        """失去焦点时的处理"""
        super().focusOutEvent(event)
        if self.current_sequence.isEmpty():
            self.key_label.setText("按下快捷键...")
            self.key_label.setStyleSheet(self.NORMAL_STYLE)
        else:
            self.key_label.setStyleSheet(self.INACTIVE_STYLE)
        
    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        # 忽略修饰键单独按下
        if event.key() in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return
            
        # 创建键序列
        key = event.key()
        modifiers = event.modifiers()
        
        # 清除键
        if key == Qt.Key_Escape:
            self.clear_sequence()
            return
        
        # 如果按下的只是普通键，不带修饰键，则提示需要组合键
        if modifiers == Qt.NoModifier:
            # 除非是功能键，如F1-F12
            if not (Qt.Key_F1 <= key <= Qt.Key_F35):
                self.key_label.setText("请使用Ctrl/Alt/Shift等组合键")
                self.key_label.setStyleSheet(self.FOCUS_STYLE)
                return
        
        # 创建新的快捷键
        sequence = QKeySequence(int(modifiers) + key)
        self.setKeySequence(sequence)
        
        # 吞噬事件，不要传递给父控件
        event.accept()
    

class SettingsDialog(QDialog):
    """设置对话框，动态生成设置界面"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None, app_settings=None):
        super().__init__(parent)
        self.app_settings = app_settings or AppSettings()
        self.widgets = {}  # 存储所有设置控件
        self.init_ui()

    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("设置")
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        tab_widget = QTabWidget()
        
        # 创建设置分类页
        categories = {}
        for key, config in AppSettings.SETTINGS_CONFIG.items():
            category = config['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((key, config))
            
        # 动态生成设置页
        for category, items in categories.items():
            page = QWidget()
            form = QFormLayout()
            
            for key, config in items:
                # 根据类型创建不同控件
                if config['type'] == bool:
                    widget = QCheckBox()
                    widget.setChecked(self.app_settings.get(key))
                elif config['type'] == int:
                    widget = QSpinBox()
                    widget.setMinimum(1)
                    widget.setMaximum(1000)
                    widget.setValue(self.app_settings.get(key))
                elif config['type'] == 'key':
                    widget = KeySequenceEdit()
                    widget.setKeySequence(self.app_settings.get(key))
                # 可以继续添加其他类型控件...
                
                # 添加控件和标签
                label = QLabel(config['name'] + ":")
                form.addRow(label, widget)
                self.widgets[key] = widget
            
            page.setLayout(form)
            tab_widget.addTab(page, category)
        
        # 添加按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(tab_widget)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def accept(self):
        """保存所有设置"""
        # 创建一个标记，记录是否有任何设置发生了变更
        has_changes = False
        
        for key, widget in self.widgets.items():
            old_value = self.app_settings.get(key)
            new_value = None
            
            if isinstance(widget, QCheckBox):
                new_value = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                new_value = widget.value()
            elif isinstance(widget, KeySequenceEdit):
                new_value = widget.keySequence()
                
            # 只有当值发生变化时才更新设置
            if old_value != new_value:
                self.app_settings.set(key, new_value)
                has_changes = True
        
        # 应用所有设置
        self.app_settings.apply_all()
        
        # 立即刷新UI，强制重绘KeySequenceEdit控件
        for widget in self.widgets.values():
            if isinstance(widget, KeySequenceEdit) and widget.isVisible():
                widget.update()
                
        # 如果发生了变更，则发出信号
        if has_changes:
            self.settings_changed.emit()
            
        super().accept()
        
    def is_show_grid_enabled(self):
        """获取是否显示网格设置（兼容旧代码）"""
        return self.app_settings.get('MapSettings/ShowGrid')
    
    def is_performance_monitor_enabled(self):
        """获取是否启用性能监控设置（兼容旧代码）"""
        return self.app_settings.get('Performance/EnablePerformanceMonitor')
        
    def get_grid_size(self):
        """获取网格大小设置（兼容旧代码）"""
        return self.app_settings.get('MapSettings/GridSize')