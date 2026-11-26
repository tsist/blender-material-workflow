# 按几何位置分配旧化信号

<!-- wiki-index: {"id":"MW-004","title":"按几何位置分配旧化信号","stage":"bake","material":"通用","effect":"凸缘与凹槽","channel":"Mesh Maps","symptom":"磨损与积尘铺满表面","evidence":"source","applies":"0.9.2 辅助图；双箱未复验"} -->

适用：0.9.2 辅助图；双箱未复验。证据：来源已核。

## 任务

让旧化位置由实际凸缘、凹槽与接触区域决定。

## 输入

记录模型单位、方向、UV、倒角、凸／凹／鞍面三处对照。

## 执行

分别输出 edge、cavity 灰度。检查凸缘和凹槽；把接触区作为独立输入。水迹方向以重力为准，不从随机噪声推断。

## 通过条件

凸缘与凹槽可隔离；干净平面不统一蒙灰；换模型后用新几何重算。

## 失败处理

edge 不是带符号曲率，cavity 只取对象内。需要接触阴影时另记录环境，不能拿当前 cavity 代替。

## 证据

[0.9.2 辅助图实现](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/procedural_mesh_maps.py)；[Adobe Dirt](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/effects/generators/dirt)。
