"""Independent float-EXR readback and angle checks; needs NumPy, Pillow and FFmpeg."""
import hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

run,dest=map(Path,sys.argv[1:])
dest.mkdir(parents=True,exist_ok=True)
r=json.loads((run/'record.json').read_text())
assert (r['build'],r['engine'],r['device'])==('02f0899d78e3','CYCLES','CPU')
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def exr(e,w,h):
    path=run/e['file']
    assert sha(path)==e['sha256']
    planes=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-threads','1','-i',str(path),'-pix_fmt','gbrapf32le','-f','rawvideo','-threads','1','-']),'<f4')
    x=planes.reshape(4,h,w)[[2,0,1,3]].transpose(1,2,0)
    assert np.isfinite(x).all()
    return x
def unit(v):
    return v/np.linalg.norm(v,axis=-1,keepdims=True)
def angle(u,v):
    u,v=unit(np.array(u)),unit(np.array(v))
    return float(np.degrees(np.arctan2(np.linalg.norm(np.cross(u,v)),np.dot(u,v))))
z=[0,0,1]; plusx=[.6,0,.8]; plusy=[0,.6,.8]
guesses={'named_tilt':(plusx,plusx),'strength_zero':(z,z),'missing_name':(z,z),'same_rgb_rotated':(plusx,plusy)}
r['probe_metrics']={}
for name,target in guesses.items():
    m=r['normals'][name]
    img=exr(m,192,96)
    xp=np.stack([img[44:52,c:c+8,:3].astype(np.float64).mean(axis=(0,1)) for c in (44,140)])
    assert np.allclose(xp,np.array(m['rgb']),rtol=0,atol=2e-7)
    v=unit(2*xp-1)
    avg=[angle(a,t) for a,t in zip(v,target)]
    assert max(avg)<0.5
    r['probe_metrics'][name]={
        'world_normals':v.tolist(), 'tilt_degrees':[angle(x,z) for x in v],
        'direction_error_deg':avg,'across_charts_degrees':angle(*v)}
raws={}
for name,e in r['bakes'].items():
    path=run/e['raw']
    assert sha(path)==e['raw_sha256']
    b=np.fromfile(path,'<f4').reshape(128,128,4)
    assert np.array_equal(exr(e,128,128)[::-1],b)
    raws[name]=b
n0,n8,na=[raws[f'normal_{x}'] for x in ('extend_0','extend_8','adjacent_faces_8')]
e0,e8,ea=[raws[f'emit_{x}'] for x in ('extend_0','extend_8','adjacent_faces_8')]
assert np.array_equal(n8,na) and r['bakes']['normal_extend_8']['sha256']==r['bakes']['normal_adjacent_faces_8']['sha256']
assert np.all(n0[...,3]==1)
changed=lambda a,b: np.any(np.abs(a-b)>1e-6,axis=-1)
n_changed=changed(n0,n8)
assert n_changed.sum()>0 and not np.any(n_changed & (e0[...,3]>.5))
patch=(48,50)
left_uv_normal=[.8,.5,.9]; right_uv_normal=[.5,.2,.9]
assert np.allclose(e8[patch][:3],left_uv_normal,atol=1e-6)
assert np.allclose(ea[patch][:3],right_uv_normal,atol=1e-6)
assert np.allclose(n0[patch][:3],[.5,.5,1.],atol=1e-6)
left_interior=(48,32);right_interior=(48,96)
right_to_world=lambda v: [-v[1],v[0],v[2]]
native_tilts=[angle(2*n8[left_interior][:3]-1,plusx),
              angle(right_to_world(2*n8[right_interior][:3]-1),plusx)]
assert max(native_tilts)<0.02
angle_if_misread=angle(2*ea[patch][:3]-1, 2*e8[patch][:3]-1)
r['gutter_metrics']={
    'covered_pixels_baseline_emit_alpha':int((e0[...,3]>.5).sum()),
    'native_rgb_pixels_changed_after_adding_8':int(n_changed.sum()),
    'native_extend_vs_requested_adjacent_changed':int(changed(n8,na).sum()),
    'emit_extend_vs_adjacent_rgba_changed':int(changed(e8,ea).sum()),
    'emit_shared_edge_donor_count':int((np.all(np.abs(e8[32:65,48:56,:3]-left_uv_normal)<1e-6,axis=-1)&np.all(np.abs(ea[32:65,48:56,:3]-right_uv_normal)<1e-6,axis=-1)).sum()),
    'left_gutter_pixel_xy_from_bottom':[patch[1],patch[0]],
    'left_gutter_emit_extend':e8[patch][:3].tolist(),
    'left_gutter_emit_adjacent':ea[patch][:3].tolist(),
    'left_gutter_native_zero':n0[patch][:3].tolist(),
    'left_gutter_native_extend':n8[patch][:3].tolist(),
    'gutter_angle_if_donor_read_in_receiver_deg':angle_if_misread,
    'native_interior_max_error_deg':max(native_tilts)}
assert abs(angle_if_misread-50.20818)<0.001
(dest/'r19-receipt.json').write_text(json.dumps(r,indent=2)+'\n')
W,H=840,620
out=Image.new('RGB',(W,H),'#171c25');d=ImageDraw.Draw(out)
font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
d.text((22,14),'UV tangent basis | Cycles 5.3.0 / synthetic 90-degree seam',font=font(24),fill='white')
def paste(a, at,size, invert):
    if invert: a=a[::-1]
    img=Image.fromarray(np.uint8(np.clip(a[...,:3],0,1)*255+.5)).resize(size,Image.Resampling.NEAREST)
    out.paste(img,at)
for i,(key,label) in enumerate((('named_tilt','Correct UV names'),('missing_name','Missing UV names'),('same_rgb_rotated','Same RGB, rotated UV'))):
    xx=22+270*i
    d.text((xx,58),label,font=font(17),fill='#e3e9f7')
    paste(exr(r['normals'][key],192,96),(xx,90),(248,124),False)
    vals=r['probe_metrics'][key]
    d.text((xx,223),f"Across charts: {vals['across_charts_degrees']:.2f} deg",font=font(16),fill='#c5d9ff')
for j,kind in enumerate(('normal','emit')):
    y=268+j*142
    for i,(key,label) in enumerate((('extend_0','Zero margin'),('extend_8','Extend 8'),('adjacent_faces_8','Requested Adjacent 8'))):
        xx=22+270*i
        key=kind+'_'+key
        d.text((xx,y),f'{kind.upper()} {label}',font=font(16),fill='#e3e9f7')
        paste(raws[key][30:67,8:120],(xx,y+30),(248,82),True)
        x=int(xx+(50-8+.5)*248/112)
        py=int(y+30+(67-48-.5)*82/37)
        d.rectangle((x-3,py-3,x+3,py+3),outline='yellow',width=1)
d.text((22,571),'Yellow marker = recipient gutter. Native NORMAL uses Extend in both 8 px requests.',font=font(16),fill='#c5d9ff')
d.text((22,594),'False-colour RGB is a diagnostic, not a material beauty render.',font=font(15),fill='#b7c3d9')
out.save(dest/'tangent-normal-uv-guard.png',optimize=True)
print(json.dumps(r['gutter_metrics'],indent=2))
