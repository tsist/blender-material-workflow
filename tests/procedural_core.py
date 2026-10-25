# SPDX-License-Identifier: GPL-3.0-or-later
"""Real Blender graph, parameter protection, export and reopen smoke tests."""
import sys
sys.dont_write_bytecode = True
import bpy, copy, json, pathlib, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
root = prepare_output('core', require_blender=True)
from material_workflow_addon import procedural_core as core
from material_workflow_addon.procedural_contract import normalize_manifest
from material_workflow_addon.procedural_bake import bake_channels, rebuild_material
from material_workflow_addon.contract import WorkflowError

checks=[]
def check(name, value):
    checks.append({'name':name,'pass':bool(value)})
    if not value: raise AssertionError(name)
    print('PASS',name,flush=True)

def signal(identity, kind, parameters=None, inputs=None):
    return {'id':identity,'type':kind,'parameters':parameters or {},'inputs':inputs or {}}

bpy.ops.wm.read_factory_settings(use_empty=False)
obj=bpy.data.objects['Cube']
spec={'schema_version':'2.0','context':{'scene':'Scene','view_layer':'ViewLayer'},
      'target':{'object':'Cube','uv_layer':'UVMap'},'material':{'id':'core_smoke','name':'Core Smoke'},
      'signals':[signal('grain','noise',{'scale':4}),signal('rough','constant',{'value':.35}),
                 signal('color','ramp',{'stops':[{'position':0,'color':[.03,.07,.12,1]},{'position':1,'color':[.1,.2,.32,1]}]}, {'value':'grain'})],
      'layers':[{'id':'base','name':'Metal','channels':{'base_color':'color','roughness':'rough'},'values':{'metallic':1}}],
      'preview':{'device':{'backend':'CPU'},'views':[{'id':'front'}]}}
try:
    result=core.apply_material(spec,work_dir=str(root/'first'))
    material=obj.material_slots[0].material
    check('build_and_verified',core.verify_managed_state(material)['ok'])
    check('object_link_preserved',obj.material_slots[0].link=='OBJECT')
    controls=material.node_tree.nodes['MWP Controls']
    controls.inputs['S/rough/value'].default_value=.46
    live=core.get_stored_manifest(material)
    check('live_parameter_export',abs(live['signals'][1]['parameters']['value']-.46)<1e-6)
    incoming=copy.deepcopy(spec);incoming['signals'][0]['parameters']['scale']=6
    core.apply_material(incoming,work_dir=str(root/'update'))
    material=obj.material_slots[0].material
    check('disjoint_manual_parameter_preserved',abs(core.get_stored_manifest(material)['signals'][1]['parameters']['value']-.46)<1e-6)
    material.node_tree.nodes['MWP Controls'].inputs['S/rough/value'].default_value=.55
    incoming['signals'][1]['parameters']['value']=.65
    try: core.apply_material(incoming,work_dir=str(root/'conflict'))
    except WorkflowError as e: check('overlapping_edit_rejected',e.code=='managed_conflict')
    else: check('overlapping_edit_rejected',False)
    group=material.node_tree.nodes['MWP Controls'].node_tree
    coord=next(n for n in group.nodes if n.type=='TEX_COORD')
    empty=bpy.data.objects.new('Reference',None);bpy.context.scene.collection.objects.link(empty)
    coord.object=empty
    check('coordinate_pointer_edit_detected',not core.verify_managed_state(material)['ok'])
    coord.object=None
    check('coordinate_restore',core.verify_managed_state(material)['ok'])
    template=core.save_template(material,str(root/'template.json'))
    report=bake_channels(obj,material,str(root/'export'),{'size':128,'samples':4,'channels':['base_color','roughness','metallic','normal'],'margin':4,'bit_depth':'16'})
    check('bake_complete',report['status']=='complete')
    check('post_bake_author_unchanged',core.verify_managed_state(material)['ok'])
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'author.blend'))
    rebuilt=rebuild_material(report)
    obj.material_slots[0].material=rebuilt
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'reconstructed.blend'))
    bpy.ops.wm.open_mainfile(filepath=str(root/'author.blend'))
    material=bpy.data.objects['Cube'].material_slots[0].material
    check('author_reopen_verified',core.verify_managed_state(material)['ok'])
    bpy.ops.wm.open_mainfile(filepath=str(root/'reconstructed.blend'))
    rebuilt=bpy.data.objects['Cube'].material_slots[0].material
    check('rebuilt_no_procedural_groups',not any(n.type=='GROUP' for n in rebuilt.node_tree.nodes))
    check('normal_no_double_bump',not any(n.type=='BUMP' for n in rebuilt.node_tree.nodes))
finally:
    (root/'checks.json').write_text(json.dumps({'checks':checks,'root':str(root)},indent=2),encoding='utf8')
    print('CORE_REPORT',root/'checks.json',flush=True)
