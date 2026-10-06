#!/usr/bin/env python3
"""score_study.py — which placement measures actually predict a clean route? Measured on the corpus.

Every board gets five placements of the same netlist, from good to bad:

  designer   as its designer placed it
  swap25     the designer's placement with a quarter of the interchangeable parts (same footprint,
  swap100    same side) swapped among themselves, or all of them: still legal, worse wiring
  pk         place_kicad.py (our annealer + untangle), from scratch
  tm         tracemaker-place --mode full, from scratch

Each is routed with TraceMaker under one short budget and judged by KiCad DRC. Then every placement
measure is scored on how well it predicts the outcome, across boards and between placements of the
same board.

  python3 evals/corpus/score_study.py route [--limit N] [--time 20] [--jobs 3]   # resumable
  python3 evals/corpus/score_study.py analyze                                     # -> score_study.md

Needs the corpus cache (collect.py fetch), tracemaker and tracemaker-place on PATH.
"""
import argparse, concurrent.futures as cf, json, math, os, random, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SCRIPTS = ROOT / 'pcb-layout' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE.parent / 'pcbworld'))
CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'corpus'
STEM = 'processed_v9_guide_v3'
VARIANTS = ['designer', 'swap25', 'swap100', 'pk', 'tm']
ROWS = HERE / 'score_study.jsonl'

SWAP = r'''
import random, sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
import pcbnew
src, out, frac, seed = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
b = pcbnew.LoadBoard(src)
groups = {}
for f in b.GetFootprints():
    if not f.IsLocked() and any(p.GetNetCode() > 0 for p in f.Pads()):
        groups.setdefault((f.GetFPIDAsString(), f.GetLayer(), f.GetPadCount()), []).append(f)
rng = random.Random(seed)
moved = 0
for key in sorted(groups, key=str):
    g = sorted(groups[key], key=lambda f: f.GetReference())
    if len(g) < 2:
        continue
    pick = g if frac >= 1 else rng.sample(g, max(2, round(len(g) * frac)))
    slots = [(f.GetPosition(), f.GetOrientationDegrees()) for f in pick]
    order = slots[1:] + slots[:1] if len(slots) == 2 else rng.sample(slots, len(slots))
    for f, (pos, deg) in zip(pick, order):
        if f.GetPosition() != pos:
            moved += 1
        f.SetPosition(pos); f.SetOrientationDegrees(deg)
pcbnew.SaveBoard(out, b)
print(moved)
'''


def drc(board):
    out = board.with_suffix('.drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-error', '--units', 'mm', '-o', str(out), str(board)], capture_output=True, timeout=600)
    d = json.loads(out.read_text())
    return len(d.get('violations', [])), len(d.get('unconnected_items', []))


def place(variant, src, out, work):
    """Write the variant's placed, unrouted board; returns False when the placer produced nothing."""
    py = '/usr/bin/python3'
    if variant == 'designer':
        shutil.copy(src, out)
    elif variant.startswith('swap'):
        subprocess.run([py, '-c', SWAP, str(src), str(out), str(int(variant[4:]) / 100), '1'], capture_output=True, timeout=300)
    elif variant in ('pk', 'pk2'):
        subprocess.run([py, str(SCRIPTS / 'place_kicad.py'), str(src), '-o', str(out)], capture_output=True, timeout=1800)
    elif variant in ('h1', 'h2', 'h3'):  # hints derived from the designer's placement, at three levels of detail
        hints = work / f'{variant}.hints'
        hints.write_text(subprocess.run([py, str(SCRIPTS / 'place_hints.py'), 'derive', str(src), '--level', variant[1]], capture_output=True, text=True, timeout=300).stdout)
        r = subprocess.run([py, str(SCRIPTS / 'place_kicad.py'), str(src), '-o', str(out), '--hints', str(hints)], capture_output=True, text=True, timeout=1800)
        (work / f'{variant}.place.log').write_text(r.stdout + r.stderr)
    elif variant == 'tm':
        pile = work / 'pile.kicad_pcb'
        subprocess.run([py, str(HERE.parent / 'pcbworld' / 'unplace.py'), str(src), '-o', str(pile), '--pile', 'centre'], capture_output=True, timeout=300)
        subprocess.run(['tracemaker-place', str(pile), '-o', str(out), '--mode', 'full', '--threads', '4'], capture_output=True, timeout=900)
    return out.exists()


def run_board(b, a):
    folder = CACHE / 'boards' / b['id']
    work = CACHE / 'score_study' / b['id']
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    bare = work / 'unrouted.kicad_pcb'  # zone fills cleared: they belong to the designer's routing
    shutil.copy(folder / f'{STEM}_unrouted.kicad_pcb', bare)
    subprocess.run(['/usr/bin/python3', str(SCRIPTS / 'zone_fill.py'), str(bare), '--unfill'], capture_output=True, timeout=300)
    for v in a.variants:
        placed, routed = work / f'{v}.kicad_pcb', work / f'{v}.routed.kicad_pcb'
        for f in (placed, routed):
            f.unlink(missing_ok=True)
        for ext in ('.kicad_pro', '.kicad_dru'):
            if (folder / (STEM + ext)).exists():
                for f in (placed, routed):
                    shutil.copy(folder / (STEM + ext), f.with_suffix(ext))
        row = {'board': b['id'], 'variant': v, 'connections': b['connections']}
        try:
            if not place(v, bare, placed, work):
                rows.append({**row, 'failed': 'no placement'})
                continue
            subprocess.run(['/usr/bin/python3', str(SCRIPTS / 'zone_fill.py'), str(placed), '--unfill'], capture_output=True, timeout=300)
            row['placement_drv'], u0 = drc(placed)
            t0 = time.time()
            subprocess.run(['tracemaker', 'route', str(placed), '-o', str(routed), '--time', str(a.time), '--threads', '4', '--no-kb'], capture_output=True, timeout=a.time * 4 + 120)
            row['route_s'] = round(time.time() - t0, 1)
            if not routed.exists():
                rows.append({**row, 'failed': 'no route'})
                continue
            subprocess.run(['/usr/bin/python3', str(SCRIPTS / 'zone_fill.py'), str(routed)], capture_output=True, timeout=600)
            row['drv'], row['open'] = drc(routed)
            row['rout'] = round(max(0.0, 1 - row['open'] / u0), 4) if u0 else 1.0
            row['clean'] = row['drv'] == 0 and row['open'] == 0
            routed.unlink()
        except Exception as e:
            row['failed'] = f'{type(e).__name__}: {e}'[:120]
        rows.append(row)
    return rows


def route(a):
    boards = [b for b in json.loads((HERE / 'manifest.json').read_text())['boards'] if b['bare_drv'] == 0 and b['connections'] <= a.max_connections]
    global ROWS
    ROWS = HERE / a.rows
    done = {json.loads(l)['board'] for l in ROWS.read_text().splitlines()} if ROWS.exists() else set()
    todo = [b for b in boards if b['id'] not in done][:a.limit]
    print(f'{len(todo)} of {len(boards)} boards to run', flush=True)
    with cf.ThreadPoolExecutor(a.jobs) as pool, open(ROWS, 'a') as sink:
        for i, f in enumerate(cf.as_completed([pool.submit(run_board, b, a) for b in todo]), 1):
            rows = f.result()
            for r in rows:
                sink.write(json.dumps(r) + '\n')
            sink.flush()
            print(f"  [{i}/{len(todo)}] {rows[0]['board'][:50]:50s} " + ' '.join(f"{r['variant']}:{'x' if r.get('failed') else ('✓' if r['clean'] else format(r['rout'], '.2f'))}" for r in rows), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('step', choices=['route', 'analyze'])
    p.add_argument('--limit', type=int)
    p.add_argument('--time', type=int, default=20)
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--max-connections', type=int, default=150)
    p.add_argument('--rows', default='score_study.jsonl', help='results file under evals/corpus')
    p.add_argument('--variants', type=lambda s: s.split(','), default=VARIANTS)
    a = p.parse_args()
    if a.step == 'route':
        route(a)
    else:
        import score_analyze
        score_analyze.main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
