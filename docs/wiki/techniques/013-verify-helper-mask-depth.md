# 验证辅助遮罩的实际位深

<!-- wiki-index: {"id":"MW-013","title":"验证辅助遮罩的实际位深","stage":"bake","material":"喷漆金属","effect":"层遮罩量化和阈值跳变","channel":"Edge、Cavity、Roughness","symptom":"16 位导出后遮罩仍有阶梯或跳变","evidence":"independent","applies":"Blender 5.3.0；材质 PR #3 0f39fcf 加隔离实验补丁；Cycles CPU"} -->

## 任务

找出精度是丢在烘焙缓冲、PNG 写盘还是下游采样。最终 PBR 贴图写成 16 位，不会补回辅助图已丢掉的精度。

## 输入

同一白模、UV、配方、尺寸、采样和扩边。准备现有 8 位路线与原生浮点缓冲、16 位 PNG 路线。记录 Blender 构建号和实际目标镜头。

## 执行

1. 重烘两档辅助图。按 PNG 的 IHDR 看每通道位深，按 Non-Color 重载，比对磁盘值和烘焙缓冲。读取 16 位像素时避免先转 RGB8。
2. 检查 16 位图是否仍只在 8 位网格上取值：8 位整数放到 16 位是乘 257。超出该网格说明保住了额外数值；同画像素重新另存 16 位不算重烘。
3. 比较程序层阈值附近、最终粗糙度和目标镜头。同机位看柔光与掠射光，放大图集仅用于定位。没有镜头收益时，保留 8 位工作档；必要时只升级受影响的辅助图。

## 通过条件

输入指纹一致，PNG 的位深和数值对得上，16 位磁盘重读与浮点缓冲最大误差不超过一个 16 位码值。画质升级另用目标镜头证明，不能用更多码值代替。

## 失败处理

缓冲已是 8 位重烘；重载数值偏移先查 Non-Color、写盘变换和抖动；同设置仍有较大随机差异先锁采样。硬切遮罩翻转多时，先检查临界输入与过渡宽度，再决定是否值得升位深。PNG 位深、采样噪点、UV 边距和贴图分辨率分别控制。

## 证据

[双工具箱原生对照、命令和截图](../labs/helper-mask-depth-native.md)。[PNG 规范](https://www.w3.org/TR/png-3/)定义容器位深；[Blender PNG 支持](https://docs.blender.org/manual/en/5.1/files/media/image_formats.html)与[Adobe 纹理集设置](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/interface/texture-set/texture-set-settings)分别说明格式能力与原始数据通道。
