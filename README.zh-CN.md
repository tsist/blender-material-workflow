# Material Workflow 材质插件

**本地候选：插件0.8.0、技能包0.3.0（材质指导0.7.0）、配套CLI0.64.0。** 许可证GPL-3.0-or-later。

[英文说明](README.md) · [技能安装](skills/README.md) · [扩展指南](docs/EXTENSION_README.md) · [候选范围](docs/EXTENSION_README.md)

候选在既有静态图像分层v1/v2旁新增程序化/混合PBR的2.0合同。15类有类型信号支持统一坐标、域扭曲、Noise、Wave木纹、Voronoi与重映射；木轴和局部XYZ采样倍率由调用者明确指定，旧化按区域分布且保留零旧化对照。常量、图像、程序化或混合按需求选择，没有生图工具也可完成适合程序化的目标。

同时保留可编辑author和仅磁盘贴图重建：真实Cycles逐通道烘焙、sRGB基色、Non-Color数据、IOR编码、有符号Height EXR及切线Normal，重建避免重复Bump。核对源/资源SHA、非目标保护、受管手改冲突、磁盘读回和保存重开。需要既有UV，不提供自动UV、体积吸收、真实几何置换或任意节点图接管；Eevee玻璃差异单列。

限定案例的文件阶段制作与观察已完成：14个材质目标、126张必要2K通道通过独立完整像素与磁盘重建检查；主线程实际看过30张双引擎/换光最终图及12张局部补图，共42张，包含油桶真实上肩和顶盖边缘。DeepSeek真实完成制作/修正、2K导出、重建与最终有限看图；主线程介入过木纹mix、油桶图层和玻璃厚度诊断，所以属于有协助复用，不是无协助盲测或完整无人值守。2K微孔/细线变软、Eevee玻璃近似及逐对conditional结论仍保留。

解压后的build-a通过15个技术阶段，包括73项host用例（2项可选Pillow用例跳过）、本轮contract/core/bake/optics及独立重开、公共CLI128×128九图surface往返及全像素最大误差0、25成员扩展的隔离安装/旧接口/surface保存和独立重开。这仅验证已测build-a代码与字节；最终文档更新后仍须重封包和最终检查，不预填后续包通过。私有案例与审计不随包公开，仓内`tests/procedural_runner.py`会自造夹具供复现。版本仍为候选、没有公开release资产，不宣称跨机器、任意道具或最终美术认证。

本说明未发布候选下载资产。可先审阅本地源码和验证范围，按实际打包结果再安装；不提供不存在的候选release链接。技能保持同级安装，已有同名技能会拒绝覆盖。

原[blenderctl仓库](https://github.com/tsist/blenderctl)继续作为普通CLI源码后端，不需要子模块。`BLENDERCTL_ROOT`指向包含`tools/blenderctl/cli.py`的CLI源码；本扩展仓库本身不是CLI后端。Blender与CLI单独安装，扩展不会自动下载。历史仅拆仓的0.7.0说明见[CHANGELOG](CHANGELOG.md)，原样复制声明不用于本次功能候选。
