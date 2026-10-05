# Material Workflow 材质插件独立仓库

本次仅拆分 GitHub 仓库，便于单独管理插件和配套技能。**插件保持 0.7.0，技能保持 0.2.0，blenderctl 保持 0.54.1**；运行代码、接口、依赖方式和技能正文均保持原样。

[同一发布页](https://github.com/tsist/blender-material-workflow/releases/tag/v0.7.0)提供插件安装包、完整四技能包、独立仓库源码和校验文件。

原 blenderctl 仓库继续保留原来的代码目录，直接克隆即可，不需要子模块。新仓库用于单独维护 GitHub 发布；插件后台提交仍填写原 blenderctl 源码根，`BLENDERCTL_ROOT` 仍指向原 CLI 源码。

插件运行模块、manifest 及全部技能文件从原公开提交 `fbb76afa5da7e8577f366738b6ca5e392e6c3853` 原样复制并逐文件校验。插件 ZIP 与此前发布包完全一致；技能 ZIP 由原有配套发行流程重建，内容与版本不变。个人安装和生产文件未修改。

下载 `material-workflow-0.7.0.zip` 后在 Blender「偏好设置 → 扩展 → 从磁盘安装」安装。技能包 `blender-skills-0.2.0.zip` 解压后运行 `python install_skills.py --destination '<实际技能目录绝对路径>'`；已有同名技能会拒绝复制。

之前扩大范围的子模块改造与升版已撤回，0.7.1/CLI0.54.2误发版保留为草稿记录。参见[仓库拆分边界](docs/MIGRATION.md)。
