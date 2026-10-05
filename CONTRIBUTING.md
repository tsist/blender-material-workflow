# Contributing

This repository hosts unchanged copies of Material Workflow and companion skills for independent GitHub management. Original code provenance: tsist/blenderctl commit fbb76afa5da7e8577f366738b6ca5e392e6c3853. Current repository separation does not change runtime dependencies or authorize an architecture redesign.

GPL-3.0-or-later attribution is retained. Keep runtime changes explicit, preserve protected inputs and managed-edit contracts, and validate actual affected Blender behavior. Repository packaging checks can run with `python -m unittest discover -s tests -p "test_*.py" -v`, `python scripts/check_skills.py` and repeated `scripts/build_release.py --verify` builds.
