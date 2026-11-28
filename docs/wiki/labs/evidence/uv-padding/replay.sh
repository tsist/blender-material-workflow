#!/usr/bin/env bash
# Execute from a new run root with the verified R16 replay bundle extracted as r16/.
set -euo pipefail
root="$PWD"; src="$root/r16/R13/CarryToolbox/whitebox.blend"
expected=537214fbf4c462c2dc3e20f0eac16c94307eef46afed929cd36818319d8efaa5
printf '%s  %s\n' "$expected" "$src" | sha256sum -c -
mkdir -p "$root/native"
test ! -e "$root/native/result.json"
# Prepare isolated CLI source as in the lab (all three patches applied).
taskset -c "${CPUSET:?}" python "$root/cli/tools/blenderctl/cli.py" \
  --blender "${BLENDER_BIN:?}" --jobs-dir "$root/native/jobs" --timeout 1100 --full \
  material procedural-run "$src" --expected-sha256 "$expected" \
  --resources "$root/r16/R12/replay/r11/resources.json" --manifest "$root/evidence/manifest.json" \
  --export "$root/evidence/export.json" >"$root/native/result.json"
jq -e '.ok and .data.source_unchanged and (.data.source_saved|not)' "$root/native/result.json"
mapfile -t runs < <(find "$root/native/jobs" -name r17-settings.json)
test "${#runs[@]}" = 1
python "$root/evidence/analyze.py" "$root/r16/evidence/corner-seam" "$(dirname "${runs[0]}")" "$root/evidence/receipt.json"
