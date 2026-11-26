#!/usr/bin/env python3
"""Re-root a reconstruction and its declared textures before independent CLI open."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

def sha(p):
    return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()

def write(p,data):
    p.write_text(json.dumps(data, indent=2)+'\n')

root=Path(sys.argv[1]).resolve()
dest=Path(sys.argv[2]).resolve()
ctl=Path(sys.argv[3]).resolve()
blender=Path(sys.argv[4]).resolve()
for name in sys.argv[5:]:
    result=json.loads((root/name/'result.json').read_text())
    assert result['ok']
    job=Path(result['artifacts']['job_directory'])
    report=json.loads((job/'procedural-report.json').read_text())
    original=Path(report['reconstructed']['file']).resolve()
    bake_dirs=list((job/'baked').glob('bake-*'))
    assert len(bake_dirs)==1
    b=json.loads((bake_dirs[0]/'report.json').read_text())
    srcpaths={Path(c['file']).resolve():c['sha256'] for c in b['channels'].values()}
    d=dest/name
    d.mkdir(parents=True,exist_ok=False)
    candidate=d/original.relative_to(job)
    shutil.copy2(original,candidate)
    assert sha(original)==sha(candidate)
    resources=[]
    for p,s in sorted(srcpaths.items()):
        q=d/p.relative_to(job)
        q.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,q)
        assert sha(p)==sha(q)==s
        resources.append({'file':str(q),'expected_sha256':s})
    rp=d/'resources.json';write(rp,resources)
    args=[sys.executable,str(ctl),'--blender',str(blender),'--jobs-dir',str(d/'verify-jobs'),'--full',
        'project','verify',str(candidate),'--expected-sha256',sha(candidate),'--resources',str(rp)]
    out=json.loads(subprocess.check_output(args))
    h=out['data']
    declared={r['file'] for r in resources}
    resolved=set(h['external_paths'])
    assert out['ok'] and h['validation']['open']=='pass' and not h['undeclared_paths']
    # Alpha and height may be declared files but not linked in reconstruction.
    assert resolved and not (resolved-declared) and all(Path(p).is_relative_to(d) for p in resolved)
    assert all(h['input_hashes'][r['file']]==r['expected_sha256'] for r in resources)
    assert h['source_unchanged'] and h['profile']['background'] and h['profile']['factory_startup']
    write(d/'verified.json',{'mode':name,'opened':h['validation']['open'],
        'same_file_sha256':sha(original),'declared_png_hashes':{str(Path(a['file']).relative_to(d)):a['expected_sha256'] for a in resources},
        'loaded_in_move_tree':sorted(str(Path(a).relative_to(d)) for a in resolved),
        'undeclared':h['undeclared_paths'],'unneeded_declared':sorted(str(Path(a).relative_to(d)) for a in declared-resolved),
        'offline_factory_startup':not h['profile']['online_access'] and h['profile']['factory_startup'],
        'source_unchanged':h['source_unchanged'],'render_on_moved_copy':'not_run'})
