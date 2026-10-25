# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.dont_write_bytecode = True
"""Real background operator checks; never attach to the user's GUI process."""
import hashlib
import json
import math
from pathlib import Path
import sys
import tomllib
import uuid

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
RUN = prepare_output('ui', require_blender=True)
import material_workflow_addon as addon
from material_workflow_addon import procedural_ui as ui, procedural_core as core

checks = []


def passed(name, **evidence):
    checks.append({'name': name, 'status': 'pass', **evidence})


def operator(name):
    result = getattr(bpy.ops.material_workflow, name)()
    assert result == {'FINISHED'}, (name, result, bpy.context.scene.mwp_ui_error)
    return json.loads(Path(bpy.context.scene.mwp_ui_last_report).read_text(encoding='utf-8'))


def rejected(name):
    try: result = getattr(bpy.ops.material_workflow, name)()
    except RuntimeError: result = {'CANCELLED'}
    assert result == {'CANCELLED'} and bpy.context.scene.mwp_ui_error


def protected_state(obj):
    return {'filepath': bpy.data.filepath, 'scene': bpy.context.scene.name,
        'window_scene': bpy.context.window.scene.name, 'layer': bpy.context.view_layer.name,
        'active': bpy.context.view_layer.objects.active.name,
        'selected': sorted(o.name for o in bpy.context.selected_objects),
        'engine': bpy.context.scene.render.engine, 'samples': bpy.context.scene.cycles.samples,
        'uv': [(u.name, u.active_render) for u in obj.data.uv_layers],
        'uv_active': obj.data.uv_layers.active_index,
        'matrix': [float(x) for row in obj.matrix_world for x in row],
        'mesh': [list(v.co) for v in obj.data.vertices],
        'polygon_slots': [p.material_index for p in obj.data.polygons],
        'slots': [(s.link, s.material.name if s.material else None) for s in obj.material_slots]}


class _Layout:
    """Check draw's RNA references without claiming visible layout acceptance."""
    def __init__(self): self.calls = []
    def row(self, **kwargs): return self
    def box(self): return self
    def label(self, **kwargs): self.calls.append(('label', kwargs.get('text')))
    def prop(self, owner, field, **kwargs):
        assert hasattr(owner, field), (owner, field)
        self.calls.append(('prop', field))
    def prop_search(self, owner, field, search, collection, **kwargs):
        assert hasattr(owner, field) and hasattr(search, collection)
        self.calls.append(('search', field))
    def operator(self, name, **kwargs):
        self.calls.append(('operator', name)); return self


addon.register()
try:
    assert addon.bl_info['version'] == (0, 8, 0)
    assert tomllib.loads((ROOT/'blender_manifest.toml').read_text())['version'] == '0.8.0'
    assert hasattr(bpy.types.Scene, 'mwp_ui_work_dir')
    assert bpy.types.MWP_PT_procedural.bl_category == 'Material Workflow'
    passed('whole-addon registration and both version metadata 0.8.0')
    scene = bpy.context.scene; obj = bpy.data.objects['Cube']
    bpy.context.view_layer.objects.active=obj; bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    scene.render.engine='BLENDER_EEVEE'; scene.cycles.samples=11
    scene.mwp_ui_work_dir=str(RUN);scene.mwp_ui_mesh_size='128';scene.mwp_ui_export_size='128'
    scene.mwp_ui_bake_samples=4;scene.mwp_ui_family='wood';scene.mwp_ui_seed=7
    scene.mwp_ui_grain_axis='Z';scene.mwp_ui_metal_region='lower'
    assert tuple(scene.mwp_ui_timber_scale)==(1,1,1)
    scene.mwp_ui_timber_scale=(.125,.25,1.5)
    scene.mwp_ui_name='UI Procedural Wood';scene.mwp_ui_slot=0
    before=protected_state(obj)
    created=operator('procedural_create')
    author=ui.current_material(bpy.context);identity=author[core.KEY]
    assert core.verify_managed_state(author)['ok'] and not author.use_fake_user
    actual=core.get_stored_manifest(author)
    timber=next(s for s in actual['signals'] if s['id']=='timber_coordinates')
    assert abs(timber['parameters']['coordinate']['rotation'][1]-math.pi/2)<1e-6
    assert timber['parameters']['coordinate']['scale']==[.125,.25,1.5]
    assert before['scene']==bpy.context.scene.name and before['engine']==scene.render.engine and bpy.data.filepath==''
    passed('actual create operator builds public wood recipe on current UV/slot', material=author.name, receipt=scene.mwp_ui_last_report)
    layout=_Layout();ui.MWP_PT_panel.draw(type('DrawContext',(),{'layout':layout})(),bpy.context)
    assert ('prop','mwp_ui_grain_axis') in layout.calls
    assert ('prop','mwp_ui_timber_scale') in layout.calls

    root=author.node_tree.nodes['MWP Controls']
    root.inputs['L/timber/coat_weight'].default_value=0.31
    root.inputs['S/satin_roughness/to_min'].default_value=0.41
    controls=ui.visible_controls(author,'LAYER','coat_weight')
    assert any(s.as_pointer()==root.inputs['L/timber/coat_weight'].as_pointer() for s in controls)
    assert ui.visible_controls(author,'SIGNAL','satin_roughness/to_min')[0].default_value>0.40
    actual=core.get_stored_manifest(author)
    assert abs(actual['layers'][0]['values']['coat_weight']-0.31)<1e-6
    passed('visible controls bind actual root sockets and live edits are readable')
    # New-preset widgets must not reset an existing author's live controls.
    scene.mwp_ui_family='glass_clear';scene.mwp_ui_seed=999;scene.mwp_ui_weathering=0
    scene.mwp_ui_grain_axis='X';scene.mwp_ui_metal_region='seam'
    scene.mwp_ui_timber_scale=(2,3,4)
    updated=operator('procedural_update');author=ui.current_material(bpy.context)
    actual=core.get_stored_manifest(author)
    assert author[core.KEY]==identity and abs(actual['layers'][0]['values']['coat_weight']-0.31)<1e-6
    assert any(s['id']=='growth_rings' for s in actual['signals'])
    assert abs(next(s for s in actual['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']['rotation'][1]-math.pi/2)<1e-6
    assert next(s for s in actual['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']['scale']==[.125,.25,1.5]
    assert abs(next(s for s in actual['signals'] if s['id']=='satin_roughness')['parameters']['to_min']-0.41)<1e-6
    passed('update keeps material ID, live layer/signal edits and family despite changed new-preset widgets')

    saved=operator('procedural_template_save')
    template_path=Path(scene.mwp_ui_json_path);template=json.loads(template_path.read_text(encoding='utf-8'))
    assert template['schema']=='material-procedural-template-1.0'
    assert abs(template['manifest']['layers'][0]['values']['coat_weight']-0.31)<1e-6
    passed('save template records current actual controls in unique directory', file=str(template_path))
    bpy.ops.mesh.primitive_cube_add(location=(3,0,0));other=bpy.context.object;other.name='UI_TemplateTarget'
    other.data.uv_layers.active.name='ExplicitSecondUV';scene.mwp_ui_uv='ExplicitSecondUV'
    source_before=core.get_stored_manifest(author)
    loaded=operator('procedural_load');current=ui.current_material(bpy.context)
    rebound=core.get_stored_manifest(current)
    assert current[core.KEY]!=identity and rebound['target']=={
        'object':other.name,'material_slot':0,'uv_layer':'ExplicitSecondUV'}
    assert rebound['context']['scene']==scene.name and rebound['context']['view_layer']==bpy.context.view_layer.name
    assert core.get_stored_manifest(author)==source_before
    assert abs(rebound['layers'][0]['values']['coat_weight']-0.31)<1e-6
    assert next(s for s in rebound['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']['scale']==[.125,.25,1.5]
    passed('JSON template load creates fresh identity, binds current target/UV/context and preserves source', new_id=current[core.KEY])

    scene.mwp_ui_show_controls=True;scene.mwp_ui_control_scope='SIGNAL';scene.mwp_ui_control_filter='satin_roughness'
    layout=_Layout();ui.MWP_PT_panel.draw(type('DrawContext',(),{'layout':layout})(),bpy.context)
    assert ('prop','default_value') in layout.calls
    passed('background panel draw RNA references resolve with filtered live controls; visual layout not asserted')

    before=protected_state(other);before_snapshot=core._snapshot(current);fake_before=current.use_fake_user
    exported=operator('procedural_export')
    assert protected_state(other)==before
    assert current.use_fake_user==fake_before==False and core._snapshot(current)==before_snapshot
    assert exported['author_binding_retained'] and ui.current_material(bpy.context)==current
    rebuilt=bpy.data.materials[exported['rebuilt_material']]
    assert rebuilt.use_fake_user and core.KEY not in rebuilt
    assert not any(n.bl_idname in {'ShaderNodeTexNoise','ShaderNodeTexWave','ShaderNodeBevel','ShaderNodeAmbientOcclusion','ShaderNodeGroup'} for n in rebuilt.node_tree.nodes)
    report=json.loads(Path(exported['report_file']).read_text(encoding='utf-8'))
    assert report['status']=='complete' and report['delivery']['disk_decode_verified']
    assert set(report['channels'])==set(ui.EXPORT_CHANNELS)
    assert all(e['width']==128 and e['height']==128 and e['decoded'] for e in report['channels'].values())
    library=Path(exported['rebuilt_library']['file'])
    assert hashlib.sha256(library.read_bytes()).hexdigest()==exported['rebuilt_library']['sha256']
    with bpy.data.libraries.load(str(library),link=False) as (source,destination):
        assert source.materials==[rebuilt.name]
    passed('actual 128px full-channel bake/report and standalone texture-material library; author/context preserved',
           receipt=scene.mwp_ui_last_report, library=str(library), bake_report=exported['report_file'])
    previous_id=current[core.KEY];operator('procedural_update');current=ui.current_material(bpy.context)
    assert current[core.KEY]==previous_id and not current.use_fake_user
    passed('author remains updateable after export; fake-user applies only to new rebuilt material')

    before=protected_state(other); scene.mwp_ui_work_dir='relative-output'
    rejected('procedural_create');assert protected_state(other)==before
    scene.mwp_ui_work_dir=str(RUN);scene.mwp_ui_uv='MissingUV'
    rejected('procedural_create');assert protected_state(other)==before
    scene.mwp_ui_uv='ExplicitSecondUV';scene.mwp_ui_slot=1
    rejected('procedural_create');scene.mwp_ui_slot=0
    passed('relative directory, missing UV and unused material slot errors are reported without source mutation')
    # A manual graph edit is protected rather than silently recreated from a preset.
    current.node_tree.nodes.new('ShaderNodeValue')
    protected=core._snapshot(current);rejected('procedural_update')
    assert core._snapshot(current)==protected
    passed('unrepresentable author graph edit blocks update and remains untouched')
    scene.mwp_ui_family='painted_metal';scene.mwp_ui_metal_region='edges';scene.mwp_ui_weathering=.4
    operator('procedural_create');metal=ui.current_material(bpy.context)
    actual=core.get_stored_manifest(metal)
    fields={s['id']:s for s in actual['signals']}
    assert fields['localized_weathering']['inputs']['a']=='top_rim_region'
    assert 'rolled_seam_exposure' not in fields and core._snapshot(current)==protected
    layout=_Layout();ui.MWP_PT_panel.draw(type('DrawContext',(),{'layout':layout})(),bpy.context)
    assert ('prop','mwp_ui_metal_region') in layout.calls
    passed('actual create honors metal region selector and preserves earlier rejected manual graph')
    result={'status':'pass','blender':bpy.app.version_string,'build':bpy.app.build_hash.decode(),
            'checks':checks,'run':str(RUN),'export':exported,
            'limitations':['tests use a fresh independent factory-startup background instance',
                'visible GUI layout/click interaction not verified',
                'UI export tested128 only; 2K option exists but is not a 2K UI performance claim',
                'material library names/SHA verified; final cross-engine visual acceptance is separate']}
finally:
    addon.unregister()
    assert not hasattr(bpy.types.Scene,'mwp_ui_work_dir')
    assert not hasattr(bpy.types.Scene,'mwp_ui_timber_scale')
    assert not hasattr(bpy.types,'MWP_PT_procedural')
    passed('whole-addon unregister removes procedural operators/panel/RNA properties')

result['checks']=checks
(RUN/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('PROCEDURAL_UI_REPORT='+str(RUN/'report.json'))
print(json.dumps({'status':'pass','checks':len(checks),'run':str(RUN)}))
