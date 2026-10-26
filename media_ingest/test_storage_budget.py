import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple
from storage_budget import transact
Disk=namedtuple('Disk','total used free')
class BudgetTests(unittest.TestCase):
 def test_reservations_and_no_destructive_action(self):
  with tempfile.TemporaryDirectory() as d,patch('storage_budget.shutil.disk_usage',return_value=Disk(100,10,90)):
   r=Path(d)/'registry.json';a=Path(d)/'A';b=Path(d)/'B';a.mkdir();b.mkdir();(a/'source').write_bytes(b'1234567890')
   self.assertTrue(transact(r,'A',a,40,floor=10)['admitted'])
   self.assertTrue(transact(r,'B',b,40,floor=10)['admitted'])
   before=r.read_bytes()
   with self.assertRaises(RuntimeError):transact(r,'B',b,60,floor=10)
   self.assertEqual(before,r.read_bytes());self.assertEqual((a/'source').read_bytes(),b'1234567890')
   with self.assertRaises(ValueError):transact(r,'NESTED',a,1,floor=10)
   transact(r,'A',release=True,floor=10);self.assertTrue((a/'source').exists())
 def test_existing_files_consume_peak(self):
  with tempfile.TemporaryDirectory() as d,patch('storage_budget.shutil.disk_usage',return_value=Disk(100,10,90)):
   r=Path(d)/'r.json';a=Path(d)/'A';a.mkdir();(a/'x').write_bytes(b'0'*10)
   row=transact(r,'A',a,40,floor=10)['projects'][0]
   self.assertEqual(row['remaining_reserved_bytes'],30)
if __name__=='__main__':unittest.main()
