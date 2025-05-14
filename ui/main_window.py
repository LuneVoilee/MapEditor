# ui/main_window.py
from PyQt5.QtWidgets import (QMainWindow, QDockWidget, QVBoxLayout, QHBoxLayout, 
                            QWidget, QToolBar, QAction, QLabel, QStatusBar, 
                            QFileDialog, QMessageBox, QColorDialog, QPushButton,
                            QApplication, QProgressDialog, QSlider)
from PyQt5.QtGui import QIcon, QColor, QMouseEvent, QKeySequence
from PyQt5.QtCore import Qt, QPoint, QTimer, QSize

from ui.map_canvas_view import MapCanvasView
from ui.tools_panel import ToolsPanel
from ui.controllers.map_controller import MapController
from ui.styles.modern_style import apply_modern_style, apply_light_style
from ui.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    """地图编辑器主窗口"""
    
    def __init__(self):
        # 移除 Qt.FramelessWindowHint，使用标准窗口
        super().__init__()
        self.setWindowTitle("PyQt5地图编辑器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 应用现代样式
        self.is_dark_mode = True
        self.apply_style()
        
        # 窗口尺寸调整防抖定时器
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(100)  # 100ms防抖间隔
        self.resize_timer.timeout.connect(self.on_resize_timeout)
        
        self.init_ui()
        
    def apply_style(self):
        """应用UI样式"""
        if self.is_dark_mode:
            apply_modern_style(QApplication.instance())
        else:
            apply_light_style(QApplication.instance())
    
    def toggle_theme(self):
        """切换深色/浅色主题"""
        self.is_dark_mode = not self.is_dark_mode
        self.apply_style()
    
    def init_ui(self):
        """初始化UI组件"""
        # 创建主容器
        self.main_container = QWidget()
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 设置内容容器为中央部件
        self.setCentralWidget(self.main_container)
        
        # 创建地图控制器
        self.map_controller = MapController(self)
        
        # 创建内容容器（包含菜单、工具栏和地图画布）
        content_container = QMainWindow()
        content_container.setWindowFlags(Qt.Widget)  # 作为普通部件使用
        main_layout.addWidget(content_container)
        
        # 在内容容器中创建菜单
        self.create_menus(content_container)
        
        # 在内容容器中创建工具栏
        self.create_toolbars(content_container)
        
        # 中央地图画布
        self.map_canvas = MapCanvasView(content_container)
        self.map_canvas.set_controller(self.map_controller)
        content_container.setCentralWidget(self.map_canvas)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        content_container.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 创建停靠窗口
        self.create_docks(content_container)
        
        # 创建键盘快捷键
        self.create_shortcuts()
        
        # 连接控制器信号
        self.connect_signals()
    
    def connect_signals(self):
        """连接信号和槽"""
        # 地图控制器信号
        self.map_controller.map_changed.connect(self.on_map_changed)
        self.map_controller.selection_changed.connect(self.on_selection_changed)
        
        # 工具面板信号
        self.tool_panel.tool_activated.connect(self.on_tool_activated)
        self.tool_panel.province_operation.connect(self.on_province_operation)
        self.tool_panel.terrain_operation.connect(self.on_terrain_operation)
        self.tool_panel.texture_operation.connect(self.on_texture_operation)
        
        # 地图画布信号
        self.map_canvas.mouse_pressed.connect(self.on_map_mouse_pressed)
        self.map_canvas.mouse_moved.connect(self.on_map_mouse_moved)
        self.map_canvas.mouse_released.connect(self.on_map_mouse_released)
        self.map_canvas.key_pressed.connect(self.on_map_key_pressed)
    
    def on_map_changed(self):
        """地图变更事件处理"""
        self.status_bar.showMessage("地图已更新")
    
    def on_selection_changed(self, province):
        """选择变更事件处理"""
        if province:
            self.status_bar.showMessage(f"已选择省份: {province.name}")
        else:
            self.status_bar.showMessage("未选择省份")
    
    def on_tool_activated(self, tool_id):
        """处理工具激活事件"""
        if tool_id == "generate_land_plots":
            self.generate_land_plots()
        else:
            self.map_controller.set_tool(tool_id)
            
            # 根据工具类型显示/隐藏笔刷控制工具栏
            has_brush = tool_id in ["province", "height", "continent", "river", "texture"]
            self.brush_toolbar.setVisible(has_brush)
            
            # 如果是特殊工具，设置预设值
            if tool_id == "hill":
                self.size_slider.setValue(30)
                self.strength_slider.setValue(20)
            elif tool_id == "mountain":
                self.size_slider.setValue(50)
                self.strength_slider.setValue(40)
            elif tool_id == "water":
                self.size_slider.setValue(40)
                self.strength_slider.setValue(-20)
            
            self.status_bar.showMessage(f"已选择工具: {tool_id}")
    
    def on_province_operation(self, operation):
        """处理省份操作"""
        if operation == "new_province":
            province = self.map_controller.create_new_province()
            self.status_bar.showMessage(f"已创建新省份: {province.name}")
            self.map_controller.set_tool("province")
        elif operation == "finish_province":
            if self.map_controller.finalize_province_from_plots():
                self.status_bar.showMessage("省份创建完成")
            else:
                self.status_bar.showMessage("无法完成省份，请确保已选择足够的地块")
        elif operation == "delete_province":
            if self.map_controller.selected_province:
                if self.map_controller.delete_province(self.map_controller.selected_province):
                    self.status_bar.showMessage("省份已删除")
                else:
                    self.status_bar.showMessage("删除省份失败")
            else:
                self.status_bar.showMessage("未选择任何省份")
    
    def on_terrain_operation(self, operation):
        """处理地形操作"""
        if operation == "hill":
            self.map_controller.set_tool("height")
            self.map_controller.set_brush_size(30)
            self.map_controller.set_brush_strength(20)
            self.status_bar.showMessage("已选择丘陵工具")
        elif operation == "mountain":
            self.map_controller.set_tool("height")
            self.map_controller.set_brush_size(50)
            self.map_controller.set_brush_strength(40)
            self.status_bar.showMessage("已选择山脉工具")
        elif operation == "water":
            self.map_controller.set_tool("height")
            self.map_controller.set_brush_size(40)
            self.map_controller.set_brush_strength(-20)
            self.status_bar.showMessage("已选择水域工具")
    
    def on_texture_operation(self, operation):
        """处理纹理操作"""
        if operation == "generate_texture":
            self.status_bar.showMessage("正在生成纹理...")
            # 实现纹理生成逻辑
        elif operation == "import_texture":
            self.status_bar.showMessage("请选择纹理文件...")
            # 实现纹理导入逻辑
    
    def on_map_mouse_pressed(self, pos, button):
        """地图鼠标按下事件处理"""
        tool = self.map_controller.current_tool
        
        if button == Qt.LeftButton:
            if tool == "province":
                # 在笔刷范围内选择地块
                self.map_controller.select_plots_in_brush(pos, is_adding=True)
            elif tool == "height":
                # TODO: 实现高程笔刷
                pass
            elif tool == "select":
                # 选择省份
                self.map_controller.select_province(pos)
        elif button == Qt.RightButton:
            if tool == "province":
                # 从选择中移除地块
                self.map_controller.select_plots_in_brush(pos, is_adding=False)
    
    def on_map_mouse_moved(self, pos):
        """地图鼠标移动事件处理"""
        tool = self.map_controller.current_tool
        
        if tool == "province" and hasattr(self, '_is_left_button_pressed') and self._is_left_button_pressed:
            # 在鼠标拖动时持续选择地块
            self.map_controller.select_plots_in_brush(pos, is_adding=True)
    
    def on_map_mouse_released(self, pos, button):
        """地图鼠标释放事件处理"""
        if button == Qt.LeftButton:
            self._is_left_button_pressed = False
    
    def on_map_key_pressed(self, key):
        """地图键盘按下事件处理"""
        if key == Qt.Key_Delete:
            # 删除当前选中的省份
            if self.map_controller.selected_province:
                self.map_controller.delete_province(self.map_controller.selected_province)
                self.status_bar.showMessage("省份已删除")
        elif key == Qt.Key_Escape:
            # 取消当前工具
            self.map_controller.selected_province = None
            self.map_controller.selection_changed.emit(None)
            self.status_bar.showMessage("已取消选择")
    
    def create_menus(self, parent_window):
        """创建菜单"""
        menu_bar = parent_window.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_map)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_map)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_map)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为", self)
        save_as_action.triggered.connect(self.save_map_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_map_data)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.import_map_data)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menu_bar.addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        # 视图菜单
        view_menu = menu_bar.addMenu("视图")
        
        theme_action = QAction("切换主题", self)
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # 设置菜单
        settings_menu = menu_bar.addMenu("设置")
        
        preferences_action = QAction("偏好设置", self)
        preferences_action.triggered.connect(self.show_settings)
        settings_menu.addAction(preferences_action)
        
        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        
        generate_land_action = QAction("生成自然地块", self)
        generate_land_action.triggered.connect(self.generate_land_plots)
        tools_menu.addAction(generate_land_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbars(self, parent_window):
        """创建工具栏"""
        
        # 创建笔刷工具栏
        self.brush_toolbar = QToolBar("笔刷控制", parent_window)
        self.brush_toolbar.setMovable(False)
        parent_window.addToolBar(Qt.TopToolBarArea, self.brush_toolbar)
        
        # 创建笔刷控制容器组件
        brush_widget = QWidget()
        brush_layout = QHBoxLayout(brush_widget)
        brush_layout.setContentsMargins(5, 2, 5, 2)
        
        # 添加笔刷大小控制
        size_layout = QHBoxLayout()
        size_label = QLabel("笔刷大小:")
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(100)
        self.size_slider.setValue(20)
        self.size_slider.valueChanged.connect(
            lambda value: self.map_controller.set_brush_size(value))
        self.size_value_label = QLabel("20")
        self.size_slider.valueChanged.connect(
            lambda value: self.size_value_label.setText(str(value)))
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_value_label)
        
        # 添加笔刷强度控制
        strength_layout = QHBoxLayout()
        strength_label = QLabel("笔刷强度:")
        self.strength_slider = QSlider(Qt.Horizontal)
        self.strength_slider.setMinimum(1)
        self.strength_slider.setMaximum(50)
        self.strength_slider.setValue(10)
        self.strength_slider.valueChanged.connect(
            lambda value: self.map_controller.set_brush_strength(value))
        self.strength_value_label = QLabel("10")
        self.strength_slider.valueChanged.connect(
            lambda value: self.strength_value_label.setText(str(value)))
        
        strength_layout.addWidget(strength_label)
        strength_layout.addWidget(self.strength_slider)
        strength_layout.addWidget(self.strength_value_label)
        
        # 添加颜色选择按钮
        color_layout = QHBoxLayout()
        color_label = QLabel("颜色:")
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 24)
        self.color_btn.setStyleSheet("background-color: #6496C8; border: 1px solid #777777;")
        self.color_btn.clicked.connect(self.choose_color)
        
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_btn)
        
        # 将控制项添加到布局
        brush_layout.addLayout(size_layout)
        brush_layout.addSpacing(10)
        brush_layout.addLayout(strength_layout)
        brush_layout.addSpacing(10)
        brush_layout.addLayout(color_layout)
        
        # 添加到工具栏
        self.brush_toolbar.addWidget(brush_widget)
        
        # 默认隐藏笔刷工具栏，只在需要时显示
        self.brush_toolbar.setVisible(False)
    
    def create_docks(self, parent_window):
        """创建停靠窗口"""
        # 创建统一工具面板
        self.tool_panel = ToolsPanel(parent_window)
        parent_window.addDockWidget(Qt.LeftDockWidgetArea, self.tool_panel)
    
    def generate_land_plots(self):
        """生成自然地块"""
        # 创建进度对话框
        progress = QProgressDialog("正在生成地块...", "取消", 0, 100, self)
        progress.setWindowTitle("生成地块")
        progress.setModal(True)
        progress.show()
        QApplication.processEvents()  # 更新界面
        
        try:
            # 调用控制器的地块生成方法
            progress.setValue(20)
            QApplication.processEvents()
            
            success = self.map_controller.generate_land_plots(plot_cell_size=50)
            
            progress.setValue(100)
            QApplication.processEvents()
            
            if success:
                self.status_bar.showMessage("已生成地块")
            else:
                QMessageBox.warning(self, "警告", "生成地块失败，请检查高程图数据")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成地块时出错: {str(e)}")
        finally:
            progress.close()
            
    def new_map(self):
        """创建新地图"""
        reply = QMessageBox.question(self, "确认", "创建新地图会丢失当前未保存的更改。是否继续？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.map_controller.reset_map()
            self.status_bar.showMessage("已创建新地图")
    
    def open_map(self):
        """打开地图文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "打开地图", "", "地图文件 (*.map);;所有文件 (*.*)")
        if file_path:
            try:
                success = self.map_controller.load_map(file_path)
                if success:
                    self.status_bar.showMessage(f"已加载地图: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "无法解析地图文件")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开地图文件: {str(e)}")
    
    def save_map(self):
        """保存地图"""
        if not self.map_controller.current_file_path:
            self.save_map_as()
        else:
            try:
                success = self.map_controller.save_map(self.map_controller.current_file_path)
                if success:
                    self.status_bar.showMessage(f"地图已保存至: {self.map_controller.current_file_path}")
                else:
                    QMessageBox.critical(self, "错误", "保存地图失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存地图文件: {str(e)}")
    
    def save_map_as(self):
        """另存为地图文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存地图", "", "地图文件 (*.map);;所有文件 (*.*)")
        if file_path:
            try:
                success = self.map_controller.save_map(file_path)
                if success:
                    self.status_bar.showMessage(f"地图已保存至: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "保存地图失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存地图文件: {str(e)}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于地图编辑器", 
                          "PyQt5地图编辑器 v1.0\n\n"
                          "服务于游戏的地图编辑工具，提供以下功能：\n"
                          "• 省份创建和编辑\n"
                          "• 地形高程绘制\n"
                          "• 河流绘制\n"
                          "• 自动地块生成\n"
                          "• 地图导入导出\n\n"
                          "采用MVC设计模式，模块化架构，支持深色/浅色主题切换。\n\n"
                          )
    
    def export_map_data(self):
        """导出地图数据"""
        file_path, _ = QFileDialog.getSaveFileName(self, "导出地图数据", "", "地图数据 (*.json);;所有文件 (*.*)")
        if file_path:
            # 确保文件名以.json结尾
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
                
            try:
                success = self.map_controller.export_map_data(file_path)
                if success:
                    self.status_bar.showMessage(f"地图数据已导出至: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "导出地图数据失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出地图数据时发生错误: {str(e)}")
    
    def import_map_data(self):
        """导入地图数据"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入地图数据", "", "地图数据 (*.json);;所有文件 (*.*)")
        if file_path:
            try:
                success = self.map_controller.import_map_data(file_path)
                if success:
                    self.status_bar.showMessage(f"已导入地图数据: {file_path}")
                else:
                    QMessageBox.critical(self, "错误", "导入地图数据失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入地图数据时发生错误: {str(e)}")
    
    def create_shortcuts(self):
        """创建键盘快捷键"""
        # 撤销动作
        self.undo_action = QAction("撤销", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.undo_action.triggered.connect(self.undo)
        self.addAction(self.undo_action)
        
        # 重做动作
        self.redo_action = QAction("重做", self)
        self.redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        self.redo_action.triggered.connect(self.redo)
        self.addAction(self.redo_action)
    
    def undo(self):
        """执行撤销操作"""
        if self.map_controller.undo():
            self.status_bar.showMessage("已撤销")
        else:
            self.status_bar.showMessage("无法撤销")
    
    def redo(self):
        """执行重做操作"""
        if self.map_controller.redo():
            self.status_bar.showMessage("已重做")
        else:
            self.status_bar.showMessage("无法重做")
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.apply_settings)
        
        if dialog.exec_():
            self.apply_settings()
    
    def apply_settings(self):
        """应用设置"""
        # 重新加载快捷键设置
        self.load_shortcuts()
        
    def load_shortcuts(self):
        """从设置加载快捷键配置"""
        from PyQt5.QtCore import QSettings
        
        settings = QSettings("MapEditor", "Settings")
        settings.beginGroup("Shortcuts")
        
        # 更新撤销/重做快捷键
        self.undo_action.setShortcut(settings.value("撤销", "Ctrl+Z"))
        self.redo_action.setShortcut(settings.value("重做", "Ctrl+Y"))
        
        settings.endGroup()
    
    def choose_color(self):
        """选择颜色"""
        current_color = self.color_btn.palette().button().color()
        color = QColorDialog.getColor(current_color, self, "选择笔刷颜色")
        
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #777777;")
            self.map_controller.set_color(color)
    
    def resizeEvent(self, event):
        """窗口大小变化事件处理"""
        # 启动防抖定时器
        if self.resize_timer.isActive():
            self.resize_timer.stop()
        
        # 设置优化绘制模式
        if hasattr(self, 'map_canvas') and self.map_canvas:
            self.map_canvas.optimized_drawing = True
        
        # 使用200ms防抖间隔
        self.resize_timer.setInterval(200)
        self.resize_timer.start()
        
        super().resizeEvent(event)
    
    def on_resize_timeout(self):
        """窗口尺寸调整结束后的处理"""
        if hasattr(self, 'map_canvas') and self.map_canvas:
            # 取消优化绘制模式
            self.map_canvas.optimized_drawing = False
            self.map_canvas.needs_redraw = True
            
            # 清除省份缓存以便在新尺寸下重建
            if hasattr(self.map_canvas, 'provinces_cache'):
                delattr(self.map_canvas, 'provinces_cache')
                
            self.map_canvas.update()