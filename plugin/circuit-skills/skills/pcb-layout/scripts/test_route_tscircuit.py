"""route_tscircuit.mjs with a stand-in tsci: the preset reaches the <board>, the design is never
edited, the temporary entry is removed, live status is written, and a board without tracks fails."""
import json, os, stat, subprocess, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / 'route_tscircuit.mjs'

FAKE_TSCI = '''#!/bin/sh
# tsci export -f kicad_pcb <entry> -o <relative out>: record the entry, write a board.
entry="$4"; out="$6"
cp "$entry" "$PWD/seen-entry.tsx"
mkdir -p "$(dirname "$out")"
if [ "${FAKE_NO_TRACKS:-}" = 1 ]; then echo '(kicad_pcb)' > "$out"
else printf '(kicad_pcb\\n (segment (start 0 0) (end 1 0) (width 0.2) (layer "F.Cu") (net 1))\\n (via (at 1 0) (size 0.6) (drill 0.3)))\\n' > "$out"; fi
echo "Exported to $out!"
'''

DESIGN = '''import { JLCPCB } from "./lib/fab"
export default () => (
  <board width="10mm" height="10mm" {...JLCPCB} autorouter="sequential-trace"
    autorouterEffortLevel="1x">
    <resistor name="R1" resistance="1k" footprint="0402" />
  </board>
)
'''


class RouteTscircuit(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.entry = self.dir / 'index.circuit.tsx'
        self.entry.write_text(DESIGN)
        self.tsci = self.dir / 'tsci'
        self.tsci.write_text(FAKE_TSCI)
        self.tsci.chmod(self.tsci.stat().st_mode | stat.S_IEXEC)

    def run_route(self, *extra, env=None):
        return subprocess.run(['node', str(SCRIPT), str(self.entry), '--tsci', str(self.tsci), *extra],
                              capture_output=True, text=True, env={**os.environ, **(env or {})})

    def test_routes_with_the_preset_and_leaves_the_design_alone(self):
        board = self.dir / 'live.kicad_pcb'
        r = self.run_route('-o', str(self.dir / 'build' / 'cand.kicad_pcb'), '--preset', 'auto_local', '--effort', '2x', '--board', str(board))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        seen = (self.dir / 'seen-entry.tsx').read_text()
        self.assertIn('<board autorouter="auto_local" autorouterEffortLevel="2x" width="10mm"', seen)
        self.assertNotIn('sequential-trace', seen)
        self.assertNotIn('"1x"', seen)
        self.assertEqual(self.entry.read_text(), DESIGN)
        self.assertEqual([p.name for p in self.dir.glob('.route-tscircuit-*')], [])
        status = json.loads((self.dir / 'live.kicad_pcb.routing.json').read_text())
        self.assertEqual((status['backend'], status['state']), ('tscircuit:auto_local', 'candidate'))
        self.assertIn('1 track segments, 1 vias', status['message'])

    def test_a_board_without_tracks_is_a_failure(self):
        r = self.run_route('-o', str(self.dir / 'cand.kicad_pcb'), env={'FAKE_NO_TRACKS': '1'})
        self.assertEqual(r.returncode, 1)
        self.assertIn('did not route', r.stdout)

    def test_refuses_to_overwrite_and_bad_presets(self):
        (self.dir / 'cand.kicad_pcb').write_text('x')
        self.assertEqual(self.run_route('-o', str(self.dir / 'cand.kicad_pcb')).returncode, 2)
        self.assertEqual(self.run_route('-o', str(self.dir / 'new.kicad_pcb'), '--preset', 'auto"; rm').returncode, 2)


if __name__ == '__main__':
    unittest.main()
