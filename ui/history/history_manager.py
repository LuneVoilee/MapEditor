import copy
import numpy as np

class HistoryManager:
    """历史记录管理器，负责管理地图编辑器的撤销和重做功能"""
    
    def __init__(self, max_history=50):
        self.history = []  # 历史记录列表
        self.current_index = -1  # 当前历史记录索引
        self.max_history = max_history  # 最大历史记录数量
    
    def add_state(self, state):
        """添加一个新的状态到历史记录
        
        Args:
            state: 要保存的地图状态（需要深拷贝）
        """
        # 如果当前不在历史记录的末尾，则删除当前索引之后的所有记录
        if self.current_index < len(self.history) - 1:
            self.history = self.history[:self.current_index + 1]
        
        # 添加新状态（深拷贝）
        self.history.append(copy.deepcopy(state))
        
        # 如果历史记录超过最大限制，删除最早的记录
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # 更新当前索引
        self.current_index = len(self.history) - 1
    
    def can_undo(self):
        """检查是否可以撤销操作"""
        return self.current_index > 0
    
    def can_redo(self):
        """检查是否可以重做操作"""
        return self.current_index < len(self.history) - 1
    
    def undo(self):
        """撤销操作，返回前一个状态"""
        if not self.can_undo():
            return None
        
        self.current_index -= 1
        return self.history[self.current_index]
    
    def redo(self):
        """重做操作，返回下一个状态"""
        if not self.can_redo():
            return None
        
        self.current_index += 1
        return self.history[self.current_index]
    
    def clear(self):
        """清空历史记录"""
        self.history = []
        self.current_index = -1 