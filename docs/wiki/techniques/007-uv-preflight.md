# 烘焙前查目标槽 UV

<!-- wiki-index: {"id":"MW-007","title":"烘焙前查目标槽 UV","stage":"bake","material":"通用","effect":"UV 覆盖","channel":"UV","symptom":"烘焙报重叠或 UV 越界","evidence":"single","applies":"Material Workflow 0.9.2 主机合同"} -->

适用：Material Workflow 0.9.2 主机合同。证据：单件复现（按所列范围）。

## 任务

确定目标槽的 UV 是否能通过插件烘焙校验。

## 输入

指定目标材质槽、UV 层；保留未应用的源模型。

## 执行

运行[主机正反例](../labs/texture-contract.md)。目标工作副本先查一张 0–1 UV；分开镜像岛；确认重叠是否发生在同一目标槽。

## 通过条件

共享边与不叠合的镜像岛允许。同目标槽正面积叠合、越界、一般退化 UV 拒绝；非目标槽不参与本次判定。

## 失败处理

报正面积重叠时分开目标槽叠岛；缺层时指定有效 UV。共享边通过不等于边距通过，另做 [缩图检查](008-padding-mips.md)。

## 证据

六组结果与脚本见[复验](../labs/texture-contract.md)。主机调用真实合同函数，未执行 Blender 烘焙。
