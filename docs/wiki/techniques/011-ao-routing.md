# 把 AO 辅助遮罩与交付 AO 分开

<!-- wiki-index: {"id":"MW-011","title":"把 AO 辅助遮罩与交付 AO 分开","stage":"export","material":"通用","effect":"AO 路由","channel":"AO、Base Color","symptom":"程序导出拒绝 AO 通道","evidence":"single","applies":"Material Workflow 0.9.2；Blender 5.3.0 Cycles CPU 三岛合成试样"} -->

适用：Material Workflow 0.9.2。证据：单件复现（程序导出合同、原生三岛投射）。

## 任务

选择 AO 的用途和路径：做旧遮罩或交付图。

## 输入

定义目标槽、接收模型和 UV；投射另给相互独立的源高模、射线距离和 AO 距离。用单槽接收体：Principled 直接连到适用全部引擎的唯一活动输出，Principled 的 Normal 不接线。

## 执行

程序图的 cavity 使用局部 AO 的反向作为凹区信号。用它控制积尘，不把它冒充交付 AO。需要独立 AO 时走高低模投射流程；0.9.2 的投射在命中源表面采样局部 AO。烘焙并在预览保留 AO 独立通道。

## 通过条件

程序导出可同时声明 Normal 和 Height，直接声明 AO 则拒绝。投射验收：先确认开阔平面和同一高模上的凹槽都命中，再比较 AO 灰度；平面比凹槽亮；正式导出 AO 后另核对 Base Color 未混入 AO。96 个纹素从全部命中变为全部漏射，AO 仍为 65,535；详见[原生试样和实测值](../labs/texture-contract.md#原生-ao-投射验收)保留局部命中证据。

## 失败处理

投射绑定报 Normal 已连接：不要断开正式材质的 Bump。用单独接收体跑投射试样；原材质的法线组合另验。程序导出拒绝 AO：换正确路线，不重命名其他图顶替。白色 AO 既可能是无遮挡，也可能是投射漏射后的中性填充。总命中率不能确认某个凹槽命中；在该区域核对命中图。排查射线距离时先记录 Cage 模式：0.9.2 的非零 Extrusion 会启用 Cage；Blender 的 Max Ray Distance 属于无 Cage 的设置。跨物件接触阴影另设试样。

## 证据

[合同探针](../labs/texture-contract.md)；[0.9.2 投射](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/projection_bake.py#L195)；[漏射填充与汇总](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/projection_bake.py#L234)；[Blender 5.3 投射设置](https://docs.blender.org/manual/en/5.3/render/cycles/baking.html#selected-to-active)；[材质槽前置检查](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/projection_material.py#L141)；[Khronos AO 语义](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materials)。
