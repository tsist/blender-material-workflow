# Repository split and maintenance

Material Workflow originated in `tsist/blenderctl` commit `fbb76afa5da7e8577f366738b6ca5e392e6c3853` (extension 0.7.0, skill bundle 0.2.0). This initial independent release retains GPL attribution and material algorithms; changes are distribution, extension version/website, backend UI wording and companion links/metadata.

The complete Blender package is at this repository root. blenderctl consumes a pinned commit as `tools/material_workflow_addon`; all `material.*` host adapters, immutable job protocols and source/resource checks remain in blenderctl. To propose a material core change, edit this repository and validate it first; then update the consumer's submodule commit and run its host and Blender integration checks. Never edit two copies of the same core independently.

The four-skill suite is shipped together because its internal references form a connected resource graph. The old CLI repository retains its prior skill snapshot for compatibility; new material companion releases are published here. Installed personal skills are separate and require explicit migration if names collide.

Normal addon editing does not require a backend. Background handoff uses an explicit backend root containing `tools/blenderctl/cli.py` and its public schemas. A plugin source clone alone is not that root. CLI source release ZIPs include the pinned plugin; Git clones require submodule initialization. Automatic GitHub source archives exclude submodule contents.

Preserve old releases, source assets and recovery jobs. Changes to implementation identities invalidate prior checkpoint reuse even when visible materials are equivalent. Use new requests/jobs for a new distribution. Scope of evidence remains version-specific.
