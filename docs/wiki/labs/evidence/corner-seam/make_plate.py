#!/usr/bin/env python3
"""Create a review-only contact sheet; metrics use native-resolution files."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def load(root,size,tag,variant,light):
    tiles=list((root/f'{size}-{tag}'/'jobs').glob(f'*/{variant}-views/{light}/render-000001.png'))
    assert len(tiles)==1
    return Image.open(tiles[0]).convert('RGB')

root,out,size=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
panel=208
p=Image.new('RGB',(824,16+2*(panel+36)),(21,22,27))
d=ImageDraw.Draw(p)
font=ImageFont.load_default(size=13)
for row,light in enumerate(('soft','raking')):
    y=12+row*(panel+36)
    for column,(v,tag) in enumerate((('author','b8'),('author','f16'),
                                      ('reconstructed','b8'),('reconstructed','f16'))):
        x=8+column*204
        d.text((x,y),f'{light} / {v} / {8 if tag=="b8" else 16}-bit',font=font,fill=(239,238,241))
        im=load(root,size,tag,v,light)
        p.paste(im.resize((196,196),Image.Resampling.LANCZOS),(x,y+24))
p.save(out,optimize=True,compress_level=9)
