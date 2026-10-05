# Material Workflow

An independently distributed Blender extension for editable layered PBR materials, explicit templates and assignments, managed incremental changes, and diagnostic previews.

**Extension 0.7.1 · Companion skills 0.2.1 · GPL-3.0-or-later**

[中文说明](README.zh-CN.md) · [Workflow](docs/MATERIAL_WORKFLOW.md) · [Skills](skills/README.md) · [Migration](docs/MIGRATION.md) · [Verification](docs/RELEASE_VERIFICATION.md)

## Install

Download `material-workflow-0.7.1.zip` from [Releases](https://github.com/tsist/blender-material-workflow/releases/tag/v0.7.1). In Blender choose **Preferences → Extensions → Install from Disk**, then enable Material Workflow. Open **View3D → Sidebar → Material Workflow**. The extension ZIP has its manifest at the archive root and contains only the runtime modules, license and installation README.

The manifest minimum is Blender 5.2.0; the tested runtime baseline is Windows / Blender 5.2.1 LTS, build `9e2066aef7ef`. Existing UVs and static images are required. Cycles and Eevee use different device/node contracts.

## Separate backend

Ordinary material draft editing, templates and assignments run in Blender without a CLI installation. Background snapshot jobs, `material.run`, `material.batch`, `material.study` and recovery use the separate [blenderctl](https://github.com/tsist/blenderctl) backend. Configure the plugin's **blenderctl 后端源码目录** to that checkout, not to this repository.

```powershell
git clone --recurse-submodules https://github.com/tsist/blenderctl.git
# For an existing checkout after updating its main branch:
git submodule update --init --recursive
```

blenderctl 0.54.2 pins this extension through a Git submodule. Its source release includes the pinned dependency; GitHub's automatic source archive does not include submodules. Previous blenderctl 0.54.1 distributions retain their bundled 0.7.0 extension and remain usable. Old checkpoint implementation fingerprints must not be transplanted across releases.

## Companion skills

Download `material-workflow-skills-0.2.1.zip` from the same release. It contains material authoring and its three sibling guidance dependencies, preserving all cross-skill references. From this checkout:

```powershell
python scripts/install_skills.py --list
python scripts/install_skills.py --destination '<actual-absolute-skill-directory>'
```

The installer refuses existing same-named skills before copying. Set `BLENDERCTL_ROOT` to the separately installed backend for CLI discovery. Blender, image generators, MCP, memory providers and optional Pillow are not bundled or installed automatically.

## Develop and verify

The Blender package lives at the repository root (`__init__.py`, core/UI modules, `blender_manifest.toml`). This layout allows blenderctl to consume the complete pinned repository as `tools/material_workflow_addon` without a second editable copy of the core.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/check_skills.py
python scripts/build_release.py --output dist
python scripts/build_release.py --output dist --verify
```

The build produces an installable extension ZIP, a complete source ZIP, the skill ZIP, a release manifest and SHA-256 checksums. Tests separate host contracts, actual extension installation and real Blender execution. See [verification](docs/RELEASE_VERIFICATION.md) for scope. General automatic UV, UDIM/animated textures, DLSS and automatic aesthetic selection are not included.
