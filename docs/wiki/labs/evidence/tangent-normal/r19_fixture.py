"""R19 experiment only. Loaded by an isolated, pinned Material Workflow worker."""
from array import array
import hashlib
import json
import math
from pathlib import Path

import bpy

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def make_mesh(scene, name, z, quads):
    mesh = bpy.data.meshes.new(name)
    grid = [(-1,-.5),(0,-.5),(1,-.5),(-1,.5),(0,.5),(1,.5)]
    mesh.from_pydata([(x,y,z(x)) for x,y in grid], [], quads)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    return ob

def shader(ob, slot, encoded, uv):
    mat = bpy.data.materials.new('R19 tilt '+str(slot))
    ob.data.materials.append(mat)
    mat.use_nodes = True
    tree=mat.node_tree
    tree.nodes.clear()
    n=tree.nodes.new('ShaderNodeNormalMap')
    n.space='TANGENT'
    n.uv_map=uv
    n.inputs['Color'].default_value=(*encoded,1)
    n.inputs['Strength'].default_value=1
    scale=tree.nodes.new('ShaderNodeVectorMath')
    scale.operation='SCALE'
    scale.inputs['Scale'].default_value=.5
    offset=tree.nodes.new('ShaderNodeVectorMath')
    offset.operation='ADD'
    offset.inputs[1].default_value=(.5,.5,.5)
    emit=tree.nodes.new('ShaderNodeEmission')
    output=tree.nodes.new('ShaderNodeOutputMaterial')
    for a,b in [(n.outputs[0],scale.inputs[0]),(scale.outputs[0],offset.inputs[0]),
                (offset.outputs[0],emit.inputs[0]),(emit.outputs[0],output.inputs[0])]:
        tree.links.new(a,b)
    return tree,n,emit

def read_image(image):
    f=array('f',[0])*len(image.pixels)
    image.pixels.foreach_get(f)
    return f

def stats(pixels, W, H, cols):
    means=[]
    for x0,x1 in cols:
        rows=[[pixels[(y*W+x)*4+c] for c in range(3)] for y in range(H//2-4,H//2+4)
                    for x in range(x0,x1)]
        means.append([sum(p[c] for p in rows)/len(rows) for c in range(3)])
    return means

def run(job):
    directory=job/'r19'
    directory.mkdir()
    window=bpy.context.window
    scene=bpy.data.scenes.new('R19_Disposable_Only')
    window.scene=scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=8
    scene.cycles.seed=0
    scene.cycles.use_adaptive_sampling=False
    scene.cycles.use_denoising=False
    scene.render.film_transparent=True
    scene.render.resolution_x=192
    scene.render.resolution_y=96
    scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Raw'
    scene.render.image_settings.file_format='OPEN_EXR'
    scene.render.image_settings.color_mode='RGBA'
    scene.render.image_settings.color_depth='32'
    scene.render.image_settings.exr_codec='ZIP'
    scene.render.use_simplify=False
    if hasattr(scene.render,'use_texture_cache'):
        scene.render.use_texture_cache=False
        scene.render.use_auto_generate_texture_cache=False
    quads=[(0,1,4,3),(1,2,5,4)]
    low=make_mesh(scene,'R19_RotatedUV_Low',lambda _:0,quads)
    high=make_mesh(scene,'R19_TiltedPlane_High',lambda x: .05-.75*x,quads)
    high.hide_render=True
    uv=low.data.uv_layers.new(name='R19_UV')
    # Left chart T=+X, B=+Y. Right chart T=+Y, B=-X.
    chart=[[(.125,.25),(.375,.25),(.375,.5),(.125,.5)],
           [(.625,.5),(.625,.25),(.875,.25),(.875,.5)]]
    for poly, pts in zip(low.data.polygons,chart):
        for li,p in zip(poly.loop_indices,pts):
            uv.uv[li].vector=p
    r0=(.8,.5,.9); r1=(.5,.2,.9)
    l,r=shader(low,0,r0,uv.name),shader(low,1,r1,uv.name)
    low.data.polygons[1].material_index=1
    camera=bpy.data.objects.new('R19_Orthographic',bpy.data.cameras.new('R19_Orthographic'))
    scene.collection.objects.link(camera)
    scene.camera=camera
    camera.location=(0,0,4)
    camera.data.type='ORTHO'
    camera.data.ortho_scale=2.4
    report={'build':bpy.app.build_hash.decode(),'engine':scene.render.engine,'device':scene.cycles.device,
            'samples':scene.cycles.samples,'build_version':bpy.app.version_string,'uv':uv.name,
            'chart':chart,'normals':{},'bakes':{}}
    for case in ('named_tilt','strength_zero','missing_name','same_rgb_rotated'):
        for _,n,e in (l,r):
            n.uv_map='R19_ABSENT_UV' if case=='missing_name' else uv.name
            n.inputs['Strength'].default_value=0 if case=='strength_zero' else 1
        r[1].inputs['Color'].default_value=(*(r0 if case=='same_rgb_rotated' else r1),1)
        path=directory/(case+'.exr')
        scene.render.filepath=str(path)
        if bpy.ops.render.render(write_still=True)!={'FINISHED'}:
            raise RuntimeError('R19 render '+case)
        image=bpy.data.images.load(str(path),check_existing=False)
        f=read_image(image)
        v=stats(f,192,96,((44,52),(140,148)))
        bpy.data.images.remove(image)
        report['normals'][case]={'file':path.name,'sha256':digest(path),'rgb':v}
    # Native selected-to-active normal bake: physical world-space normal is (0.6, 0, 0.8).
    high.hide_render=False
    # Target is hidden only from previous camera renders; both objects now active in depsgraph.
    bpy.context.view_layer.objects.active=low
    low.select_set(True)
    high.select_set(True)
    for kind in ('NORMAL','EMIT'):
        high.select_set(kind=='NORMAL')
        for mode,margin in (('EXTEND',0),('EXTEND',8),('ADJACENT_FACES',8)):
            label=f'{kind.lower()}_{mode.lower()}_{margin}'
            target=bpy.data.images.new('R19_'+label,128,128,alpha=True,float_buffer=True,is_data=True)
            target.colorspace_settings.name='Non-Color'
            target.generated_color=(0,0,0,0)
            nodes=[]
            for (tree,n,em),encoded in zip((l,r),(r0,r1)):
                # EMIT arm stores pre-encoded tangent numbers, it is not native NORMAL.
                for link in list(em.inputs['Color'].links): tree.links.remove(link)
                em.inputs['Color'].default_value=(*encoded,1)
                node=tree.nodes.new('ShaderNodeTexImage')
                node.image=target
                node.select=True
                tree.nodes.active=node
                nodes.append((tree,node))
            result=bpy.ops.object.bake(type=kind,target='IMAGE_TEXTURES',uv_layer=uv.name,
                margin=margin,margin_type=mode,use_clear=True,use_selected_to_active=(kind=='NORMAL'),
                cage_extrusion=1.0,max_ray_distance=2.0,normal_space='TANGENT',
                normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z')
            if result!={'FINISHED'}:
                raise RuntimeError('R19 bake '+label+' '+str(result))
            path=directory/(label+'.exr')
            target.save_render(str(path),scene=scene)
            f=read_image(target)
            raw=directory/(label+'.rgba-f32')
            raw.write_bytes(f.tobytes())
            report['bakes'][label]={'file':path.name,'sha256':digest(path),'raw':raw.name,
                                     'raw_sha256':digest(raw),'mode_requested':mode,'margin':margin}
            for tree,n in nodes: tree.nodes.remove(n)
            bpy.data.images.remove(target)
    (directory/'record.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
