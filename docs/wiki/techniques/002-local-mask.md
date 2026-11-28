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

普通输入图变化应触发受管冲突；不要关闭图快照核验。把局部数据接入专用提交路径。保存 .blend 和提交图像分开验；提交后绑定新摘要，保持其他普通受管图的完整性检查。

## 证据

已验证预制加减图在两件工具箱上保存、冷开、改参和导出。Blender 画笔录入与保存待验，参照[原生图像保存说明](https://docs.blender.org/manual/en/5.3/sculpt_paint/texture_paint/introduction.html)和[画笔提交规格](../research-handoff.md#画笔提交的最小规格)。[0.9.2 图像快照](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/procedural_core.py#L52)。

### 复制后验收写入范围

区分「独立副本」和「显式共享」。复制后两张图像素可完全相同，像素摘要只能证明内容相同，不能证明编辑目标独立。放两个初始相同的遮罩，一个连两层，另一个独立；只改一笔。独立副本的写入只能影响自己的目标；显式共享只能影响登记的消费层。共享之外全部像素不变。保存或打包后重开，重测两次，不能只凭节点名和文件名通过。

[最小探针](../labs/evidence/mask-identity/probe.py)（仓根执行 `python docs/wiki/labs/evidence/mask-identity/probe.py`）以假图像运行已固定提交的本插件签名函数。同尺寸、同色彩空间和像素的独立对象与共享对象初始签名相同；同一对象改像素时两引用同时变化，独立对象不变。此探针只验证签名口径；未实测 Blender 画笔、撤回或冷开。
