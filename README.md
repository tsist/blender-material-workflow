# Material Workflow

Separate GitHub home for the existing Material Workflow Blender extension and its companion agent skills.

**Extension 0.7.0 · Skills 0.2.0 · GPL-3.0-or-later**

[中文说明](README.zh-CN.md) · [Release](https://github.com/tsist/blender-material-workflow/releases/tag/v0.7.0) · [Companion skills](skills/README.md)

This is a repository-management split only. Plugin runtime modules, Blender manifest and all companion skill files are byte-for-byte copies of their previously published source in `tsist/blenderctl` commit `fbb76afa5da7e8577f366738b6ca5e392e6c3853`. No material algorithms, UI behavior, CLI dependency, software version or skill guidance is changed by this split.

The original [blenderctl](https://github.com/tsist/blenderctl) repository retains its existing layout and bundled material core. There is no submodule and no recursive-clone requirement. Background handoff still uses a normal blenderctl checkout containing `tools/blenderctl/cli.py`. This repository alone is not a CLI backend root.

## Downloads

- `material-workflow-0.7.0.zip`: existing Blender extension; Preferences → Extensions → Install from Disk.
- `blender-skills-0.2.0.zip`: the unchanged complete four-skill suite, keeping all sibling references. Extract and run `python install_skills.py --destination '<actual-absolute-skill-directory>'`; existing skills are refused before copying.
- `material-workflow-0.7.0-source.zip`: independent repository source and packaging tools.
- Release manifest and SHA-256 checksums.

The extension ZIP is byte-identical to the previously published blenderctl release asset. The skill source files are unchanged; their complete ZIP is reproduced from the existing companion build. GitHub documentation and separate release tooling describe repository ownership only. Source/skill file hashes are verified against the original Git commit, in addition to normal package audits and repeated builds.

Manifest minimum Blender 5.2.0; historical runtime baseline Windows / Blender 5.2.1 LTS build `9e2066aef7ef`. Existing UVs and static image files are required. No new runtime feature or compatibility guarantee is introduced. See [existing workflow documentation](https://github.com/tsist/blenderctl/blob/main/docs/MATERIAL_WORKFLOW.md).

## Repository checks

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/check_skills.py
python scripts/build_release.py --output dist
python scripts/build_release.py --output dist --verify
```

The earlier submodule-based 0.7.1 proposal was withdrawn after clarification. Current repositories preserve their original execution and dependency structure.
