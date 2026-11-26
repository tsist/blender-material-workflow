# 按镜头检验辅助图分辨率

<!-- wiki-index: {"id":"MW-012","title":"按镜头检验辅助图分辨率","stage":"bake","material":"喷漆金属","effect":"凸缘磨损与凹处积尘","channel":"Edge、Cavity、PBR","symptom":"导出 2K 后边缘遮罩仍显粗糙","evidence":"independent","applies":"Blender 5.3.0；材质 PR #3 0f39fcf；Cycles CPU"} -->

## 任务

确认细节先丢在 Edge / Cavity 辅助图，还是丢在最终贴图、UV 或显示中。按目标镜头选择烘焙档，而不是只看交付 PNG 的宽高。

## 输入

同一白模、UV、配方、采样和相机；同一个最终 2048² 导出合同。只切换配方的 `mesh_map_size`：512 和 2048。

## 执行

1. 从同一白模各跑一次 `material procedural-run`。保存两份实际辅助 PNG、最终贴图、柔光和掠射光重建。
2. 把 512 辅助图按纹素中心线性放大，与原生 2048 图对照。在 UV 岛内部读同坐标，另外查岛边扩像素。
3. 对比相同镜头下的资产。如果差异只出现在贴图放大图里，继续用小图迭代；目标镜头或下游贴图确实读到细节再保留高档。

## 通过条件

两档的几何、UV 指纹、遮罩参数和最终分辨率相同；同时核对辅助图实际位深、最终通道受影响的区域和工时。确认哪些变化传到材质，哪些只是采样或接缝差异。

## 失败处理

改最终导出尺寸不等于重烘焙辅助遮罩。[位深不足](013-verify-helper-mask-depth.md)、采样噪点和岛边串色各自有独立的排查方法。当前固定 8 像素辅助图边距，512 和 2K 的 UV 占比不同；另用 [UV 扩边与 mip 检查](008-padding-mips.md) 验接缝。

## 证据

[双工具箱 A/B、复跑命令和截图](../labs/mesh-map-resolution-native.md)。商用行为参考：[Adobe Mesh Map Settings](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/baking/mesh-map-settings) 将辅助图尺寸、边距和抗锯齿分开设置。
