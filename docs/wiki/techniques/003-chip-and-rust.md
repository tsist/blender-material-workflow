# 分离掉漆、露钢和锈蚀

<!-- wiki-index: {"id":"MW-003","title":"分离掉漆、露钢和锈蚀","stage":"weathering","material":"喷漆钢","effect":"掉漆和锈蚀","channel":"Metallic、Roughness","symptom":"每处掉漆都长出同样的锈","evidence":"single","applies":"0.9.2 配方基线；新配方未复验"} -->

适用：0.9.2 配方基线；新配方未复验。证据：单件复现（按所列范围）。

## 任务

给掉漆和氧化独立控制。

## 输入

凸缘、凹槽、完好面、新鲜划伤、一处积水；统一模型单位。

## 执行

查基线的掉漆与氧化信号。分开漆、底漆、露钢；在露钢与滞湿条件上派生氧化，再从可积水边沿重力加水迹。

## 通过条件

新鲜伤口可露钢但无锈；完好面保持漆；水迹向下；氧化层不照用裸钢金属度。切换第二形体验证位置。

## 失败处理

两遮罩同源同阈值：把氧化条件从损伤阈值拆开；不要把相同遮罩改个名字当新工艺。

## 证据

基线合同复现同掩膜；新配方未复验。[对照命令](../labs/mask-baseline.md)；[剥漆教程](https://www.adobe.com/us/learn/substance-3d-painter/web/substance-painter-peeled-paint-effect)。
