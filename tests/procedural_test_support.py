# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable test bootstrap and exclusive, explicit output ownership."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def bootstrap():
    """Mount this checkout as the add-on package without installing it."""
    root = Path(__file__).resolve().parents[1]
    name = 'material_workflow_addon'
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(existing.__file__).resolve() != root / '__init__.py':
            raise RuntimeError('Another material_workflow_addon package is already loaded')
        return root
    spec = importlib.util.spec_from_file_location(name, root / '__init__.py',
                                                 submodule_search_locations=[str(root)])
    if spec is None or spec.loader is None:
        raise RuntimeError('Cannot bootstrap the add-on checkout')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return root


def arguments():
    raw = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description='Isolated procedural-material acceptance test')
    parser.add_argument('--output', required=True,
                        help='Absolute NEW directory for this invocation; existing paths are refused')
    args, extra = parser.parse_known_args(raw)
    return args, extra


def prepare_output(case, *, require_blender=False):
    if require_blender:
        import bpy
        if not bpy.app.background:
            raise RuntimeError('These tests refuse a visible/user Blender GUI; use --background --factory-startup')
        if bpy.app.version < (5, 2, 0):
            raise RuntimeError('Blender 5.2 or newer is required; the verified baseline is 5.2.1')
    args, extra = arguments()
    if extra and not (case == 'examples' and len(extra) == 2 and extra[0] == '--verify-fixtures'):
        raise ValueError('Unsupported test arguments: ' + repr(extra))
    path = Path(args.output)
    if not path.is_absolute():
        raise ValueError('--output must name an absolute NEW directory')
    if path.exists():
        raise FileExistsError('Refusing to reuse or overwrite --output: ' + str(path))
    path.mkdir(parents=True, exist_ok=False)
    write_json(path / 'invocation.json', {'case': case, 'status': 'started',
               'output': str(path.resolve()), 'extra_arguments': extra,
               'isolation': 'independent background process' if require_blender else 'host Python'})
    return path.resolve()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
