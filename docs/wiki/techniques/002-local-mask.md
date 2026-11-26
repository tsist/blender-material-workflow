# 分开保存程序遮罩与手工加减

<!-- wiki-index: {"id":"MW-002","title":"分开保存程序遮罩与手工加减","stage":"mask","material":"通用","effect":"遮罩修正","channel":"Mask","symptom":"重算覆盖手工笔迹","evidence":"single","applies":"Material PR 3；Blender 5.3.0"} -->

适用：Material PR 3；Blender 5.3.0。证据：单件复现级，覆盖同一环境两种箱体。

## 任务

把手工加、减数据与程序遮罩分开提交。

## 输入

程序灰度、加笔、减笔和相同 UV。选程序为 0、为 1、未绘制三处。

## 执行

用独立 Non-Color 加图 A 和减图 E 组合 `max(P,A) × (1-E)`。冷开后只改程序权重 P，再导出及重建；步骤见[双工具箱原生验证](../labs/toolbox-native.md)。

## 通过条件

加区保留增强、减区保留擦除、无笔迹区跟随程序。独立导出与原图一致；只改 Roughness 时 Base Color 和 Metallic 保持同一 SHA。

## 失败处理

普通输入图变化应触发受管冲突；不要关闭图快照核验。将局部数据接入专用提交路径。

## 证据

已验证预制加减图在两件工具箱上保存、冷开、改参和导出。Blender 画笔录入与保存待验。[0.9.2 图像快照](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/procedural_core.py#L52)。
