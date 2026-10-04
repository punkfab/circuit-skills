"""run_d3.py scoring and selection, plus route_kicad_dsn's routing stripper, without routing anything."""
import sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / 'pcb-layout' / 'scripts'))
import run_d3  # noqa: E402
import route_kicad_dsn  # noqa: E402

BOARD = '''(kicad_pcb (version 20241229)
  (net 0 "") (net 1 "A") (net 2 "B")
  (gr_circle (center 10 10) (end 20 10) (layer "Edge.Cuts"))
  (footprint "R" (layer "F.Cu") (at 10 10) (property "Reference" "R1")
    (pad "1" smd rect (at -1 0) (size 0.5 0.6) (layers "F.Cu") (net 1 "A"))
    (pad "2" smd rect (at 1 0) (size 0.5 0.6) (layers "F.Cu") (net 2 "B")))
  (segment (start 1 1) (end 2 2) (width 0.2) (layer "F.Cu") (net 1) (uuid "a"))
  (arc (start 2 2) (mid 3 3) (end 4 2) (width 0.2) (layer "F.Cu") (net 1) (uuid "b"))
  (via (at 2 2) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net 1) (uuid "c"))
  (zone (net 1) (net_name "A") (layer "B.Cu") (name "via (not a via)"))
)'''


class Scoring(unittest.TestCase):
    def test_splits_match_the_paper(self):
        self.assertEqual(len(run_d3.board_ids('d3a')), 99)
        self.assertEqual(len(run_d3.board_ids('d3b')), 10)
        self.assertEqual(len(run_d3.board_ids('d3c')), 10)
        self.assertEqual(run_d3.board_ids('d3a', only=['0018']), ['0018_Hardware_Playground_hy_adapter'])

    def test_clean_pass_needs_connected_and_no_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'b.kicad_pcb'
            b.write_text(BOARD)
            clean = run_d3.pcbworld_row(b, {'violations': [], 'unconnected_items': []}, 4)
            short = run_d3.pcbworld_row(b, {'violations': [{'type': 'clearance'}], 'unconnected_items': []}, 4)
            opened = run_d3.pcbworld_row(b, {'violations': [], 'unconnected_items': [{}]}, 4)
        self.assertEqual((clean['cp'], clean['rout'], clean['vias']), (True, 1.0, 1))
        self.assertEqual((short['cp'], short['drv']), (False, 1))
        self.assertEqual((opened['cp'], opened['rout']), (False, 0.75))

    def test_best_candidate_is_clean_first_then_routability(self):
        rows = [dict(cp=False, rout=1.0, drv=3, vias=0, wl_mm=10), dict(cp=True, rout=1.0, drv=0, vias=9, wl_mm=99),
                dict(cp=False, rout=0.5, drv=0, vias=0, wl_mm=1)]
        self.assertTrue(min(rows, key=run_d3.select_key)['cp'])
        self.assertEqual(min(rows[::2], key=run_d3.select_key)['rout'], 1.0)

    def test_auc_and_failed_backends_count_as_not_clean(self):
        self.assertEqual(run_d3.auc([3, 4], [1, 2]), 1.0)
        self.assertEqual(run_d3.auc([1], [1]), 0.5)
        rows = [{'board': 'x', 'u0': 2, 'methods': {'freerouting': {'failed': True}}},
                {'board': 'y', 'u0': 2, 'methods': {'freerouting': dict(cp=True, rout=1.0, drv=0, open=0, wl_mm=5, vias=0, time_s=1)}}]
        s = run_d3.method_stats(rows, 'freerouting')
        self.assertEqual((s['cp'], s['rout'], s['ran']), (0.5, 0.5, 1))
        self.assertIn('| freerouting | 0.50 |', run_d3.summarize(rows, 'd3a', {'run': 't', 'backends': 'freerouting', 'time': 1, 'versions': {}}))


class Strip(unittest.TestCase):
    def test_strips_top_level_tracks_only(self):
        out = route_kicad_dsn.strip_routing(BOARD)
        self.assertNotIn('(segment', out)
        self.assertNotIn('(arc', out)
        self.assertNotIn('(via (at', out)
        self.assertIn('(zone (net 1)', out)
        self.assertIn('"via (not a via)"', out)
        self.assertIn('(pad "2"', out)
        self.assertEqual(out.count('('), out.count(')'))


class RoundBoard(unittest.TestCase):
    def test_round_outline_is_center_plus_radius(self):
        import placement_score
        self.assertEqual(placement_score.read_board(BOARD)['bbox'], (0.0, 0.0, 20.0, 20.0))


if __name__ == '__main__':
    unittest.main()
