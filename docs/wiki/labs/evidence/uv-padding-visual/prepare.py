#!/usr/bin/env python3
"""Make scalar inputs from R17's verified native EXR channels, no Blender access."""
import copy, hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path('evidence').resolve()))
from probe_corner import floats, pyramid
root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
out.mkdir(exist_ok=False)
def sha(p): return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
src=json.loads((root/'report.json').read_text())
surface=json.loads((root/'r16-surface.json').read_text())
report=copy.deepcopy(src)
docs={}
def include(p):
    h=sha(p); docs[str(p)]={'file':str(p),'expected_sha256':h}; return h
for c,e in report['channels'].items():
    p=root/Path(e['file']).name
    h=include(p)
    assert h==e['sha256'],c
    e.update(file=str(p))
decl=json.loads(Path('evidence/receipt.json').read_text())
targets={}
for label,stem in [('extend4','pad_extend_4'),('extend16','pad_extend_16'),('adjacent8','pad_adjacent_faces_8'),('zero','r16-probe')]:
    p=root/(stem+'.exr')
    # Replay can change EXR file bytes but the numerical R17 receipt is checked separately.
    buf=floats(p,2048)[2].copy()
    assert np.isfinite(buf).all() and buf.min()>=-1e-6 and buf.max()<=1.00001
    for k in [0,3]:
        res=2048//2**k
        data=pyramid(buf,k)
        vals=np.clip(np.rint(data.astype("f8")*65535),0,65535).astype('<u2')
        f=out/f'{label}_{res}.png'
        Image.fromarray(vals).save(f)
        got=np.asarray(Image.open(f)).astype('f8')/65535
        assert got.shape==(res,res) and np.max(np.abs(got-data)) <= .501/65535
        targets[f'{label}_{res}']=dict(file=str(f),sha256=include(f),side=res,
            native_exr_sha256=sha(p),source_mode=stem,box_factor=2**k)
# Independent geometry-only endpoints, selected by R17.
pts=np.asarray(surface['vertices'])
low,high=pts.min(axis=0),pts.max(axis=0)
seam=pts[[93,136]]
setting={'schema':'wm-r18-visual-v1','original':report,'candidates':targets,
         'bounds':[low.tolist(),high.tolist()],'seam_world':seam.tolist(),
         'focus':((seam.mean(axis=0)-low)/(high-low)).tolist()}
f=out/'r18-lab-config.json'; f.write_text(json.dumps(setting,indent=2)+'\n')
include(f)
j=root.parent.parent
for t in json.loads((j/'procedural-resources.json').read_text()):
    p=Path(t['file']); h=include(p); assert h==t['expected_sha256']
(out/'resources.json').write_text(json.dumps(list(docs.values()),indent=2)+'\n')
print(setting['focus'])
