#!/usr/bin/env python3
"""Compare replayed native helper PNG pairs without converting to 8-bit RGB."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt


def read(path):
    return json.loads(path.read_text())


def one(paths):
    paths = list(paths)
    if len(paths) != 1:
        raise ValueError(paths)
    return paths[0]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def png(p):
    raw = p.read_bytes()[:26]
    assert raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR'
    w, h, bit, model = struct.unpack('>IIBB', raw[16:26])
    # raw: no color-space conversion or quantization to RGB8
    b = subprocess.check_output(['convert', str(p), '-depth', '16',
                                 '-endian', 'LSB', 'rgba:-'])
    return bit, model, np.frombuffer(b, dtype='<u2').reshape(h, w, 4)


def stats(a, b, mask=None):
    if mask is not None:
        a, b = a[mask], b[mask]
    d = np.abs(a.astype(np.int32) - b)
    return {'n': int(a.size), 'changed': int(np.count_nonzero(d)),
            'at_least_1pct': int(np.count_nonzero(d >= 656)),
            'mean_abs': round(float(d.mean()/65535), 8),
            'p99_abs': round(float(np.percentile(d, 99)/65535), 8),
            'max_abs': round(float(d.max()/65535), 8)}


def inputs(root, mode, name):
    folder = root/f'{mode}-{name}'
    result = read(folder/'result.json')
    assert result['ok'] and result['data']['source_unchanged']
    assert all(v == 'pass' for v in result['data']['checks'].values())
    j = folder/'jobs'/result['job_id']
    helper = one(j.glob('helpers/mesh_maps/*/mesh-maps.json'))
    return result, j, helper.parent, read(helper)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('r15', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('variants', nargs='+')
    p.add_argument('--images-out', type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    graphic = Image.new('RGB', (840, len(args.variants)*2*220+32), '#181b20')
    draw = ImageDraw.Draw(graphic)
    draw.text((12, 10), 'Native helper bake: same settings | 8-bit vs 16-bit | residual x64', fill='white')
    frames = Image.new('RGB', (1280,len(args.variants)*358+32), '#181b20')
    fd = ImageDraw.Draw(frames)
    fd.text((12,10),'Authoring preview | matched camera and light | 320px',fill='white')
    receipt = {}
    for i, name in enumerate(args.variants):
        old, new = [inputs(args.r15, mode, name) for mode in ('b8', 'f16')]
        assert old[3]['inputs']['sha256'] == new[3]['inputs']['sha256']
        assert old[0]['data']['input_hashes'] == new[0]['data']['input_hashes']
        assert old[0]['data']['source_sha256'] == new[0]['data']['source_sha256']
        entry = {'job_ids': [x[0]['job_id'] for x in (old,new)],
                 'source_sha256': old[0]['data']['source_sha256'],
                 'input_hashes': {Path(k).name: v for k,v in old[0]['data']['input_hashes'].items()},
                 'mesh_fingerprint': old[3]['inputs']['sha256'],
                 'build': old[3]['inputs']['blender_build_hash'],
                 'maps': {}, 'author_renders': {}, 'export': {}}
        for m, signal in enumerate(('contact_edges', 'sheltered_recess')):
            files = [x[2]/f'{signal}.png' for x in (old,new)]
            a, b = [png(f) for f in files]
            assert (a[0],b[0]) == (8,16)
            assert a[2].shape==b[2].shape
            aa, bb = a[2][:,:,0], b[2][:,:,0]
            sample = (aa > 0) | (bb > 0)
            q8 = ((bb.astype(np.uint32)+128)//257*257).astype(np.uint16)
            rec = [x[3]['maps'][signal] for x in (old,new)]
            assert all(v['disk_decode_verified'] for v in rec)
            assert (rec[0]['parameters'], rec[0]['uv_margin']) == (rec[1]['parameters'], rec[1]['uv_margin'])
            orig = args.r15.parent/'results'/name/(signal+'.png')
            rr = {'full_atlas':stats(aa,bb), 'nonzero_union':stats(aa,bb,sample),
                  'round_16_to_8_vs_native_8':stats(aa,q8,sample),
                  'multiples_of_257_in_16': int((bb[sample]%257==0).sum()),
                  'cut_at_raw_0_5_flip': int(np.count_nonzero((aa>=32768)!=(bb>=32768))),
                  'unique_codes':[int(len(np.unique(t))) for t in (aa,bb)],
                  'bit':[a[0],b[0]],'png_type':[a[1],b[1]],'bytes':[f.stat().st_size for f in files],
                  'sha256':[sha(f) for f in files], 'match_prior_native8': sha(orig)==sha(files[0]),
                  'buffer_disk_error':[v['buffer_disk_max_abs_error'] for v in rec],
                  'parameters':rec[0]['parameters'],'margin':rec[0]['uv_margin']}
            # 64x64 atlas crop chosen using the mean abs residual, not a screen-space crop.
            size=64
            residual=np.abs(aa.astype(np.int32)-bb)
            h,w=aa.shape
            n=np.unravel_index(residual.reshape(h//size,size,w//size,size).mean(axis=(1,3)).argmax(),(h//size,w//size))
            y,x=[int(z)*size for z in n]
            rr['atlas_crop_xywh']=[x,y,size,size]
            entry['maps'][signal]=rr
            y0=32+(i*2+m)*220
            draw.text((12,y0+4),f'{name} | {signal} | atlas ({x},{y},64,64)',fill='white')
            for k,(array,label,gain) in enumerate(((aa,'8-bit native',1),(bb,'16-bit native',1),(residual,'Difference x64',64))):
                tile=np.rint(np.clip(array[y:y+size,x:x+size].astype(float)*gain/65535,0,1)*255).astype('u1')
                picture=Image.fromarray(tile).resize((176,176),Image.Resampling.NEAREST).convert('RGB')
                left=12+270*k
                graphic.paste(picture,(left,y0+22))
                draw.text((left,y0+201),label,fill='white')
        for k,view in enumerate(('soft','raking')):
            renders=[one(x[1].glob(f'author-views/{view}/render-*.png')) for x in (old,new)]
            entry['author_renders'][view]=stats(*(png(f)[2][:,:,:3] for f in renders))
            for lane,photo in enumerate(renders):
                x,y=(2*k+lane)*320,32+i*358
                fd.text((x+8,y+3),f'{name} | {view} | {8 if lane==0 else 16}-bit',fill='white')
                with Image.open(photo) as picture:
                    frames.paste(picture.convert('RGB'),(x,y+22))
        e = [list(x[1].glob('baked/*/roughness.png')) for x in (old,new)]
        if any(e):
            exp=[one(y).parent for y in e]
            av=[png(x/'alpha.png')[2] for x in exp]
            assert np.array_equal(*av)
            mask=distance_transform_edt(av[0][:,:,3]>32767)>12
            entry['export']={'same_alpha':True,'uv_interior':int(mask.sum()),
                             'elapsed_seconds':[round(x[0]['data']['seconds'],1) for x in (old,new)]}
            for channel in ('base_color','roughness','metallic','normal'):
                arr=[png(x/f'{channel}.png')[2][:,:,:3] for x in exp]
                entry['export'][channel]={'all_rgb':stats(*arr,mask),'png_sha256':[sha(x/f'{channel}.png') for x in exp]}
                if channel in ('roughness','metallic'):
                    assert all(np.array_equal(t[:,:,0],t[:,:,1]) and np.array_equal(t[:,:,0],t[:,:,2]) for t in arr)
                    entry['export'][channel]['scalar']=stats(*(t[:,:,0] for t in arr),mask)
            for view in ('soft','raking'):
                paths=[one(x[1].glob(f'reconstructed-views/{view}/render-*.png')) for x in (old,new)]
                entry['export'][view]=stats(*(png(f)[2][:,:,:3] for f in paths))
        receipt[name]=entry
    images = args.images_out or args.out
    images.mkdir(parents=True, exist_ok=True)
    graphic.save(images/'helper-depth.png',optimize=True)
    frames.resize((640,frames.height//2),Image.Resampling.LANCZOS).save(
        images/'helper-depth-views.png',optimize=True)
    (args.out/'helper-depth-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__ == '__main__':
    main()
