# SPDX-License-Identifier: GPL-3.0-or-later
"""Run portable host/background acceptance cases; never install the add-on."""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

CASES = ('contract', 'signals', 'core', 'ui', 'mesh_maps', 'bake', 'examples', 'regressions', 'optics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='Absolute NEW suite-output directory')
    parser.add_argument('--blender', help='Path to an existing Blender executable; never installed by the suite')
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--timeout', type=int, default=300, help='Per-process seconds, 10..3600')
    args = parser.parse_args()
    if len(set(args.cases)) != len(args.cases): parser.error('--cases must not contain duplicates')
    output = Path(args.output)
    if not output.is_absolute() or output.exists():
        parser.error('--output must be an absolute path which does not exist')
    if not 10 <= args.timeout <= 3600: parser.error('--timeout must be 10..3600 seconds')
    blender = Path(args.blender).resolve() if args.blender else None
    if any(case != 'contract' for case in args.cases) and (blender is None or not blender.is_file()):
        parser.error('Background cases require --blender pointing to an existing executable')
    output.mkdir(parents=True, exist_ok=False)
    scripts = Path(__file__).resolve().parent
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    results = []
    for case in args.cases:
        script = scripts / ('procedural_' + case + '.py')
        destination = output / case
        command = ([sys.executable, str(script), '--output', str(destination)] if case == 'contract' else
            [str(blender), '--background', '--factory-startup', '--python-exit-code', '1',
             '--python', str(script), '--', '--output', str(destination)])
        log = output / (case + '.log')
        started = time.monotonic()
        row = {'case': case, 'command': command, 'log': str(log), 'output': str(destination)}
        try:
            if case == 'signals':
                host_log = output / 'signals-host.log'
                host_command = [sys.executable, '-B', str(script), '--host', '--output', str(output/'signals-host')]
                with host_log.open('x', encoding='utf-8') as stream:
                    host = subprocess.run(host_command, cwd=scripts.parent, env=environment,
                        stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
                row['host'] = {'status':'pass' if host.returncode == 0 else 'fail', 'exit_code':host.returncode,
                               'command':host_command, 'log':str(host_log)}
            with log.open('x', encoding='utf-8') as stream:
                process = subprocess.run(command, cwd=scripts.parent, env=environment,
                    stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
            row.update(status='pass' if process.returncode == 0 else 'fail', exit_code=process.returncode)
            if case in ('examples', 'optics') and row['status'] == 'pass':
                # Reopen in a separate process, never the process which created
                # the meshes/materials, and use another exclusive output tree.
                reopen_output = output / (case + '-reopen')
                reopen_log = output / (case + '-reopen.log')
                reopen_command = [str(blender), '--background', '--factory-startup', '--python-exit-code', '1',
                    '--python', str(script), '--', '--output', str(reopen_output),
                    '--verify-fixtures', str(destination / 'fixtures.json') if case == 'examples' else str(destination)]
                with reopen_log.open('x', encoding='utf-8') as stream:
                    reopened = subprocess.run(reopen_command, cwd=scripts.parent, env=environment,
                        stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
                row['independent_reopen'] = {'exit_code': reopened.returncode,
                    'status': 'pass' if reopened.returncode == 0 else 'fail',
                    'command': reopen_command, 'log': str(reopen_log), 'output': str(reopen_output)}
                if reopened.returncode != 0: row['status'] = 'fail'
            if case == 'signals' and row['status'] == 'pass':
                reopen_log = output / 'signals-reopen.log'
                reopen_command = [str(blender), '--background', '--factory-startup', str(destination/'signals.blend'),
                    '--python-exit-code','1','--python',str(script),'--','--output',str(output/'signals-reopen'),
                    '--native-output',str(destination),'--reopen']
                with reopen_log.open('x', encoding='utf-8') as stream:
                    reopened = subprocess.run(reopen_command, cwd=scripts.parent, env=environment,
                        stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout, check=False)
                row['independent_reopen'] = {'exit_code':reopened.returncode,
                    'status':'pass' if reopened.returncode == 0 else 'fail','command':reopen_command,'log':str(reopen_log)}
                if reopened.returncode != 0: row['status']='fail'
            if case == 'signals' and row.get('host',{}).get('status') != 'pass': row['status']='fail'
        except subprocess.TimeoutExpired:
            row.update(status='fail', error='per-process timeout exceeded')
        except OSError as error:
            row.update(status='fail', error=str(error))
        row['elapsed_seconds'] = time.monotonic() - started
        results.append(row)
        print(case + ': ' + row['status'] + ' (' + str(log) + ')', flush=True)
    report = {'status': 'pass' if all(row['status'] == 'pass' for row in results) else 'fail',
              'cases': results, 'limitations': ['No user GUI process is connected or controlled',
                  'Small acceptance fixtures do not prove 2K performance or visual equivalence across engines']}
    with (output / 'suite.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print('SUITE_REPORT=' + str(output / 'suite.json'))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
