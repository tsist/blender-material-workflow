# Release verification 0.7.1

This is a repository/distribution split from extension 0.7.0, with backend field wording and version/website updates. Core algorithms are unchanged. Historical validation belongs to its original distribution; this release is checked independently.

Required checks: host bridge contracts; actual four-sibling skill installation and collision protection; complete resource graph; finite source credential/private-path audit; byte-identical repeated ZIP build; Blender extension ZIP installation/enabling/disabling in isolated user directories; installed material operator application, save and independent reopen; real CPU preview through blenderctl's pinned dependency; recursive-clone and complete source-ZIP rehearsal.

Host CI uses Windows/Ubuntu × Python 3.12/3.13. Blender runtime verification is local Windows / Blender 5.2.1 LTS build `9e2066aef7ef`. Tests use original Cube/UV and numerical textures, not private assets. Visual sidebar interaction, GPU/Eevee, animation, all batch recovery combinations and artistic quality are not revalidated by this packaging release. Background tests must not connect to an open user scene or save global preferences.
