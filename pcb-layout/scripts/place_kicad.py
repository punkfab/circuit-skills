#!/usr/bin/env python3
"""place_kicad.py — place the parts of a bare KiCad board with this skill's own placement heuristics.

  /usr/bin/python3 place_kicad.py <board.kicad_pcb> -o <placed.kicad_pcb> [--hints FILE] [--restarts 4] [--seed 1]

--hints takes a placement-hint file (place_hints.py): rough, relative statements such as "J1 on edge
left", "U2 right of U1", "C1 near U1.7". They are soft terms in the cost; the hints it could not meet
are listed at the end.

autoplace.mjs anneals subcircuit blocks of a tscircuit design and untangle.mjs turns parts to shorten
their nets; both work on circuit.json. place_kicad.mjs does both in one cost on the single parts of
any KiCad board: anneal position and rotation (pad-level wirelength, hard penalties for overlap and
leaving the board, soft penalties for unmet hints), then push overlapping bodies apart.

Every part that carries a net is placed from scratch, wherever it is now. Locked parts and parts
without a net stay and are obstacles. Bodies are boxes (courtyard, else pads + 0.25 mm) and parts keep
their side; the outline is its polygon, cutouts are their boxes. Without hints it knows nothing about
intent (decoupling, connectors at the edge): that is what the hints are for. Needs pcbnew and node.
"""
import argparse, json, math, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def body(fp, pcbnew, courtyard=True):
    """Body box in board coordinates (mm): the courtyard when asked for and present, else the pads + 0.25 mm."""
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd) if courtyard else ():
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
    p.add_argument('--hints', type=Path)
    p.add_argument('--hint-weight', type=float, default=12.0)
    p.add_argument('--restarts', type=int, default=4)
    p.add_argument('--seed', type=int, default=1)
    a = p.parse_args()
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    sys.path.insert(0, str(HERE))
    import pcbnew
    board = pcbnew.LoadBoard(str(a.board))
    edge = board.GetBoardEdgesBoundingBox()
    fps = list(board.GetFootprints())
    parts, origin, refs, padmap, frames = [], {}, {}, {}, []
    is_movable = lambda fp: not fp.IsLocked() and any(pad.GetNetCode() > 0 for pad in fp.Pads())
    for fp in fps:
        if is_movable(fp):
            fp.SetOrientationDegrees(0)
    # Courtyards are the right spacing when there is room. On a crowded board designers overlap them, and
    # what KiCad's DRC enforces is copper: fall back to pad extents when the courtyards cover over half the board.
    area = pcbnew.ToMM(edge.GetWidth()) * pcbnew.ToMM(edge.GetHeight())
    boxes = [body(fp, pcbnew) for fp in fps]
    crowded = sum((b[2] - b[0]) * (b[3] - b[1]) for b in boxes) > 0.5 * area
    for i, fp in enumerate(fps):
        movable = is_movable(fp)
        x0, y0, x1, y1 = body(fp, pcbnew, courtyard=not crowded)
        # A frame: pads round the rim of a box that spans much of the board (castellated modules, edge
        # connectors drawn as one footprint). A box cannot stand for it, so it stays put and its pads are obstacles.
        px = [pad.GetBoundingBox() for pad in fp.Pads()]
        pad_area = sum(pcbnew.ToMM(q.GetWidth()) * pcbnew.ToMM(q.GetHeight()) for q in px)
        hollow = (x1 - x0) * (y1 - y0) > 0.25 * area and pad_area < 0.25 * (x1 - x0) * (y1 - y0)
        if hollow:
            movable = False
            frames += [[pcbnew.ToMM(q.GetLeft()) - 0.2, -pcbnew.ToMM(q.GetBottom()) - 0.2, pcbnew.ToMM(q.GetRight()) + 0.2, -pcbnew.ToMM(q.GetTop()) + 0.2] for q in px]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        pos = fp.GetPosition()
        origin[i] = (pcbnew.ToMM(pos.x) - cx, pcbnew.ToMM(pos.y) - cy)  # footprint origin from the body centre, rotation 0
        off = lambda pad: [pcbnew.ToMM(pad.GetPosition().x) - cx, -(pcbnew.ToMM(pad.GetPosition().y) - cy)]
        pads = [{'net': pad.GetNetname(), 'off': off(pad)} for pad in fp.Pads() if pad.GetNetCode() > 0]
        padmap[fp.GetReference()] = {pad.GetNumber(): off(pad) for pad in fp.Pads()}
        refs.setdefault(fp.GetReference(), i)
        parts.append({'ref': str(i), 'w': x1 - x0, 'h': y1 - y0, 'cx': cx, 'cy': -cy, 'locked': not movable, 'pads': pads,  # Y up
                      'side': 'B' if fp.GetLayer() == pcbnew.B_Cu else 'F', 'through': any(pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for pad in fp.Pads()), 'hollow': hollow or fp.GetPadCount() == 0})  # no pads: a logo or a graphic, nothing to collide with
    bbox = [pcbnew.ToMM(edge.GetLeft()), -pcbnew.ToMM(edge.GetBottom()), pcbnew.ToMM(edge.GetRight()), -pcbnew.ToMM(edge.GetTop())]
    poly, cuts = [], []
    try:  # the real outline and its holes, when KiCad can close it
        shape = pcbnew.SHAPE_POLY_SET()
        if board.GetBoardPolygonOutlines(shape) and shape.OutlineCount():
            o = shape.Outline(0)
            poly = [[pcbnew.ToMM(o.CPoint(k).x), -pcbnew.ToMM(o.CPoint(k).y)] for k in range(o.PointCount())]
            for k in range(shape.HoleCount(0)):
                hb = shape.Hole(0, k).BBox()
                cuts.append([pcbnew.ToMM(hb.GetLeft()), -pcbnew.ToMM(hb.GetBottom()), pcbnew.ToMM(hb.GetRight()), -pcbnew.ToMM(hb.GetTop())])
    except Exception:
        pass
    hints = []
    if a.hints:
        import place_hints
        try:
            hints = place_hints.parse(a.hints.read_text(), refs, padmap)
        except place_hints.HintError as e:
            print(f'place_kicad: {a.hints}: {e}', file=sys.stderr)
            return 2
    with tempfile.TemporaryDirectory(prefix='place_kicad-') as tmp:
        prob, sol = Path(tmp) / 'problem.json', Path(tmp) / 'solution.json'
        if os.getenv("PLACE_KICAD_DUMP"): Path(os.getenv("PLACE_KICAD_DUMP")).write_text(json.dumps({"bbox": bbox, "parts": parts, "cuts": cuts + frames, "crowded": crowded}))
        prob.write_text(json.dumps({'bbox': bbox, 'poly': poly, 'cuts': cuts + frames, 'parts': parts, 'hints': hints}))
        r = subprocess.run(['node', str(HERE / 'place_kicad.mjs'), str(prob), str(sol), '--restarts', str(a.restarts), '--seed', str(a.seed), '--hint-weight', str(a.hint_weight)])
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
    for z in board.Zones():  # a fill belongs to a routing; left in, a router that reads the file sees it as copper in its way
        z.UnFill()
    pcbnew.SaveBoard(str(a.output), board)
    pro = a.board.with_suffix('.kicad_pro')
    if pro.exists() and pro != a.output.with_suffix('.kicad_pro'):
        shutil.copy(pro, a.output.with_suffix('.kicad_pro'))
    print(f"place_kicad: {a.output} · {moved} parts placed · HPWL {res['hpwl']} mm (on the board: {real:.1f}) · overlap {res['overlap']} mm2 · off board {res['outside']} mm")
    unmet = [h for h in res.get('hints', []) if h['miss'] > 0.5]
    for h in unmet[:20]:
        print(f"  hint not met by {h['miss']} mm: {h['text']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
