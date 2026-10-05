"""route_kicad_dsn.py's text-level helpers (no KiCad needed)."""
import re, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import route_kicad_dsn  # noqa: E402


class GrowKeepouts(unittest.TestCase):
    def test_cutout_keepouts_grow_evenly_and_planes_are_left_alone(self):
        dsn = ('(structure\n (plane GND (polygon B.Cu 0  0 0  5000 0  5000 5000  0 5000\n  0 0))\n'
               ' (keepout "" (polygon signal 0  0 0  1000 0  1000 1000  0 1000\n  0 0)))')
        out = route_kicad_dsn.grow_keepouts(dsn, 100)
        self.assertIn('(plane GND (polygon B.Cu 0  0 0  5000 0', out)
        nums = [float(v) for v in re.search(r'polygon signal 0\s+([-\d.\s]+)\)', out).group(1).split()]
        xs, ys = nums[0::2], nums[1::2]
        # A square grows by the margin along each diagonal: every side moves out by margin / sqrt(2).
        self.assertAlmostEqual(min(xs), -70.7, places=1)
        self.assertAlmostEqual(max(xs), 1070.7, places=1)
        self.assertAlmostEqual(min(ys), -70.7, places=1)
        self.assertAlmostEqual(max(ys), 1070.7, places=1)
        self.assertEqual((xs[0], ys[0]), (xs[-1], ys[-1]))  # still closed


if __name__ == '__main__':
    unittest.main()
