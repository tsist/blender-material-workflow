# 用缩图定位 UV 边缘渗色

<!-- wiki-index: {"id":"MW-008","title":"用缩图定位 UV 边缘渗色","stage":"bake","material":"通用","effect":"填充边距","channel":"Base Color、Roughness","symptom":"原尺寸正常，远处或缩图出现接缝","evidence":"single","applies":"线性算例；Blender 5.3.0 单件原生扩边与 CPU 缩图"} -->

适用：线性算例；Blender 5.3.0 单件原生扩边与 CPU 缩图。证据：单件复现（按所列范围）。

## 任务

分开排查纹理岛边外填充和岛间距。

## 输入

锁定 UV、原始分辨率与目标最小读图级别。选一处岛边、一个狭窄缝隙和两块邻接面。

## 执行

同一贴图原生烘零扩边、Extend 4/8/16 和 Adjacent Faces 4/8/16。保持原图、UV 与滤波一致，按同一条几何边取缝两侧样点，分别对照各面原值和两侧差；用排除空白和邻岛的同岛参照隔离正常低通。

## 通过条件

算例的原岛值为 1：无填充时缩图边缘读 0.5，填充后读 1。便携箱原生 2K 粗糙度盒滤到 512 档，Extend 三档在测试点相同；256 档加宽明显有效。先找目标尺度下最小有效宽度，再用实际占屏尺寸与掠射光复核。Adjacent Faces 可缩小两面差值的变化，同时使各面更偏离原值；两个指标分开看。

## 失败处理

边缘像素取到背景：增填充。取到别的岛：先增岛距或调整图集，再重测目标缩图。

## 证据

[实跑算例](../labs/texture-contract.md)；[Blender 5.3 Bake Margin](https://docs.blender.org/manual/en/5.3/render/cycles/baking.html)；[Painter Padding](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/technical-support/workflow-issues/export-issues/texture-dilation-or-padding)。 [同一工具箱实际切口与零扩边负对照](../labs/corner-seam-native.md)。

[原生七档扩边、同岛参照和正反图](../labs/uv-padding-native.md)。

[实际 Cycles 近景／整物换图对照](../labs/uv-padding-cycles-visual.md)：此缝在原生 2K 下两档 Extend 一样；只有显式低分辨率输入时，较宽的扩边才明显帮助近景。
