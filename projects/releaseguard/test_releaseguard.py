import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from releaseguard import evaluate, timestamp

BASE = json.loads((Path(__file__).parent/'samples/healthy.json').read_text())
NOW = timestamp('2026-09-30T10:00:00Z')
class GateTests(unittest.TestCase):
    def run_gate(self, evidence):
        return evaluate(evidence, BASE['release_id'], 'staging', NOW)
    def test_healthy(self):
        self.assertEqual(self.run_gate(BASE)['decision'], 'pass')
    def test_samples_hold(self):
        for name in ('high-errors','stale','failed-restore'):
            with self.subTest(name=name):
                self.assertEqual(self.run_gate(json.loads((Path(__file__).parent/f'samples/{name}.json').read_text()))['decision'],'hold')
    def test_missing_all_top_level_fields(self):
        for key in BASE:
            e=copy.deepcopy(BASE);del e[key]
            with self.subTest(key=key):self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_bad_numbers(self):
        for key in BASE['service']:
            for value in (True,-1,float('nan'),float('inf'),'5',None,1.5):
                e=copy.deepcopy(BASE);e['service'][key]=value
                with self.subTest(key=key,value=value):self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_no_traffic(self):
        e=copy.deepcopy(BASE);e['service'].update(total_requests=0,error_requests=0)
        self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_inconsistent_counts(self):
        e=copy.deepcopy(BASE);e['service']['error_requests']=5001
        self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_partial_capacity(self):
        e=copy.deepcopy(BASE);e['service']['ready_replicas']=2
        self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_bad_timestamps(self):
        for value in ('not-date','2026-09-30T09:59:00','2026-09-30T10:01:00Z',None):
            e=copy.deepcopy(BASE);e['observed_at']=value
            self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_bindings(self):
        for key in ('release_id','environment'):
            e=copy.deepcopy(BASE);e[key]='other'
            self.assertEqual(self.run_gate(e)['decision'],'hold')
    def test_restore_invalid(self):
        for key,value in [('completed_at','2026-09-28T10:00:00Z'),('duration_seconds',901),('checksum_verified','true'),('artifact_sha256','bad'),('environment','prod'),('backup_id','')]:
            e=copy.deepcopy(BASE);e['restore'][key]=value
            self.assertEqual(self.run_gate(e)['decision'],'hold')
    def cli(self, content, *extra):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.json';p.write_text(content)
            r=subprocess.run([sys.executable,str(Path(__file__).parent/'releaseguard.py'),str(p),'--release-id',BASE['release_id'],'--environment','staging',*extra],capture_output=True,text=True)
            return r.returncode,json.loads(r.stdout)
    def test_live_cli_pass(self):
        from datetime import datetime, timezone
        e=copy.deepcopy(BASE);e['observed_at']=e['restore']['completed_at']=datetime.now(timezone.utc).isoformat()
        code,result=self.cli(json.dumps(e));self.assertEqual(code,0);self.assertTrue(result['release_authorized'])
    def test_replay_cannot_authorize(self):
        code,result=self.cli(json.dumps(BASE),'--replay-at',NOW.isoformat())
        self.assertEqual(code,1);self.assertEqual(result['decision'],'pass');self.assertFalse(result['release_authorized'])
    def test_malformed_cli(self):
        for value in ('{','{"x":NaN}','{"x":1,"x":2}'):
            code,result=self.cli(value);self.assertEqual(code,2);self.assertEqual(result['decision'],'hold')
    def test_live_hold(self):
        code,result=self.cli('{}');self.assertEqual(code,1);self.assertFalse(result['release_authorized'])
if __name__=='__main__':unittest.main()
