#!/usr/bin/env bash
# Call from the extracted R14 replay root after preparing cli and cli16.
set -euo pipefail
size=${1:?Specify helper size}; shift
case "$size" in 512|2048) ;; *) exit 2 ;; esac
for asset in "$@"; do
  case "$asset" in CarryToolbox|ChestToolbox) ;; *) exit 2 ;; esac
  for mode in b8 f16; do
    route=cli; [[ $mode != f16 ]] || route=cli16
    src="$PWD/R13/$asset/whitebox.blend"
    name="$asset-$size"
    w="$PWD/r15/$mode-$name"; mkdir -p "$w"
    test ! -e "$w/result.json"
    sha=$(sha256sum "$src" | cut -d' ' -f1)
    exp=(); [[ $size != 2048 ]] || exp=(--export "$PWD/experiment/export.json")
    taskset -c "${CPUSET:?}" python "$route/tools/blenderctl/cli.py" \
      --blender "${BLENDER_BIN:?}" --jobs-dir "$w/jobs" --timeout 850 --full \
      material procedural-run "$src" --expected-sha256 "$sha" \
      --resources "$PWD/R12/replay/r11/resources.json" \
      --manifest "$PWD/experiment/$name/manifest.json" "${exp[@]}" > "$w/result.json"
    jq -e '.ok == true' "$w/result.json"
  done
done
