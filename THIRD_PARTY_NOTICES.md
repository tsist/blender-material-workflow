# Third-party dependencies and attribution

Material Workflow, its companion skill adaptations and release tooling are GPL-3.0-or-later. The code was split from tsist/blenderctl; existing SPDX declarations and GPL LICENSE files are retained. Copyright © 2026 blenderctl and Material Workflow contributors.

Blender and its Python modules are separately installed and licensed by their distribution. Python release/test tools use the standard library. Companion material image decoding optionally uses Pillow, which is not bundled. Background handoff uses the separately distributed GPL blenderctl backend. Image generators, MCP and memory tools are optional host facilities and are not supplied or configured here.

No Blender binaries, user textures, asset libraries, service credentials or private production scenes are distributed. Runtime tests generate their own simple geometry and numerical texture. No additional third-party library implementation is vendored by this split. This scoped source review is not a legal certification of future contributions.
