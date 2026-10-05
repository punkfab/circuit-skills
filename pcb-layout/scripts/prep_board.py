#!/usr/bin/env python3
"""prep_board.py — turn a tscircuit KiCad export into a clean, unrouted, pour-ready board, headless.

  /usr/bin/python3 prep_board.py <board.kicad_pcb> [-o out.kicad_pcb] [--pour NET:LAYER ...]
                                 [--fab jlcpcb] [--keep-routing]

The starting point for routing a 2-layer (or any) board with route_eval's bare-board backends, with
no live KiCad and no tscircuit DSN:
  1. strip tscircuit's own routing (text level; see route_kicad_dsn.strip_routing),
  2. add a pour zone per --pour (default GND:B.Cu) over the whole board; KiCad clips it to the outline
     and cutouts when it fills (tscircuit's <copperpour> does not export),
  3. write the board, create its .kicad_pro, apply the fab's rules (apply_fab_rules.py), fill zones.

Run merge_nets.py first on a modular (subcircuit) design. Needs the pcbnew module.
"""
import argparse, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from route_kicad_dsn import strip_routing  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('board', type=Path)
    p.add_argument('-o', '--output', type=Path)
    p.add_argument('--pour', action='append', help='NET:LAYER, repeatable (default GND:B.Cu); "none" for no pour')
    p.add_argument('--fab', default='jlcpcb')
    p.add_argument('--keep-routing', action='store_true')
    a = p.parse_args()
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    import pcbnew
    src = a.board.resolve()
    out = (a.output or a.board).resolve()
    text = src.read_text()
    out.write_text(text if a.keep_routing else strip_routing(text))
    board = pcbnew.LoadBoard(str(out))
    for z in list(board.Zones()):  # idempotent: drop pours this script made before
        if z.GetZoneName().startswith('pour_'):
            board.Delete(z)
    bb = board.GetBoardEdgesBoundingBox()
    pours = [] if a.pour == ['none'] else (a.pour or ['GND:B.Cu'])
    for spec in pours:
        net, _, layer = spec.partition(':')
        code = board.GetNetcodeFromNetname(net)
        if code <= 0:
            p.error(f'no net named {net} on the board')
        zone = pcbnew.ZONE(board)
        zone.SetLayer(board.GetLayerID(layer))
        zone.SetNetCode(code)
        zone.SetZoneName(f'pour_{net}_{layer}')
        zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        # Solid to SMD pads, thermal reliefs on through-hole pads only: a cap under a module can't starve.
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        poly = zone.Outline()
        poly.NewOutline()
        m = pcbnew.FromMM(1.0)
        for x, y in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m),
                     (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
            poly.Append(int(x), int(y))
        board.Add(zone)
    pcbnew.SaveBoard(str(out), board)  # also writes the .kicad_pro when there is none
    pro = out.with_suffix('.kicad_pro')
    if pro.exists():
        print(subprocess.run([sys.executable, str(HERE / 'apply_fab_rules.py'), str(pro), '--fab', a.fab], capture_output=True, text=True).stdout.strip())
    board = pcbnew.LoadBoard(str(out))  # reload so the fill uses the fab clearances
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(out), board)
    print(f'prep_board: {out} · {len(board.GetTracks())} tracks · pours: {", ".join(pours) or "none"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
