#!/usr/bin/env python3
"""R16: measure native bake buffers and a box-filter UV sampling proxy."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, map_coordinates


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def floats(path, n):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-threads', '1',
        '-gamma', '1', '-i', str(path), '-frames:v', '1', '-c:v', 'rawvideo',
        '-threads', '1', '-pix_fmt', 'gbrapf32le', '-f', 'rawvideo', 'pipe:1'])
    return np.frombuffer(raw, '<f4').reshape(4, n, n)[[2,0,1,3]]


def gray_png(path, n):
    hdr = path.read_bytes()[:29]
    assert hdr[:8] == b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>IIB',hdr[16:25]) == (n,n,16)
    raw = subprocess.check_output(['convert',str(path),'-channel','R','-separate',
                                   '+channel','-depth','16','-endian','MSB','gray:-'])
    return np.frombuffer(raw,'>u2').reshape(n,n).astype(np.float32)/65535


def find_geometry(d, n):
    """Select the seam using geometry only; rasterize XYZ ROI at actual texel centers."""
    V = np.array(d['vertices'])
    T = [(t['face'], t['vertices'], np.array(t['uv'])) for t in d['triangles']]
    edges = defaultdict(list)
    roi = {k:np.zeros((n,n),bool) for k in ('corner','front_control')}
    low = np.array([.20,-.123,.136]); high = np.array([.250,-.077,.194])
    low_c = np.array([-.075,-.116,.057]); high_c = np.array([.075,-.111,.109])
    for face, ids, uv in T:
        pos = V[ids]
        for i,j,k in [(0,1,2),(1,2,0),(2,0,1)]:
            if ids[i] > ids[j]: i,j=j,i
            edges[ids[i],ids[j]].append((face,ids[k],uv[[i,j,k]]))
        ranges = [(name,lower,upper) for name,lower,upper in [('corner',low,high),('front_control',low_c,high_c)]
                  if np.all(pos.max(axis=0)>=lower) and np.all(pos.min(axis=0)<=upper)]
        if not ranges: continue
        uv = uv*np.array([1,-1])+[0,1]
        U = (uv[1:] - uv[0]).T
        if abs(np.linalg.det(U)) < 1e-12: continue
        x0,y0 = np.maximum(np.floor(uv.min(axis=0)*n).astype(int),0)
        x1,y1 = np.minimum(np.ceil(uv.max(axis=0)*n).astype(int),n)
        y,x = np.mgrid[y0:y1,x0:x1]
        w = (np.stack((x+.5,y+.5),axis=-1)/n-uv[0]) @ np.linalg.inv(U).T
        inside = (w.min(axis=-1)>=-1e-8)&(w.sum(axis=-1)<=1+1e-8)
        xyz = pos[0] + w @ (pos[1:] - pos[0])
        for name,lower,upper in ranges:
            roi[name][y0:y1,x0:x1] |= inside & np.all((xyz>=lower)&(xyz<=upper),axis=-1)
    candidates = []
    for edge,sides in edges.items():
        if len(sides)!=2 or sides[0][0]==sides[1][0]: continue
        if np.max(np.abs(sides[0][2][:2]-sides[1][2][:2])) < 1e-5: continue
        A,B=V[list(edge)]
        length=np.linalg.norm(B-A)
        M=(A+B)/2
        if length<.009 or not np.all((M>=low)&(M<=high)): continue
        def inward(s):
            return V[s[1]]-A - np.dot(V[s[1]]-A,B-A)/length**2*(B-A)
        widths=[np.linalg.norm(inward(s)) for s in sides]
        if min(widths)<.0012:continue
        candidates.append((float(np.linalg.norm(M-[.225,-.111,.163])),edge,length,sides))
    if not candidates: raise ValueError('No two-sided UV cut in declared corner band')
    _,edge,length,sides=min(candidates,key=lambda item:(item[0],item[1]))
    A,B=V[list(edge)]
    s_values=np.linspace(.2,.8,65)
    UV=[]
    # Constant physical inset toward each adjacent triangle, same arclength.
    inset=.0003
    for face,other,uv in sides:
        side=V[other]-A
        proj=np.dot(side,B-A)/length**2
        h=np.linalg.norm(side-proj*(B-A))
        w=inset/h
        t=s_values-w*proj
        if min(t.min(),1-t.max()-w)<0:raise ValueError('Inset escaped selected triangle')
        UV.append((1-t-w)[:,None]*uv[0]+t[:,None]*uv[1]+w*uv[2])
    return roi,{'vertex_ids':list(edge),'face_ids':[s[0] for s in sides],
                'xyz_endpoints':[list(A),list(B)],'inset_m':inset,
                'samples_per_side':len(s_values),
                'uv_endpoints':[s[2][:2].tolist() for s in sides]}, np.array(UV)


def stats(vals, threshold=.01):
    vals=np.abs(np.asarray(vals,dtype='f8'))
    return {'count':int(vals.size),'mean_abs':float(vals.mean()) if vals.size else None,
            'max_abs':float(vals.max()) if vals.size else None,
            'at_least_0p01':int(np.count_nonzero(vals>=threshold))}


def sample(im, uv):
    n,m=im.shape
    y,x=(1-uv[...,1])*n-.5,uv[...,0]*m-.5
    return map_coordinates(im,[y,x],order=1,mode='nearest',prefilter=False)


def pyramid(im, k):
    f=2**k
    a,b=im.shape
    return im.reshape(a//f,f,b//f,f).mean(axis=(1,3))


def run(root, helper):
    loaded=[]
    for mode in ['b8','f16']:
        dirs=list((root/f'{helper}-{mode}'/'jobs').glob('*/baked/bake-*'))
        assert len(dirs)==1,dirs
        p=dirs[0];job=p.parent.parent
        result=json.loads((root/f'{helper}-{mode}'/'result.json').read_text())
        assert result['ok'] and result['data']['source_unchanged'] and not result['data']['source_saved']
        assert result['data']['source_sha256']=='537214fbf4c462c2dc3e20f0eac16c94307eef46afed929cd36818319d8efaa5'
        assert all(val=='pass' for val in result['data']['checks'].values())
        b=json.loads((p/'report.json').read_text()); n=b['settings']['size']; assert n==2048
        views=json.loads((job/'procedural-report.json').read_text())['outputs']
        uv=json.loads((p/'r16-surface.json').read_text())
        a=floats(p/'r16-probe.exr',n)
        assert np.isfinite(a).all() and (a[3]>.99).sum()>100000
        rough=gray_png(p/'roughness.png',n)
        present=a[3]>.99
        assert np.max(np.abs(a[2][present]-rough[present])) <= 3/65535, 'OpenEXR channel/alpha or scalar bake mismatch'
        assert uv['incoming_node']=='weathering_susceptibility/math'
        manifest=json.loads((job/'procedural-manifest.json').read_text())
        loss=next(s for s in manifest['signals'] if s['id']=='coating_loss')
        rn=loss['parameters']
        assert abs(rn['from_min']-.25)<1e-7 and abs(rn['from_max']-.28)<1e-7
        assert rn['interpolation']=='SMOOTHSTEP' and loss['inputs']['value']=='weathering_susceptibility'
        assert manifest['mesh_map_size']==helper and b['settings']['bit_depth']=='16'
        assert a[1][present].min()>=0 and a[1][present].max()==1
        assert np.unique(a[0][present]).size>10000 and np.unique(a[1][present]).size>10000
        loaded.append((p,b,uv,a,rough,views))
    (p,b,uv,x,r8,v8),(q,c,uv2,y,r16,v16)=loaded
    assert uv==uv2 and b['uv_source']==c['uv_source']
    assert [(i['id'],i['framing']) for i in v8]==[(i['id'],i['framing']) for i in v16]
    assert np.array_equal(x[3],y[3])
    assert (p/'alpha.png').read_bytes()==(q/'alpha.png').read_bytes()
    roi,seam,UV=find_geometry(uv,n)
    band_x=(x[0]>.25)&(x[0]<.28);band_y=(y[0]>.25)&(y[0]<.28)
    regional={}
    for name,region in roi.items():
        ok=region&(x[3]>.99)
        u=ok&(band_x|band_y)
        regional[name]={'covered':int(ok.sum()),'band_8':int((ok&band_x).sum()),
            'band_16':int((ok&band_y).sum()),'band_union':int(u.sum()),
            'before':stats((x[0]-y[0])[ok]),'mask':stats((x[1]-y[1])[ok]),
            'mask_in_union':stats((x[1]-y[1])[u]),'roughness':stats((r8-r16)[ok])}
    pre_x=sample(x[0],UV);pre_y=sample(y[0],UV)
    valid_seam=(sample(x[3],UV)>.999)&(sample(y[3],UV)>.999)
    seam['probe_full_coverage_pairs']=int(valid_seam.all(axis=0).sum())
    seam['native_unpadded_point_samples']={
        'band_8':int(((pre_x>.25)&(pre_x<.28)&valid_seam).sum()),
        'band_16':int(((pre_y>.25)&(pre_y<.28)&valid_seam).sum()),
        'mask_difference':stats((sample(x[1],UV)-sample(y[1],UV))[valid_seam])}
    rows=[]
    # Independent offline candidate: nearest covered texel at fixed radii. This
    # is not a native EXTEND bake or proof of the nearest island's identity.
    distance, indices=distance_transform_edt(x[3]<=.99, return_indices=True)
    nearest=x[2][tuple(indices)]
    dilation={}
    baseline=sample(r8,UV)
    for radius in (4,8,16):
        trial=np.where(distance<=radius, nearest, 0).astype('f4')
        dilation[str(radius)]={str(k):stats(sample(pyramid(trial,k),UV)-baseline) for k in (0,1,2,3,4)}
    for k in range(5):
        a0,b0=sample(r8,UV),sample(r16,UV)
        a1,b1=sample(pyramid(r8,k),UV),sample(pyramid(r16,k),UV)
        # Negative control: true margin-zero probe, not a change to the final export.
        u8,u16=sample(pyramid(x[2],k),UV),sample(pyramid(y[2],k),UV)
        rows.append({'level':k,'mip_size':n//2**k,'between_depths':stats(b1-a1),
            'extend_deviation_from_level0':{'b8':stats(a1-a0),'f16':stats(b1-b0)},
            'change_in_two_side_gap_b8':stats((a1[0]-a1[1])-(a0[0]-a0[1])),
            'no_margin_deviation_from_padded_level0':{'b8':stats(u8-a0),'f16':stats(u16-b0)}})
    vis={}
    by16={v['id']:v for v in v16}
    for v in v8:
        a=np.array(Image.open(v['file']).convert('RGB'),dtype='i2');z=np.array(Image.open(by16[v['id']]['file']).convert('RGB'),dtype='i2')
        vis[v['id']]={'mean_abs_code':float(np.abs(a-z).mean()),'max_abs_code':int(np.abs(a-z).max()),
                      'pixels_at_least_4_codes':int((np.abs(a-z).max(axis=2)>=4).sum()),
                      'file_sha256':[sha(Path(v['file'])),sha(Path(by16[v['id']]['file']))]}
    def noncommutativity(data):
        t=np.clip((data[0]-.25)/.03,0,1)
        err=t*t*(3-2*t)-data[1]
        return {k:stats(err[m&(data[3]>.99)]) for k,m in roi.items()}
    return {'remap_of_baked_input_vs_baked_remap':{'b8':noncommutativity(x),'f16':noncommutativity(y)},
            'helper_size':helper,'final_size':n,'margin':b['settings']['margin'],'uv_layer':uv['exact_uv'],
            'source_sha256':'537214fbf4c462c2dc3e20f0eac16c94307eef46afed929cd36818319d8efaa5',
            'incoming_node':uv['incoming_node'],'regions':regional,'seam':seam,'mips_box_proxy':rows,
            'dilation_candidate_cpu_only':dilation,
            'render_comparison_srgb_display_codes':vis,'framing':v8[0]['framing'],
            'sha256':{mode:{key:sha(d/key) for key in ['r16-probe.exr','r16-surface.json','roughness.png','alpha.png']} for mode,d in [('b8',p),('f16',q)]}}


if __name__=='__main__':
    root, output, *sizes=sys.argv[1:]
    results=[run(Path(root),int(size)) for size in sizes]
    Path(output).write_text(json.dumps(results,indent=2)+'\n')
