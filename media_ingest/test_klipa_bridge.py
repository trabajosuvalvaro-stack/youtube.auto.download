import io, json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import klipa_bridge as k
class Response(io.BytesIO):
    headers={'Content-Type':'application/json'}
    url='https://cdn.example.test/output.mp4'
    def __enter__(self):return self
    def __exit__(self,*a):self.close()
class Tests(unittest.TestCase):
    def test_no_secret(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'AUTH_REQUIRED'):k.Client()
    def test_protocol(self):
        responses=[{'result':{'protocolVersion':'2025-03-26'}},{}, {'result':{'tools':[{'name':'list_jobs'}]}}]
        seen=[]
        def request(req,**kw):
            seen.append(json.loads(req.data));return Response(json.dumps(responses.pop(0)).encode())
        with patch.dict(os.environ,{'KLIPA_TOKEN':'test-only'}),patch('urllib.request.urlopen',side_effect=request):
            c=k.Client();self.assertEqual(c.catalog()[0]['name'],'list_jobs')
        self.assertEqual([r['method'] for r in seen],['initialize','notifications/initialized','tools/list'])
    def test_transfer_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/'source.mp4'
            with patch('urllib.request.urlopen',return_value=Response(b'fixture')),patch.object(k,'probe',return_value={'decoded':True}):
                r=k.receive('https://cdn.example.test/result?secret=temporary',dst)
            self.assertTrue(dst.exists());self.assertEqual(r['probe']['decoded'],True)
            self.assertNotIn('temporary',dst.with_suffix('.mp4.receipt.json').read_text())
            with self.assertRaisesRegex(ValueError,'DESTINATION_EXISTS'):k.receive('https://cdn.example.test/result',dst)
            with self.assertRaisesRegex(ValueError,'HTTPS'):k.receive('http://example.test/result',Path(d)/'x.mp4')
if __name__=='__main__':unittest.main()
