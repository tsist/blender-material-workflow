# Material Workflow 0.8.0 candidate

GPL-3.0-or-later Blender extension for existing static image-layer v1/v2 workflows and procedural/hybrid PBR manifest2.0 authoring. Companion CLI0.64.0 and skills0.3.0 remain candidates; material source guidance is0.7.0. Bounded build-a qualification is complete, but no public candidate release assets are announced.

When a verified package is available, install with Preferences → Extensions → Install from Disk, enable it, and open View3D → Sidebar → Material Workflow. Manifest minimum is Blender5.2.0; the bounded maintainer runtime baseline is Windows / Blender5.2.1 LTS. Blender and CLI are separate installations, not bundled downloads.

Fifteen typed procedural signals build editable layers. Wood axis and XYZ local sampling scale are explicit, metal weathering has named regions and a zero control. The current-scene procedural panel creates materials, exposes live controls, updates managed state and exports required channels plus texture-only reconstruction. Read actual RNA/manifest values, observe new renders, and keep author/reconstructed separately. Legacy drafts, templates, assignments and snapshot handoff remain separate contracts.

Cycles baking preserves BaseColor/data color spaces, signed Height and encoded IOR, performs real tangent Normal baking, reloads disk pixels, and prevents duplicate Height Bump in reconstruction. Validate UVs, source/dependency SHA, shared references and non-target state; structural/manual conflicts are refused. Save/reopen and rendering success do not replace aesthetic review.

Background handoff uses a normal unpacked blenderctl source checkout containing `tools/blenderctl` and `docs/cli/schemas`; `BLENDERCTL_ROOT` points there. Supported GUI snapshots are persistent separate copies; do not replace the unsaved source. Keep job/handoff files for recovery.

Existing valid UVs are required; static FILE images are needed only for image inputs. No general automatic UV, UDIM/animation, volume absorption, true displacement or automatic aesthetic selection is included. Cycles/Eevee have separate contracts and observable glass/filtering differences.

Bounded evidence covers 14 material targets, 126 required 2K maps with independent full-pixel disk checks/reconstruction, and 42 actually viewed final images: 30 dual-engine/relighting plus 12 local supplements. DeepSeek completed file-stage creation/correction, 2K export, reconstruction and finite image review with maintainer assistance in wood mixing, oil layers and glass thickness. This was assisted reuse, not a blind or fully unattended test. Softer 2K microdetail, approximate Eevee glass and conditional visual findings remain.

Extracted build-a passed 15 technical stages: 73 host cases with two optional Pillow skips, fresh standalone contract/core/bake/optics and independent reopen, a public 128×128/nine-map surface round trip with full-pixel maximum error 0, and isolated legacy/surface/save/reopen checks of the new 25-member installed extension. Later documentation changes require repacking and final checks; later archives are not prequalified. Private cases are not bundled, while source-checkout `tests/procedural_runner.py` creates reproducible fixtures. No arbitrary-prop, cross-machine or final aesthetic certification is implied. See the [procedural method and bounded evidence](../skills/blender-material-authoring/references/pbr/procedural-pbr.md) and [skills](../skills/README.md).

SPDX-License-Identifier: GPL-3.0-or-later. See [LICENSE](../LICENSE).
