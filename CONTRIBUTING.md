# Contributing

The Blender package lives at this repository root; companion skills live in `skills/`. CLI adapters and job protocols are maintained separately in [blenderctl](https://github.com/tsist/blenderctl). Keep explicit drafts, source/resource identity, conflict detection and dependency retention. Do not silently retry submissions whose acceptance is unknown.

Run `python -m unittest discover -s tests -p "test_*.py" -v`, `python scripts/check_skills.py`, `python scripts/check_release.py`, and a repeated `scripts/build_release.py --verify` build. Blender runtime changes also require actual extension ZIP installation and representative material save/reopen/render tests. Host CI does not prove Linux Blender or artistic compatibility.

Increment both manifest and bl_info versions for plugin changes. Build from a staged reviewed tree; archives exclude developer tests/scripts from the installed extension. Never publish private assets, configuration or credentials. Contributions use GPL-3.0-or-later; retain upstream attribution and identify third-party dependencies.
