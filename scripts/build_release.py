# SPDX-License-Identifier: GPL-3.0-or-later
"""Build standalone extension, source and companion skills with fixed ZIP metadata."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tomllib
import zipfile
from check_release import ROOT, public_files, audit
from check_skills import check


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, content in sorted(entries):
            item = zipfile.ZipInfo(name, date_time=(2026, 10, 6, 0, 0, 0))
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(item, content, compresslevel=9)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist'))
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    files = public_files()
    errors = audit(files) + check()['errors']
    if errors: raise SystemExit('\n'.join(errors))
    version = tomllib.loads((ROOT / 'blender_manifest.toml').read_text())['version']
    info = re.search(r'"version": \(([^)]+)\)', (ROOT / '__init__.py').read_text()).group(1)
    if tuple(map(int, version.split('.'))) != tuple(map(int, info.split(','))):
        raise SystemExit('Manifest and bl_info versions differ')
    skills = json.loads((ROOT / 'skills/manifest.json').read_text())['bundle_version']
    # Runtime files are root modules only; development resources belong in the source ZIP.
    runtime = [p for p in files if p.parent == ROOT and
               (p.suffix == '.py' or p.name in {'blender_manifest.toml', 'LICENSE', 'README.md'})]
    required = {'__init__.py', 'blender_manifest.toml', 'LICENSE', 'core.py', 'core_v2.py', 'ui.py', 'job_bridge.py'}
    if not required <= {p.name for p in runtime}: raise SystemExit('Incomplete extension')
    entries = [('material-workflow-skills-' + skills + '/' + p.relative_to(ROOT).as_posix(), p.read_bytes())
               for p in files if p.is_relative_to(ROOT / 'skills')]
    entries.append(('material-workflow-skills-' + skills + '/install_skills.py', (ROOT / 'scripts/install_skills.py').read_bytes()))
    payloads = {
        f'material-workflow-{version}.zip': archive([(p.name, p.read_bytes()) for p in runtime]),
        f'material-workflow-{version}-source.zip': archive([(f'material-workflow-{version}/' + p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in files]),
        f'material-workflow-skills-{skills}.zip': archive(entries),
    }
    rows = [{'file': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in sorted(payloads.items())]
    payloads['release-manifest.json'] = (json.dumps({'extension_version': version, 'skills_bundle_version': skills,
        'license': 'GPL-3.0-or-later', 'repository': 'tsist/blender-material-workflow',
        'backend': {'repository': 'tsist/blenderctl', 'tested_version': '0.54.2', 'optional_for_local_editing': True},
        'audited_source_files': len(files), 'extension_files': len(runtime), 'artifacts': rows}, indent=2) + '\n').encode()
    payloads['SHA256SUMS.txt'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n' for name, data in sorted(payloads.items())).encode()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, data in payloads.items():
        path = output / name
        if args.verify:
            if not path.is_file() or path.read_bytes() != data: raise SystemExit('Reproducibility failed: ' + name)
        else:
            with path.open('xb') as stream: stream.write(data)
    print(json.dumps({'ok': True, 'mode': 'verify' if args.verify else 'build', 'artifacts': rows}, indent=2))


if __name__ == '__main__': main()
