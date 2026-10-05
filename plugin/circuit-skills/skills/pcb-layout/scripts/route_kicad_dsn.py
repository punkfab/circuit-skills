#!/usr/bin/env python3
"""route_kicad_dsn.py — Freerouting (or FastRoute) on any KiCad board, headless, through KiCad's own
Specctra exporter and importer. No tscircuit DSN involved, so none of its mirroring or padstack bugs.

  /usr/bin/python3 route_kicad_dsn.py <board.kicad_pcb> -o <out.kicad_pcb> [--backend freerouting|fastroute]
                                      [--time S] [--passes N] [--keep-routing]

Steps: load the board with pcbnew, strip its tracks and vias (unless --keep-routing, which leaves them
as fixed wiring), ExportSpecctraDSN, route with route_dsn.py (FREERT / freert224, bounded wall time),
ImportSpecctraSES, refill zones, save <out> with the board's .kicad_pro beside it. Writes <out>.dsn and
<out>.ses next to the output. Needs the pcbnew module (the system /usr/bin/python3 of a KiCad 9 install).
Exit 0 when a routed board was written, 1 when the router saved no session, 2 on bad input.

KiCad's exporter returns False, with no reason given headless, for a board that has a footprint with an
empty reference; tscircuit exports bare holes and vias that way, so they are named NOREFn for the round
trip and blanked again. Pour zones go out as planes and Edge.Cuts cutouts as keepouts. A board KiCad
still refuses exits 2 and route_eval records the backend as failed.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def strip_routing(text):
    """Drop the top-level segment / arc / via items from board text. Done on the text, because
    board.Remove() on pcbnew tracks leaves wrappers that crash Python's garbage collector later."""
    out, i, depth, start, n = [], 0, 0, 0, len(text)
    keep_from = 0
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif c == '(':
            depth += 1
            if depth == 2:
                start = i
        elif c == ')':
            if depth == 2 and (text[start + 1:start + 9].split() or [''])[0] in ('segment', 'arc', 'via'):
                out.append(text[keep_from:start])
                keep_from = i + 1
            depth -= 1
        i += 1
    out.append(text[keep_from:])
    return ''.join(out)


def grow_keepouts(dsn_text, margin_um):
    """Push every (keepout (polygon ...)) vertex away from the polygon's centroid by margin_um.
    KiCad exports Edge.Cuts cutouts as bare keepouts, so a router keeps only track clearance from a
    slot or window, not the fab's copper-to-edge clearance. Exact for circles, near enough for
    convex cutouts (windows, slots)."""
    import re

    def grow(m):
        nums = [float(v) for v in m.group(3).split()]
        pts = list(zip(nums[0::2], nums[1::2]))
        ring = pts[:-1] if len(pts) > 1 and pts[0] == pts[-1] else pts  # closed polygons repeat the first vertex
        cx, cy = sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring)
        out = []
        for x, y in pts:
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 or 1.0
            out.append(f'{x + (x - cx) / d * margin_um:.1f} {y + (y - cy) / d * margin_um:.1f}')
        return f'{m.group(1)}{m.group(2)}  {"  ".join(out)}'

    return re.sub(r'(\(keepout "[^"]*" \(polygon )(\S+ \S+)\s+([-\d.\s]+?)(?=\))', grow, dsn_text)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('board', type=Path)
    p.add_argument('-o', '--output', type=Path, required=True)
    p.add_argument('--backend', choices=['freerouting', 'fastroute'], default='freerouting')
    p.add_argument('--time', type=int, default=int(os.getenv('MAXT', '120')))
    p.add_argument('--passes', type=int, default=int(os.getenv('MP', '100')))
    p.add_argument('--keep-routing', action='store_true', help='route around the existing tracks instead of stripping them')
    a = p.parse_args()
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    import pcbnew  # here, so strip_routing imports without KiCad
    src, out = a.board.resolve(), a.output.resolve()
    if not src.is_file():
        p.error(f'no board at {src}')
    out.parent.mkdir(parents=True, exist_ok=True)
    dsn, ses = out.with_suffix('.dsn'), out.with_suffix('.ses')
    for f in (dsn, ses):
        f.unlink(missing_ok=True)

    load = src
    if not a.keep_routing:
        load = out.with_name(out.stem + '.unrouted.kicad_pcb')
        load.write_text(strip_routing(src.read_text()))
        if src.with_suffix('.kicad_pro').exists():  # the DSN's clearances and widths come from the project's net classes
            shutil.copy(src.with_suffix('.kicad_pro'), load.with_suffix('.kicad_pro'))
    board = pcbnew.LoadBoard(str(load))
    # KiCad's exporter refuses a board with an empty footprint reference (it returns False, silently,
    # headless). tscircuit exports bare holes and vias that way, so name them for the round trip.
    unnamed = [f for f in board.GetFootprints() if not f.GetReference()]
    for i, f in enumerate(unnamed):
        f.SetReference(f'NOREF{i + 1}')
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)) or not dsn.exists():
        print(f'route_kicad_dsn: KiCad refused to export {src.name} as DSN', file=sys.stderr)
        return 2

    # Cutout keepouts get the copper-to-edge clearance (project rule, 0.3 mm when there is none).
    edge = 0.3
    try:
        edge = json.loads(load.with_suffix('.kicad_pro').read_text())['board']['design_settings']['rules'].get('min_copper_edge_clearance', edge)
    except (OSError, ValueError, KeyError):
        pass
    dsn.write_text(grow_keepouts(dsn.read_text(), (edge + 0.05) * 1000))

    env = dict(os.environ)
    if a.backend == 'freerouting' and not env.get('FREERT'):
        env['FREERT'] = str(Path.home() / '.local/bin/freert224')
    # Freerouting 2.2.4 splits its -de/-do paths on spaces, so route in a space-free scratch folder.
    with tempfile.TemporaryDirectory(prefix='route_kicad_dsn-') as tmp:
        tdsn, tses = Path(tmp) / 'board.dsn', Path(tmp) / 'board.ses'
        shutil.copy(dsn, tdsn)
        code = subprocess.run([sys.executable if Path(sys.executable).name.startswith('python') else 'python3',
                               str(HERE / 'route_dsn.py'), str(tdsn), '-o', str(tses), '--backend', a.backend,
                               '--max-time', str(a.time), '--max-passes', str(a.passes)], env=env).returncode
        for f, dest in ((tses, ses), (Path(str(tses) + '.log'), Path(str(ses) + '.log')), (Path(str(tses) + '.report.json'), Path(str(ses) + '.report.json'))):
            if f.exists():
                shutil.copy(f, dest)
    if code != 0 or not ses.exists():
        print(f'route_kicad_dsn: {a.backend} saved no session (exit {code}); log {ses}.log', file=sys.stderr)
        return 1
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        print(f'route_kicad_dsn: KiCad could not import {ses}', file=sys.stderr)
        return 1
    for f in unnamed:
        f.SetReference('')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(out), board)
    pro = src.with_suffix('.kicad_pro')
    if pro.exists() and pro != out.with_suffix('.kicad_pro'):
        shutil.copy(pro, out.with_suffix('.kicad_pro'))
    tracks = board.GetTracks()
    vias = sum(1 for t in tracks if t.GetClass() == 'PCB_VIA')
    print(f'route_kicad_dsn: {a.backend} -> {out} ({len(tracks) - vias} segments, {vias} vias)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
