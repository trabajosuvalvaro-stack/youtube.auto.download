#!/usr/bin/env python3
"""Cooperative disk admission for parallel video jobs. Never deletes project data.
Budgets are declared peak working-set sizes, not filesystem quotas.
"""
import argparse,fcntl,json,os,re,shutil,tempfile,time
from pathlib import Path
GIB=1024**3
DEFAULT=Path('/workspace/scratch/MARTY_STORAGE/reservations.json')
def usage(root):
 seen=set();total=0
 for p in Path(root).rglob('*'):
  try:
   if p.is_symlink() or not p.is_file():continue
   st=p.stat();key=(st.st_dev,st.st_ino)
   if key not in seen:seen.add(key);total+=st.st_size
  except FileNotFoundError:pass
 return total

def transact(registry,project=None,root=None,peak=None,release=False,floor=4*GIB):
 registry=Path(registry);registry.parent.mkdir(parents=True,exist_ok=True)
 with registry.with_suffix('.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  data=json.loads(registry.read_text()) if registry.exists() else {'projects':{}}
  projects=data['projects']
  if project and not re.fullmatch('[A-Za-z0-9_-]{1,100}',project):raise ValueError('INVALID_PROJECT_ID')
  if release:projects.pop(project,None)
  elif project:
   root=Path(root).resolve()
   if not root.is_dir():raise ValueError('ROOT_MUST_EXIST')
   if peak<=0:raise ValueError('POSITIVE_PEAK_REQUIRED')
   if root.stat().st_dev!=registry.parent.stat().st_dev:raise ValueError('DIFFERENT_FILESYSTEM')
   for name,p in projects.items():
    other=Path(p['root'])
    if name!=project and (root.is_relative_to(other) or other.is_relative_to(root)):raise ValueError('OVERLAPPING_PROJECT_ROOT')
   projects[project]={'root':str(root),'peak_bytes':int(peak),'registered_at':time.time()}
  rows=[];remaining=0
  for name,p in projects.items():
   current=usage(p['root']);extra=max(0,p['peak_bytes']-current);remaining+=extra
   rows.append({'project':name,**p,'current_bytes':current,'remaining_reserved_bytes':extra,'over_budget':current>p['peak_bytes']})
  free=shutil.disk_usage(registry.parent).free
  admitted=free-remaining>=floor and not any(r['over_budget'] for r in rows)
  if project and not release and not admitted:raise RuntimeError('INSUFFICIENT_DISK_BUDGET: reduce concurrent jobs/working set or clear verified caches')
  if project:
   fd,tmp=tempfile.mkstemp(dir=registry.parent,prefix='reservations-')
   with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2)
   os.replace(tmp,registry)
  return {'free_bytes':free,'safety_floor_bytes':floor,'remaining_reserved_bytes':remaining,'unreserved_headroom_bytes':free-remaining-floor,'admitted':admitted,'projects':rows,'enforcement':'cooperative; jobs must use this gate, no automatic eviction or expiry'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--registry',default=str(DEFAULT));s=p.add_subparsers(dest='cmd',required=True)
 s.add_parser('status');a=s.add_parser('reserve');a.add_argument('project');a.add_argument('root');a.add_argument('--peak-gib',type=float,required=True)
 a=s.add_parser('release');a.add_argument('project');a=s.add_parser('check');a.add_argument('--next-write-gib',type=float,default=0)
 a=p.parse_args()
 if a.cmd=='reserve':r=transact(a.registry,a.project,a.root,a.peak_gib*GIB)
 elif a.cmd=='release':r=transact(a.registry,a.project,release=True)
 else:r=transact(a.registry)
 if a.cmd=='check' and (not r['admitted'] or r['free_bytes']-a.next_write_gib*GIB<r['safety_floor_bytes']):raise SystemExit('DISK_CHECK_BLOCKED')
 print(json.dumps(r,indent=2))
if __name__=='__main__':main()
