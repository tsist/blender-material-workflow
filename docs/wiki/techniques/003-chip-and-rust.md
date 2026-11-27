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

源点与尾迹也分开：原地氧化受露钢限制，流痕沉积可以越过完好漆面。验证时只改流痕方向或长度，保护原地锈、露钢与流痕起点不变。分别读遮罩，不从最终颜色反推。[两份 Material Maker 源图与端口检查](../labs/weathering-native.md#material-maker-源图先查斑点和流痕有没有独立出口)。

薄层流痕只写颜色和粗糙度时，显式设置 `affects: ["base_color", "roughness"]`。省略该字段不是继承：实测颜色、粗糙度都没变，高度仍误改 219 个纹素。[方向与漏写通道的正反对照](../labs/weathering-native.md#r24单向沉积层必须显式限制写入通道)。
