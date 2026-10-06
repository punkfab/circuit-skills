#!/usr/bin/env python3
"""place_kicad.py — place the parts of a bare KiCad board with this skill's own placement heuristics.

  /usr/bin/python3 place_kicad.py <board.kicad_pcb> -o <placed.kicad_pcb> [--restarts 6] [--seed 1]

autoplace.mjs anneals subcircuit blocks of a tscircuit design and untangle.mjs turns parts to shorten
their nets; both work on circuit.json. This runs the same two steps on single parts of any KiCad
board, so the heuristics can be measured where there is no tscircuit project (evals/pcbworld/
run_unplaced.py): anneal positions (signal-net wirelength, hard penalties for overlap and leaving
the board), then pick each part's best of 0/90/180/270.

Every part that carries a net is placed from scratch, wherever it is now. Locked parts and parts
without a net stay and are obstacles. The board is treated as its bounding box and bodies as boxes
(courtyard, else pads + 0.25 mm); parts keep their side. It does not know about decoupling,
connectors at the edge, or any other intent: in a real design those come from the modules and
lib/place.tsx, and this script is the fallback and the benchmark, not the workflow. Needs pcbnew and node.
"""
import argparse, json, math, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def body(fp, pcbnew):
    """Body box in board coordinates (mm): courtyard when the footprint has one, else pads + 0.25 mm."""
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        c = fp.GetCourtyard(layer)
        if c.OutlineCount():
            b = c.BBox()
            return [pcbnew.ToMM(v) for v in (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())]
    xs, ys = [], []
    for pad in fp.Pads():
        b = pad.GetBoundingBox()
        xs += [b.GetLeft(), b.GetRight()]
        ys += [b.GetTop(), b.GetBottom()]
    if not xs:
        b = fp.GetBoundingBox(False)
        xs, ys = [b.GetLeft(), b.GetRight()], [b.GetTop(), b.GetBottom()]
    return [pcbnew.ToMM(min(xs)) - 0.25, pcbnew.ToMM(min(ys)) - 0.25, pcbnew.ToMM(max(xs)) + 0.25, pcbnew.ToMM(max(ys)) + 0.25]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('board', type=Path)
    p.add_argument('-o', '--output', type=Path, required=True)
    p.add_argument('--restarts', type=int, default=6)
    p.add_argument('--seed', type=int, default=1)
    a = p.parse_args()
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    import pcbnew
    board = pcbnew.LoadBoard(str(a.board))
    edge = board.GetBoardEdgesBoundingBox()
    fps = list(board.GetFootprints())
    parts, origin = [], {}
    for i, fp in enumerate(fps):
        movable = not fp.IsLocked() and any(pad.GetNetCode() > 0 for pad in fp.Pads())
        if movable:
            fp.SetOrientationDegrees(0)
        x0, y0, x1, y1 = body(fp, pcbnew)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        pos = fp.GetPosition()
        origin[i] = (pcbnew.ToMM(pos.x) - cx, pcbnew.ToMM(pos.y) - cy)  # footprint origin from the body centre, rotation 0
        pads = [{'net': pad.GetNetname(), 'off': [pcbnew.ToMM(pad.GetPosition().x) - cx, -(pcbnew.ToMM(pad.GetPosition().y) - cy)]}
                for pad in fp.Pads() if pad.GetNetCode() > 0]
        parts.append({'ref': str(i), 'w': x1 - x0, 'h': y1 - y0, 'cx': cx, 'cy': -cy, 'locked': not movable, 'pads': pads})  # Y up
    bbox = [pcbnew.ToMM(edge.GetLeft()), -pcbnew.ToMM(edge.GetBottom()), pcbnew.ToMM(edge.GetRight()), -pcbnew.ToMM(edge.GetTop())]
    with tempfile.TemporaryDirectory(prefix='place_kicad-') as tmp:
        prob, sol = Path(tmp) / 'problem.json', Path(tmp) / 'solution.json'
        prob.write_text(json.dumps({'bbox': bbox, 'parts': parts}))
        r = subprocess.run(['node', str(HERE / 'place_kicad.mjs'), str(prob), str(sol), '--restarts', str(a.restarts), '--seed', str(a.seed)])
        if r.returncode or not sol.exists():
            return 1
        res = json.loads(sol.read_text())
    moved = 0
    for i, fp in enumerate(fps):
        if parts[i]['locked']:
            continue
        s = res['parts'][str(i)]
        t = math.radians(s['rot'])
        ox, oy = origin[i][0], -origin[i][1]  # Y up
        rx, ry = ox * math.cos(t) - oy * math.sin(t), ox * math.sin(t) + oy * math.cos(t)
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(s['cx'] + rx), pcbnew.FromMM(-(s['cy'] + ry))))
        fp.SetOrientationDegrees(s['rot'])
        moved += 1
    # The model's wirelength must match the board it produced, or a frame or rotation convention is off.
    real, nets = 0.0, {}
    for i, fp in enumerate(fps):
        for pad in fp.Pads():
            if pad.GetNetCode() > 0:
                nets.setdefault(pad.GetNetname(), {}).setdefault(i, []).append(pad.GetPosition())
    for members in nets.values():
        if 2 <= len(members) <= 8:
            pts = [q for ps in members.values() for q in ps]
            real += pcbnew.ToMM(max(q.x for q in pts) - min(q.x for q in pts)) + pcbnew.ToMM(max(q.y for q in pts) - min(q.y for q in pts))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(a.output), board)
    pro = a.board.with_suffix('.kicad_pro')
    if pro.exists() and pro != a.output.with_suffix('.kicad_pro'):
        shutil.copy(pro, a.output.with_suffix('.kicad_pro'))
    print(f"place_kicad: {a.output} · {moved} parts placed · HPWL {res['hpwl']} mm (on the board: {real:.1f}) · overlap {res['overlap']} mm2")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
