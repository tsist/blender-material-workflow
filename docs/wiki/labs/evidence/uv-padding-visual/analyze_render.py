#!/usr/bin/env python3
"""Compare fixed renderer frames; sRGB display-code differences are not linear energy."""
from pathlib import Path
import hashlib, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import map_coordinates
j=Path(sys.argv[1])
dest=Path(sys.argv[2])
dest.mkdir(exist_ok=True)
p=json.loads((j/'procedural-report.json').read_text())
assert p['status']=='pass' and p['checks']['r18_guarded_reconstruction_render_decode']=='pass'
def sha(path):return hashlib.file_digest(Path(path).open('rb'),'sha256').hexdigest()
variants=p['r18']['variants']
assert len(variants)==8 and all(v['preserved_non_target'] for v in variants.values())
assert len({tuple(sorted(v['other_channel_hashes'].items())) for v in variants.values()})==1
frames={}
views={}
for row in p['outputs']:
    if row['variant'] not in variants: continue
    f=Path(row['file'])
    assert sha(f)==row['sha256'] and row['engine']=='CYCLES' and row['device']['backend']=='CPU'
    key=(row['variant'],row['view'])
    im=np.asarray(Image.open(f).convert('RGB'))
    case=row['framing']['r18']
    assert im.shape==(384,384,3) and not any(case[x] for x in ('simplify','texture_cache','auto_generate_cache'))
    frames[key]=im
    views[key]=(case,row['sha256'])
assert len(frames)==16
results={'inputs':variants,'branch':'cache_disabled; no Simplify; 256 are controlled offline box inputs','views':{},'measurements':{}}
modes=('zero','extend4','extend16','adjacent8')
for view in ('detail','whole'):
    case=views['extend4_2048',view][0]
    assert all(views[v,view][0]==case for v in variants)
    line=np.array(case['seam_px'])
    delta=line[1]-line[0]
    span=np.linalg.norm(delta)
    normal=np.array([-delta[1],delta[0]])/span
    y,x=np.mgrid[0:384,0:384]
    xy=np.stack((x+.5,y+.5),axis=-1)-line[0]
    u=(xy@delta)/span**2
    s=xy@normal
    seam=(u>=.15)&(u<=.85)&(np.abs(s)<=3)
    flanks=(u>=.15)&(u<=.85)&(np.abs(s)>=5)&(np.abs(s)<=10)
    assert min(seam.sum(),flanks.sum())>30
    coords=line[0]+np.linspace(.2,.8,41)[:,None]*delta
    def cross_gap(img):
        y=img.astype(float)@[.2126,.7152,.0722]
        sample=lambda c: map_coordinates(y,[c[:,1]-.5,c[:,0]-.5],order=1,prefilter=False)
        return sample(coords+2*normal)-sample(coords-2*normal)
    def diff(a,b):
        d=np.abs(a.astype('i2')-b.astype('i2')).max(axis=-1)
        def measure(mask):
            v=d[mask]
            return {'px':int(v.size),'mean_max_rgb_code':float(v.mean()),'max_code':int(v.max()),
                    'px_at_least_4':int((v>=4).sum()),'px_at_least_8':int((v>=8).sum())}
        return {'band':measure(seam),'flanks':measure(flanks),
                'absolute_pair_gap_change_luma_mean':float(np.abs(cross_gap(a)-cross_gap(b)).mean())}
    results['views'][view]=dict(case,seam_span_pixels=float(span))
    ref=frames['extend4_2048',view]
    for mode in modes:
        for side in (256,2048):
            v=f'{mode}_{side}'
            im=frames[v,view]
            results['measurements'][v+':'+view]={'against_extend4_same_size':diff(im,frames[f'extend4_{side}',view]),
                 'against_r17_native4_originalsize':diff(im,ref),'screen_sha256':views[v,view][1]}
    for mode in modes:
        key=f'{mode}_256:{view}'
        results['measurements'][key]['against_same_mode_native_size']=diff(frames[mode+'_256',view],frames[mode+'_2048',view])
    board=Image.new('RGB',(960,590),'#191e27');d=ImageDraw.Draw(board)
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    d.text((16,10),f'Cycles roughness swap | {view.title()} view | seam spans {span:.0f} px in the 384 px frame',font=font(20),fill='white')
    for column,mode in enumerate(modes):
        xx=16+234*column
        d.text((xx,45),{'zero':'No margin','extend4':'Extend 4 px','extend16':'Extend 16 px','adjacent8':'Adjacent Faces 8 px'}[mode],font=font(16),fill='white')
        for i,sz in enumerate((2048,256)):
            yy=76+i*250
            d.text((xx,yy),('Native 2048 input' if sz==2048 else 'Manual box-filtered 256'),font=font(14),fill='#bfc9d7')
            im=Image.fromarray(frames[f'{mode}_{sz}',view])
            # Original screen pixels in a centered crop. No resampling.
            c=np.rint(line.mean(axis=0)).astype(int)
            rect=np.concatenate((c-[88,100],c+[88,100]))
            panel=im.crop(tuple(rect))
            board.paste(panel,(xx,yy+22))
    board.save(dest/f'cycles-roughness-{view}.png',optimize=True)
(dest/'r18-receipt.json').write_text(json.dumps(results,indent=2)+'\n')
