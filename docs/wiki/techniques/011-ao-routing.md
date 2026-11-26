# 把 AO 辅助遮罩与交付 AO 分开

<!-- wiki-index: {"id":"MW-011","title":"把 AO 辅助遮罩与交付 AO 分开","stage":"export","material":"通用","effect":"AO 路由","channel":"AO、Base Color","symptom":"程序导出拒绝 AO 通道","evidence":"single","applies":"Material Workflow 0.9.2 主机合同；投射未复验"} -->

适用：Material Workflow 0.9.2。证据：单件复现（程序导出合同）。

## 任务

选择 AO 的用途和路径：做旧遮罩或交付图。

## 输入

定义目标槽、接收模型和 UV；投射另给相互独立的源高模、射线距离和 AO 距离。

## 执行

程序图的 cavity 使用局部 AO 的反向作为凹区信号。用它控制积尘，不把它冒充交付 AO。需要独立 AO 时走高低模投射流程；0.9.2 的投射在命中源表面采样局部 AO。烘焙并在预览保留 AO 独立通道。

## 通过条件

程序导出可同时声明 Normal 和 Height，直接声明 AO 则拒绝。投射试样中原底色保持不变、AO 未反相成 cavity；输出灰度在见光平面比遮挡槽高。投射试样未复验。

## 失败处理

程序导出拒绝 AO：换正确路线，不重命名其他图顶替。模型之间的接触阴影不是当前仅采源表面的局部 AO，另设参考检验。

## 证据

[合同探针](../labs/texture-contract.md)；[0.9.2 投射](https://github.com/tsist/blender-material-workflow/blob/9d560ee71fa9ece6dab007f2159541823eb9c093/projection_bake.py#L195)；[Khronos AO 语义](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materials)。
