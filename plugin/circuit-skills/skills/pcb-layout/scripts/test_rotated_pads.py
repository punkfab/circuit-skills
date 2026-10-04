import subprocess, sys, tempfile, unittest
from pathlib import Path
scripts=Path(__file__).parent
class RotatedPads(unittest.TestCase):
    def test_rotated_drill_and_floating_pad(self):
        with tempfile.TemporaryDirectory() as tmp:
            board=Path(tmp)/'b.kicad_pcb'
            # KiCad +90 degrees maps local (5,0) to global (10,5), in screen coordinates.
            board.write_text('''(kicad_pcb (net 0 "") (net 1 "SIG")
              (footprint "X" (at 10 10 90) (property "Reference" "J1")
                (pad "1" thru_hole circle (at 5 0) (size 2 2) (drill 1) (layers "*.Cu") (net 1 "SIG")))
              (footprint "R" (at 10 10 90) (property "Reference" "R1")
                (pad "1" smd rect (at 5 0) (size 1 1) (layers "F.Cu") (net 1 "SIG")))
              (via (at 10.2 5) (size .6) (drill .3) (layers "F.Cu" "B.Cu") (net 0))
              (segment (start 10 5) (end 12 5) (width .2) (layer "B.Cu") (net 1)))''')
            result=subprocess.run([sys.executable,str(scripts/'dfm_check.py'),str(board)],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stdout); self.assertIn('J1@(10.00,5.00)',result.stdout)
            result=subprocess.run([sys.executable,str(scripts/'check_floating.py'),str(board)],capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stdout);self.assertIn('R1.1',result.stdout)
    def test_rotated_npth_keepout(self):
        with tempfile.TemporaryDirectory() as tmp:
            board=Path(tmp)/'b.kicad_pcb';dsn=Path(tmp)/'b.dsn'
            board.write_text('''(kicad_pcb (footprint "H" (at 10 10 90)
              (pad "" np_thru_hole circle (at 5 0) (size 1 1) (drill 1) (layers "*.Cu")))
              (gr_line (start 0 0) (end 20 0) (layer "Edge.Cuts"))
              (gr_line (start 20 0) (end 20 20) (layer "Edge.Cuts")))''')
            dsn.write_text('(pcb "test" (structure (layer F.Cu (type signal)) (boundary (path pcb 0 0 0 20000 0 20000 -20000 0 -20000 0 0))) (placement))')
            result=subprocess.run([sys.executable,str(scripts/'add_npth_keepouts.py'),str(board),str(dsn)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('9200',dsn.read_text());self.assertIn('-5800',dsn.read_text())
if __name__=='__main__':unittest.main()
