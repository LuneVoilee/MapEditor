# 地图编辑器

一个基于PyQt5的地图编辑器，用于创建和编辑各种地图元素，为一款规划中的4x类型小游戏做准备。

感谢claude-3.7-sonnet提供的全面中文注释

## 架构设计

地图编辑器采用经典的MVC(Model-View-Controller)架构：

- **Model**: 包含`Province`、`HeightMap`等数据模型类，定义在`models`目录
- **View**: 主要是`MapCanvasView`类，负责渲染和用户界面交互
- **Controller**: `MapController`类，处理所有业务逻辑和数据操作
