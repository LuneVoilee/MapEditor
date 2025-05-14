from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QLabel, QSlider, QGroupBox, QTreeWidget, 
                           QTreeWidgetItem, QColorDialog, QSpinBox, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor

class ToolWindow(QDockWidget):

    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        # 创建内容窗口
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(5)
        
        self.setWidget(self.content_widget)
"""
class ToolBox(ToolWindow):
    # 工具箱窗口，包含多级菜单结构的工具选择
    
    # 自定义信号
    tool_selected = pyqtSignal(str)
    brush_size_changed = pyqtSignal(int)
    brush_strength_changed = pyqtSignal(int)
    color_changed = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__("工具箱", parent)
        
        self.init_ui()
    
    def init_ui(self):

        # 工具树形菜单
        tools_group = QGroupBox("工具选择")
        tools_layout = QVBoxLayout()
        
        self.tools_tree = QTreeWidget()
        self.tools_tree.setHeaderHidden(True)
        self.tools_tree.itemClicked.connect(self.on_tool_selected)
        
        # 添加工具分类
        # 1. 省份工具
        province_category = QTreeWidgetItem(self.tools_tree, ["省份工具"])
        
        province_tool = QTreeWidgetItem(province_category, ["省份笔刷"])
        province_tool.setData(0, Qt.UserRole, "province")
        
        plot_select_tool = QTreeWidgetItem(province_category, ["地块选择"])
        plot_select_tool.setData(0, Qt.UserRole, "plot_select")
        
        # 2. 地形工具
        terrain_category = QTreeWidgetItem(self.tools_tree, ["地形工具"])
        
        height_tool = QTreeWidgetItem(terrain_category, ["高程笔刷"])
        height_tool.setData(0, Qt.UserRole, "height")
        
        river_tool = QTreeWidgetItem(terrain_category, ["河流工具"])
        river_tool.setData(0, Qt.UserRole, "river")
        
        # 3. 大陆工具
        continent_category = QTreeWidgetItem(self.tools_tree, ["大陆工具"])
        
        continent_tool = QTreeWidgetItem(continent_category, ["大陆笔刷"])
        continent_tool.setData(0, Qt.UserRole, "continent")
        
        land_divider_tool = QTreeWidgetItem(continent_category, ["地块生成"])
        land_divider_tool.setData(0, Qt.UserRole, "land_divider")
        
        # 4. 选择工具
        select_category = QTreeWidgetItem(self.tools_tree, ["选择工具"])
        
        select_tool = QTreeWidgetItem(select_category, ["选择工具"])
        select_tool.setData(0, Qt.UserRole, "select")
        
        pan_tool = QTreeWidgetItem(select_category, ["平移工具"])
        pan_tool.setData(0, Qt.UserRole, "pan")
        
        # 展开所有分类
        self.tools_tree.expandAll()
        
        tools_layout.addWidget(self.tools_tree)
        tools_group.setLayout(tools_layout)
        
        # 添加到主布局
        self.content_layout.addWidget(tools_group)
        
        # 笔刷属性控制
        brush_group = QGroupBox("笔刷属性")
        brush_layout = QVBoxLayout()
        
        # 笔刷大小
        size_layout = QHBoxLayout()
        size_label = QLabel("笔刷大小:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 100)
        self.size_spin.setValue(20)
        self.size_spin.valueChanged.connect(self.on_brush_size_changed)
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        
        # 笔刷大小滑块
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(self.size_spin.setValue)
        self.size_spin.valueChanged.connect(self.size_slider.setValue)
        
        # 笔刷强度
        strength_layout = QHBoxLayout()
        strength_label = QLabel("笔刷强度:")
        self.strength_spin = QSpinBox()
        self.strength_spin.setRange(1, 50)
        self.strength_spin.setValue(10)
        self.strength_spin.valueChanged.connect(self.on_brush_strength_changed)
        
        strength_layout.addWidget(strength_label)
        strength_layout.addWidget(self.strength_spin)
        
        # 笔刷强度滑块
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setRange(1, 50)
        self.strength_slider.setValue(10)
        self.strength_slider.valueChanged.connect(self.strength_spin.setValue)
        self.strength_spin.valueChanged.connect(self.strength_slider.setValue)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        color_label = QLabel("颜色:")
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(50, 24)
        self.current_color = QColor(100, 150, 200)
        self.update_color_button()
        self.color_btn.clicked.connect(self.choose_color)
        
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_btn)
        
        # 将控件添加到笔刷布局
        brush_layout.addLayout(size_layout)
        brush_layout.addWidget(self.size_slider)
        brush_layout.addLayout(strength_layout)
        brush_layout.addWidget(self.strength_slider)
        brush_layout.addLayout(color_layout)
        
        brush_group.setLayout(brush_layout)
        
        # 添加到主布局
        self.content_layout.addWidget(brush_group)
        
        # 省份操作按钮
        province_op_group = QGroupBox("省份操作")
        province_op_layout = QVBoxLayout()
        
        # 新建省份按钮
        self.new_province_btn = QPushButton("新建省份")
        self.new_province_btn.clicked.connect(self.on_new_province)
        province_op_layout.addWidget(self.new_province_btn)
        
        # 完成省份按钮
        self.finish_province_btn = QPushButton("完成省份")
        self.finish_province_btn.clicked.connect(self.on_finish_province)
        province_op_layout.addWidget(self.finish_province_btn)
        
        # 删除省份按钮
        self.delete_province_btn = QPushButton("删除省份")
        self.delete_province_btn.clicked.connect(self.on_delete_province)
        province_op_layout.addWidget(self.delete_province_btn)
        
        province_op_group.setLayout(province_op_layout)
        
        # 添加到主布局
        self.content_layout.addWidget(province_op_group)
        
        # 添加弹性空间
        self.content_layout.addStretch(1)
    
    def update_color_button(self):

        self.color_btn.setStyleSheet(
            f"background-color: {self.current_color.name()}; border: 1px solid #777777;"
        )
    
    def on_tool_selected(self, item, column):

        # 获取关联的工具名称
        tool_name = item.data(0, Qt.UserRole)
        if tool_name:
            self.tool_selected.emit(tool_name)
    
    def on_brush_size_changed(self, value):

        self.brush_size_changed.emit(value)
    
    def on_brush_strength_changed(self, value):

        self.brush_strength_changed.emit(value)
    
    def choose_color(self):

        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.color_changed.emit(color)
    
    def on_new_province(self):

        # 这里发射一个假的工具选择信号，具体的逻辑由控制器处理
        self.tool_selected.emit("new_province")
    
    def on_finish_province(self):

        self.tool_selected.emit("finish_province")
    
    def on_delete_province(self):

        self.tool_selected.emit("delete_province")
"""

class PropertiesWindow(ToolWindow):
    """属性窗口，显示和编辑当前选中对象的属性"""
    
    # 自定义信号
    property_changed = pyqtSignal(str, object)  # 属性名称, 新值
    
    def __init__(self, parent=None):
        super().__init__("属性", parent)
        
        self.init_ui()
        
        # 当前选中对象
        self.current_object = None
    
    def init_ui(self):
        """初始化UI组件"""
        # 属性组
        self.properties_group = QGroupBox("对象属性")
        self.properties_layout = QVBoxLayout()
        
        # 无选中对象时的提示
        self.no_selection_label = QLabel("未选中任何对象")
        self.properties_layout.addWidget(self.no_selection_label)
        
        self.properties_group.setLayout(self.properties_layout)
        
        # 添加到主布局
        self.content_layout.addWidget(self.properties_group)
        
        # 添加弹性空间
        self.content_layout.addStretch(1)
    
    def set_object(self, obj):
        """设置当前选中对象"""
        self.current_object = obj
        
        # 清除现有属性控件
        while self.properties_layout.count():
            item = self.properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if obj is None:
            # 显示无选中提示
            self.no_selection_label = QLabel("未选中任何对象")
            self.properties_layout.addWidget(self.no_selection_label)
            return
        
        # 添加对象类型
        type_label = QLabel(f"类型: {obj.__class__.__name__}")
        self.properties_layout.addWidget(type_label)
        
        # 添加省份属性控件
        if hasattr(obj, 'name'):
            name_layout = QHBoxLayout()
            name_label = QLabel("名称:")
            name_edit = QLineEdit(obj.name)
            name_edit.editingFinished.connect(
                lambda: self.property_changed.emit('name', name_edit.text())
            )
            
            name_layout.addWidget(name_label)
            name_layout.addWidget(name_edit)
            self.properties_layout.addLayout(name_layout)
        
        if hasattr(obj, 'color'):
            color_layout = QHBoxLayout()
            color_label = QLabel("颜色:")
            color_btn = QPushButton()
            color_btn.setFixedSize(50, 24)
            color_btn.setStyleSheet(
                f"background-color: {obj.color.name()}; border: 1px solid #777777;"
            )
            color_btn.clicked.connect(self.change_object_color)
            
            color_layout.addWidget(color_label)
            color_layout.addWidget(color_btn)
            self.properties_layout.addLayout(color_layout)
        
        # 其他属性显示
        if hasattr(obj, 'plot_indices'):
            plots_count = len(obj.plot_indices) if obj.plot_indices else 0
            plots_label = QLabel(f"地块数量: {plots_count}")
            self.properties_layout.addWidget(plots_label)
        
        # 添加弹性空间
        self.properties_layout.addStretch(1)
    
    def change_object_color(self):
        """更改对象颜色"""
        if not self.current_object or not hasattr(self.current_object, 'color'):
            return
        
        color = QColorDialog.getColor(self.current_object.color, self, "选择颜色")
        if color.isValid():
            self.property_changed.emit('color', color) 