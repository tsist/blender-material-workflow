# Repository-only split

The user clarified that only GitHub repository organization was requested. The submodule dependency conversion and software version changes were withdrawn.

Material Workflow 0.7.0 and companion skills 0.2.0 are copied unchanged from `tsist/blenderctl` commit `fbb76afa5da7e8577f366738b6ca5e392e6c3853`. Original plugin runtime files, manifest and all skill files are byte-identical to that Git tree. The CLI main tree was restored to that same tree using a revert commit, without rewriting public history. Existing releases remain available; mistaken split implementation releases are retained as drafts.

The independent repository changes GitHub management and release location only. The original CLI keeps its bundled material code and existing imports. No submodule, dynamic external import, runtime install dependency or new CLI wrapper is introduced. The plugin's existing optional backend handoff continues to use the normal separate blenderctl checkout.

Repository READMEs and standalone packaging tools describe this distribution. They do not replace original runtime modules or skill instructions. Future runtime changes require their own request and verification; repository separation alone is not authorization to change architecture.
