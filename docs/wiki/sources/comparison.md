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

只存原创测试与具备再分发许可的资产，逐件记录来源、许可、版本和摘要。代码许可与素材许可分开。不把商业教程附件或旧项目工程放进公开仓。
