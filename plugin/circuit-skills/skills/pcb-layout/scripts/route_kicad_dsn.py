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

Known limit: KiCad's exporter refuses some boards (it returns False with no reason given headless,
e.g. the tscircuit einhander board); those exit 2 and route_eval records the backend as failed.
"""
import argparse, os, shutil, subprocess, sys, tempfile
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
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)) or not dsn.exists():
        print(f'route_kicad_dsn: KiCad refused to export {src.name} as DSN', file=sys.stderr)
        return 2

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
