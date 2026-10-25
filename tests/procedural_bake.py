# SPDX-License-Identifier: GPL-3.0-or-later
"""Real Blender fixture tests, not a mock-bpy/unit-only substitute.

Run: blender --background --factory-startup --python this_file -- --output ABSOLUTE_NEW_DIRECTORY
Each invocation creates an exclusive test-UUID subdirectory and never saves a
source blend. The small fixture is owned entirely by this process.
"""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
import sys
import time
import traceback
import uuid

import bpy
import numpy as np

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from procedural_test_support import bootstrap, prepare_output
ROOT = bootstrap()
OUT = prepare_output('bake', require_blender=True)
from material_workflow_addon import procedural_bake as bake


def _fixture():
    mesh=bpy.data.meshes.new('BakeFixtureMesh')
    mesh.from_pydata([(-1,-1,0),(0,-1,0),(0,1,0),(-1,1,0),
                     (0,-1,0),(1,-1,0),(1,1,0),(0,1,0)],[],[(0,1,2,3),(4,5,6,7)])
    uv=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:
        for li,point in zip(face.loop_indices,[(.05,.05),(.95,.05),(.95,.95),(.05,.95)]):uv.data[li].uv=point
    decoy=mesh.uv_layers.new(name='NotTheBakeUV')
    mesh.uv_layers.active=decoy;decoy.active_render=True
    obj=bpy.data.objects.new('BakeFixture',mesh);bpy.context.scene.collection.objects.link(obj)
    material=bpy.data.materials.new('FixtureMetal');material.use_nodes=True
    tree=material.node_tree;nodes=tree.nodes;links=tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');shader=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(shader.outputs['BSDF'],output.inputs['Surface'])
    uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='UVMap'
    separate=nodes.new('ShaderNodeSeparateXYZ');links.new(uvnode.outputs['UV'],separate.inputs[0])
    def math_node(op,a,b=None):
        node=nodes.new('ShaderNodeMath');node.operation=op
        if isinstance(a,(int,float)):node.inputs[0].default_value=a
        else:links.new(a,node.inputs[0])
        if b is not None:
            if isinstance(b,(int,float)):node.inputs[1].default_value=b
            else:links.new(b,node.inputs[1])
        return node.outputs[0]
    first=math_node('GREATER_THAN',separate.outputs['X'],1/3)
    second=math_node('GREATER_THAN',separate.outputs['X'],2/3)
    ramp=math_node('MULTIPLY',math_node('ADD',first,second),.5)
    ior=math_node('ADD',math_node('MULTIPLY',ramp,3),1)
    height=math_node('MULTIPLY',math_node('SINE',math_node('MULTIPLY',separate.outputs['X'],20)),.1)
    values={'base_color':(.2,.35,.6,1), 'roughness':ramp,'metallic':1.,'height':height,
            'alpha':1.,'transmission':0.,'ior':ior,'coat_weight':.3,'coat_roughness':.1}
    routes={}
    for channel,value in values.items():
        if isinstance(value,tuple):
            source=nodes.new('ShaderNodeRGB');source.outputs[0].default_value=value;signal=source.outputs[0]
        elif isinstance(value,(int,float)):
            source=nodes.new('ShaderNodeValue');source.outputs[0].default_value=value;signal=source.outputs[0]
        else:signal=value
        route=nodes.new('NodeReroute');route['mwp_channel']=channel;links.new(signal,route.inputs[0]);routes[channel]=route
        if channel in bake.SOCKETS:links.new(route.outputs[0],shader.inputs[bake.SOCKETS[channel]])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.02
    bump.inputs['Strength'].default_value=1;material['mwp_height_distance']=.02
    links.new(routes['height'].outputs[0],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],shader.inputs['Normal'])
    links.new(bump.outputs['Normal'],shader.inputs['Coat Normal'])
    other=bpy.data.materials.new('UntouchedOtherMaterial');other.use_nodes=True
    mesh.materials.append(material);mesh.materials.append(other);mesh.polygons[1].material_index=1
    original_image=bpy.data.images.new('OriginalActiveImage',width=16,height=16)
    node=nodes.new('ShaderNodeTexImage');node.image=original_image;nodes.active=node;node.select=True
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    return obj,material


def _state(obj,material):
    scene=bpy.context.scene
    return {'scene':scene.name,'layer':bpy.context.view_layer.name,
            'active':bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None,
            'selected':sorted(o.name for o in bpy.context.selected_objects),
            'engine':scene.render.engine,'samples':scene.cycles.samples,
            'bake_margin':scene.render.bake.margin,'bake_clear':scene.render.bake.use_clear,
            'uv':obj.data.uv_layers.active.name,'uv_render':[(u.name,u.active_render) for u in obj.data.uv_layers],
            'slots':[(s.link,s.material.name if s.material else None) for s in obj.material_slots],
            'polygons':[(p.index,p.material_index) for p in obj.data.polygons],
            'node_active':material.node_tree.nodes.active.name,
            'node_select':[(n.name,n.select) for n in material.node_tree.nodes],
            'links':sorted((l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in material.node_tree.links),
            'images':[(i.name,i.source,i.filepath,i.colorspace_settings.name,i.is_dirty,list(i.size)) for i in bpy.data.images],
            'ids':{k:sorted(x.name for x in getattr(bpy.data,k)) for k in ('scenes','objects','meshes','materials')}}


def _image(entry):
    image=bpy.data.images.load(entry['file'],check_existing=False)
    image.colorspace_settings.name=entry['color_space'];image.alpha_mode='STRAIGHT'
    pixels=bake._pixels(image);bpy.data.images.remove(image)
    return pixels


def _probe_rebuilt_ior(obj,material):
    """Run the rebuilt Math decoder through a second actual Cycles Emit bake."""
    tree=material.node_tree;nodes=tree.nodes;links=tree.links
    shader=next(n for n in nodes if n.bl_idname=='ShaderNodeBsdfPrincipled')
    output=next(n for n in nodes if n.bl_idname=='ShaderNodeOutputMaterial')
    decoded=shader.inputs['IOR'].links[0].from_socket
    divide=nodes.new('ShaderNodeMath');divide.operation='DIVIDE';divide.inputs[1].default_value=4
    links.new(decoded,divide.inputs[0])
    emit=nodes.new('ShaderNodeEmission');links.new(divide.outputs[0],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface'])
    image=bpy.data.images.new('DecodedIORProbe',width=96,height=96,alpha=True,float_buffer=True)
    image.colorspace_settings.name='Non-Color';image.generated_color=(0,0,0,0)
    node=nodes.new('ShaderNodeTexImage');node.image=image;nodes.active=node
    for n in nodes:n.select=False
    node.select=True
    old=[s.material for s in obj.material_slots]
    oldengine=bpy.context.scene.render.engine
    try:
        obj.material_slots[0].material=material
        # Other slot bakes to an independent discard image, exercising overlap isolation.
        discard=old[1].node_tree.nodes.new('ShaderNodeTexImage');discard.image=bpy.data.images.new('IORDiscard',width=16,height=16)
        old[1].node_tree.nodes.active=discard
        bpy.context.scene.render.engine='CYCLES';bpy.context.scene.cycles.samples=2
        result=bpy.ops.object.bake(type='EMIT',uv_layer='UVMap',use_clear=True,margin=1)
        assert result=={'FINISHED'}
        p=bake._pixels(image).reshape((96,96,4))
        values=[float(p[48,x,0]) for x in (20,48,76)]
        assert np.allclose(values,[.25,.625,1],atol=.001), values
        return values
    finally:
        for slot,value in zip(obj.material_slots,old):slot.material=value
        bpy.context.scene.render.engine=oldengine
        bpy.data.images.remove(image)


def run(destination):
    root=Path(destination)/('test-'+uuid.uuid4().hex);root.mkdir(parents=True,exist_ok=False)
    result={'status':'running','blender':bpy.app.version_string,'root':str(root),'checks':{},'start':time.time()}
    try:
        obj,material=_fixture()
        before=_state(obj,material)
        report=bake.bake_channels(obj,material,str(root/'images'),
            {'channels':list(bake.CHANNELS),'size':96,'margin':2,'samples':2,'bit_depth':'16'})
        after=_state(obj,material)
        assert before==after, {'before':before,'after':after}
        result['checks']['source_state_restored']=True
        result['report_file']=report['report_file']
        assert report['status']=='complete' and len(report['channels'])==10
        result['checks']['disk_roundtrips']={c:e['roundtrip_max_error'] for c,e in report['channels'].items()}
        color=_image(report['channels']['base_color']).reshape((96,96,4))
        assert np.allclose(color[48,48,:3],[.2,.35,.6],atol=.0002),color[48,48].tolist()
        result['checks']['metallic_base_color']=color[48,48,:3].tolist()
        rough=_image(report['channels']['roughness']).reshape((96,96,4))
        values=[float(rough[48,x,0]) for x in (20,48,76)]
        assert np.allclose(values,[0,.5,1],atol=.0002),values
        result['checks']['unit_data_0_half_1']=values
        ior=_image(report['channels']['ior']).reshape((96,96,4))
        assert np.allclose([ior[48,x,0]*3+1 for x in (20,48,76)],[1,2.5,4],atol=.0005)
        result['checks']['ior_encoding']=True
        height=_image(report['channels']['height'])
        assert np.min(height[:,0])<-.09 and np.max(height[:,0])>.09
        result['checks']['signed_height_exr']=True
        normal=_image(report['channels']['normal'])
        assert np.ptp(normal[normal[:,3]>.5,0])>.01
        assert report['normal']['includes_height'] and report['normal']['convention']=='OpenGL'
        result['checks']['real_tangent_normal_contains_height']=True
        rebuilt=bake.rebuild_material(report)
        assert not any(n.bl_idname in ('ShaderNodeTexNoise','ShaderNodeTexVoronoi','ShaderNodeBump') for n in rebuilt.node_tree.nodes)
        assert sum(n.bl_idname=='ShaderNodeNormalMap' for n in rebuilt.node_tree.nodes)==1
        assert rebuilt['mwp_rebuild']=='disk-images-and-declared-parameters-only'
        result['checks']['rebuild_no_procedural_or_double_bump']=True
        result['checks']['rebuilt_ior_actual_emit_probe']=_probe_rebuilt_ior(obj,rebuilt)
        # Omitted dynamic roughness and IOR are promoted to actual files.
        thin=bake.bake_channels(obj,material,str(root/'auto'),
            {'channels':['normal'],'size':48,'margin':1,'samples':1,'bit_depth':'8'})
        assert {'roughness','ior'}.issubset(thin['required_added_channels'])
        result['checks']['required_channels_added']=thin['required_added_channels']
        # Simulate disk failure after a completed channel. Partial files remain,
        # but no temporary Blender IDs or original state changes may remain.
        before=_state(obj,material);original=bake._save_verified;count=[0]
        def failing_save(*args,**kwargs):
            count[0]+=1
            if count[0]==2:raise OSError('fixture intentional disk failure')
            return original(*args,**kwargs)
        bake._save_verified=failing_save
        try:
            try:
                bake.bake_channels(obj,material,str(root/'failure'),
                    {'channels':['base_color','roughness'],'size':32,'margin':1,'samples':1,'bit_depth':'16'})
                raise AssertionError('Intentional failure was not reported')
            except bake.WorkflowError as error:
                partial=json.loads(Path(error.report_path).read_text(encoding='utf-8'))
                assert partial['status']=='partial' and not partial['delivery']['complete']
                assert 'base_color' in partial['channels']
                result['partial_report']=error.report_path
                try:bake.rebuild_material(partial)
                except bake.WorkflowError as reject:assert reject.code=='bake_incomplete'
                else:raise AssertionError('Partial report accepted for reconstruction')
        finally:bake._save_verified=original
        assert before==_state(obj,material)
        result['checks']['failure_partial_and_state_restored']=True
        # Genuine positive-area target overlap must fail before baking.
        obj.data.polygons[1].material_index=0
        try:
            bake.bake_channels(obj,material,str(root/'overlap'),{'channels':['base_color'],'size':32,'margin':1})
        except bake.WorkflowError as error:assert error.code=='bake_uv_overlap'
        else:raise AssertionError('Overlapping target UVs accepted')
        finally:obj.data.polygons[1].material_index=1
        result['checks']['uv_overlap_rejected']=True
        bpy.ops.mesh.primitive_cube_add(size=2,location=(3,0,0))
        cube=bpy.context.object;cube.name='BevelFixture';cube.data.materials.append(material)
        bevel=cube.modifiers.new('OrdinaryStaticBevel','BEVEL');bevel.width=.08;bevel.segments=2
        bevel_report=bake.bake_channels(cube,material,str(root/'bevel'),
            {'channels':['base_color','normal'],'size':64,'margin':2,'samples':2,'bit_depth':'16'})
        assert bevel_report['status']=='complete' and bevel_report['evaluated_geometry']['modifiers']==['BEVEL']
        result['checks']['static_bevel']=bevel_report['uv_evaluated']
        result['bevel_report']=bevel_report['report_file']
        result['status']='pass'
    except Exception as error:
        result['status']='fail';result['error']=str(error);result['traceback']=traceback.format_exc()
        raise
    finally:
        result['elapsed_seconds']=time.time()-result['start']
        path=root/'tests.json';path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('MWP_BAKE_TEST_REPORT',str(path),flush=True)


if __name__=='__main__':
    try:run(str(OUT))
    except Exception:
        traceback.print_exc();sys.exit(1)
