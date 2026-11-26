# 排故

自动生成。编辑工艺页，不手改此页。

## 原尺寸正常，远处或缩图出现接缝

- [MW-008 · 用缩图定位 UV 边缘渗色](../techniques/008-padding-mips.md) · 单件复现

## 只有镜像侧的刻痕凹凸反了

- [MW-009 · 区分镜像切线与绿色轴错误](../techniques/009-mirror-tangents.md) · 单件复现

## 抛光把底色改灰或金属度下降

- [MW-001 · 把手只改粗糙度](../techniques/001-grip-roughness.md) · 单件复现

## 有命令但材质事务不启动

- [MW-006 · 区分 CLI 能发现与事务能执行](../techniques/006-linux-procedural.md) · 单件复现

## 每处掉漆都长出同样的锈

- [MW-003 · 分离掉漆、露钢和锈蚀](../techniques/003-chip-and-rust.md) · 单件复现

## 烘焙报重叠或 UV 越界

- [MW-007 · 烘焙前查目标槽 UV](../techniques/007-uv-preflight.md) · 单件复现

## 磨损与积尘铺满表面

- [MW-004 · 按几何位置分配旧化信号](../techniques/004-mesh-map-roles.md) · 来源已核

## 程序导出拒绝 AO 通道

- [MW-011 · 把 AO 辅助遮罩与交付 AO 分开](../techniques/011-ao-routing.md) · 单件复现

## 贴图搬走后重建提示资源不见或变化

- [MW-010 · 搬运贴图后核对摘要再重建](../techniques/010-relocate-bake.md) · 单件复现

## 重建变灰或镜像 UV 凹凸反转

- [MW-005 · 从贴图重建时保持颜色空间与切线](../techniques/005-rebuild-pbr.md) · 来源已核

## 重算覆盖手工笔迹

- [MW-002 · 分开保存程序遮罩与手工加减](../techniques/002-local-mask.md) · 单件复现
