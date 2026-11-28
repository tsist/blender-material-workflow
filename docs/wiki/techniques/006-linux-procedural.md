# 区分 CLI 能发现与事务能执行

<!-- wiki-index: {"id":"MW-006","title":"区分 CLI 能发现与事务能执行","stage":"mask","material":"通用","effect":"Linux 入口","channel":"全部","symptom":"有命令但材质事务不启动","evidence":"single","applies":"Linux；CLI 0.64.0 PR #2"} -->

适用：Linux；CLI 0.64.0 PR #2。证据：单件复现（按所列范围）。

## 任务

核对 Linux CLI 是否真正进入材质创建和导出。

## 输入

Blender 5.3.0，CLI 4046c7a，独立输入文件和作业目录，记录 SHA-256。

## 执行

先用 `material describe --operation procedural-run --schema` 核对合同。再提交 `material procedural-run` 和 `material procedural-export` 的合法小样，记录作业编号与终态。

## 通过条件

两条作业实际产出，导出贴图可独立重开。帮助文本只是命令发现。

## 失败处理

若返回 `Transactions currently require Windows`，记录 CLI 事务阻断；不要改贴图或改渲染器试错。

## 证据

已在 Linux 复现两条失败；修复未复验。[CLI PR #2](https://github.com/tsist/blenderctl/pull/2)。
