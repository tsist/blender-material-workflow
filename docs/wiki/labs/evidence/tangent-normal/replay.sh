#!/usr/bin/env bash
# Run from a fresh experiment root; extract the R16/R17 proof archives to r16/r17.
set -euo pipefail
ROOT="$PWD"; HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test ! -e cli && test ! -e material && test ! -e out
mkdir cli material out
curl -fsSL https://codeload.github.com/tsist/blenderctl/tar.gz/4046c7a8677514e45b2490a12133b9e587ec279f | tar -xz --strip-components=1 -C cli
curl -fsSL https://codeload.github.com/tsist/blender-material-workflow/tar.gz/0f39fcf0c62ee71f8264e807b52d18722ed20388 | tar -xz --strip-components=1 -C material
mkdir -p cli/tools/material_workflow_addon
cp material/*.py cli/tools/material_workflow_addon/
cp "$HERE/r19_fixture.py" cli/tools/material_workflow_addon/
cmp r17/evidence/compat.patch r16/replay/compat.patch
git -C cli apply --check --ignore-space-change ../r17/evidence/compat.patch
git -C cli apply --ignore-space-change ../r17/evidence/compat.patch
git -C cli apply --check "$HERE/r19-hook.patch"
git -C cli apply "$HERE/r19-hook.patch"
"${BLENDER_BIN:?}" --version >out/blender-version.txt
grep -q '02f0899d78e3' out/blender-version.txt
src="$ROOT/r16/R13/CarryToolbox/whitebox.blend"
sha=537214fbf4c462c2dc3e20f0eac16c94307eef46afed929cd36818319d8efaa5
printf '%s  %s\n' "$sha" "$src" | sha256sum -c -
taskset -c "${CPUSET:?}" python cli/tools/blenderctl/cli.py \
  --blender "$BLENDER_BIN" --jobs-dir "$ROOT/out/jobs" --timeout 1100 --full \
  material procedural-run "$src" --expected-sha256 "$sha" \
  --resources "$ROOT/r16/R12/replay/r11/resources.json" \
  --manifest "$ROOT/r17/evidence/manifest.json" --export "$ROOT/r17/evidence/export.json" >out/result.json
jq -e '.ok and .data.source_unchanged and (.data.source_saved|not)' out/result.json
mapfile -t results < <(find out/jobs -type d -name r19)
test "${#results[@]}" = 1
python "$HERE/analyze.py" "${results[0]}" out/evidence
