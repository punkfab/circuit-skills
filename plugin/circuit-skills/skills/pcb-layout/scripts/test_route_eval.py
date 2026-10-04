"""route_eval.py: the ranking order, routing metrics, and a bare-board run that records history."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import route_eval  # noqa: E402

EINHANDER = Path(os.getenv('CIRCUIT_VIEWER_FIXTURE', Path.home() / 'sandbox/audiodestrukt/einhander')) / 'pcb'


def s(**kw):
    base = dict(shorts=0, unconnected=0, dfm_actionable=0, floating=0, size_violations=0, clearance=0, vias=10, track_mm=100.0)
    return {**base, **kw}


class Ranking(unittest.TestCase):
    def test_order_of_what_matters(self):
        ranked = sorted([s(shorts=1), s(unconnected=2), s(dfm_actionable=3), s(clearance=40), s(vias=5), s(), None], key=route_eval.rank_key)
        self.assertEqual(ranked[0], s(vias=5))           # all clean: fewer vias wins
        self.assertEqual(ranked[1], s())
        self.assertEqual(ranked[2], s(clearance=40))     # clearance before DFM, open nets, shorts
        self.assertEqual(ranked[3], s(dfm_actionable=3))
        self.assertEqual(ranked[4], s(unconnected=2))
        self.assertEqual(ranked[5], s(shorts=1))
        self.assertIsNone(ranked[6])                     # a failed backend ranks last

    def test_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'b.kicad_pcb'
            b.write_text('(kicad_pcb (net 0 "") (net 1 "GND") (net 2 "SIG")\n'
                         ' (segment (start 0 0) (end 3 4) (width 0.2) (layer "F.Cu") (net 2) (uuid "a"))\n'
                         ' (segment (start 0 0) (end 0 2) (width 0.2) (layer "F.Cu") (net 1) (uuid "b"))\n'
                         ' (via (at 0 2) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net 1))\n'
                         ' (zone (net 1) (net_name "GND") (layer "In1.Cu")))')
            self.assertEqual(route_eval.metrics(b), {'track_mm': 7.0, 'segments': 2, 'vias': 1, 'plane_net_track_mm': 2.0})


@unittest.skipUnless((EINHANDER / 'index.circuit.kicad_pcb').exists() and shutil.which('kicad-cli'), 'einhander fixture or kicad-cli missing')
class BareBoard(unittest.TestCase):
    def test_current_baseline_is_scored_and_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            for ext in ('kicad_pcb', 'kicad_pro'):
                shutil.copy(EINHANDER / f'index.circuit.{ext}', Path(tmp) / f'board.{ext}')
            r = subprocess.run([sys.executable, str(Path(route_eval.__file__)), str(Path(tmp) / 'board.kicad_pcb'), '--backends', 'current'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            history = [json.loads(l) for l in (Path(tmp) / 'route-evals' / 'history.jsonl').read_text().splitlines()]
            self.assertEqual(len(history), 1)
            h = history[0]
            self.assertEqual((h['backend'], h['rank'], h['best']), ('current', 1, 'current'))
            self.assertEqual(h['score']['vias'], 49)          # the shipped board
            self.assertEqual(h['score']['unconnected'], 0)
            run_dir = Path(tmp) / 'route-evals' / h['run']
            self.assertTrue((run_dir / 'summary.md').exists() and (run_dir / 'results.json').exists())


if __name__ == '__main__':
    unittest.main()
