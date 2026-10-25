# 程序化PBR公开验收套件

本套件直接验证仓库根目录的插件代码。`procedural_test_support.py`通过`importlib`将当前仓库挂为`material_workflow_addon`，不安装插件，不依赖私有工程目录或其他已安装副本。

先准备Python和已有的Blender可执行文件；套件不会下载/安装依赖。已验证运行时为Blender 5.2.1 LTS，后台测试需要Blender附带的bpy、NumPy及OpenImageIO能力。合同测试仅需标准Python库。

`--output`必须是绝对路径且尚不存在。每次使用新的目录；已有文件/目录会被拒绝。测试产物和日志都位于显式输出目录，测试入口禁写源码字节码缓存。请将产物目录放在仓库外。

## 全套运行

从任意目录执行以下命令，将占位符替换为实际绝对路径：

```text
python <checkout>/tests/procedural_runner.py --blender <absolute-blender-executable> --output <absolute-new-output-directory>
```

默认依次执行contract、signals、core、ui、mesh_maps、bake、examples、regressions、optics。每个Blender案例都由独立子进程以`--background --factory-startup --python-exit-code 1`启动。examples和optics之后还会在另一个进程独立重开fixture。

顶层`suite.json`记录命令、退出码、耗时和逐项日志。失败保留所有已产生证据并返回非0，不删除或跳过失败断言；单进程默认超时300秒，可用`--timeout 10..3600`调整。

只运行host合同：

```text
python <checkout>/tests/procedural_runner.py --cases contract --output <absolute-new-output-directory>
```

只运行指定案例：

```text
python <checkout>/tests/procedural_runner.py --cases core ui mesh_maps bake --blender <absolute-blender-executable> --output <absolute-new-output-directory>
```

单独运行一个Blender案例时也需要显式新目录：

```text
<blender> --background --factory-startup --python-exit-code 1 --python <checkout>/tests/procedural_mesh_maps.py -- --output <absolute-new-output-directory>
```

测试入口检查`bpy.app.background`，拒绝在可见用户GUI中执行。fixture创建、重置或载入只发生在该测试自己的后台进程中。

## 覆盖范围

| 案例 | 核心验证 |
|---|---|
| contract | 完整manifest2.0合同测试；信号DAG、类型、有限数值/界限、通道、资源身份、旧合同不变 |
| signals | VECTOR/DAG、独立纹理/坐标Scale、Color warp、下游mapping、Voronoi双引擎、remap、float32闭包；host与native均执行并独立进程重开 |
| core | 真正构图、根控制编辑/冲突、模板保存、128贴图导出、作者与贴图重建blend独立重开 |
| ui | 实际注册/反注册与operator；创建/更新/JSON重绑、实际socket参数、128全通道导出与材质库、错误保护 |
| mesh_maps | 低密倒角立方体/L形/尺度变化、全对象跨槽UV与求值UV拒绝、局部AO隔离、磁盘解码、源状态恢复 |
| bake | 全通道数值/色彩/IOR编码与重建解码、signed Height、切线Normal、跨槽隔离、失败partial与恢复、UV拒绝、Bevel |
| examples | 五类模板与自造油桶/桌/厚壁玻璃14部件；UV裁剪重叠检查、128预览、三blend独立重开 |
| regressions | 浮点0→.5、同值合并/重叠冲突、Fake User、错误group名称、图像/坐标指针篡改、失败清理、双引擎验证路径、重复四视图真实渲染与原始Material ID生命周期 |
| optics | 无surface旧配方/旧形状snapshot、SPHERE/SLAB与AUTO/显式0/正厚度保存及独立进程重开、手改mode/link保护、32贴图bake/rebuild保留厚度、未知动态Thickness拒绝 |

公开案例保留原验收的有效断言；路径、引导及输出路由改为仓库布局和显式`--output`。回归案例保留程序后端测试，不携带私有旧测试脚本的启动路径。

## 结果边界

- 这些是功能/保护与小型图像数值验收，不证明所有资产、2K性能或生产级美术质量。
- engine兼容路径通过不等于Cycles/Eevee画面完全相同；可见GUI布局与鼠标体验不在后台套件验收内。
- 双预览材质ID回归可验证引用生命周期和有限重复渲染，不证明所有驱动/内存情况下的间歇性崩溃已经消除。
- fixture UV是测试自行制作并检查的准备步骤，不是插件自动UV能力。
- 测试不连接真实用户GUI，不对网络、插件安装或全局偏好进行操作。

## 信号与float32闭包

`signals`包含host合同、后台节点/小图机制和独立进程重开。仅host可执行`python <checkout>/tests/procedural_signals.py --host --output <absolute-new-directory>`。每个阶段输出独立目录。

旧未发布2.0 Noise/Wood Scale碰撞图只读诊断后用新material ID重建，不将旧图当新视觉基线。float32端点可往返；溢出、非零下溢和转换后相等的remap源界在建图前拒绝。新强度/映射范围与艺术适用性需分别验证。本套件仍不代替2K或最终美术验收。
