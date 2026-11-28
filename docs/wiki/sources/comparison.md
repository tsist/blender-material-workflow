# 原始资料与取舍

核对日期：2026-11-26。下列商业能力查官方文档；开源项目查固定源码；本插件实测另见[基线](../labs/mask-baseline.md)。此处不做画质或性能排名。

| 来源 | 借鉴动作 | 用到的工艺 |
| --- | --- | --- |
| [Painter 遮罩与效果](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/interface/layer-stack/masking-and-effects)、[通道混合](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/interface/layer-stack/blending-modes) | 区分禁用通道与下层合成；独立查看灰度遮罩 | [粗糙度隔离](../techniques/001-grip-roughness.md) |
| [Mari 遮罩](https://learn.foundry.com/mari/content/user_guide/layers/add_layers_masks.html) | 把画笔目标与程序来源分开，不复制投影绘制界面 | [局部修正](../techniques/002-local-mask.md) |
| [Toolbag 烘焙](https://docs.marmoset.co/docs/setting-up-a-bake-project/) | 高低模投射独立检查 cage、偏斜、接缝 | [重建](../techniques/005-rebuild-pbr.md) |
| [Ucupaint 的遮罩实现](https://github.com/ucupumar/ucupaint/blob/9807cd716304aa1c26fa03ea56bc2da3ac0b981d/Mask.py) | 保留遮罩身份、通道状态、预览及生命周期；用像素断言加强旧测试 | GPL-3.0；不复制实现 |
| [ArmorPaint 的层对象](https://github.com/armory3d/armorpaint/blob/deac70436ea784308180071e576d1f8e66c57b74/paint/sources/slots/slot_layer.c) | 分开保存层、组、遮罩和撤销数据 | 根许可 zlib/libpng；不带其 GPU 依赖 |
| [Material Maker 的几何贴图](https://github.com/RodZill4/material-maker/blob/7d6daae3c74c09720afe4138ce09699ab3591ce1/addons/material_maker/engine/nodes/gen_meshmap.gd) | 换模型只替换几何信号；固定配方参数与随机种子 | 默认 MIT，例外另核；不引 Godot |
| [Adobe 剥漆实操](https://www.adobe.com/us/learn/substance-3d-painter/web/substance-painter-peeled-paint-effect)、[工具箱作者拆解](https://80.lv/articles/how-to-make-tool-kit-with-history-using-zbrush-substance-3d-painter) | 先学伤口如何驱动翘边与渗锈，再用自己的输入做正反例；前者是旧版界面，后者是作者经验 | [分开掉漆与锈](../techniques/003-chip-and-rust.md) |

补充三条设计对照：

- [Adobe Anchor Points](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/effects/anchor-point)：同纹理集里的显式引用有层序约束。我们先借鉴有标识的单向依赖，保留错序、错图层和循环反例，不做隐式跨纹理集查找。
- [Blender 5.3 Texture Paint](https://docs.blender.org/manual/en/5.3/sculpt_paint/texture_paint/introduction.html)：保存工程不能代替检查编辑图像是否实际保存或打包。先做好独立笔迹提交，再考虑图集复用。
- [Toolbag 投射工具](https://docs.marmoset.co/docs/projection-tools/)：投射偏移与偏斜按烘焙组控制，UV 改变要重新核对修正图。与 Blender 的投射命中见证分开记录。

只存原创测试与具备再分发许可的资产，逐件记录来源、许可、版本和摘要。代码许可与素材许可分开。不把商业教程附件或旧项目工程放进公开仓。

### 笔迹副本：结构相同，不等于数据独立

2026-11-28 源码定点复核。[Ucupaint 2.4.9 图层复制](https://github.com/ucupumar/ucupaint/blob/138cdfc74702f2f61c1f342dece26b8ff67a933b/Layer.py#L5413-L5540)先复制节点结构，再按外部图／打包图选项处理数据；外部图复制未启用时可沿用原图。处理图集与 UDIM 时还单独管理区段和映射；同批节点原来共用一幅普通图时，可共用一份新图。其[图像复制辅助函数](https://github.com/ucupumar/ucupaint/blob/138cdfc74702f2f61c1f342dece26b8ff67a933b/common.py#L7875-L7947)特意处理未提交的像素，说明不能只检查复制出的名称。这里只读源码，不运行、不引入 Ucupaint。
