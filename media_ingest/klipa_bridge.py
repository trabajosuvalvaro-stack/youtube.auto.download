#!/usr/bin/env python3
"""Klipa MCP adapter. No credentials, signed URLs or media are persisted to Drive."""
import argparse, json, os, shutil, ssl, sys, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlsplit
from ingest import probe, write

ENDPOINT='https://mcp.klipa.ai/mcp'
class Client:
    def __init__(self):
        self.token=os.environ.get('KLIPA_TOKEN')
        if not self.token: raise RuntimeError('AUTH_REQUIRED: configure KLIPA_TOKEN in the executing environment secret store')
        self.session=None;self.seq=0;self.protocol='2025-03-26'
        result=self.rpc('initialize',{'protocolVersion':self.protocol,'capabilities':{},'clientInfo':{'name':'marty-roads-media-ingest','version':'1.0'}})
        self.protocol=result.get('protocolVersion',self.protocol)
        self.rpc('notifications/initialized',{},notification=True)
    def rpc(self,method,params,notification=False):
        self.seq+=1
        body={'jsonrpc':'2.0','method':method,'params':params}
        if not notification: body['id']=self.seq
        headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':self.protocol}
        if self.session:headers['Mcp-Session-Id']=self.session
        req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=90,context=ssl.create_default_context()) as r:
                self.session=r.headers.get('Mcp-Session-Id',self.session)
                if notification:return {}
                if 'text/event-stream' in r.headers.get('Content-Type',''):
                    data=[]
                    for raw in r:
                        line=raw.decode().rstrip('\r\n')
                        if line.startswith('data:'):data.append(line[5:].lstrip())
                        elif not line and data:
                            msg=json.loads('\n'.join(data));data=[]
                            if msg.get('id')==body['id']:break
                    else:raise RuntimeError('MCP_NO_MATCHING_RESPONSE')
                else:msg=json.load(r)
        except urllib.error.HTTPError as e:raise RuntimeError('KLIPA_HTTP_'+str(e.code)) from None
        if 'error' in msg:raise RuntimeError('KLIPA_RPC_ERROR_'+str(msg['error'].get('code')))
        return msg.get('result',{})
    def catalog(self):
        rows=[];params={}
        while True:
            r=self.rpc('tools/list',params);rows.extend(r.get('tools',[]))
            if not r.get('nextCursor'):return rows
            params={'cursor':r['nextCursor']}

def receive(url,destination):
    """Explicit result URL only, no bearer token forwarded to download hosts."""
    u=urlsplit(url)
    if u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('HTTPS_RESULT_URL_REQUIRED')
    dst=Path(destination).resolve()
    if dst.exists():raise ValueError('DESTINATION_EXISTS')
    dst.parent.mkdir(parents=True,exist_ok=True);tmp=dst.with_suffix(dst.suffix+'.pending')
    if tmp.exists():raise ValueError('PENDING_FILE_EXISTS')
    req=urllib.request.Request(url,headers={'User-Agent':'MartyRoads/1.0'})
    with urllib.request.urlopen(req,timeout=60,context=ssl.create_default_context()) as r:
        if urlsplit(r.url).scheme!='https':raise ValueError('INSECURE_REDIRECT')
        if 'text/html' in r.headers.get('Content-Type',''):raise ValueError('HTML_INSTEAD_OF_MEDIA')
        with tmp.open('xb') as f:
            while True:
                block=r.read(1024*1024)
                if not block:break
                if shutil.disk_usage(dst.parent).free < len(block)+64*1024**2:raise RuntimeError('INSUFFICIENT_DISK_SPACE')
                f.write(block)
    info=probe(tmp);tmp.replace(dst)
    write(dst.with_suffix(dst.suffix+'.receipt.json'),{'provider':'klipa','probe':info,'original_quality_verified':False})
    return {'local_file':str(dst),'probe':info}

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('check')
    t=s.add_parser('catalog');t.add_argument('out')
    t=s.add_parser('call');t.add_argument('tool');t.add_argument('arguments');t.add_argument('--execute',action='store_true')
    t=s.add_parser('receive');t.add_argument('url_file');t.add_argument('destination')
    a=p.parse_args()
    if a.cmd=='receive':r=receive(Path(a.url_file).read_text().strip(),a.destination)
    else:
        c=Client();catalog=c.catalog()
        if a.cmd=='check':r={'authenticated':True,'tool_count':len(catalog),'raw_download_verified':False}
        elif a.cmd=='catalog':write(a.out,{'tools':catalog});r={'saved':a.out,'tool_count':len(catalog)}
        else:
            if a.tool not in {t['name'] for t in catalog}:raise ValueError('TOOL_NOT_IN_LIVE_CATALOG')
            args=json.loads(Path(a.arguments).read_text())
            if not a.execute:r={'status':'DRY_RUN','tool':a.tool,'schema':next(t['inputSchema'] for t in catalog if t['name']==a.tool)}
            else:
                r=c.rpc('tools/call',{'name':a.tool,'arguments':args})
                # Result may contain temporary signed links; stdout is for local use only.
    print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as e:
        # Do not print URLs, tokens or arbitrary remote exception payloads.
        print(json.dumps({'status':'BLOCKED','reason':str(e) if isinstance(e,(ValueError,RuntimeError)) else type(e).__name__}),file=sys.stderr);sys.exit(2)
