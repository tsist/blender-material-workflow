# 查工艺

自动生成。编辑工艺页，不手改此页。

## 喷漆金属 / 凸缘磨损与凹处积尘 / Edge、Cavity、PBR

- [MW-012 · 按镜头检验辅助图分辨率](../techniques/012-match-mesh-map-resolution.md) · 独立复验

## 喷漆金属 / 层遮罩量化和阈值跳变 / Edge、Cavity、Roughness

- [MW-013 · 验证辅助遮罩的实际位深](../techniques/013-verify-helper-mask-depth.md) · 独立复验

## 喷漆钢 / 掉漆和锈蚀 / Metallic、Roughness

- [MW-003 · 分离掉漆、露钢和锈蚀](../techniques/003-chip-and-rust.md) · 单件复现

## 喷漆钢 / 握位抛光 / Roughness

- [MW-001 · 把手只改粗糙度](../techniques/001-grip-roughness.md) · 单件复现

## 通用 / AO 路由 / AO、Base Color

- [MW-011 · 把 AO 辅助遮罩与交付 AO 分开](../techniques/011-ao-routing.md) · 单件复现

## 通用 / Linux 入口 / 全部

- [MW-006 · 区分 CLI 能发现与事务能执行](../techniques/006-linux-procedural.md) · 单件复现

## 通用 / UV 覆盖 / UV

- [MW-007 · 烘焙前查目标槽 UV](../techniques/007-uv-preflight.md) · 单件复现

## 通用 / 依赖回读 / 全部

- [MW-010 · 搬运贴图后核对摘要再重建](../techniques/010-relocate-bake.md) · 单件复现

## 通用 / 凸缘与凹槽 / Mesh Maps

- [MW-004 · 按几何位置分配旧化信号](../techniques/004-mesh-map-roles.md) · 来源已核

## 通用 / 填充边距 / Base Color、Roughness

- [MW-008 · 用缩图定位 UV 边缘渗色](../techniques/008-padding-mips.md) · 单件复现

## 通用 / 纯贴图重建 / Base Color、Normal、AO

- [MW-005 · 从贴图重建时保持颜色空间与切线](../techniques/005-rebuild-pbr.md) · 来源已核

## 通用 / 遮罩修正 / Mask

- [MW-002 · 分开保存程序遮罩与手工加减](../techniques/002-local-mask.md) · 单件复现

## 通用 / 镜像接缝 / Normal

- [MW-009 · 区分镜像切线与绿色轴错误](../techniques/009-mirror-tangents.md) · 单件复现
