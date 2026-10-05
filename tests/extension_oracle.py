# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent Blender reopen of an installed-extension operator result."""
import json
from pathlib import Path
import sys
import bpy

folder = Path(sys.argv[sys.argv.index('--') + 1]).resolve(strict=True)
bpy.ops.wm.open_mainfile(filepath=str(folder / 'installed-material.blend'), load_ui=False, use_scripts=False)
cube = bpy.data.objects['IndependentCube']
assert len(cube.data.vertices) == 8 and len(cube.data.polygons) == 6
assert cube.data.uv_layers.get('UVMap')
material = cube.material_slots[0].material
assert material.use_nodes
assert material.get('mw_id') == 'IndependentMaterial', dict(material.items())
assert any(n.bl_idname == 'ShaderNodeBsdfPrincipled' for n in material.node_tree.nodes)
result = {'ok': True, 'blender': bpy.app.version_string, 'material': material.name,
          'geometry_uv_preserved': True, 'managed_nodes_preserved': True}
(folder / 'reopen.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
