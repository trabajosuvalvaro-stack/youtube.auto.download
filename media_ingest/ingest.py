#!/usr/bin/env python3
"""Marty Roads media acquisition. Standard library + yt-dlp + FFmpeg."""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

def run(cmd, timeout=1800):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError(p.stderr[-2500:] or p.stdout[-2500:])
    return p.stdout

def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''): h.update(b)
    return h.hexdigest()

def write(p,j):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(j,indent=2,ensure_ascii=False));t.replace(p)

def ident(s):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',s):raise ValueError('Unsafe project/scene/source id')
    return s

def probe(p,decode=True):
    p=Path(p)
    with p.open('rb') as f: head=f.read(512).lower()
    if b'<html' in head or b'<!doctype html' in head:raise ValueError('HTML_INSTEAD_OF_MEDIA: download is a blocked/error page')
    j=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
    v=next((s for s in j['streams'] if s['codec_type']=='video'),None)
    if not v or v.get('width',0)<1 or float(j['format'].get('duration',0))<=0:raise ValueError('Invalid video stream/duration')
    if decode:run(['ffmpeg','-v','error','-xerror','-i',str(p),'-map','0:v:0','-map','0:a?','-f','null','-'])
    return {'width':v['width'],'height':v['height'],'fps':v.get('avg_frame_rate'),'duration':float(j['format']['duration']),'bytes':p.stat().st_size,'sha256':digest(p),'decoded':decode}

def ytdlp(extra):
    # Trust the OS certificate store; never disable certificate verification.
    return [sys.executable,str(Path(__file__).with_name('yt_runner.py')),'--ignore-config','--no-playlist','--socket-timeout','15','--retries','1','--extractor-retries','1','--js-runtimes','node',*extra]

def metadata(url):return json.loads(run(ytdlp(['--skip-download','--dump-single-json',url]),180))

def discover(query,out):
    j=json.loads(run(ytdlp(['--flat-playlist','--dump-single-json','ytsearch5:'+query]),180))
    # Discovery never implies authorization or geographic/historical match.
    rows=[{k:e.get(k) for k in ['id','title','url','channel','duration']} for e in j.get('entries',[])]
    write(out,{'query':query,'candidates':rows,'status':'CANDIDATES_REQUIRE_SELECTION_AND_AUTHORIZATION'});return rows

def acquire(source,root,cap):
    if source.get('authorized') is not True:raise ValueError('Source is not marked authorized')
    sid=ident(source['id']);folder=root/'sources'/sid;folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/'receipt.json'
    if receipt.exists():
        r=json.loads(receipt.read_text());p=folder/r['file']
        if p.exists() and digest(p)==r['probe']['sha256']:return p,r
    if source.get('local_file'):
        src=Path(source['local_file']).resolve();probe(src);p=folder/('source'+src.suffix)
        if src!=p.resolve():shutil.copy2(src,p)
        info={'id':sid,'title':source.get('title','Manual import'),'duration':probe(p,False)['duration']}
    else:
        info=metadata(source['url'])
        formats=info.get('formats',[])
        usable=[f for f in formats if f.get('height') and f.get('vcodec')!='none' and (not cap or f['height']<=cap)]
        if not usable and info.get('extractor_key')=='Youtube':raise ValueError('No usable video formats')
        maxheight=max((f['height'] for f in usable),default=None)
        # Do not silently turn a failed 1080p source into 360p.
        fmt=f'bv*[height={maxheight}]+ba/b[height={maxheight}]' if maxheight else 'bv*+ba/b'
        est=max([f.get('filesize') or f.get('filesize_approx') or 0 for f in usable]+[0])
        if shutil.disk_usage(root).free<max(256*1024**2,est*3):raise RuntimeError('INSUFFICIENT_DISK_SPACE')
        public={k:info.get(k) for k in ['id','title','channel','webpage_url','duration','upload_date']}
        public['formats']=[{k:f.get(k) for k in ['format_id','width','height','fps','vcodec','acodec','filesize']} for f in formats]
        write(folder/'metadata.json',public) # no signed CDN URLs/cookies
        try:
            run(ytdlp(['-f',fmt,'-S','res,fps,br','--merge-output-format','mkv','--keep-video','-o',str(folder/'source.%(ext)s'),source['url']]))
        except Exception:
            for f in folder.glob('source.*'):
                if f.is_file():
                    with f.open('rb') as fh:head=fh.read(512).lower()
                    if b'<html' in head:raise RuntimeError('HTML_INSTEAD_OF_MEDIA: CDN unavailable; request manual MP4 or run same manifest in Codex')
            raise
        candidates=[f for f in folder.glob('source.*') if f.suffix in ['.mkv','.mp4','.webm'] and '.f' not in f.name]
        if not candidates:raise RuntimeError('No merged media produced')
        p=max(candidates,key=lambda f:f.stat().st_mtime)
    verified=probe(p)
    if info.get('duration') and abs(verified['duration']-info['duration'])>max(2,info['duration']*.01):raise ValueError('Truncated source duration')
    r={'id':sid,'url':source.get('url'),'file':p.name,'probe':verified,'authorized':True,'provenance':{k:source.get(k) for k in ['credit','epoch','location','authorization_note']}}
    write(receipt,r);return p,r

def build(manifest,cache):
    m=json.loads(Path(manifest).read_text());root=Path(cache).resolve()/ident(m['project']);root.mkdir(parents=True,exist_ok=True)
    # Exclusive project lock prevents concurrent writers. A stale lock is inspected manually.
    lock=root/'RUNNING.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        sources={};rows=[]
        for s in m['sources']:sources[s['id']]=acquire(s,root,m.get('max_height'))
        for s in m['scenes']:
            scene=ident(s['id']);src,rec=sources[s['source']];start=float(s['start']);duration=float(s['duration'])
            if start<0 or duration<=0 or start+duration>rec['probe']['duration']+.05:raise ValueError('Scene interval outside source')
            d=root/'scenes'/scene;d.mkdir(parents=True,exist_ok=True);out=d/'clip.mp4'
            key=hashlib.sha256(json.dumps([s,rec['probe']['sha256'],m.get('output',{})],sort_keys=True).encode()).hexdigest()
            saved=d/'receipt.json'
            if saved.exists() and out.exists():
                old=json.loads(saved.read_text())
                if old.get('key')==key and digest(out)==old['probe']['sha256']:rows.append(old);continue
            target=m.get('output',{});h=min(int(target.get('height',1080)),rec['probe']['height']);fps=int(target.get('fps',30))
            tmp=d/'clip.pending.mp4'
            cmd=['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(src),'-t',str(duration),'-map','0:v:0','-vf',f'scale=-2:{h}:flags=lanczos,fps={fps},setsar=1','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2']
            cmd+=['-map','0:a?','-c:a','aac'] if s.get('use_source_audio',False) else ['-an']
            run(cmd+['-movflags','+faststart',str(tmp)]);v=probe(tmp)
            if abs(v['duration']-duration)>max(.15,2/fps):raise ValueError('Clip duration mismatch')
            tmp.replace(out)
            row={'id':scene,'source':s['source'],'source_start':start,'duration':duration,'kind':'video','asset':f'INGEST_{scene}','file':str(out),'probe':v,'key':key}
            write(saved,row);rows.append(row)
        result={'project':m['project'],'manifest_sha256':digest(manifest),'scenes':rows,'status':'READY','source_receipts':[r for _,r in sources.values()]}
        write(root/'EDIT_MEDIA.json',result);return result
    except Exception as e:
        write(root/'STATUS.json',{'status':'BLOCKED','error':str(e),'time':time.time()});raise
    finally:lock.unlink(missing_ok=True)

def publish(index,project):
    j=json.loads(Path(index).read_text());dest=Path(project)/'assets/clips';dest.mkdir(parents=True,exist_ok=True)
    patch=[]
    for s in j['scenes']:
        src=Path(s['file']);assert digest(src)==s['probe']['sha256']
        out=dest/(s['asset']+'.mp4')
        if out.exists() and digest(out)!=digest(src):raise ValueError('Refusing to overwrite existing different asset')
        if not out.exists():shutil.copy2(src,out)
        patch.append({k:s[k] for k in ['id','kind','asset','duration']})
    write(Path(project)/'INGEST_SHOT_PLAN_PATCH.json',patch) # original SHOT_PLAN never overwritten

def validate_final(index,render,reviewed=False):
    if not reviewed:raise ValueError('Final audiovisual review must be explicitly confirmed')
    j=json.loads(Path(index).read_text())
    for s in j['scenes']:
        if digest(s['file'])!=s['probe']['sha256']:raise ValueError('Scene changed after build')
    v=probe(render);receipt={'render':str(Path(render).resolve()),'probe':v,'index_sha256':digest(index),'reviewed':True}
    write(Path(index).parent/'FINAL_VALIDATED.json',receipt)

def cleanup(index,execute=False):
    index=Path(index).resolve();root=index.parent;r=json.loads((root/'FINAL_VALIDATED.json').read_text())
    if r['index_sha256']!=digest(index) or digest(r['render'])!=r['probe']['sha256'] or not r['reviewed']:raise ValueError('Stale final validation')
    # Delete only this module\'s source/scene caches; never editor copies/final renders.
    folders=[root/'sources',root/'scenes']
    if any(Path(r['render']).resolve().is_relative_to(p) for p in folders):raise ValueError('Final render lies inside cache')
    for p in folders:
        if p.is_symlink():raise ValueError('Refusing linked cache')
    if execute:
        for p in folders:
            if p.exists():shutil.rmtree(p)
        write(root/'CLEANUP.json',{'deleted':[str(p) for p in folders],'final_sha256':r['probe']['sha256']})
    return [str(p) for p in folders]

def main():
    a=argparse.ArgumentParser();sp=a.add_subparsers(dest='cmd',required=True)
    d=sp.add_parser('discover');d.add_argument('query');d.add_argument('out')
    b=sp.add_parser('build');b.add_argument('manifest');b.add_argument('--cache',default='media_cache')
    p=sp.add_parser('publish');p.add_argument('index');p.add_argument('project')
    v=sp.add_parser('validate-final');v.add_argument('index');v.add_argument('render');v.add_argument('--reviewed',action='store_true')
    c=sp.add_parser('cleanup');c.add_argument('index');c.add_argument('--execute',action='store_true')
    args=a.parse_args()
    if args.cmd=='discover':result=discover(args.query,args.out)
    elif args.cmd=='build':result=build(args.manifest,args.cache)
    elif args.cmd=='publish':result=publish(args.index,args.project)
    elif args.cmd=='validate-final':result=validate_final(args.index,args.render,args.reviewed)
    else:result=cleanup(args.index,args.execute)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
