from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QSizePolicy, QGraphicsDropShadowEffect, QShortcut,
                           QDockWidget)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPalette, QKeySequence

from tools.performance.performance_monitor import StaticMonitor


class PerformanceWidget(QDockWidget):
    """性能监控窗口
    
    显示FPS、帧时间和自定义性能指标的窗口。
    作为主窗口的一部分，支持快捷键切换显示。
    """
    
    # 关闭信号
    closed = pyqtSignal()
    
    def __init__(self, name,parent=None):
        """初始化性能监控窗口
        
        Args:
            parent: 父窗口部件
        """
        super().__init__(name,parent)
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(250)
        
        # 初始化UI
        self._init_ui()
        
        # 连接性能监控器信号
        StaticMonitor.data_updated.connect(self._update_metrics)
    
    def _init_ui(self):
        """初始化UI组件"""
        # 创建内容部件
        content_widget = QWidget()
        self.setWidget(content_widget)
        
        # 主布局
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        close_button = QPushButton("×")
        close_button.setFixedSize(16, 16)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FF0000;
            }
        """)
        close_button.clicked.connect(self.hide)
        close_button.clicked.connect(self.closed.emit)

        
        # 分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        separator.setStyleSheet("background-color: #555555;")
        main_layout.addWidget(separator)
        
        # 自定义指标容器
        self.custom_metrics_layout = QVBoxLayout()
        self.custom_metrics_layout.setContentsMargins(0, 5, 0, 0)
        self.custom_metrics_layout.setSpacing(3)

        # FPS显示
        self.fps_label = QLabel("FPS: 0")
        self.custom_metrics_layout.addWidget(self.fps_label)
        
        # 帧时间显示
        self.frame_time_label = QLabel("帧时间: 0 ms")
        self.custom_metrics_layout.addWidget(self.frame_time_label)
        

        main_layout.addLayout(self.custom_metrics_layout)
        
        # 自定义指标标签字典
        self.custom_metric_labels = {}

        self.setWidget(content_widget)
    

    
    def toggle_visibility(self):
        """切换窗口显示/隐藏状态"""
        self.setVisible(not self.isVisible())
    
    def _update_metrics(self, metrics):
        """更新性能指标显示
        
        Args:
            metrics: 性能指标字典
        """
        # 更新FPS
        self.fps_label.setText(f"FPS: {metrics['fps']}")
        
        # 更新帧时间
        self.frame_time_label.setText(f"帧时间: {metrics['frame_time']} ms")
        
        # 更新自定义指标
        custom_metrics = metrics.get('custom_metrics', {})
        
        # 添加或更新自定义指标标签
        for name, value in custom_metrics.items():
            if name not in self.custom_metric_labels:
                # 创建新标签
                label = QLabel(f"{name}: {value} ms")
                self.custom_metrics_layout.addWidget(label)
                self.custom_metric_labels[name] = label
            else:
                # 更新现有标签
                self.custom_metric_labels[name].setText(f"{name}: {value} ms") 