#!/usr/bin/env python3
"""Make contact sheet of the actual baked roughness pixels near both UV sides."""
from pathlib import Path
import sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from probe_corner import floats

def main(root, dest):
    surface=json.loads((root/'r16-surface.json').read_text())
    sides=[]
    for f in (299,564):
        tri=next(t for t in surface['triangles'] if t['face']==f and {93,136}.issubset(t['vertices']))
        a,b=[tri['uv'][tri['vertices'].index(v)] for v in (93,136)]
        midpoint=(np.array(a)+b)/2
        cx,cy=np.rint(midpoint*[2048,-2048]+[0,2048]).astype(int)
        sides.append((slice(cy-15,cy+15),slice(cx-32,cx+32),np.array([a,b])*[2048,-2048]+[32-cx,2048+15-cy]))
    modes=[('r16-probe','0 px'),('pad_extend_4','Extend 4'),('pad_extend_8','Extend 8'),('pad_extend_16','Extend 16'),('pad_adjacent_faces_4','Adjacent 4'),('pad_adjacent_faces_8','Adjacent 8'),('pad_adjacent_faces_16','Adjacent 16')]
    board=Image.new('RGB',(888,265),'#191f2b')
    d=ImageDraw.Draw(board)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    f=ImageFont.truetype(font,13); b=ImageFont.truetype(font,19)
    d.text((12,10),'Native Cycles roughness · same seam, seven padding arms',fill='white',font=b)
    d.text((12,233),'Gray = linear roughness; orange dashes = UV edge. Both rows are atlas crops, not 3D renders.',fill='#c3cbd8',font=f)
    d.text((12,42),'Face 299 above · Face 564 below · 64 × 30 texture pixels per crop, magnified',fill='#c3cbd8',font=f)
    for i,(stem,name) in enumerate(modes):
        x=12+i*124
        pixels=floats(root/(stem+'.exr'),2048)[2]
        d.text((x,66),name,fill='white',font=f)
        for j,(Y,X,ends) in enumerate(sides):
            data=pixels[Y,X]
            data=np.clip(np.rint(data*255),0,255).astype('uint8')
            y=93+65*j
            tile=Image.fromarray(data).resize((116,54),Image.Resampling.NEAREST).convert('RGB')
            # Clip overlay to the tile so edges cannot cross neighbouring labels.
            td=ImageDraw.Draw(tile)
            for t in np.arange(0.,1.,.035):
                uv=np.array([ends[0]*(1-p)+ends[1]*p for p in (t,min(t+.018,1.))])*[116/64,54/30]
                td.line([tuple(v) for v in uv],fill='#ffb04b',width=1)
            board.paste(tile,(x,y))
    board.save(dest,optimize=True)

main(Path(sys.argv[2]),Path(sys.argv[3]))
