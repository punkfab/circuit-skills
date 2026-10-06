#!/usr/bin/env python3
"""unplace.py — turn a placed, unrouted D3 board into an unplaced one.

There is no public corpus of unplaced real boards; placement papers build theirs by scattering the
footprints of real designs. This does the same to PCBWorld D3: every footprint that carries a net is
moved to a grid pile beside the outline at rotation 0, which is the state KiCad's "Update PCB from
Schematic" leaves a new board in. The netlist, outline, zones, rules and each part's side are kept.
Left where they are: locked footprints and footprints with no net (mounting holes, logos, fiducials).

  /usr/bin/python3 evals/pcbworld/unplace.py <unrouted.kicad_pcb> -o <unplaced.kicad_pcb> [--pile centre]

--pile centre stacks the parts on the board's centre instead: for placers that treat a part outside
the outline as fixed (TraceMaker's does).

The designer's placement (the input) is the reference a placer is compared with. Needs pcbnew.
"""
import argparse, shutil, sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('board', type=Path)
    p.add_argument('-o', '--output', type=Path, required=True)
    p.add_argument('--pile', choices=['beside', 'centre'], default='beside')
    p.add_argument('--gap', type=float, default=2.0, help='gap between piled parts, mm')
    a = p.parse_args()
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    import pcbnew
    board = pcbnew.LoadBoard(str(a.board))
    edge = board.GetBoardEdgesBoundingBox()
    gap = pcbnew.FromMM(a.gap)
    movable = [f for f in board.GetFootprints() if not f.IsLocked() and any(pad.GetNetCode() > 0 for pad in f.Pads())]
    movable.sort(key=lambda f: f.GetReference())
    x0, y = edge.GetRight() + pcbnew.FromMM(10), edge.GetTop()
    x, row_h, row_w = x0, 0, max(edge.GetWidth(), pcbnew.FromMM(60))
    for f in movable:
        f.SetOrientationDegrees(0)
        if a.pile == 'centre':
            f.SetPosition(edge.GetCenter())
            continue
        bb = f.GetBoundingBox(False)
        if x > x0 and x + bb.GetWidth() > x0 + row_w:
            x, y, row_h = x0, y + row_h + gap, 0
        pos = f.GetPosition()
        f.SetPosition(pcbnew.VECTOR2I(int(pos.x + x - bb.GetLeft()), int(pos.y + y - bb.GetTop())))
        x += bb.GetWidth() + gap
        row_h = max(row_h, bb.GetHeight())
    a.output.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(a.output), board)
    pro = a.board.with_suffix('.kicad_pro')
    if pro.exists():
        shutil.copy(pro, a.output.with_suffix('.kicad_pro'))
    print(f'unplace: {a.output} · {len(movable)} parts piled, {len(board.GetFootprints()) - len(movable)} left in place')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
