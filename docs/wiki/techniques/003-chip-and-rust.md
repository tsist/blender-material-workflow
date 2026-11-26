# 分离掉漆、露钢和锈蚀

<!-- wiki-index: {"id":"MW-003","title":"分离掉漆、露钢和锈蚀","stage":"weathering","material":"喷漆钢","effect":"掉漆和锈蚀","channel":"Metallic、Roughness","symptom":"每处掉漆都长出同样的锈","evidence":"single","applies":"Material PR 3；Blender 5.3.0 双箱"} -->

适用：Material PR 3；Blender 5.3.0 双箱。证据：单件复现（按所列范围）。

## 任务

给掉漆和氧化独立控制。

## 输入

凸缘、凹槽、完好面、新鲜划伤、一处积水；统一模型单位。

## 执行

用两段阈值分出掉漆与露钢，再令氧化 = 露钢 × 潮湿 × 强度。水迹用独立强度和明确坐标系。[消融和命令](../labs/weathering-native.md)。

## 通过条件

所有覆盖像素满足氧化 ≤ 露钢 ≤ 掉漆，存在露钢少锈和仅底漆区。分别关闭氧化、水迹，非目标遮罩 SHA 不变。仿重力另验坐标；物体局部方向不等于世界方向。

## 失败处理

两遮罩同源同阈值：把氧化条件从损伤阈值拆开；不要把相同遮罩改个名字当新工艺。

## 证据

基线合同复现同掩膜；新版做法通过两箱原生消融、局部轴旋转和 512² 出图。此证据不代表独立质量复验或智能材质定稿。[对照命令](../labs/mask-baseline.md)；[剥漆教程](https://www.adobe.com/us/learn/substance-3d-painter/web/substance-painter-peeled-paint-effect)。
