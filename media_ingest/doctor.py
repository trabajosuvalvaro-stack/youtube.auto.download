import json,sys,shutil,subprocess,platform
from pathlib import Path
import ingest
out={'python':platform.python_version(),'disk_free_bytes':shutil.disk_usage('.').free,'tools':{}}
for name in ['ffmpeg','ffprobe','node']:
 try:out['tools'][name]=ingest.run([name,'-version' if name!='node' else '--version']).splitlines()[0]
 except Exception as e:out['tools'][name]=str(e)
try:out['yt_dlp']=ingest.run(ingest.ytdlp(['--version'])).strip()
except Exception as e:out['yt_dlp_error']=str(e)
if len(sys.argv)>1:
 try:
  j=ingest.metadata(sys.argv[1]);out['metadata']={k:j.get(k) for k in ['id','title','duration']};out['max_advertised_height']=max((f.get('height') or 0 for f in j.get('formats',[])),default=0)
  out['warning']='Metadata access does not prove CDN/download access. Run build and require decode success.'
 except Exception as e:out['metadata_error']=str(e)
ingest.write('DOCTOR.json',out);print(json.dumps(out,indent=2))
