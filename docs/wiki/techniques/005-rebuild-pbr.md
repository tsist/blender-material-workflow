# 从贴图重建时保持颜色空间与切线

<!-- wiki-index: {"id":"MW-005","title":"从贴图重建时保持颜色空间与切线","stage":"export","material":"通用","effect":"纯贴图重建","channel":"Base Color、Normal、AO","symptom":"重建变灰或镜像 UV 凹凸反转","evidence":"source","applies":"贴图契约；Blender 对照未复验"} -->

适用：贴图契约；Blender 对照未复验。证据：来源已核。

## 任务

在干净 Blender 工程仅用导出贴图重建材质。

## 输入

相同 UV、材质槽、贴图分辨率、切线手性和灯光。单列切线法线、粗糙度、金属度；AO 和高度按配方提供。

## 执行

底色用 sRGB；标量及法线用 Non-Color。记录法线绿色轴；同几何、机位和灯光比较原配方与重建，检查镜像接缝和掠射高光。

## 通过条件

8-bit 127 灰作为底色线性约 0.212231，线性标量约 0.498039。AO 不乘进底色；法线已含高低时不重复叠加同一高度。

## 失败处理

方向错先核切线、绿色轴和固定三角化，再调节点强度。保留可编辑四边面原件。详见[镜像与切线排故](009-mirror-tangents.md)和[搬运后摘要校验](010-relocate-bake.md)。

## 证据

[glTF 材质定义](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materials)；[MikkTSpace](https://github.com/mmikk/MikkTSpace/blob/3e895b49d05ea07e4c2133156cfa94369e19e409/mikktspace.h)；[算例](../labs/mask-baseline.md)。
