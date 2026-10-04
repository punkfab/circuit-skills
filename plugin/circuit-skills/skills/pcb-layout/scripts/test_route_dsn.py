import importlib.util, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
script=Path(__file__).with_name('route_dsn.py')
spec=importlib.util.spec_from_file_location('router',script); router=importlib.util.module_from_spec(spec); spec.loader.exec_module(router)
class RouterTest(unittest.TestCase):
    def test_backend_flags(self):
        fast=router.command('fastroute','bin','a.dsn','b.ses',4,20,'report')
        free=router.command('freerouting','bin','a.dsn','b.ses',4,20,'report')
        self.assertIn('--max-time=20',fast);self.assertNotIn('-oit',fast)
        self.assertIn('-oit',free);self.assertFalse(any(x.startswith('--report') for x in free))
    def test_candidate_and_failure_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dsn=root/'b.dsn';dsn.write_text('(pcb)');board=root/'b.kicad_pcb';board.write_text('(kicad_pcb)')
            exe=root/'fake';exe.write_text('#!/usr/bin/env python3\nimport pathlib,sys\np=pathlib.Path(sys.argv[sys.argv.index("-do")+1]);p.write_text("(session)")\n');exe.chmod(0o755)
            out=root/'b.ses'
            args=[sys.executable,str(script),str(dsn),'-o',str(out),'--executable',str(exe),'--backend','fastroute','--board',str(board),'--max-time','2']
            self.assertEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(json.loads(Path(str(board)+'.routing.json').read_text())['state'],'candidate')
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0) # no stale candidate reuse
            out.unlink();exe.write_text('#!/bin/sh\nexit 1\n')
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(json.loads(Path(str(board)+'.routing.json').read_text())['state'],'failed')
if __name__=='__main__':unittest.main()
