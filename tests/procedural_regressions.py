# SPDX-License-Identifier: GPL-3.0-or-later
"""Focused real-Blender graph/protection, bake and preview-lifetime regressions.
All fixtures and outputs are owned by this new background-process invocation.
"""
import sys
sys.dont_write_bytecode = True
import copy
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
RUN = prepare_output('regressions', require_blender=True)

from material_workflow_addon.contract import WorkflowError
from material_workflow_addon.procedural_contract import normalize_manifest
from material_workflow_addon import procedural_core as core, engine_compat as compat, preview
from material_workflow_addon.procedural_bake import bake_channels
from material_workflow_addon.procedural_examples import make_recipe

checks=[]
files=[Path(core.__file__),Path(compat.__file__),Path(preview.__file__)]
production_before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def passed(name,**facts):checks.append({'name':name,'status':'pass',**facts})


def material(obj):return obj.material_slots[0].material


def state(obj):
    mat=material(obj)
    return {'materials':sorted(bpy.data.materials.keys()),'images':sorted(bpy.data.images.keys()),
        'groups':sorted(bpy.data.node_groups.keys()),'meshes':sorted(bpy.data.meshes.keys()),
        'objects':sorted(bpy.data.objects.keys()),'scenes':sorted(bpy.data.scenes.keys()),
        'slots':[(s.link,s.material.name if s.material else None) for s in obj.material_slots],
        'active':bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
        'selected':sorted(o.name for o in bpy.context.selected_objects),
        'uv':[(u.name,u.active_render) for u in obj.data.uv_layers],
        'scene':bpy.context.scene.name,'layer':bpy.context.view_layer.name,
        'engine':bpy.context.scene.render.engine,'samples':bpy.context.scene.cycles.samples,
        'filepath':bpy.data.filepath,'matrix':[list(row) for row in obj.matrix_world],
        'fake_user':mat.use_fake_user if mat else None,
        'graph':core._snapshot(mat) if mat and mat.use_nodes else None,
        'properties':dict(mat.items()) if mat else None}


def reject(call,code,obj=None):
    before=state(obj) if obj else None
    try:call()
    except WorkflowError as error:assert error.code==code,(error.code,str(error))
    else:raise AssertionError('expected '+code)
    if obj:assert state(obj)==before,'rejection mutated source/context/datablocks'


def recipe(identity,obj):
    return normalize_manifest({'schema_version':'2.0',
        'context':{'scene':bpy.context.scene.name,'view_layer':bpy.context.view_layer.name,'frame':1},
        'target':{'object':obj.name,'material_slot':0,'uv_layer':'UVMap'},
        'material':{'id':identity,'name':'Regression '+identity,'template':'procedural_pbr_v1'},
        'signals':[
            {'id':'color','type':'constant','parameters':{'value':[0.3,0.13,0.04,1]},'inputs':{}},
            {'id':'rough','type':'constant','parameters':{'value':0},'inputs':{}},
            {'id':'fine','type':'noise','parameters':{'scale':4,'detail':0,'roughness':0.5,'distortion':0,
                'seed':0,'coordinate':{'space':'OBJECT','scale':[1,1,1]}},'inputs':{}}],
        'layers':[{'id':'base','name':'Base','values':{'metallic':0,'coat_weight':0},
                   'channels':{'base_color':'color','roughness':'rough','height':'fine'}}],
        'height_distance':0.0003,'mesh_map_size':128,
        'preview':{'engine':'CYCLES','device':{'backend':'CPU'},'width':128,'height':128,
                   'samples':4,'views':[{'id':'test'}]}})


obj=bpy.data.objects['Cube'];original=recipe('float_controls',obj)
core.apply_material(original,work_dir=RUN/'initial')
mat=material(obj);root=mat.node_tree.nodes['MWP Controls']
for key in ('S/rough/value','S/fine/detail','S/fine/distortion','L/base/metallic','L/base/coat_weight'):
    assert root.inputs[key].default_value==0
    root.inputs[key].default_value=0.5
live=core.get_stored_manifest(mat)
assert live['signals'][1]['parameters']['value']==0.5
assert live['signals'][2]['parameters']['detail']==0.5
assert live['signals'][2]['parameters']['distortion']==0.5
assert live['layers'][0]['values']['metallic']==0.5
assert live['layers'][0]['values']['coat_weight']==0.5
template=core.save_template(mat,RUN/'float-template.json')
core.apply_material(original,work_dir=RUN/'float-update')
assert core.get_stored_manifest(material(obj))['signals'][1]['parameters']['value']==0.5
passed('legitimate numeric fields originally integer zero accept live float .5, template export and three-way update',template=template)

mat=material(obj);root=mat.node_tree.nodes['MWP Controls']
root.inputs['S/fine/seed'].default_value=0.5
reject(lambda:core.get_stored_manifest(mat),'invalid_parameter',obj)
root.inputs['S/fine/seed'].default_value=0
passed('only schema-integer seed rejects fractional live value')
bake=bake_channels(obj,mat,RUN/'float-bake',{'channels':['base_color','roughness','metallic','normal'],
    'size':64,'margin':8,'samples':4,'bit_depth':'16'},uv_layer='UVMap')
assert bake['status']=='complete' and bake['delivery']['disk_decode_verified']
passed('legal float controls also pass real 64px PBR image export',report=bake['report_file'])

mat=material(obj);mat.node_tree.nodes['MWP Controls'].inputs['S/rough/value'].default_value=0.73
same=core.get_stored_manifest(mat)
core.apply_material(same,work_dir=RUN/'same-value-update')
assert abs(core.get_stored_manifest(material(obj))['signals'][1]['parameters']['value']-0.73)<1e-6
passed('incoming value equal to live manual edit accepted')
mat=material(obj);baseline=json.loads(mat[core.MANIFEST])
mat.node_tree.nodes['MWP Controls'].inputs['S/rough/value'].default_value=0.69
different=copy.deepcopy(baseline);different['signals'][1]['parameters']['value']=0.82
reject(lambda:core.apply_material(different,work_dir=RUN/'overlap'),'managed_conflict',obj)
mat.node_tree.nodes['MWP Controls'].inputs['S/rough/value'].default_value=baseline['signals'][1]['parameters']['value']
passed('overlapping different incoming/manual values rejected with full state preserved')

mat.use_fake_user=True
reject(lambda:core.apply_material(baseline,work_dir=RUN/'fake-user'),'protected_material',obj)
mat.use_fake_user=False
passed('Fake User retained author update rejected before any mutation')

unrelated=bpy.data.node_groups.new('UnrelatedGroupDoNotDelete','ShaderNodeTree')
unrelated[core.KEY]=mat[core.KEY];unrelated['sentinel']='unrelated group despite copied metadata tag'
unrelated.nodes.new('ShaderNodeValue').outputs[0].default_value=0.123
unrelated_pointer=unrelated.as_pointer()
mat['mwp_group_name']=unrelated.name
core.apply_material(baseline,work_dir=RUN/'group-spoof')
assert bpy.data.node_groups.get(unrelated.name).as_pointer()==unrelated_pointer
assert unrelated['sentinel']=='unrelated group despite copied metadata tag'
passed('spoofed mwp_group_name cannot delete unrelated group, even with copied ownership tag')

mat=material(obj)
for engine in compat.ENGINES:
    evidence=compat.validate_material(mat,engine)
    assert evidence['scope']=='managed_procedural_surface' and 'ShaderNodeTexNoise' in evidence['node_types']
passed('new managed procedural Noise/Object-coordinate path validates in Cycles and Eevee',engines=list(compat.ENGINES))
plain=bpy.data.materials.new('UnmanagedNoise');plain.use_nodes=True
plain.node_tree.nodes.new('ShaderNodeTexNoise')
for engine in compat.ENGINES:reject(lambda e=engine:compat.validate_material(plain,e),'unsupported_node')
passed('unmanaged Noise retains legacy rejection in both engines')
plain[core.KEY]='forged-label';plain[core.MANIFEST]=json.dumps(baseline)
assert core.STATE not in plain
for engine in compat.ENGINES:reject(lambda e=engine:compat.validate_material(plain,e),'managed_conflict')
passed('forged managed labels/manifest without state do not bypass engine subset')

mat=material(obj);group=mat.node_tree.nodes['MWP Controls'].node_tree
coord=next(n for n in group.nodes if n.bl_idname=='ShaderNodeTexCoord')
external=bpy.data.objects.new('ExternalCoordinateAnchor',None);bpy.context.scene.collection.objects.link(external)
external.location=(2,3,4);coord.object=external
assert not core.verify_managed_state(mat)['ok']
reject(lambda:core.get_stored_manifest(mat),'managed_conflict',obj)
for engine in compat.ENGINES:reject(lambda e=engine:compat.validate_material(mat,e),'managed_conflict')
coord.object=None
assert core.verify_managed_state(mat)['ok']
passed('TexCoord.object pointer edit detected by managed snapshot and both engine routes')
tamper=group.nodes.new('ShaderNodeValue')
for engine in compat.ENGINES:reject(lambda e=engine:compat.validate_material(mat,e),'managed_conflict')
group.nodes.remove(tamper)
assert core.verify_managed_state(mat)['ok']
passed('disconnected graph tampering rejects managed Cycles/Eevee acceptance')

bpy.ops.mesh.primitive_cube_add(location=(4,0,0));image_obj=bpy.context.object;image_obj.name='ImageRegressionCube'
image=bpy.data.images.new('SourceImageFixture',width=4,height=4)
image.pixels=[0.2,0.4,0.6,1]*16;image.file_format='PNG';image.filepath_raw=str(RUN/'input-color.png');image.save()
bpy.data.images.remove(image)
record={'file':str(RUN/'input-color.png'),'expected_sha256':hashlib.sha256((RUN/'input-color.png').read_bytes()).hexdigest(),'color_space':'sRGB'}
image_recipe=recipe('image_integrity',image_obj)
image_recipe['signals'][0]={'id':'color','type':'image','parameters':{'image':record,'output':'COLOR'},'inputs':{}}
image_recipe=normalize_manifest(image_recipe);core.apply_material(image_recipe,work_dir=RUN/'image-create')
image_mat=material(image_obj);image_group=image_mat.node_tree.nodes['MWP Controls'].node_tree
packed=next(n.image for n in image_group.nodes if n.bl_idname=='ShaderNodeTexImage')
initial=packed.pixels[0];packed.pixels[0]=0.87;packed.update()
assert not core.verify_managed_state(image_mat)['ok']
reject(lambda:core.apply_material(image_recipe,work_dir=RUN/'image-mutated'),'managed_conflict',image_obj)
for engine in compat.ENGINES:reject(lambda e=engine:compat.validate_material(image_mat,e),'managed_conflict')
packed.pixels[0]=initial;packed.update()
assert core.verify_managed_state(image_mat)['ok']
passed('packed image pixel mutation detected without disk SHA change and source remains protected')

before=state(image_obj);original_build=core.Builder.build
def failed_build(self):
    original_build(self)
    raise RuntimeError('injected failure after graph and image creation')
core.Builder.build=failed_build
fresh=copy.deepcopy(image_recipe);fresh['material']['id']='failed_build_identity'
try:
    try:core.apply_material(fresh,work_dir=RUN/'failed-build')
    except RuntimeError as error:assert 'injected failure' in str(error)
    else:raise AssertionError('build failure injection not reached')
finally:core.Builder.build=original_build
assert state(image_obj)==before
passed('failure after real graph/image creation restores binding and removes all new groups/materials/images')
invalid=copy.deepcopy(image_recipe);invalid['layers'][0]['values']['metallic']=float('nan')
reject(lambda:core.apply_material(invalid,work_dir=RUN/'invalid'),'INVALID_REQUEST',image_obj)
invalid=copy.deepcopy(image_recipe);invalid['target']['uv_layer']='MissingUV'
reject(lambda:core.apply_material(invalid,work_dir=RUN/'missing-uv'),'missing_uv',image_obj)
passed('illegal numeric input and missing UV reject with exact source/context/datablock preservation')

# Regression for persistent preview meshes accidentally retaining temporary
# depsgraph-evaluated Material IDs. Exercise a ring with packed geometry maps,
# repeated rig construction and both soft/raking scene rebuilds/renders.
bpy.ops.mesh.primitive_torus_add(major_radius=0.46,minor_radius=0.015,
    major_segments=48,minor_segments=8,location=(0,0,1.0))
ring=bpy.context.object;ring.name='BarrelRib1ReferenceRegression'
for p in ring.data.polygons:p.use_smooth=True
ring_recipe=make_recipe('painted_metal',
    {'scene':bpy.context.scene.name,'view_layer':bpy.context.view_layer.name,'frame':1},
    {'object':ring.name,'material_slot':0,'uv_layer':'UVMap'},'ring_reference_lifetime')
ring_recipe['mesh_map_size']=128;ring_recipe['preview'].update(width=64,height=64,samples=2,denoise=False)
ring_recipe=normalize_manifest(ring_recipe)
core.apply_material(ring_recipe,work_dir=RUN/'ring-material')
ring_material=material(ring);source_scene=bpy.context.scene
source_state={'graph':core._snapshot(ring_material),
    'matrix':[list(row) for row in ring.matrix_world],
    'uv':[list(c.uv) for c in ring.data.uv_layers['UVMap'].data],
    'mesh':ring.data.as_pointer(),'users':ring_material.users}
evidence=[];directory=RUN/'preview-references';directory.mkdir()
for cycle in range(2):
    source_scene.frame_set(1);bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get();depsgraph.update()
    evaluated_material=ring.evaluated_get(depsgraph).material_slots[0].material
    evaluated_was_temporary=evaluated_material.is_evaluated
    assert evaluated_was_temporary and evaluated_material.as_pointer()!=ring_material.as_pointer()
    banks={name:set(getattr(bpy.data,name)) for name in ('objects','scenes','meshes','materials','cameras','lights','worlds')}
    rig=preview.build_preview(ring_recipe,ring)
    try:
        assert rig['object'].data is not ring.data
        for i,view in enumerate(ring_recipe['preview']['views']):
            for slot in rig['object'].material_slots:
                assert slot.material==ring_material and not slot.material.is_evaluated
                assert slot.material.original==ring_material and not slot.material.node_tree.is_evaluated
            preview.configure_view(rig,view)
            source_scene.frame_set(i+2);bpy.context.view_layer.update()
            bpy.context.evaluated_depsgraph_get().update()
            rig['scene'].frame_set(i+2);rig['view_layer'].update()
            path=directory/('cycle'+str(cycle+1)+'-'+view['id']+'.png')
            rig['scene'].render.filepath=str(path)
            bpy.ops.render.render(write_still=True,scene=rig['scene'].name)
            data=path.read_bytes();assert struct.unpack('>II',data[16:24])==(64,64)
            image=bpy.data.images.load(str(path),check_existing=False)
            try:assert len(image.pixels)==64*64*4
            finally:bpy.data.images.remove(image)
            assert rig['object'].material_slots[0].material.as_pointer()==ring_material.as_pointer()
            assert not rig['object'].material_slots[0].material.is_evaluated
            assert core._snapshot(ring_material)==source_state['graph']
            assert ring.data.as_pointer()==source_state['mesh']
            assert [list(row) for row in ring.matrix_world]==source_state['matrix']
            assert [list(c.uv) for c in ring.data.uv_layers['UVMap'].data]==source_state['uv']
            evidence.append({'cycle':cycle+1,'view':view['id'],'file':str(path),'bytes':len(data),
                'width':64,'height':64,'source_evaluated_id_was_temporary':evaluated_was_temporary,
                'preview_material_is_original':True,'preview_material_is_evaluated':False,
                'source_graph_fingerprint_unchanged':True})
    finally:
        source_scene.frame_set(1)
        for item in set(bpy.data.objects)-banks['objects']:bpy.data.objects.remove(item,do_unlink=True)
        for item in set(bpy.data.scenes)-banks['scenes']:bpy.data.scenes.remove(item)
        for name in ('meshes','materials','cameras','lights','worlds'):
            collection=getattr(bpy.data,name)
            for item in set(collection)-banks[name]:
                if item.users==0:collection.remove(item)
    assert ring_material.users==source_state['users']
    assert core._snapshot(ring_material)==source_state['graph']
passed('two repeated soft/raking previews retain original material IDs after frame/depsgraph rebuilds and four real renders',
       views=evidence,scope='64px repeated lifecycle regression; not a 2K memory/driver stability proof')

production_after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
assert production_after==production_before,'production code changed during this acceptance run'
report={'status':'pass','blender':bpy.app.version_string,'build':bpy.app.build_hash.decode(),
    'checks':checks,'production_sha256':production_after,
    'limitations':['isolated factory-startup background process; no user GUI session touched',
        'engine checks validate runtime compatibility routes; not visual cross-engine equivalence',
        '64px real PBR export here; 2K/fixture visual acceptance belongs to separate final suite']}
(RUN/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PROCEDURAL_REGRESSION_REPORT='+str(RUN/'report.json'))
print(json.dumps({'status':'pass','checks':len(checks),'run':str(RUN)}))
