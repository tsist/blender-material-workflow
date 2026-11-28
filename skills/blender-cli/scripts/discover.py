"""Read local Blender CLI inventory without executing or modifying Blender files."""
import argparse,json,sys
from pathlib import Path
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def describe(root,command=None,query=None,limit=8,include_schema=False):
    root=root.resolve();docs=root/'docs/cli';inventory=read(docs/'通用化开发清单.json');request=read(docs/'schemas/request.schema.json')
    commands=request['properties']['command']['enum'];allowed=inventory['pipeline_allowed']
    if command and command not in commands:raise ValueError('Unknown dotted JSON command: '+command)
    rows=inventory['items']
    if command:rows=[r for r in rows if command in r['commands']]
    if query:rows=[r for r in rows if all(t in json.dumps(r,ensure_ascii=False).casefold() for t in query.casefold().split())]
    result={'ok':True,'root':str(root),'cli_inventory_version':inventory['cli_version'],'entry':str(root/'blenderctl.ps1'),
      'inventory':str(docs/'通用化开发清单.json'),'request_schema':str(docs/'schemas/request.schema.json'),
      'counts':{'request':len(commands),'pipeline':len(allowed),'standalone':len(set(commands)-set(allowed))},
      'command':command,'query':query,'pipeline_allowed':command in allowed if command else None,'matched':len(rows),'truncated':len(rows)>limit,
      'items':[{'id':r['id'],'status':r['status'],'use_case':r['use_case'],'boundary':r['current_boundary'],'commands':r['commands'],
                'schemas':[str(root/p) for p in r['schemas']],'sources':[str(root/p) for p in r['sources']]} for r in rows[:limit]],
      'meaning':'Inventory navigation only; run current CLI help and inspect real inputs. No runtime or GUI certification.'}
    if include_schema:
        if not command:raise ValueError('--schema requires --command')
        branches=[]
        for row in request.get('allOf',[]):
            condition=row.get('if',{}).get('properties',{}).get('command',{})
            if condition.get('const')==command or command in condition.get('enum',[]):branches.append(row)
        result['request_branches']=branches
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('<PROJECT_ROOT>'));p.add_argument('--command');p.add_argument('--query');p.add_argument('--limit',type=int,default=8);p.add_argument('--schema',action='store_true');a=p.parse_args()
    try:
        if not 1<=a.limit<=62:raise ValueError('--limit must be 1..62')
        result=describe(a.root,a.command,a.query,a.limit,a.schema)
    except (OSError,ValueError,KeyError) as e:
        print(json.dumps({'ok':False,'error':str(e),'hint':'Use --root with the existing Blender CLI project; no runtime is installed by this helper.'},ensure_ascii=False));return 2
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
