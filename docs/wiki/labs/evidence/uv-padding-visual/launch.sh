#!/usr/bin/env bash
set -euo pipefail
root="$PWD"
mapfile -t known < <(find native/jobs -mindepth 1 -maxdepth 1 -type d)
test "${#known[@]}" = 1
j="${known[0]}"
checksha() { sha256sum -- "$1" | cut -d' ' -f1; }
jq -e '.ok and .data.source_unchanged and (.data.source_saved|not)' native/result.json
mapfile -t bakes < <(find "$j"/baked -name r17-settings.json)
test "${#bakes[@]}" = 1
python visual-prep/prepare.py "$(dirname "${bakes[0]}")" "$root/study-input"
jq '.context' evidence/manifest.json >study-input/context.json
jq '.target' evidence/manifest.json >study-input/target.json
mkdir -p visual
test ! -e visual/result.json
taskset -c "${CPUSET:?}" python "$root/cli-visual/tools/blenderctl/cli.py" \
 --blender "${BLENDER_BIN:?}" --jobs-dir "$root/visual/jobs" --timeout 1200 --full \
 material procedural-export "$root/$j/author.blend" --expected-sha256 "$(checksha "$root/$j/author.blend")" \
 --resources "$root/study-input/resources.json" --context "$root/study-input/context.json" \
 --target "$root/study-input/target.json" --export "$root/evidence/export.json" > visual/result.json
jq -e '.ok and .data.source_unchanged and (.data.source_saved|not)' visual/result.json
