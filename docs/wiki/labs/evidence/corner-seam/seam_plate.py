#!/usr/bin/env python3
"""Show the actual two UV strips, with the crop centred at each seam side."""
from pathlib import Path
import json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from probe_corner import find_geometry,floats,gray_png,pyramid

bake=Path(sys.argv[1]); out=Path(sys.argv[2])
n=2048; probe=floats(bake/'r16-probe.exr',n)
rough=gray_png(bake/'roughness.png',n)
_,seam,uv=find_geometry(json.loads((bake/'r16-surface.json').read_text()),n)
dst=Image.new('RGB',(818,430),(25,25,31))
d=ImageDraw.Draw(dst);f=ImageFont.load_default(size=13)
for row in range(2):
    U=np.mean(np.array(seam['uv_endpoints'][row]),axis=0)
    y=16+207*row
    for j,(label,im) in enumerate((('2048 / Extend 4 px',rough),('512 proxy / Extend 4 px',pyramid(rough,2)),
                                   ('512 proxy / no padding',pyramid(probe[2],2)))):
        x=10+j*270
        r=im.shape[0]
        center=np.array([U[0],1-U[1]])*r
        half=round(r*0.0125)
        x0,y0=(np.round(center).astype(int)-half).tolist()
        crop=im[y0:y0+2*half,x0:x0+2*half]
        patch=Image.fromarray(np.uint8(np.clip(crop,0,1)*255)).convert('RGB').resize((248,164),Image.Resampling.NEAREST)
        dst.paste(patch,(x,y+24))
        d.text((x,y),f'Side {row+1}: {label}',font=f,fill=(234,234,239))
        for u,v in (uv[row,0],uv[row,-1]):
            px=x+(u*r-x0)/(2*half)*248
            py=y+24+((1-v)*r-y0)/(2*half)*164
            d.ellipse((px-3,py-3,px+3,py+3),fill=(250,111,47))
dst.save(out,optimize=True,compress_level=9)
