from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

def apply_modern_style(app):
    """应用现代风格样式到应用程序
    
    Args:
        app: QApplication 实例
    """
    # 优先使用Fusion风格，这是一个跨平台的现代风格
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 创建深色调色板
    dark_palette = QPalette()
    
    # 设置暗色调色板
    dark_color = QColor(45, 45, 45)
    disabled_color = QColor(70, 70, 70)
    text_color = QColor(220, 220, 220)
    highlight_color = QColor(42, 130, 218)
    
    # 应用颜色
    dark_palette.setColor(QPalette.Window, dark_color)
    dark_palette.setColor(QPalette.WindowText, text_color)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, dark_color)
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, text_color)
    dark_palette.setColor(QPalette.Disabled, QPalette.Text, disabled_color)
    dark_palette.setColor(QPalette.Button, dark_color)
    dark_palette.setColor(QPalette.ButtonText, text_color)
    dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_color)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, highlight_color)
    dark_palette.setColor(QPalette.Highlight, highlight_color)
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    dark_palette.setColor(QPalette.Disabled, QPalette.HighlightedText, disabled_color)
    
    # 应用调色板
    app.setPalette(dark_palette)
    
    # 添加额外的样式表
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a2a2a; 
            border: 1px solid #767676; 
            border-radius: 4px;
            padding: 2px;
        }
        
        QWidget {
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            font-size: 10pt;
        }
        
        QMainWindow, QDialog {
            background-color: #2d2d2d;
        }
        
        QMenuBar {
            background-color: #2d2d2d;
            color: #ffffff;
        }
        
        QMenuBar::item {
            background: transparent;
            padding: 4px 10px;
        }
        
        QMenuBar::item:selected {
            background-color: #3d3d3d;
            border-radius: 2px;
        }
        
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 2px;
        }
        
        QMenu::item {
            padding: 6px 20px;
        }
        
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
        
        QPushButton {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #505050;
            border-radius: 4px;
            padding: 6px 16px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #505050;
            border: 1px solid #606060;
        }
        
        QPushButton:pressed {
            background-color: #606060;
        }
        
        QPushButton:disabled {
            background-color: #353535;
            color: #656565;
            border: 1px solid #454545;
        }
        
        QToolBar {
            background-color: #333333;
            border: none;
            spacing: 3px;
            padding: 3px;
        }
        
        QToolBar::handle {
            /* 移除引用外部资源的代码
            background-image: url(:/images/handle.png);
            background-repeat: repeat-y;
            background-position: center;
            */
        }
        
        QToolButton {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 2px;
            padding: 3px;
        }
        
        QToolButton:hover {
            background-color: #404040;
            border: 1px solid #505050;
        }
        
        QToolButton:pressed {
            background-color: #505050;
        }
        
        QDockWidget {
            border: 1px solid #3d3d3d;
            /* 移除引用外部资源的代码
            titlebar-close-icon: url(:/images/close.png);
            titlebar-normal-icon: url(:/images/undock.png);
            */
        }
        
        QDockWidget::title {
            background-color: #2a2a2a;
            padding-left: 10px;
            padding-top: 4px;
            padding-bottom: 4px;
        }
        
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            background-color: #2d2d2d;
        }
        
        QTabBar::tab {
            background-color: #2a2a2a;
            padding: 6px 12px;
            border: 1px solid #3d3d3d;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #3d3d3d;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #323232;
        }
        
        QScrollBar:vertical {
            background-color: #2a2a2a;
            width: 14px;
            margin: 15px 0 15px 0;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #5a5a5a;
            min-height: 20px;
            border-radius: 3px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #6a6a6a;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 15px;
            background-color: #2a2a2a;
            subcontrol-origin: margin;
        }
        
        QScrollBar::add-line:vertical {
            subcontrol-position: bottom;
        }
        
        QScrollBar::sub-line:vertical {
            subcontrol-position: top;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background-color: #2a2a2a;
        }
        
        QScrollBar:horizontal {
            background-color: #2a2a2a;
            height: 14px;
            margin: 0 15px 0 15px;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #5a5a5a;
            min-width: 20px;
            border-radius: 3px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #6a6a6a;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 15px;
            background-color: #2a2a2a;
            subcontrol-origin: margin;
        }
        
        QScrollBar::add-line:horizontal {
            subcontrol-position: right;
        }
        
        QScrollBar::sub-line:horizontal {
            subcontrol-position: left;
        }
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background-color: #2a2a2a;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #3d3d3d;
            height: 8px;
            background-color: #2a2a2a;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background-color: #5a5a5a;
            border: 1px solid #5a5a5a;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #6a6a6a;
            border: 1px solid #6a6a6a;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #1a1a1a;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            padding: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #5a5a5a;
        }
        
        QComboBox {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            padding: 3px 18px 3px 3px;
            min-width: 6em;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #3d3d3d;
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        
        QComboBox::down-arrow {
            /* 移除引用外部资源的代码
            image: url(:/images/down-arrow.png);
            */
        }
        
        QComboBox QAbstractItemView {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            selection-background-color: #3d3d3d;
        }
        
        QCheckBox, QRadioButton {
            color: #ffffff;
            spacing: 5px;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
        
        QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
            border: 1px solid #5a5a5a;
            background-color: #2a2a2a;
        }
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            border: 1px solid #5a5a5a;
            background-color: #2a82da;
        }
        
        QGroupBox {
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 3px;
            margin-top: 6px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: #ffffff;
        }
    """)

def apply_light_style(app):
    """应用浅色现代风格样式到应用程序
    
    Args:
        app: QApplication 实例
    """
    # 使用Fusion风格
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # 使用默认浅色调色板
    app.setPalette(QApplication.style().standardPalette())
    
    # 添加现代风格的额外样式表
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            font-size: 10pt;
        }
        
        QPushButton {
            background-color: #f0f0f0;
            border: 1px solid #c0c0c0;
            border-radius: 4px;
            padding: 6px 16px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #b0b0b0;
        }
        
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
        
        QPushButton:disabled {
            background-color: #f5f5f5;
            color: #a0a0a0;
            border: 1px solid #d0d0d0;
        }
        
        QToolBar {
            background-color: #f5f5f5;
            border: none;
            spacing: 3px;
            padding: 3px;
        }
        
        QToolBar::handle {
            background-color: #e0e0e0;
        }
        
        QToolButton {
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: 2px;
            padding: 3px;
        }
        
        QToolButton:hover {
            background-color: #e0e0e0;
            border: 1px solid #d0d0d0;
        }
        
        QToolButton:pressed {
            background-color: #d0d0d0;
        }
        
        QDockWidget {
            border: 1px solid #c0c0c0;
        }
        
        QDockWidget::title {
            background-color: #f0f0f0;
            padding-left: 10px;
            padding-top: 4px;
            padding-bottom: 4px;
        }
        
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: #ffffff;
        }
        
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 6px 12px;
            border: 1px solid #c0c0c0;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #ffffff;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #e5e5e5;
        }
        
        QScrollBar:vertical {
            background-color: #f5f5f5;
            width: 14px;
            margin: 15px 0 15px 0;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #c0c0c0;
            min-height: 20px;
            border-radius: 3px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #a0a0a0;
        }
        
        QScrollBar:horizontal {
            background-color: #f5f5f5;
            height: 14px;
            margin: 0 15px 0 15px;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #c0c0c0;
            min-width: 20px;
            border-radius: 3px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #a0a0a0;
        }
        
        QSlider::groove:horizontal {
            border: 1px solid #c0c0c0;
            height: 8px;
            background-color: #f0f0f0;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background-color: #2a82da;
            border: 1px solid #2a82da;
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #1c72c8;
            border: 1px solid #1c72c8;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 3px;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 1px solid #2a82da;
        }
        
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            padding: 3px 18px 3px 3px;
            min-width: 6em;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: #c0c0c0;
            border-left-style: solid;
            border-top-right-radius: 3px;
            border-bottom-right-radius: 3px;
        }
        
        QGroupBox {
            border: 1px solid #c0c0c0;
            border-radius: 3px;
            margin-top: 6px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
        }
        
        QMenuBar {
            background-color: #f0f0f0;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QMenuBar::item {
            spacing: 3px;
            padding: 4px 10px;
            background: transparent;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background: #e0e0e0;
        }
        
        QMenuBar::item:pressed {
            background: #d0d0d0;
        }
        
        QMenu {
            background-color: #f5f5f5;
            border: 1px solid #c0c0c0;
            border-radius: 3px;
        }
        
        QMenu::item {
            padding: 6px, 20px, 6px, 20px;
            border-radius: 3px;
        }
        
        QMenu::item:selected {
            background-color: #e0e0e0;
        }
        
        QTreeView, QListView, QTableView {
            background-color: #ffffff;
            alternate-background-color: #f5f5f5;
            border: 1px solid #c0c0c0;
        }
        
        QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {
            background-color: #308cc6;
            color: #ffffff;
        }
        
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 4px;
            border: 1px solid #c0c0c0;
            border-top-left-radius: 3px;
            border-top-right-radius: 3px;
        }
    """)

def get_available_styles():
    """获取系统可用的样式列表"""
    return QStyleFactory.keys() 