# Material Workflow

Blender extension and companion agent skills, licensed **GPL-3.0-or-later**.

**Local candidate: Extension 0.8.0 · Skills bundle 0.3.0 (material guidance 0.6.0) · companion blenderctl 0.64.0.**

[中文说明](README.zh-CN.md) · [Companion skills](skills/README.md) · [Extension guide](docs/EXTENSION_README.md) · [Candidate scope](docs/EXTENSION_README.md)

This candidate adds procedural and hybrid PBR authoring to the existing static image-layer workflow. Fifteen typed signals include coordinate frames, vector warp, Noise, Wave wood, Voronoi and remapping; layered parameters control color, roughness, metalness, signed height and glass optical values. Wood accepts an explicit grain axis and three local sampling multipliers; metal weathering uses caller-selected regions and a clean zero-weathering control. Existing image-layer v1/v2 contracts remain available separately.

Keep editable author materials and texture-only reconstructions. Per-channel Cycles baking writes sRGB BaseColor, Non-Color data, encoded IOR, signed float Height and real tangent Normal; disk reload, source/dependency identity, target protection, managed-edit checks and save/reopen verification are part of the workflow. Existing UVs are required. No automatic UV, volume absorption, true displacement or arbitrary node-graph takeover is claimed. Cycles/Eevee and glass differences require separate observation.

Bounded file-stage production and review are complete: 14 material targets and 126 required 2K maps passed independent full-pixel disk checks and reconstruction. The maintainer actually viewed 30 final author/reconstructed images across both engines/relighting plus 12 local supplements, 42 in total, including the actual oil upper shoulder and lid edge. DeepSeek completed creation/correction, 2K export, reconstruction and finite final-image review with maintainer intervention in wood mixing, oil layers and glass-thickness diagnosis. This was assisted reuse, not an unassisted blind test or fully unattended workflow. Softer 2K pores/fine lines, Eevee glass approximations and conditional visual findings remain.

Extracted build-a passed 15 technical stages, including 73 host cases (two optional Pillow skips), fresh standalone contract/core/bake/optics cases and independent reopen, the public CLI's 128×128/nine-map surface round trip with full-pixel maximum error 0, and isolated installation, legacy load/apply, surface save and independent reopen of the 25-member extension. This qualifies tested build-a code/bytes, not later archives: final document updates still require repacking and final checks. Private cases and audits are not bundled; `tests/procedural_runner.py` creates its own reproducible fixtures. The versions remain candidates without public release assets; no cross-machine, arbitrary-prop or final aesthetic certification is claimed.

## Use the candidate

No 0.8.0/0.3.0 candidate download asset is published by this document. Review this source checkout and the validation guide before packaging or installing. A packaged extension uses Blender Preferences → Extensions → Install from Disk. Companion skills stay together as sibling folders; their installer refuses existing same-named skills. See the [skill guide](skills/README.md).

The separate [blenderctl source repository](https://github.com/tsist/blenderctl) remains the normal backend checkout; there is no submodule or recursive-clone requirement. Set `BLENDERCTL_ROOT` to its unpacked source containing `tools/blenderctl/cli.py`. This extension repository alone is not a CLI backend root. Blender and CLI are installed separately; neither is downloaded by the extension.

The historical repository-only 0.7.0 split is recorded in [CHANGELOG](CHANGELOG.md). Its byte-identical-copy statement applies to that historical split, not this candidate's new behavior.
