# 地图编辑器

一个基于PyQt5的地图编辑器，用于创建和编辑各种地图元素，为一款规划中的4x类型小游戏做准备。

感谢claude-3.7-sonnet提供的全面中文注释

## 更新报告

### 主要更改

1. **重构了`MapCanvas`类**：该类已被`MapController`和`MapCanvasView`取代，采用了更优的MVC架构。
   - `MapController`: 负责所有地图数据的处理和管理
   - `MapCanvasView`: 负责地图的视觉呈现和用户交互捕获

2. **更新历史记录系统**：
   - `map_state.py`文件已更新，移除所有对`MapCanvas`的引用
   - 现在使用`MapController`进行历史状态的存储和恢复

3. **改进笔刷系统**：
   - 修复了大陆笔刷绘制不连贯的问题
   - 优化了基于Qt的绘制方案，使用线性插值确保连续绘制

4. **优化绘制性能**：
   - 实现了基于栅格化坐标系的延迟处理方案
   - 分离了绘制和数据处理，减少卡顿
   - 改进了工具预览功能，使笔刷图标直接跟随鼠标移动

5. **完善代码注释**：
   - 更新所有主要类和方法的注释，提高代码可读性
   - 添加了参数和返回值的类型说明
   - 改进了复杂算法的说明文档

## 架构设计

地图编辑器采用经典的MVC(Model-View-Controller)架构：

- **Model**: 包含`Province`、`HeightMap`等数据模型类，定义在`models`目录
- **View**: 主要是`MapCanvasView`类，负责渲染和用户界面交互
- **Controller**: `MapController`类，处理所有业务逻辑和数据操作

### 文件结构

- `ui/`: 用户界面相关代码
  - `map_canvas_view.py`: 地图视图组件
  - `main_window.py`: 主窗口
  - `controllers/`: 控制器
  - `history/`: 历史记录管理
  - `styles/`: UI样式

- `tools/`: 工具实现
  - `brushes.py`: 笔刷工具
  - `generator.py`: 生成器工具
  - `land_divider.py`: 大陆分割工具

- `models/`: 数据模型
  - `province.py`: 省份模型
  - `heightmap.py`: 高程图模型
  - `texture.py`: 纹理模型
  - `geometry_utils.py`: 几何工具
