"""placement_score.py and route_eval's hand-finish-or-re-place diagnosis, on synthetic boards."""
import json, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import placement_score  # noqa: E402
import route_eval  # noqa: E402


def board(parts, w=60, h=40):
    """A 2-layer board: parts = [(ref, x, y, [(pad, dx, dy, net)])]."""
    nets = sorted({n for _, _, _, pads in parts for *_, n in pads if n})
    out = [f'(kicad_pcb (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user))', '(net 0 "")']
    out += [f'(net {i + 1} "{n}")' for i, n in enumerate(nets)]
    out.append(f'(gr_rect (start 0 0) (end {w} {h}) (layer "Edge.Cuts"))')
    for ref, x, y, pads in parts:
        body = ''.join(f'(pad "{p}" smd rect (at {dx} {dy}) (size 0.25 0.8) (layers "F.Cu") (net {nets.index(n) + 1} "{n}"))' for p, dx, dy, n in pads)
        out.append(f'(footprint "X" (layer "F.Cu") (at {x} {y}) (property "Reference" "{ref}") {body})')
    return '\n'.join(out) + ')'


def qfn(ref, x, y, nets):
    """A 0.4 mm pitch part with 8 pins on its top and bottom edges (16 pins)."""
    pads = []
    for k in range(8):
        pads.append((str(k + 1), -1.4 + 0.4 * k, -2, nets[k % len(nets)]))
        pads.append((str(k + 9), -1.4 + 0.4 * k, 2, nets[(k + 3) % len(nets)]))
    return (ref, x, y, pads)


class PlacementScore(unittest.TestCase):
    def score(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            b = Path(tmp) / 'b.kicad_pcb'
            b.write_text(text)
            return placement_score.score(str(b))

    def test_dense_cluster_is_the_hotspot_and_escape_pitch_is_along_rows(self):
        nets = [f'N{i}' for i in range(8)]
        parts = [qfn('U1', 15, 15, nets)]
        # Partners for every net: packed close to U1 on one side, a lone pair far away.
        parts += [(f'R{i}', 22 + (i % 4) * 1.2, 12 + (i // 4) * 6, [('1', 0, 0, n), ('2', 0.8, 0, n)]) for i, n in enumerate(nets)]
        parts += [('R99', 50, 30, [('1', 0, 0, 'FAR'), ('2', 5, 0, 'FAR')]), ('R98', 52, 35, [('1', 0, 0, 'FAR')])]
        s = self.score(board(parts))
        self.assertTrue(s['hotspots'])
        self.assertIn('U1', s['hotspots'][0]['parts'])
        self.assertEqual(s['escape'][0]['ref'], 'U1')
        self.assertAlmostEqual(s['escape'][0]['pitch'], 0.4, places=2)
        self.assertGreater(s['ratsnest']['crossings'], 0)

    def test_spreading_parts_lowers_peak_congestion_and_costs_wire(self):
        nets = [f'N{i}' for i in range(8)]
        tight = [qfn('U1', 15, 15, nets)] + [(f'R{i}', 18 + i * 0.6, 15, [('1', 0, 0, n)]) for i, n in enumerate(nets)]
        loose = [qfn('U1', 15, 15, nets)] + [(f'R{i}', 15 + i * 5, 32, [('1', 0, 0, n)]) for i, n in enumerate(nets)]
        t, l = self.score(board(tight)), self.score(board(loose))
        # The trade the score exposes: spreading lowers peak congestion and costs wire length.
        self.assertGreater(t['congestion']['max'], l['congestion']['max'])
        self.assertGreater(l['ratsnest']['mst_mm'], 2 * t['ratsnest']['mst_mm'])


class Diagnosis(unittest.TestCase):
    def run_dir(self, tmp, defects_by_backend, scores):
        nets = [f'N{i}' for i in range(8)]
        parts = [qfn('U1', 15, 15, nets)] + [(f'R{i}', 22 + (i % 4) * 1.2, 12 + (i // 4) * 6, [('1', 0, 0, n), ('2', 0.8, 0, n)]) for i, n in enumerate(nets)]
        b = Path(tmp) / 'b.kicad_pcb'
        b.write_text(board(parts))
        results = []
        for name, pts in defects_by_backend.items():
            viol = [{'type': 'clearance', 'items': [{'pos': {'x': x, 'y': y}}]} for x, y in pts]
            (Path(tmp) / f'{name}.drc.json').write_text(json.dumps({'violations': viol, 'unconnected_items': []}))
            results.append({'backend': name, 'ok': True, 'score': scores[name]})
        return b, results

    @staticmethod
    def sc(clearance, **kw):
        base = dict(shorts=0, unconnected=0, dfm_actionable=0, floating=0, size_violations=0, clearance=clearance, vias=10, track_mm=100.0)
        return {**base, **kw}

    def test_few_scattered_defects_say_hand_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, res = self.run_dir(tmp, {'a': [(50, 5)], 'b': [(5, 35), (55, 35)]}, {'a': self.sc(1), 'b': self.sc(2)})
            d = route_eval.diagnose(tmp, res, b)
            self.assertTrue(d['recommendation'].startswith('hand-finish a'), d['recommendation'])

    def test_many_defects_where_routers_agree_in_a_hotspot_say_re_place(self):
        hot = [(15 + dx, 15 + dy) for dx in (-1, 0, 1) for dy in (-2, 2)] * 3
        with tempfile.TemporaryDirectory() as tmp:
            b, res = self.run_dir(tmp, {'a': hot, 'b': hot, 'c': hot}, {'a': self.sc(18), 'b': self.sc(18), 'c': self.sc(18)})
            d = route_eval.diagnose(tmp, res, b)
            self.assertTrue(d['recommendation'].startswith('re-place'), d['recommendation'])
            self.assertIn('U1', d['recommendation'])

    def test_clean_best_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            b, res = self.run_dir(tmp, {'a': []}, {'a': self.sc(0)})
            self.assertTrue(route_eval.diagnose(tmp, res, b)['recommendation'].startswith('order-ready'))


if __name__ == '__main__':
    unittest.main()
