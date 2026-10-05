# Release verification 0.7.1

This is a repository/distribution split from extension 0.7.0, with backend field wording and version/website updates. Core algorithms are unchanged. Historical validation belongs to its original distribution; this release is checked independently.

Required checks: host bridge contracts; actual four-sibling skill installation and collision protection; complete resource graph; finite source credential/private-path audit; byte-identical repeated ZIP build; Blender extension ZIP installation/enabling/disabling in isolated user directories; installed material operator application, save and independent reopen; real CPU preview through blenderctl's pinned dependency; recursive-clone and complete source-ZIP rehearsal.

Host CI uses Windows/Ubuntu × Python 3.12/3.13. Blender runtime verification is local Windows / Blender 5.2.1 LTS build `9e2066aef7ef`. Tests use original Cube/UV and numerical textures, not private assets. Visual sidebar interaction, GPU/Eevee, animation, all batch recovery combinations and artistic quality are not revalidated by this packaging release. Background tests must not connect to an open user scene or save global preferences.

## Local results on 2026-10-06

| Check | Result |
| --- | --- |
| Standalone host tests | 24 passed, including actual skill installation/collision refusal and optional Pillow decoding |
| Skill resource graph | 104 local links resolved across four siblings |
| Source review | 92 tracked text files audited; only scoped release/UI wording changes in original plugin files; core algorithms/contracts unchanged |
| Deterministic build | Repeated build verified byte-identical extension, source and skills ZIPs |
| Blender Extensions installation | Actual release ZIP installed/enabled/disabled in isolated directories; installed files matched ZIP bytes |
| Installed operator and independent reopen | Manifest load, apply, save and separate Blender reopen passed; Cube geometry/UV and managed nodes preserved |
| External blenderctl 0.54.2 | Real CPU material.run saved/rendered/reopened; source preserved; plugin bridge async submission, bounded wait and owned result passed |

GitHub Actions status is visible on the repository Actions page; it is separate from these local results. The release notes report its actual state at publication.
