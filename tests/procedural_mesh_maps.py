# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with fixed Blender --background --factory-startup --python this_file."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
from pathlib import Path
import struct
import sys
import uuid

import bpy

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
RUN = prepare_output('mesh_maps', require_blender=True)
from material_workflow_addon import procedural_mesh_maps as module
from material_workflow_addon.contract import WorkflowError

checks = []
results = {}


def safe_fingerprint(obj):
    try: return module._mesh_fingerprint(obj.data, 'UVMap')
    except WorkflowError as error:
        return {'invalid': str(error),
                'coordinates': [tuple(v.co) for v in obj.data.vertices],
                'uvs': [(u.name, [tuple(c.uv) for c in u.data]) for u in obj.data.uv_layers]}


def state(obj):
    return {'scene': bpy.context.scene.name, 'layer': bpy.context.view_layer.name,
        'active': bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        'selected': sorted(o.name for o in bpy.context.selected_objects),
        'mode': bpy.context.mode, 'engine': bpy.context.scene.render.engine,
        'samples': bpy.context.scene.cycles.samples,
        'uv': [(u.name, u.active_render) for u in obj.data.uv_layers],
        'uv_active': obj.data.uv_layers.active_index,
        'slots': [(s.link, s.material.name if s.material else None) for s in obj.material_slots],
        'polygon_slots': [p.material_index for p in obj.data.polygons],
        'matrix': [float(x) for row in obj.matrix_world for x in row],
        'mesh_fingerprint': safe_fingerprint(obj),
        'materials': sorted(bpy.data.materials.keys()), 'images': sorted(bpy.data.images.keys()),
        'meshes': sorted(bpy.data.meshes.keys()), 'scenes': sorted(bpy.data.scenes.keys()),
        'objects': sorted(bpy.data.objects.keys())}


def bake(name, obj, requests, size=128):
    before = state(obj)
    result = module.bake_mesh_maps(obj, 'UVMap', requests, RUN, size)
    assert state(obj) == before, 'source/context/datablock state changed'
    for ident, item in result['maps'].items():
        file = Path(item['file']); data = file.read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256']
        assert struct.unpack('>II', data[16:24]) == (size, size)
        image = bpy.data.images.load(str(file), check_existing=False)
        image.colorspace_settings.name = 'Non-Color'
        values = list(image.pixels)[0::4]
        assert min(values) >= 0 and max(values) <= 1
        assert item['color_space'] == 'Non-Color'
        assert item['disk_decode_verified'] and item['buffer_disk_max_abs_error'] <= item['decode_tolerance']
        assert item['statistics_source'] == 'independently_reloaded_Non-Color_disk_pixels'
        item['decoded_minimum'] = min(values); item['decoded_maximum'] = max(values)
        item['decoded_mean'] = sum(values) / len(values)
        bpy.data.images.remove(image)
    checks.append(name + ': bake PNG decoded, SHA/dimensions/range, full source state restored')
    results[name] = result
    return result


def rejected(name, obj, requests, code='invalid_mesh_map', uv='UVMap', size=64):
    before = state(obj)
    try:
        module.bake_mesh_maps(obj, uv, requests, RUN, size)
    except WorkflowError as error:
        assert error.code == code, (error.code, str(error))
    else:
        raise AssertionError('expected rejection: ' + name)
    assert state(obj) == before, name + ': reject changed state'
    checks.append(name + ': rejected and source preserved')


edge = {'id': 'edge', 'type': 'edge', 'parameters': {'width': 0.12, 'samples': 16, 'gain': 32}}
cavity = {'id': 'cavity', 'type': 'cavity', 'parameters': {'distance': 0.7, 'samples': 32, 'only_local': True}}
cube = bpy.data.objects['Cube']
cube.name = 'LowDensityCube'
# Real low-density bevel, evaluated without applying the source modifier.
bevel = cube.modifiers.new('SourceStaticBevel', 'BEVEL'); bevel.width = 0.08; bevel.segments = 1
original = bpy.data.materials.new('Original Shared Slot Material')
original.use_nodes = True
cube.data.materials.clear(); cube.data.materials.append(original); cube.data.materials.append(original)
for index, poly in enumerate(cube.data.polygons): poly.material_index = index % 2
extra_uv = cube.data.uv_layers.new(name='UnusedUV')
cube.data.uv_layers.active_index = 1; extra_uv.active_render = True
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.cycles.samples = 13
result = bake('cube_edge', cube, [edge])
assert result['maps']['edge']['maximum'] - result['maps']['edge']['minimum'] > 0.02, result
assert len(cube.modifiers) == 1
checks.append('low-density beveled cube has non-constant edge response; modifier untouched')
overlap_uv = cube.data.uv_layers['UVMap']
first_polygon, second_polygon = cube.data.polygons[0], cube.data.polygons[1]
assert first_polygon.material_index != second_polygon.material_index
saved_uv = [tuple(overlap_uv.data[i].uv) for i in second_polygon.loop_indices]
for target_loop, source_loop in zip(second_polygon.loop_indices, first_polygon.loop_indices):
    overlap_uv.data[target_loop].uv = overlap_uv.data[source_loop].uv
try: rejected('cross-material-slot UV alias', cube, [edge], code='bake_uv_overlap')
finally:
    for i, value in zip(second_polygon.loop_indices, saved_uv): overlap_uv.data[i].uv = value

# Build a connected L prism with a vertical concave corner, no internal faces.
cells = {(0, 0, 0), (1, 0, 0), (0, 1, 0)}
faces = [((-1, 0, 0), [(0,0,0),(0,0,1),(0,1,1),(0,1,0)]),
         ((1, 0, 0), [(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
         ((0,-1, 0), [(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
         ((0, 1, 0), [(0,1,0),(0,1,1),(1,1,1),(1,1,0)]),
         ((0, 0,-1), [(0,0,0),(0,1,0),(1,1,0),(1,0,0)]),
         ((0, 0, 1), [(0,0,1),(1,0,1),(1,1,1),(0,1,1)])]
vertices, polygons, lookup = [], [], {}
for cell in sorted(cells):
    for offset, corners in faces:
        if tuple(cell[i] + offset[i] for i in range(3)) in cells: continue
        indices = []
        for corner in corners:
            co = tuple(cell[i] + corner[i] for i in range(3))
            if co not in lookup: lookup[co] = len(vertices); vertices.append(co)
            indices.append(lookup[co])
        polygons.append(indices)
mesh = bpy.data.meshes.new('LPrismMesh'); mesh.from_pydata(vertices, [], polygons); mesh.update()
lshape = bpy.data.objects.new('ConcaveLPrism', mesh); bpy.context.scene.collection.objects.link(lshape)
bpy.ops.object.select_all(action='DESELECT'); lshape.select_set(True); bpy.context.view_layer.objects.active = lshape
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.03); bpy.ops.object.mode_set(mode='OBJECT')
lshape.data.uv_layers[0].name = 'UVMap'
result = bake('lshape', lshape, [edge, cavity])
assert result['maps']['cavity']['maximum'] - result['maps']['cavity']['minimum'] > 0.02, result
checks.append('L prism concave cavity response non-constant')
base = result

lshape.scale = (2, 2, 2); bpy.context.view_layer.update()
scaled = bake('scaled_lshape', lshape, [edge, cavity])
assert base['inputs']['transform_sha256'] != scaled['inputs']['transform_sha256']
assert base['inputs']['sha256'] != scaled['inputs']['sha256']
assert base['maps']['edge']['sha256'] != scaled['maps']['edge']['sha256']
assert base['maps']['cavity']['sha256'] != scaled['maps']['cavity']['sha256']
checks.append('scale changes transform/input fingerprints and actual edge/cavity PNGs')

# Nearby non-target geometry must not alter target-local AO or its fingerprints.
lshape.scale = (1, 1, 1); bpy.context.view_layer.update()
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.1, 1.1, 0.5)); blocker = bpy.context.object
blocker.name = 'NonTargetOccluder'
occluded = bake('non_target_isolation', lshape, [cavity])
assert base['maps']['cavity']['sha256'] == occluded['maps']['cavity']['sha256']
assert base['inputs']['sha256'] == occluded['inputs']['sha256']
checks.append('non-target occluder excluded, target-local AO bytes and fingerprint unchanged')
array_modifier = lshape.modifiers.new('EvaluatedUVAliasing', 'ARRAY')
array_modifier.count = 2; array_modifier.relative_offset_displace = (3, 0, 0)
try: rejected('evaluated modifier UV alias', lshape, [edge], code='bake_uv_overlap')
finally: lshape.modifiers.remove(array_modifier)

fingerprint = module._mesh_fingerprint(lshape.data, 'UVMap')
lshape.data.vertices[0].co.x -= 0.01; lshape.data.update()
changed = module._mesh_fingerprint(lshape.data, 'UVMap')
assert changed['geometry_sha256'] != fingerprint['geometry_sha256']
lshape.data.vertices[0].co.x += 0.01; lshape.data.update()
before_uv = module._mesh_fingerprint(lshape.data, 'UVMap')
lshape.data.uv_layers['UVMap'].data[0].uv.x += 0.001
after_uv = module._mesh_fingerprint(lshape.data, 'UVMap')
assert before_uv['uv_sha256'] != after_uv['uv_sha256']
lshape.data.uv_layers['UVMap'].data[0].uv.x -= 0.001
before_normal = module._mesh_fingerprint(lshape.data, 'UVMap')
for p in lshape.data.polygons: p.use_smooth = True
lshape.data.update()
after_normal = module._mesh_fingerprint(lshape.data, 'UVMap')
assert before_normal['normal_sha256'] != after_normal['normal_sha256']
for p in lshape.data.polygons: p.use_smooth = False
lshape.data.update()
checks.append('real geometry/UV/split-normal edits change corresponding fingerprints')

rejected('duplicate IDs including case aliases', lshape, [edge, {**edge, 'id': 'EDGE'}])
rejected('missing UV', lshape, [edge], uv='MissingUV')
rejected('non-local AO scope', lshape, [{**cavity, 'parameters': {'only_local': False}}], 'unsupported_mesh_map_scope')
rejected('zero width', lshape, [{**edge, 'parameters': {'width': 0}}])
rejected('non-finite distance', lshape, [{**cavity, 'parameters': {'distance': float('nan')}}])
rejected('too large output', lshape, [edge], size=4096)
rejected('path traversal id', lshape, [{**edge, 'id': '../escape'}])
rejected('unknown parameter', lshape, [{**edge, 'parameters': {'unknown': 4}}])
rejected('invalid non-string type', lshape, [{**edge, 'type': []}])
rejected('Windows reserved map filename', lshape, [{**edge, 'id': 'CON'}])
uv_values = [tuple(c.uv) for c in lshape.data.uv_layers['UVMap'].data]
for c in lshape.data.uv_layers['UVMap'].data: c.uv = (0.5, 0.5)
try: rejected('degenerate UV layer', lshape, [edge])
finally:
    for c, co in zip(lshape.data.uv_layers['UVMap'].data, uv_values): c.uv = co
lshape.data.uv_layers['UVMap'].data[0].uv.x = 1.2
try: rejected('UDIM/outside tile UV', lshape, [edge])
finally: lshape.data.uv_layers['UVMap'].data[0].uv = uv_values[0]
dynamic = lshape.modifiers.new('UnsupportedDynamicNodes', 'NODES')
try: rejected('dynamic modifier scope', lshape, [edge])
finally: lshape.modifiers.remove(dynamic)
visibility = lshape.modifiers.new('VisibilityMismatch', 'BEVEL'); visibility.show_render = False
try: rejected('modifier render/viewport mismatch', lshape, [edge])
finally: lshape.modifiers.remove(visibility)
no_uv_mesh = lshape.data.copy(); no_uv_mesh.name = 'NoUVMesh'
for layer in list(no_uv_mesh.uv_layers): no_uv_mesh.uv_layers.remove(layer)
no_uv_obj = bpy.data.objects.new('NoUVObject', no_uv_mesh)
bpy.context.scene.collection.objects.link(no_uv_obj)
rejected('object has no UV layers', no_uv_obj, [edge])
for invalid_obj in (None, 'not-an-object'):
    try: module.bake_mesh_maps(invalid_obj, 'UVMap', [edge], RUN, 64)
    except WorkflowError as error: assert error.code == 'invalid_mesh_map'
    else: raise AssertionError('invalid target accepted')
checks.append('invalid target types rejected through WorkflowError')
default_size = bake('default_512', lshape, [{'id': 'default_edge', 'type': 'edge'}], 512)
assert default_size['maps']['default_edge']['width'] == 512
checks.append('default-style 512x512 PNG has real baked edge data')

before = state(lshape)
original_builder = module._build_material
counter = [0]
def inject(kind, params, image, token, owned):
    counter[0] += 1
    if counter[0] == 2: raise RuntimeError('injected second map failure')
    return original_builder(kind, params, image, token, owned)
module._build_material = inject
try:
    try: module.bake_mesh_maps(lshape, 'UVMap', [edge, cavity], RUN, 64)
    except WorkflowError as error: assert error.code == 'mesh_map_bake_failed'
    else: raise AssertionError('fault did not execute')
finally:
    module._build_material = original_builder
assert state(lshape) == before
checks.append('injected mid-batch failure restores context, slots, UV and all temporary datablocks')
assert len({r['output_dir'] for r in results.values()}) == len(results)
checks.append('every call uses a distinct output directory; no blind cache/reuse')

report = {'status': 'pass', 'blender_version': bpy.app.version_string,
    'blender_build_hash': bpy.app.build_hash.decode(), 'checks': checks, 'results': results,
    'limitations': ['target-only AO; only_local=false rejected',
        'whole-object UV tile0..1 overlap check includes all slots; evaluated Bevel-only zero-area strips allowed',
        'renderer-derived edge/cavity masks, not curvature',
        'static viewport modifier evaluation; mismatched visibility/dynamic modifiers rejected',
        'CPU Cycles, PNG 8-bit, fixed bake sample seed defaults; no cache',
        'failure may retain a partial unique output directory without a complete manifest']}
(RUN / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MESH_MAP_TEST_REPORT=' + str(RUN / 'report.json'))
print(json.dumps({'status': 'pass', 'checks': len(checks), 'run': str(RUN)}))
