# 用缩图定位 UV 边缘渗色

<!-- wiki-index: {"id":"MW-008","title":"用缩图定位 UV 边缘渗色","stage":"bake","material":"通用","effect":"填充边距","channel":"Base Color、Roughness","symptom":"原尺寸正常，远处或缩图出现接缝","evidence":"single","applies":"线性采样算例；目标渲染器未复验"} -->

适用：线性采样算例；目标渲染器未复验。证据：单件复现（按所列范围）。

## 任务

分开排查纹理岛边外填充和岛间距。

## 输入

锁定 UV、原始分辨率与目标最小读图级别。选一处岛边、一个狭窄缝隙和两块邻接面。

## 执行

对照无填充和有填充输出；在相同滤波下看原图与缩图。Blender 的 Extend 延展边缘像素；Adjacent Faces 从 UV 缝两侧相邻面取样，按输入结构对照。

## 通过条件

算例的原岛值为 1：无填充时缩图边缘读 0.5，填充后读 1。真实资产用目标的缩图及掠射光通过；不采用通用固定像素数。

## 失败处理

边缘像素取到背景：增填充。取到别的岛：先增岛距或调整图集，再重测目标缩图。

## 证据

[实跑算例](../labs/texture-contract.md)；[Blender 5.3 Bake Margin](https://docs.blender.org/manual/en/5.3/render/cycles/baking.html)；[Painter Padding](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/technical-support/workflow-issues/export-issues/texture-dilation-or-padding)。
