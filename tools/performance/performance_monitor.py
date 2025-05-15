import time
from functools import wraps
from PyQt5.QtCore import QObject, pyqtSignal


class PerformanceMonitor(QObject):
    """性能监控器，用于跟踪和记录应用程序性能指标
    
    该类提供了一个简单的接口来监控应用程序的性能，包括FPS和各种操作的执行时间。
    支持自定义性能桩，可以轻松监控任何函数的执行时间。
    """
    
    # 性能数据更新信号
    data_updated = pyqtSignal(dict)
    
    def __init__(self):
        """初始化性能监控器"""
        super().__init__()
        
        # 性能指标
        self._metrics = {
            'fps': 0,
            'frame_time': 0,
            'custom_metrics': {}
        }
        
        # FPS计算
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps_update_interval = 1.0  # 1秒更新一次FPS
        
        # 自定义性能桩
        self._active_timers = {}
    
    def update_frame(self):
        """更新帧计数，计算FPS
        
        每次绘制帧时调用此方法
        """
        self._frame_count += 1
        current_time = time.time()
        elapsed = current_time - self._last_fps_time
        
        # 每秒更新一次FPS
        if elapsed >= self._fps_update_interval:
            self._metrics['fps'] = round(self._frame_count / elapsed, 1)
            self._metrics['frame_time'] = round(1000 * elapsed / self._frame_count, 2)
            self._frame_count = 0
            self._last_fps_time = current_time
            
            # 发送更新信号
            self.data_updated.emit(self.get_metrics())

        if self._metrics['fps'] < 10:
            with open('performance_log.txt', 'a') as f:
                f.write("-"*100 + "\n")

                f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
                f.write(f"FPS: {self._metrics['fps']}, Frame Time: {self._metrics['frame_time']}\n")
                f.write(f"Custom Metrics: {self._metrics['custom_metrics']}\n")
                
                f.write("-"*100 + "\n")

    def start_timer(self, name):
        """开始一个命名计时器
        
        Args:
            name: 计时器名称
        """
        self._active_timers[name] = time.time()
    
    def stop_timer(self, name):
        """停止一个命名计时器并记录结果
        
        Args:
            name: 计时器名称
        
        Returns:
            float: 计时器运行时间（毫秒）
        """
        if name in self._active_timers:
            elapsed = (time.time() - self._active_timers[name]) * 1000  # 转换为毫秒
            self._metrics['custom_metrics'][name] = round(elapsed, 2)
            del self._active_timers[name]
            
            # 发送更新信号
            self.data_updated.emit(self.get_metrics())
            return elapsed
        return 0
    
    def get_metrics(self):
        """获取当前所有性能指标
        
        Returns:
            dict: 性能指标字典
        """
        return self._metrics
    
    def monitor(self, name=None):
        """装饰器，用于监控函数执行时间
        
        Args:
            name: 性能指标名称，默认为函数名
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            metric_name = name or func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.start_timer(metric_name)
                result = func(*args, **kwargs)
                self.stop_timer(metric_name)
                return result
            
            return wrapper
        
        return decorator


# 创建全局性能监控器实例
StaticMonitor = PerformanceMonitor()


def monitor(name=None):
    """全局性能监控装饰器
    
    用法示例:
    @monitor()
    def my_function():
        pass
        
    @monitor("自定义名称")
    def another_function():
        pass
    
    Args:
        name: 性能指标名称，默认为函数名
        
    Returns:
        装饰器函数
    """
    return StaticMonitor.monitor(name) 