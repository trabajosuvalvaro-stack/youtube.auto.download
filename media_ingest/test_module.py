import unittest,tempfile,subprocess,json,threading,http.server,functools
from pathlib import Path
import ingest
class TestPipeline(unittest.TestCase):
 def test_download_prepare_render_and_guarded_cleanup(self):
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);src=r/'fixture.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','3','-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-c:a','aac',str(src)],check=True)
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=tmp));threading.Thread(target=server.serve_forever,daemon=True).start()
   try:
    m={'project':'TEST_LOCAL_HTTP','sources':[{'id':'own','url':f'http://127.0.0.1:{server.server_port}/fixture.mp4','authorized':True}],'scenes':[{'id':'S001','source':'own','start':.5,'duration':1,'use_source_audio':False}]}
    manifest=r/'request.json';ingest.write(manifest,m);out=ingest.build(manifest,r/'cache');index=r/'cache/TEST_LOCAL_HTTP/EDIT_MEDIA.json'
    self.assertEqual(out['scenes'][0]['probe']['height'],180)
    self.assertTrue(out['scenes'][0]['probe']['decoded'])
    self.assertEqual(out,ingest.build(manifest,r/'cache'))
    with self.assertRaises(FileNotFoundError):ingest.cleanup(index,True)
    ingest.publish(index,r/'editor');final=r/'final.mp4'
    subprocess.run(['ffmpeg','-v','error','-i',out['scenes'][0]['file'],'-c','copy',str(final)],check=True)
    with self.assertRaises(ValueError):ingest.validate_final(index,final,False)
    ingest.validate_final(index,final,True);ingest.cleanup(index,False)
    self.assertTrue((index.parent/'sources').exists())
    ingest.cleanup(index,True);self.assertFalse((index.parent/'sources').exists());self.assertTrue(final.exists());self.assertTrue((r/'editor/assets/clips/INGEST_S001.mp4').exists())
   finally:server.shutdown();server.server_close()
 def test_bad_media_and_paths(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.mp4';p.write_text('<html>Site Unavailable</html>')
   with self.assertRaisesRegex(ValueError,'HTML_INSTEAD'):ingest.probe(p)
   with self.assertRaises(ValueError):ingest.ident('../escape')
   with self.assertRaises(ValueError):ingest.acquire({'id':'x','authorized':False},Path(d),None)
if __name__=='__main__':unittest.main(verbosity=2)
