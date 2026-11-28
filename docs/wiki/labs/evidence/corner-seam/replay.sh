#!/usr/bin/env bash
# Execute from the extracted R15 replay root with verified cli/ and cli16/.
set -euo pipefail
evidence=${EVIDENCE:?}
python - <<'PY'
import json
from pathlib import Path
for size in (512,2048):
    source=Path('experiment')/f'CarryToolbox-{size}'/'manifest.json'
    p=json.loads(source.read_text())
    p['preview'].update(width=512,height=512,samples=32)
    p['preview']['views']=[{'id':l,'azimuth':33,'elevation':19,'lighting':l,
                            'focus':[.935,.115,.565],'zoom':5} for l in ('soft','raking')]
    Path(f'r16-manifest-{size}.json').write_text(json.dumps(p,indent=2)+'\n')
PY
for size in 512 2048; do
  for mode in b8 f16; do
    route=cli
    [[ $mode == b8 ]] || route=cli16
    src="$PWD/R13/CarryToolbox/whitebox.blend"
    job="$PWD/r16/$size-$mode"
    mkdir -p "$job"
    test ! -e "$job/result.json"
    taskset -c "${CPUSET:?}" python "$route/tools/blenderctl/cli.py" \
      --blender "${BLENDER_BIN:?}" --jobs-dir "$job/jobs" --timeout 850 --full \
      material procedural-run "$src" --expected-sha256 "$(sha256sum "$src" | cut -d' ' -f1)" \
      --resources "$PWD/R12/replay/r11/resources.json" --manifest "$PWD/r16-manifest-$size.json" \
      --export "$PWD/experiment/export.json" > "$job/result.json"
    jq -e '.ok==true' "$job/result.json"
  done
done
python "$evidence/probe_corner.py" r16 r16-receipt.json 512 2048
