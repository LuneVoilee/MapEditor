from PyQt5.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QTreeWidget, 
                           QTreeWidgetItem, QLabel, QAction, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPoint, QEvent, QObject
from PyQt5.QtGui import QIcon, QCursor, QFont

class ToolsPanel(QDockWidget):
    """统一工具面板，使用多级菜单结构整合所有工具"""
    
    # 自定义信号
    tool_activated = pyqtSignal(str)  # 触发工具
    brush_size_changed = pyqtSignal(int)  # 笔刷大小变更
    brush_strength_changed = pyqtSignal(int)  # 笔刷强度变更
    color_changed = pyqtSignal(object)  # 颜色变更
    province_operation = pyqtSignal(str)  # 省份操作
    terrain_operation = pyqtSignal(str)  # 地形操作
    texture_operation = pyqtSignal(str)  # 纹理操作
    
    def __init__(self, parent=None):
        super().__init__("工具箱", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        # 当前工具
        self.current_tool = None
        
        # 工具分类
        self.tool_categories = {
            "创建大陆": [
                {"name": "大陆笔刷", "id": "continent", "has_brush": True},
                {"name": "生成自然地块", "id": "generate_land_plots", "has_brush": False},
            ],
            "创建省份": [
                {"name": "省份笔刷", "id": "province", "has_brush": True},
                {"name": "地块选择", "id": "plot_select", "has_brush": False},
                {"name": "新建省份", "id": "new_province", "has_brush": False},
                {"name": "完成省份", "id": "finish_province", "has_brush": False},
                {"name": "删除省份", "id": "delete_province", "has_brush": False},
            ],
            "创建地形": [
                {"name": "高程笔刷", "id": "height", "has_brush": True},
                {"name": "河流工具", "id": "river", "has_brush": True},
                {"name": "山丘工具", "id": "hill", "has_brush": True, "preset": {"size": 30, "strength": 20}},
                {"name": "山脉工具", "id": "mountain", "has_brush": True, "preset": {"size": 50, "strength": 40}},
                {"name": "水域工具", "id": "water", "has_brush": True, "preset": {"size": 40, "strength": -20}},
            ],
            "定义纹理": [
                {"name": "纹理笔刷", "id": "texture", "has_brush": True},
                {"name": "生成纹理", "id": "generate_texture", "has_brush": False},
                {"name": "导入纹理", "id": "import_texture", "has_brush": False},
            ]
        }
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化UI组件"""
        # 内容容器
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 说明标签 不需要了
        # hint_label = QLabel("选择工具:")
        # hint_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        # layout.addWidget(hint_label)
        
        # 工具树形菜单
        self.tools_tree = QTreeWidget()
        self.tools_tree.setHeaderHidden(True)
        self.tools_tree.setIndentation(15)
        self.tools_tree.setIconSize(QSize(16, 16))
        self.tools_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                font-size: 16px;
            }
            QTreeWidget::item {
                padding: 6px 4px;
                margin: 2px 0px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3a7ebf;
                color: white;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                border-image: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                border-image: none;
            }
        """)
        self.tools_tree.setMinimumHeight(300)  # 设置最小高度
        self.tools_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 使树控件可以扩展填充空间
        self.tools_tree.itemClicked.connect(self.on_tool_selected)
        
        # 创建自动调整字体大小的事件过滤器
        self.font_adjuster = FontSizeAdjuster(self.tools_tree)
        self.tools_tree.installEventFilter(self.font_adjuster)
        
        # 添加工具分类和工具项
        self.populate_tools_tree()
        
        # 增加滚动区域包装工具树
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # 允许小部件调整大小
        scroll_area.setWidget(self.tools_tree)
        scroll_area.setFrameShape(QFrame.NoFrame)  # 移除边框
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 使滚动区域可以扩展填充空间
        
        layout.addWidget(scroll_area)
        
        # 设置窗口内容
        self.setWidget(content)
    
    def populate_tools_tree(self):
        """填充工具树形菜单"""
        for category_name, tools in self.tool_categories.items():
            # 创建分类项
            category_item = QTreeWidgetItem(self.tools_tree, [category_name])
            category_item.setFlags(Qt.ItemIsEnabled)
            
            # 添加工具项
            for tool in tools:
                tool_item = QTreeWidgetItem(category_item, [tool["name"]])
                tool_item.setData(0, Qt.UserRole, tool)
            
            # 展开分类
            category_item.setExpanded(True)
    
    def on_tool_selected(self, item, column):
        """处理工具选择事件"""
        # 获取工具数据
        tool_data = item.data(0, Qt.UserRole)
        if not tool_data:
            return  # 点击的是分类标题，不是具体工具
        
        tool_id = tool_data["id"]
        has_brush = tool_data.get("has_brush", False)
        
        # 处理特殊工具
        if tool_id.startswith("generate_") or tool_id.startswith("import_"):
            # 触发相应的操作信号
            if "land" in tool_id:
                self.tool_activated.emit(tool_id)
            elif "texture" in tool_id:
                self.texture_operation.emit(tool_id)
            return
        
        # 处理省份操作
        if tool_id in ["new_province", "finish_province", "delete_province"]:
            self.province_operation.emit(tool_id)
            return
        
        # 处理地形工具
        if tool_id in ["hill", "mountain", "water"]:
            self.terrain_operation.emit(tool_id)
            return
        
        # 处理普通工具激活
        self.current_tool = tool_id
        self.tool_activated.emit(tool_id)
    
    def select_tool(self, tool_id):
        """编程方式选择工具"""
        # 查找并选择对应的工具项
        for category_idx in range(self.tools_tree.topLevelItemCount()):
            category_item = self.tools_tree.topLevelItem(category_idx)
            
            for tool_idx in range(category_item.childCount()):
                tool_item = category_item.child(tool_idx)
                tool_data = tool_item.data(0, Qt.UserRole)
                
                if tool_data and tool_data["id"] == tool_id:
                    # 选中此项
                    self.tools_tree.setCurrentItem(tool_item)
                    self.on_tool_selected(tool_item, 0)
                    return
    
    def closeEvent(self, event):
        """关闭事件处理"""
        super().closeEvent(event) 

class FontSizeAdjuster(QObject):
    """字体大小自适应调整器，通过监听窗口大小变化，动态调整字体大小"""
    
    def __init__(self, parent=None, min_font_size=18, max_font_size=22):
        super().__init__(parent)
        self.parent = parent
        self.min_font_size = min_font_size
        self.max_font_size = max_font_size
        self.base_width = 250  # 基准宽度
        
    def eventFilter(self, obj, event):
        """事件过滤器，监听调整大小事件"""
        if event.type() == QEvent.Resize:
            self.adjust_font_size(obj)
        return super().eventFilter(obj, event)
    
    def adjust_font_size(self, widget):
        """根据窗口宽度调整字体大小"""
        if not widget or not hasattr(widget, 'width'):
            return
        
        # 取得当前宽度
        current_width = widget.width()
        
        # 计算合适的字体大小
        if current_width <= self.base_width:
            font_size = self.min_font_size
        else:
            # 线性插值计算字体大小
            ratio = min(1.0, (current_width - self.base_width) / 200)
            font_size = self.min_font_size + ratio * (self.max_font_size - self.min_font_size)
        
        # 应用样式表
        widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: transparent;
                border: none;
                font-size: {int(font_size)}px;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                margin: 2px 0px;
                border-radius: 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: #3a7ebf;
                color: white;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                border-image: none;
            }}
        """) 