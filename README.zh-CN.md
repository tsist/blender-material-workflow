# Material Workflow 材质插件

**插件 0.7.1 · 配套技能包 0.2.1 · GPL-3.0-or-later**

本仓库独立维护 Blender 材质插件、材质制作技能及其配套指导。插件保留可编辑分层 PBR、模板、明确对象/材质槽/面区分配、增量冲突保护及诊断预览。blenderctl 独立负责后台调度、文件身份保护和作业恢复。

## 安装插件和技能

从[同一 Release](https://github.com/tsist/blender-material-workflow/releases/tag/v0.7.1)下载：

- `material-workflow-0.7.1.zip`：在 Blender 的「偏好设置 → 扩展 → 从磁盘安装」安装并启用；视图侧栏打开 Material Workflow。
- `material-workflow-skills-0.2.1.zip`：解压后运行 `python install_skills.py --destination '<实际技能目录绝对路径>'`。四个技能保持同级安装；已有同名技能会整体拒绝复制，先比较再迁移。
- `material-workflow-0.7.1-source.zip`：完整开发源码。

插件清单最低版本为 Blender 5.2.0，实际基线是 Windows / Blender 5.2.1 LTS。普通材质草稿编辑与模板可单独使用插件；后台快照提交、CLI 批量、参数研究和恢复需要另行安装 [blenderctl](https://github.com/tsist/blenderctl)。

## 后台配置与拆分

插件中的「blenderctl 后端源码目录」和技能的 `BLENDERCTL_ROOT` 都指向另行安装的 blenderctl 源码根，而非本仓库。首次克隆用 `git clone --recurse-submodules https://github.com/tsist/blenderctl.git`；已有克隆更新后执行 `git submodule update --init --recursive`。

blenderctl 0.54.2 通过固定提交的 Git 子模块消费本插件，不再在自身维护第二份核心。CLI 自建源码发行包包含该依赖；GitHub 自动生成的源码 ZIP 不包含子模块。历史 0.54.1/0.7.0 发行保持原状。新旧实现身份不同，不复用旧检查点冒充新版本验证。

配套包包含材质制作、工作方法论、CLI 操作和资产管理四个技能，用于保持原有交叉引用；它们不自动安装 Blender、生成器、Pillow、MCP 或记忆插件，也不继承私人服务授权。

使用前保留已有 UV、静态图层、源文件和持久快照；预览成功不替代审美验收。自动通用 UV、UDIM/动态图层、DLSS 和自动审美选优仍不在范围内。

参见[工作流说明](docs/MATERIAL_WORKFLOW.md)、[技能安装](skills/README.md)、[迁移与维护](docs/MIGRATION.md)、[发布验证](docs/RELEASE_VERIFICATION.md)。
