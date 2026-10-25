# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.dont_write_bytecode = True
"""Build self-owned prop fixtures, validate UVs and exercise public recipes.

Fixture UV creation here is test setup, not a plugin automatic-UV capability.
Run using factory-startup Blender; outputs always use a new audit directory.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import uuid

import bpy
from mathutils import Vector, Euler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
RUN = prepare_output('examples', require_blender=True)
from material_workflow_addon.contract import WorkflowError
from material_workflow_addon.procedural_contract import normalize_manifest
from material_workflow_addon.procedural_examples import make_recipe, FAMILIES
from material_workflow_addon.procedural_core import apply_material, verify_managed_state, get_stored_manifest

if '--verify-fixtures' in sys.argv:
    index_path=Path(sys.argv[sys.argv.index('--verify-fixtures')+1])
    index=json.loads(index_path.read_text(encoding='utf-8'));reopened=[]
    for fixture in index['fixtures']:
        bpy.ops.wm.open_mainfile(filepath=fixture['file'])
        assert len(bpy.data.scenes)==1 and bpy.context.scene.name==fixture['scene']
        assert hashlib.sha256(Path(fixture['file']).read_bytes()).hexdigest()==fixture['sha256']
        for part in fixture['parts']:
            obj=bpy.data.objects[part['object']]
            current=hashlib.sha256(json.dumps([list(c.uv) for c in obj.data.uv_layers['UVMap'].data]).encode()).hexdigest()
            assert current==part['uv']['uv_sha256']
            mat=obj.material_slots[part['material_slot']].material
            assert verify_managed_state(mat)['ok'],(obj.name,'managed graph after independent reopen')
            live=get_stored_manifest(mat)
            if part['family']=='wood':
                coordinate=next(s for s in live['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']
                assert coordinate['scale']==part['timber_scale']
                rotation=coordinate['rotation']
                mapped=Euler(rotation,'XYZ').to_matrix()@Vector({'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[part['grain_axis']])
                assert (mapped-Vector((1,0,0))).length<1e-6
        reopened.append({'file':fixture['file'],'scene':fixture['scene'],'parts':len(fixture['parts']),'status':'pass'})
    verification={'status':'pass','independent_background_reopen':True,'fixtures':reopened}
    output=RUN/('reopen-'+uuid.uuid4().hex[:12]+'.json')
    output.write_text(json.dumps(verification,indent=2),encoding='utf-8')
    print('FIXTURE_REOPEN_REPORT='+str(output))
    # quit_blender queues shutdown until the running Python script returns.
    # SystemExit prevents falling through into the fixture-construction body.
    raise SystemExit(0)

checks, fixtures = [], []


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def signed_area(points):
    return 0.5 * sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(points, points[1:] + points[:1]))


def intersection_area(a, b):
    clip = b if signed_area(b) > 0 else list(reversed(b))
    output = a[:]
    for c, d in zip(clip, clip[1:] + clip[:1]):
        source, output = output, []
        if not source: return 0
        def distance(p): return (d[0]-c[0])*(p[1]-c[1]) - (d[1]-c[1])*(p[0]-c[0])
        start = source[-1]; ds = distance(start)
        for end in source:
            de = distance(end)
            if (de >= -1e-12) != (ds >= -1e-12):
                factor = ds / (ds - de)
                output.append((start[0] + factor*(end[0]-start[0]), start[1] + factor*(end[1]-start[1])))
            if de >= -1e-12: output.append(end)
            start, ds = end, de
    return abs(signed_area(output)) if len(output) >= 3 else 0


def uv_report(obj):
    mesh = obj.data; uv = mesh.uv_layers['UVMap']; mesh.calc_loop_triangles()
    triangles, bounds = [], []
    for tri in mesh.loop_triangles:
        points = [tuple(uv.data[i].uv) for i in tri.loops]
        assert abs(signed_area(points)) > 1e-12, ('degenerate UV triangle', obj.name)
        triangles.append(points)
        bounds.append((min(p[0] for p in points), min(p[1] for p in points),
                       max(p[0] for p in points), max(p[1] for p in points)))
    assert all(-1e-6 <= value <= 1.000001 for box in bounds for value in box)
    cells, candidates = {}, set()
    for i, (lo_x, lo_y, hi_x, hi_y) in enumerate(bounds):
        for x in range(max(0, int(lo_x*32)), min(31, int(hi_x*32))+1):
            for y in range(max(0, int(lo_y*32)), min(31, int(hi_y*32))+1):
                bucket = cells.setdefault((x,y), [])
                for other in bucket: candidates.add((other,i))
                bucket.append(i)
    maximum, bad = 0, []
    for i,j in candidates:
        a,b = bounds[i],bounds[j]
        if min(a[2],b[2])-max(a[0],b[0]) <= 1e-10 or min(a[3],b[3])-max(a[1],b[1]) <= 1e-10: continue
        area = intersection_area(triangles[i], triangles[j]); maximum = max(maximum, area)
        if area > 1e-8: bad.append({'triangles':[i,j], 'overlap_area':area})
    assert not bad, ('UV overlap', obj.name, bad[:3])
    return {'uv_layer':'UVMap', 'method':obj.get('fixture_uv_method', 'self-owned smart_project'),
            'triangles':len(triangles), 'candidate_pairs':len(candidates),
            'overlap_pairs':0, 'maximum_intersection_area':maximum,
            'area_tolerance':1e-8, 'tile':'0..1', 'degenerate_triangles':0,
            'uv_sha256':hashlib.sha256(json.dumps([list(c.uv) for c in uv.data]).encode()).hexdigest()}


def normalize_coordinates(obj):
    bounds = [(min(v.co[i] for v in obj.data.vertices), max(v.co[i] for v in obj.data.vertices)) for i in range(3)]
    center = Vector([(lo+hi)*0.5 for lo,hi in bounds])
    half = Vector([(hi-lo)*0.5 for lo,hi in bounds])
    assert min(half) > 0
    old = obj.matrix_world.copy()
    obj.location = old @ center
    for v in obj.data.vertices:
        v.co = Vector([(v.co[i]-center[i])/half[i] for i in range(3)])
    obj.scale = Vector([obj.scale[i]*half[i] for i in range(3)])
    obj.data.update()
    obj['fixture_coordinate_frame'] = 'Centered OBJECT/local bounds -1..1; matrix_world retains physical size/location'


def unwrap(obj):
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.03, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.uv_layers.active.name='UVMap'; obj.data.uv_layers.active.active_render=True
    obj['fixture_uv_method']='self-owned mesh smart_project (66deg, margin .03), independently triangle-intersection checked'


def box(name, dimensions, location, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=2, location=location); obj=bpy.context.object; obj.name=name
    obj.scale=Vector(dimensions)*0.5; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Self-owned modeled bevel','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    normalize_coordinates(obj);unwrap(obj)
    return obj


def cylinder(name, radius, depth, z, cap='NGON', bevel=0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,end_fill_type=cap,location=(0,0,z))
    obj=bpy.context.object;obj.name=name
    if bevel:
        mod=obj.modifiers.new('Self-owned modeled bevel','BEVEL');mod.width=bevel;mod.segments=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in obj.data.polygons: p.use_smooth=len(p.vertices)==4 and abs(p.normal.z)<0.9
    normalize_coordinates(obj);unwrap(obj)
    return obj


def glass(name, x):
    # A watertight revolution: exterior floor -> body -> rim -> interior -> inner floor.
    # Both axis endpoints are single vertices, avoiding collapsed/repeated axis quads.
    profile=[(0,-1),(0.72,-1),(0.88,-0.97),(0.97,-0.86),(1,0.90),
             (0.99,0.98),(0.91,1),(0.86,0.96),(0.87,0.87),(0.84,-0.75),(0.70,-0.82),(0,-0.82)]
    n=64;verts=[];rows=[]
    for radius,z in profile:
        if radius==0: rows.append([len(verts)]);verts.append((0,0,z))
        else:
            rows.append(list(range(len(verts),len(verts)+n)))
            verts.extend((radius*math.cos(2*math.pi*j/n),radius*math.sin(2*math.pi*j/n),z) for j in range(n))
    faces=[]
    for a,b in zip(rows,rows[1:]):
        for j in range(n):
            j1=(j+1)%n
            faces.append((a[0],b[j1],b[j]) if len(a)==1 else (a[j],a[j1],b[0]) if len(b)==1
                         else (a[j],a[j1],b[j1],b[j]))
    mesh=bpy.data.meshes.new(name+'Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    obj.location=(x,0,0.63);obj.scale=(0.30,0.30,0.60)
    for p in mesh.polygons:p.use_smooth=abs(p.normal.z)<0.95
    unwrap(obj)
    # Edge incidence proves a closed wall/floor mesh, not a single transparent sheet.
    counts={}
    for p in mesh.polygons:
        for e in p.edge_keys: counts[e]=counts.get(e,0)+1
    assert all(c==2 for c in counts.values()),'vessel is not closed'
    obj['fixture_wall_thickness']='radial wall approximately .039 scene units; modeled closed rim and bottom'
    return obj


def new_scene(name):
    # This process owns factory-startup state only. Keep each saved blend
    # independent instead of carrying earlier test scenes into later fixtures.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.name=name
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
    scene.cycles.use_denoising=False;scene.render.resolution_x=128;scene.render.resolution_y=128
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    world=bpy.data.worlds.new(name+'World');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.5,0.5,0.5,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.45;scene.world=world
    return scene


def studio(scene, target, distance):
    bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0,-0.015));floor=bpy.context.object;floor.name='SelfOwnedStudioFloor'
    material=bpy.data.materials.new('SelfOwnedNeutralFloor');material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(0.16,0.17,0.18,1)
    bsdf.inputs['Roughness'].default_value=0.5;floor.data.materials.append(material)
    for name,location,energy,size in [('Key',(-3,-4,5),500,3),('Rim',(4,1,4),650,2),('Fill',(1,4,3),250,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        light=bpy.data.objects.new(name,data);scene.collection.objects.link(light);light.location=location
        light.rotation_euler=(Vector(target)-light.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.objects.new('FixtureCamera',bpy.data.cameras.new('FixtureCamera'));scene.collection.objects.link(camera)
    camera.location=Vector(target)+Vector((distance,-distance,distance*0.65));camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=50;scene.camera=camera


def finish(family_name, scene, parts, target, distance):
    directory=RUN/family_name;directory.mkdir()
    records=[]
    for index,(obj,family,weathering,direction) in enumerate(parts):
        uv=uv_report(obj)
        region='edges' if obj.name=='BarrelTop' else 'seam' if obj.name.startswith('BarrelRib') else 'lower'
        # Explicit fixture sampling choices; never derive these from obj.scale.
        timber_scale={'X':(2,1,.125),'Z':(.125,.125,1),'Y':(.125,.75,.125)}.get(direction,(1,1,1))
        manifest=make_recipe(family,{'scene':scene.name,'view_layer':scene.view_layers[0].name,'frame':1},
            {'object':obj.name,'material_slot':0,'uv_layer':'UVMap'},family_name+'_'+str(index),
            name=obj.name+' Surface',weathering=weathering,
            grain_axis=direction if family=='wood' else 'X',metal_region=region,timber_scale=timber_scale)
        normalize_manifest(manifest)
        path=directory/(obj.name+'.manifest.json');write_json(path,manifest)
        preview_manifest=copy.deepcopy(manifest);preview_manifest['mesh_map_size']=128
        bpy.context.view_layer.objects.active=obj
        protected={'matrix':[list(row) for row in obj.matrix_world],
            'geometry':[list(v.co) for v in obj.data.vertices],
            'uv':[list(c.uv) for c in obj.data.uv_layers['UVMap'].data],
            'other_bindings':[(o.name,[(s.link,s.material.name if s.material else None) for s in o.material_slots])
                for o in scene.objects if o!=obj]}
        report=apply_material(preview_manifest,work_dir=directory/(obj.name+'-work'))
        assert verify_managed_state(bpy.data.materials[report['material_name']])['ok']
        assert protected=={'matrix':[list(row) for row in obj.matrix_world],
            'geometry':[list(v.co) for v in obj.data.vertices],
            'uv':[list(c.uv) for c in obj.data.uv_layers['UVMap'].data],
            'other_bindings':[(o.name,[(s.link,s.material.name if s.material else None) for s in o.material_slots])
                for o in scene.objects if o!=obj]},'recipe mutated geometry, UV, transform or another binding'
        if family=='wood':
            live=get_stored_manifest(obj.material_slots[0].material)
            assert next(s for s in live['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']['scale']==list(timber_scale)
            rotation=next(s for s in live['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']['rotation']
            mapped=Euler(rotation,'XYZ').to_matrix()@Vector({'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[direction])
            assert (mapped-Vector((1,0,0))).length<1e-6
        records.append({'object':obj.name,'uv':uv,'family':family,'manifest':str(path),
            'material_slot':0,'preview_applied_mesh_map_size':128,
            'grain_axis':direction if family=='wood' else None,'metal_region':region if family=='painted_metal' else None,
            'timber_scale':list(timber_scale) if family=='wood' else None,
            'weathering':weathering,'non_target_preservation':'pass','matrix_world':[list(row) for row in obj.matrix_world],
            'dimensions':list(obj.dimensions),'apply_report':report})
    studio(scene,target,distance)
    scene.render.filepath=str(directory/'preview.png')
    blend=directory/(family_name+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.render.render(write_still=True)
    image=Path(scene.render.filepath);data=image.read_bytes()
    assert struct.unpack('>II',data[16:24])==(128,128)
    fixtures.append({'family':family_name,'file':str(blend),'sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),
        'scene':scene.name,'view_layer':scene.view_layers[0].name,'parts':records,
        'preview':{'file':str(image),'width':128,'height':128,'bytes':len(data),'samples':8,'engine':'CYCLES'},
        'source':'self-owned test geometry; no user assets or downloaded data'})
    checks.append(family_name+': all part recipes applied, UV intersections checked, blend saved, 128px Cycles preview decoded')


context={'scene':'ArbitraryScene','view_layer':'ArbitraryLayer','frame':1};target={'object':'ArbitraryObject','material_slot':0,'uv_layer':'UVMap'}
for family in FAMILIES:
    first=make_recipe(family,context,target,'Example_'+family)
    second=make_recipe(family,context,target,'Example_'+family)
    assert first==second
    assert first['context']==context and first['target']==target
    assert first['preview']['width']==512 and first['preview']['samples']==16 and len(first['preview']['views'])==2
    normalized=normalize_manifest(first)
    assert len(normalized['signals'])<=96
    if family.startswith('glass_'):
        assert all(layer['values']['alpha']==1 and layer['values']['transmission']==1 and layer['values']['ior']==struct.unpack('f',struct.pack('f',1.45))[0] for layer in normalized['layers'])
    first['signals'][0]['parameters'].clear()
    assert first!=second,'recipe results share mutable values'
checks.append('five recipe families normalize; deterministic seeds; copied input; independent mutable results; transparent glass invariants')
assert make_recipe('wood',context,target,'DefaultScale')==make_recipe('wood',context,target,'DefaultScale',timber_scale=(1,1,1))
caller_scale=[.125,.25,1.5]
copied_scale=make_recipe('wood',context,target,'CopiedScale',timber_scale=caller_scale)
caller_scale[0]=99
assert copied_scale['signals'][0]['parameters']['coordinate']['scale']==[.125,.25,1.5]
before_invalid={'objects':list(bpy.data.objects.keys()),'materials':list(bpy.data.materials.keys()),
    'groups':list(bpy.data.node_groups.keys()),'context':copy.deepcopy(context),'target':copy.deepcopy(target)}
for kwargs in ({'family':'unknown'},{'seed':True},{'seed':100001},{'weathering':float('nan')},{'weathering':-1},
               {'weathering':True},{'weathering':float('inf')},{'weathering':10**1000},
               {'grain_axis':'x'},{'grain_axis':True},{'grain_axis':['X']},
               {'metal_region':'body'},{'metal_region':None},{'metal_region':{}}, {'metal_region':'unknown'},
               *({'timber_scale':value} for value in (None,True,'123',{},[1,2],[1,2,3,4],
                   [True,1,1],['1',1,1],[0,1,1],[-1,1,1],[float('nan'),1,1],
                   [float('inf'),1,1],[10**1000,1,1],[1e40,1,1],[1e-50,1,1]))):
    args={'family':'wood','context':context,'target':target,'material_id':'InvalidExample'};args.update(kwargs)
    try:make_recipe(**args)
    except WorkflowError:pass
    else:raise AssertionError('invalid example parameters accepted')
assert before_invalid=={'objects':list(bpy.data.objects.keys()),'materials':list(bpy.data.materials.keys()),
    'groups':list(bpy.data.node_groups.keys()),'context':context,'target':target}
checks.append('invalid family/seed/weathering/axis/region/timber_scale rejected without source mutation; default scale compatibility and copied caller scale')
for axis in ('X','Y','Z'):
    spec=make_recipe('wood',context,target,'Axis_'+axis,grain_axis=axis,weathering=0)
    by_id={s['id']:s for s in spec['signals']}
    rotation=by_id['timber_coordinates']['parameters']['coordinate']['rotation']
    unit=Vector({'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[axis])
    assert (Euler(rotation,'XYZ').to_matrix()@unit-Vector((1,0,0))).length<1e-6
    assert all(by_id[s]['inputs']['vector']=='growth_warp' for s in ('growth_rings','long_fibres','vessel_distance','micro_fibres'))
    assert len(spec['layers'])==1 and not any(s['type'] in ('edge','cavity') for s in spec['signals'])
for region,expected in [('lower','contact_and_moisture'),('edges','top_rim_region'),('seam','rolled_seam_exposure')]:
    spec=make_recipe('painted_metal',context,target,'Region_'+region,metal_region=region)
    by_id={s['id']:s for s in spec['signals']}
    assert by_id['localized_weathering']['inputs']['a']==expected
    assert by_id['weathering_master']['parameters']['value']==.4
    assert by_id['coating_loss']['inputs']['value']==by_id['oxide_coverage']['inputs']['value']=='weathering_susceptibility'
checks.append('three named timber axes share one warped coordinate frame; zero wood weathering omits weathering sources/layers; three explicit metal regions route independently')


def evaluate_mask(signals, identity, sample):
    """Evaluate only scalar mask algebra; spatial sources receive controlled values."""
    lookup={s['id']:s for s in signals};cache={}
    def evaluate(sid):
        if sid in cache:return cache[sid]
        s=lookup[sid];p=s['parameters'];inputs=s['inputs'];kind=s['type']
        if kind=='constant':value=p['value']
        elif kind in ('noise','edge','cavity','height_band'):value=sample
        elif kind=='math':
            a,b=evaluate(inputs['a']),evaluate(inputs['b'])
            value={'MULTIPLY':lambda:a*b,'SUBTRACT':lambda:a-b,'MAXIMUM':lambda:max(a,b)}[p['operation']]()
            if p.get('clamp',True):value=min(1,max(0,value))
        elif kind=='mix':
            f=min(1,max(0,evaluate(inputs['factor'])))
            value=(1-f)*evaluate(inputs['a'])+f*evaluate(inputs['b'])
        elif kind=='remap':
            t=(evaluate(inputs['value'])-p['from_min'])/(p['from_max']-p['from_min'])
            if p['clamp']:t=min(1,max(0,t))
            if p['interpolation']=='SMOOTHSTEP':t=t*t*(3-2*t)
            value=p['to_min']+t*(p['to_max']-p['to_min'])
        else:raise AssertionError(('not a scalar mask path',sid,kind))
        cache[sid]=value;return value
    return evaluate(identity)


for region in ('lower','edges','seam'):
    fresh=make_recipe('painted_metal',context,target,'Fresh_'+region,metal_region=region,weathering=0)
    for sample in (0,.25,.6,1):
        assert evaluate_mask(fresh['signals'],'coating_loss',sample)==0
        assert evaluate_mask(fresh['signals'],'oxide_coverage',sample)==0
        assert evaluate_mask(fresh['signals'],'weathering_dust',sample)==0
        assert evaluate_mask(fresh['signals'],'intact_coating',sample)==1
checks.append('zero master eliminates coating loss, oxide and dust across all three metal region masks and controlled spatial-source samples')

# Probe the actual built timber Mapping through Cycles, using a constant input
# so geometry and texture sampling cannot conceal a scale/rotation order error.
scene=new_scene('TimberMappingOrderProbe')
bpy.ops.mesh.primitive_plane_add(size=2);probe=bpy.context.object
camera=bpy.data.objects.new('ProbeCamera',bpy.data.cameras.new('ProbeCamera'))
scene.collection.objects.link(camera);camera.location=(0,0,3);camera.data.type='ORTHO';camera.data.ortho_scale=1
scene.camera=camera;scene.render.resolution_x=4;scene.render.resolution_y=4;scene.cycles.samples=1
scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32'
point=Vector((.03,.04,.02));scale=Vector((2,3,4));mapping_results=[]
for axis in ('X','Y','Z'):
    spec=make_recipe('wood',{'scene':scene.name,'view_layer':scene.view_layers[0].name,'frame':1},
        {'object':probe.name,'material_slot':0,'uv_layer':probe.data.uv_layers.active.name},
        'OrderProbe_'+axis,grain_axis=axis,timber_scale=list(scale),weathering=0)
    report=apply_material(spec,work_dir=RUN/('mapping-'+axis))
    material=probe.material_slots[0].material
    assert verify_managed_state(material)['ok']
    live=get_stored_manifest(material)
    coordinate=next(s for s in live['signals'] if s['id']=='timber_coordinates')['parameters']['coordinate']
    assert coordinate['scale']==list(scale)
    root=material.node_tree.nodes['MWP Controls'];group=root.node_tree
    mapping=next(n for n in group.nodes if n.get('mwp_node')=='timber_coordinates/mapping')
    assert mapping.bl_idname=='ShaderNodeMapping' and mapping.vector_type=='POINT'
    for link in list(mapping.inputs['Vector'].links):group.links.remove(link)
    mapping.inputs['Vector'].default_value=point
    group.interface.new_socket(name='OrderProbe',in_out='OUTPUT',socket_type='NodeSocketVector')
    output=next(n for n in group.nodes if n.bl_idname=='NodeGroupOutput')
    group.links.new(mapping.outputs['Vector'],output.inputs['OrderProbe'])
    add=material.node_tree.nodes.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.5,.5,.5)
    emission=material.node_tree.nodes.new('ShaderNodeEmission')
    material.node_tree.links.new(root.outputs['OrderProbe'],add.inputs[0])
    material.node_tree.links.new(add.outputs['Vector'],emission.inputs['Color'])
    surface=next(n for n in material.node_tree.nodes if n.bl_idname=='ShaderNodeOutputMaterial')
    material.node_tree.links.new(emission.outputs[0],surface.inputs['Surface'])
    path=RUN/('mapping-order-'+axis+'.exr');scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    image=bpy.data.images.load(str(path),check_existing=False);actual=list(image.pixels[:3]);bpy.data.images.remove(image)
    expected=Euler(coordinate['rotation'],'XYZ').to_matrix()@Vector(tuple(point[i]*scale[i] for i in range(3)))+Vector((.5,.5,.5))
    assert max(abs(a-b) for a,b in zip(actual,expected))<2e-5,(axis,actual,list(expected))
    mapping_results.append({'axis':axis,'actual':actual,'scale_before_rotation_expected':list(expected),'file':str(path)})
write_json(RUN/'mapping-order.json',{'status':'pass','probes':mapping_results})
checks.append('Cycles float EXR probes on actual built timber Mapping confirm local scale before X/Y/Z rotation; live scale readback matches explicit caller values')

scene=new_scene('OilBarrelFixture');parts=[]
parts.append((cylinder('BarrelBody',0.46,1.20,0.62,'NOTHING'),'painted_metal',0.34,None))
parts.append((cylinder('BarrelTop',0.458,0.025,1.22,bevel=0.006),'painted_metal',0.22,None))
parts.append((cylinder('BarrelBottom',0.458,0.025,0.02,bevel=0.006),'painted_metal',0.4,None))
for i,z in enumerate((0.25,0.64,1.03)):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.463,minor_radius=0.015,major_segments=64,minor_segments=8,location=(0,0,z))
    obj=bpy.context.object;obj.name='BarrelRib'+str(i+1)
    for p in obj.data.polygons:p.use_smooth=True
    normalize_coordinates(obj);unwrap(obj);parts.append((obj,'painted_metal',0.38,None))
finish('oil_barrel',scene,parts,(0,0,0.62),2.0)

scene=new_scene('WoodDeskFixture');parts=[(box('DeskTop',(1.6,0.8,0.08),(0,0,0.79),0.012),'wood',0.25,'X')]
for i,(x,y) in enumerate(((-0.68,-0.29),(0.68,-0.29),(-0.68,0.29),(0.68,0.29))):
    parts.append((box('DeskLeg'+str(i+1),(0.075,0.075,0.75),(x,y,0.375),0.006),'wood',0.2,'Z'))
for i,x in enumerate((-.68,.68)):
    parts.append((box('DeskStretcher'+str(i+1),(.055,.58,.055),(x,0,.24),.004),'wood',.2,'Y'))
finish('wood_desk',scene,parts,(0,0,0.4),2.1)

scene=new_scene('ThickGlassFixture');parts=[]
for i,family in enumerate(('glass_clear','glass_tinted','glass_frosted')):
    parts.append((glass('Vessel'+family.title().replace('_',''),(i-1)*0.9),family,0.18,'Z'))
finish('thick_glass',scene,parts,(0,0,0.62),2.7)

report={'status':'pass','blender_version':bpy.app.version_string,'build':bpy.app.build_hash.decode(),
        'checks':checks,'fixtures':fixtures,
        'limitations':['self-owned test fixtures only; UV generation is not plugin functionality',
            'centered local coordinates -1..1 explicitly authored for these fixtures',
            'UV overlap checked with 2D triangle clipping and area tolerance 1e-8',
            '128px Cycles CPU 8-sample previews, mesh maps128 only; no 2K or Eevee acceptance here',
            'all templates use single-Principled compositing; glass tint has no volume absorption',
            'wood X/Y/Z frame migration tested on tabletop/legs/stretchers; timber species and joinery quality remain artistic review']}
write_json(RUN/'fixtures.json',report)
print('PROCEDURAL_FIXTURES_REPORT='+str(RUN/'fixtures.json'))
print(json.dumps({'status':'pass','checks':len(checks),'fixtures':len(fixtures),'run':str(RUN)}))
