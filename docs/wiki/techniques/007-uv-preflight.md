# 烘焙前查目标槽 UV

<!-- wiki-index: {"id":"MW-007","title":"烘焙前查目标槽 UV","stage":"bake","material":"通用","effect":"UV 覆盖","channel":"UV","symptom":"烘焙报重叠或 UV 越界","evidence":"single","applies":"Material Workflow 0.9.2 主机合同"} -->

适用：Material Workflow 0.9.2 主机合同。证据：单件复现（按所列范围）。

## 任务

确定目标槽的 UV 是否能通过插件烘焙校验。

## 输入

指定目标材质槽、UV 层；保留未应用的源模型。

## 执行

运行[主机正反例](../labs/texture-contract.md)。目标工作副本先查一张 0–1 UV；分开镜像岛；先确定命令验的是目标槽还是整件。

## 通过条件

共享边与不叠合的镜像岛允许。同目标槽正面积叠合、越界、一般退化 UV 拒绝；纯 PBR 通道导出按目标材质判定；程序 Edge/Cavity 辅助图生成查整件源和求值几何，跨槽重叠也算。

## 失败处理

报正面积重叠时按校验范围拆叠岛；已绑定局部遮罩的工程保留旧 UV 或迁移遮罩。缺层时指定有效 UV。共享边通过不等于边距通过，另做 [缩图检查](008-padding-mips.md)。

## 证据

六组结果与脚本见[复验](../labs/texture-contract.md)。主机六组正反例之外，[双工具箱 Cycles 烘焙](../labs/toolbox-native.md)验证了整件源／求值 UV 的两个无叠合正例；跨槽重叠的 Blender 负对照尚未执行。
