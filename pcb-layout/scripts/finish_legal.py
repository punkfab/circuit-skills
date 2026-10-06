#!/usr/bin/env python3
"""finish_legal.py — make a routed board legal: remove the copper KiCad's DRC objects to, then let a
rule-checking router put those connections back.

  python3 finish_legal.py <routed.kicad_pcb> -o <out.kicad_pcb> [--time 30] [--rounds 2] [--finisher tracemaker]

Some routers connect everything but treat clearances and widths as soft (tscircuit's capacity
autorouter necks tracks down to 0.1 mm and squeezes past pads). Their output is most of a board. This
keeps the legal part of it:

  1. KiCad DRC (error level, the board's own rules) names every track and via in a violation;
  2. those are deleted, which opens their connections again;
  3. TraceMaker routes what is open around the copper that is left, checking each segment against the
     rules before it commits it;
  4. repeat while DRC still names tracks, up to --rounds; when only open connections are left, the
     copper within a few mm of their ends is cleared too, a wider circle each round.

Prints what it removed and what is left. Needs kicad-cli, tracemaker (TRACEMAKER_BIN or PATH) and pcbnew
for the zone refill.
"""
import argparse, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = os.getenv('CIRCUIT_SKILLS_KICAD_PYTHON', '/usr/bin/python3')
COPPER = {'clearance', 'shorting_items', 'tracks_crossing', 'track_width', 'hole_clearance', 'copper_edge_clearance', 'via_diameter', 'annular_width',
          'drill_out_of_range', 'hole_to_hole', 'via_dangling', 'solder_mask_bridge'}


def drc(board):
    out = board.with_suffix('.drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-error', '--units', 'mm', '-o', str(out), str(board)], capture_output=True, timeout=900)
    return json.loads(out.read_text())


def offenders(report):
    """uuids of the tracks and vias named in copper violations."""
    ids = set()
    for v in report.get('violations', []):
        if v['type'] in COPPER:
            ids |= {i['uuid'] for i in v['items'] if re.match(r'(Track|Via|Arc)\b', i.get('description', ''))}
    return ids


def remove_items(text, uuids, near=(), radius=0.0):
    """The board text without the top-level segment/via/arc blocks whose uuid is in `uuids`, or that end
    within `radius` mm of a point in `near` (text level: pcbnew's Remove() on tracks crashes Python's GC)."""
    close = lambda block: any((float(x) - px) ** 2 + (float(y) - py) ** 2 <= radius * radius
                              for x, y in re.findall(r'\((?:start|end|at) (-?[\d.]+) (-?[\d.]+)', block) for px, py in near)
    out, depth, i, start, n, removed = [], 0, 0, None, len(text), 0
    last = 0
    while i < n:
        ch = text[i]
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
        elif ch == '(':
            if depth == 1 and re.match(r'\((segment|via|arc)\b', text[i:i + 9]):
                start = i
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 1 and start is not None:
                block = text[start:i + 1]
                m = re.search(r'\(uuid "?([0-9a-fA-F-]+)"?\)', block)
                if (m and m.group(1) in uuids) or (near and close(block)):
                    out.append(text[last:start])
                    last = i + 1
                    removed += 1
                start = None
        i += 1
    out.append(text[last:])
    return ''.join(out), removed


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('board', type=Path)
    p.add_argument('-o', '--output', type=Path, required=True)
    p.add_argument('--time', type=int, default=30)
    p.add_argument('--rounds', type=int, default=4)
    p.add_argument('--threads', default=os.getenv('TRACEMAKER_THREADS', '8'))
    a = p.parse_args()
    tm = os.getenv('TRACEMAKER_BIN') or shutil.which('tracemaker')
    if not tm:
        print('finish_legal: tracemaker not found (TRACEMAKER_BIN or PATH)', file=sys.stderr)
        return 2
    out = a.output.resolve()
    work = out.with_name(out.stem + '.work.kicad_pcb')
    shutil.copy(a.board, work)
    for ext in ('.kicad_pro', '.kicad_dru'):
        if a.board.with_suffix(ext).exists():
            for f in (work, out):
                shutil.copy(a.board.with_suffix(ext), f.with_suffix(ext))
    if not a.board.with_suffix('.kicad_pro').exists():
        print(f'finish_legal: no {a.board.with_suffix(".kicad_pro").name} beside the board: judging against KiCad defaults, not its own rules', file=sys.stderr)
    total = 0
    for rnd in range(1, a.rounds + 1):
        report = drc(work)
        ids = offenders(report)
        opens = len(report.get('unconnected_items', []))
        if not ids and not opens:
            break
        # Nothing illegal left but connections still open: the copper that stayed is in their way. Clear a
        # growing neighbourhood around each open end and let the finisher have the room.
        near, radius = [], 0.0
        if not ids and opens:
            radius = 3.0 * (rnd - 1 or 1)
            near = [(i['pos']['x'], i['pos']['y']) for u in report['unconnected_items'] for i in u['items'] if 'pos' in i]
        text, removed = remove_items(work.read_text(), ids, near, radius)
        total += removed
        work.write_text(text)
        subprocess.run([PY, str(HERE / 'zone_fill.py'), str(work), '--unfill'], capture_output=True)
        nxt = work.with_name(out.stem + f'.round{rnd}.kicad_pcb')
        nxt.unlink(missing_ok=True)
        subprocess.run([tm, 'route', str(work), '-o', str(nxt), '--time', str(a.time), '--threads', str(a.threads), '--no-kb'], capture_output=True, timeout=a.time * 4 + 120)
        if not nxt.exists():
            print(f'finish_legal: round {rnd}: the finisher wrote nothing', file=sys.stderr)
            break
        subprocess.run([PY, str(HERE / 'zone_fill.py'), str(nxt)], capture_output=True)
        shutil.move(nxt, work)
        print(f'finish_legal: round {rnd}: removed {removed} tracks and vias named in {len(report.get("violations", []))} violations ({opens} open before), re-routed')
    shutil.move(work, out)
    final = drc(out)
    for f in out.parent.glob(out.stem + '.work.*'):
        f.unlink()
    print(f"finish_legal: {out} · removed {total} items · {len(final.get('violations', []))} DRC errors, {len(final.get('unconnected_items', []))} open")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
