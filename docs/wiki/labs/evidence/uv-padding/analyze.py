#!/usr/bin/env python3
"""Analyze native Cycles buffers. Box-filter sizes are CPU proxies, not GPU mips."""
from collections import defaultdict
from pathlib import Path
import json
import sys
import numpy as np

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from probe_corner import floats, gray_png, find_geometry, sample, pyramid, stats, sha


def island_raster(surface, n):
    triangles = surface['triangles']
    edges = defaultdict(list)
    parent = list(range(len(triangles)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for idx, t in enumerate(triangles):
        ids, uv = t['vertices'], np.array(t['uv'])
        for i, j in ((0,1),(1,2),(2,0)):
            if ids[i] > ids[j]:
                i,j=j,i
            for k, other in edges[ids[i],ids[j]]:
                if np.max(np.abs(uv[[i,j]]-other)) <= 1e-6:
                    parent[find(idx)] = find(k)
            edges[ids[i],ids[j]].append((idx,uv[[i,j]]))

    roots = [find(i)+1 for i in range(len(triangles))]
    labels = np.zeros((n,n), dtype='i4')
    face_islands = defaultdict(set)
    for t, lab in zip(triangles, roots):
        face_islands[t['face']].add(lab)
        uv = np.array(t['uv'])*[1,-1]+[0,1]
        basis = (uv[1:] - uv[0]).T
        if abs(np.linalg.det(basis)) < 1e-12:
            continue
        x0,y0 = np.maximum(np.floor(uv.min(axis=0)*n).astype(int),0)
        x1,y1 = np.minimum(np.ceil(uv.max(axis=0)*n).astype(int),n)
        y,x = np.mgrid[y0:y1,x0:x1]
        w = (np.stack((x+.5,y+.5),axis=-1)/n-uv[0]) @ np.linalg.inv(basis).T
        inside = (w.min(axis=-1)>=-1e-8)&(w.sum(axis=-1)<=1+1e-8)
        region = labels[y0:y1,x0:x1]
        conflict = inside & (region != 0) & (region != lab)
        region[inside & (region == 0)] = lab
        region[conflict] = -1
    return labels, face_islands, len(set(roots))


def signed(x):
    return dict(stats(x), mean_signed=float(np.mean(x)))


def main(p, out):
    settings = json.loads((p/'r17-settings.json').read_text())
    n = settings['image_side']
    assert n == 2048 and settings['sample_count'] == 16
    surface = json.loads((p/'r16-surface.json').read_text())
    _, seam, uv = find_geometry(surface, n)
    assert seam['vertex_ids'] == [93,136] and seam['face_ids']==[299,564]
    labels, face_islands, island_count = island_raster(surface, n)
    sides = [sorted(face_islands[i]) for i in seam['face_ids']]
    assert all(len(x)==1 for x in sides), sides
    base = floats(p/'r16-probe.exr', n)
    covered = base[3]>.99
    assert np.isfinite(base).all() and np.all(sample(base[3],uv)>.999)
    scalar = gray_png(p/'roughness.png',n)
    assert np.max(np.abs(scalar[covered]-base[2][covered])) <= 3/65535
    weights = [((labels==x[0])&covered).astype('f4') for x in sides]
    numerators = [base[2]*w for w in weights]
    def local(k):
        den = [sample(pyramid(w,k),s) for s,w in zip(uv,weights)]
        assert np.min(den)>0
        return np.array([sample(pyramid(q,k),s)/d for s,q,d in zip(uv,numerators,den)]), np.array(den)
    ref, support0 = local(0)
    strict = support0 >= .95
    assert np.min(support0) > 0 and np.count_nonzero(strict)>20
    details = {'min': float(support0.min()), 'full_near': int(strict.sum()),
        'samples': int(strict.size), 'strict_threshold': .95}
    rows = []
    maps = {}
    for mode, width in settings['mode_pixels']:
        f = p/('r16-probe.exr' if width==0 else f'pad_{mode.lower()}_{width}.exr')
        pixels = floats(f,n)
        assert np.isfinite(pixels).all()
        rough, alpha = pixels[2:]
        assert np.max(np.abs(rough[covered]-base[2][covered])) <= 3/65535
        maps[f.stem] = {'sha256':sha(f),'positive_alpha_texels':int((alpha>.99).sum()),
            'covered_texels_max_abs_change':float(np.max(np.abs(rough[covered]-base[2][covered])))}
        for k in range(5):
            proxy = sample(pyramid(rough,k),uv)
            island, support = local(k)
            assert np.max(np.abs((proxy-ref)-((proxy-island)+(island-ref)))) < 1e-6
            rows.append({'mode':mode,'pixel_padding':width,'cpu_mip_side':n//2**k,
                'total':signed(proxy-ref),'same_island_lowpass':signed(island-ref),
                'atlas_minus_island':signed(proxy-island),'support_min':float(support.min()),
                'strict_subset_total':signed((proxy-ref)[strict]),
                'native_raw_baseline_total':signed(proxy-sample(base[2],uv)),
                'change_in_two_side_gap':signed((proxy[0]-proxy[1])-(ref[0]-ref[1])),
                'total_per_side':[signed(x) for x in proxy-ref]})
    result = dict(settings=settings,seam=seam,source='CarryToolbox R16 geometry and original 2K 8-bit helper route',
        island_count=island_count, same_island_2k_support=details, side_island_labels=sides, raster_conflicts=int((labels==-1).sum()),
        covered_texels=int(covered.sum()), covered_texels_unassigned=int((covered&(labels<=0)).sum()),
        maps=maps,rows=rows)
    out.write_text(json.dumps(result, indent=2)+'\n')


if __name__=='__main__':
    # Four equal-weight taps: preserve physical support separate from empty/foreign UV space.
    ref=.20; local=(.20+.40)/2; atlas=(.20+.40+0+.80)/4
    assert np.allclose([local-ref,atlas-local,atlas-ref],[.10,.05,.15])
    main(Path(sys.argv[2]),Path(sys.argv[3]))
