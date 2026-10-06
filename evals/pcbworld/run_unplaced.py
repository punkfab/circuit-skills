#!/usr/bin/env python3
"""run_unplaced.py — place-and-route on unplaced D3 boards: does a placer's board route as well as the designer's?

Each board of a stored run_d3 run is unplaced (unplace.py), handed to a placer command, and the
placed board is routed with route_eval and judged exactly as run_d3 judges (stock kicad-cli DRC,
error level, the board's own rules; a courtyard overlap or a part off the board is a violation like
any other). The base run's best-of row, on the designer's placement, is the reference.

  python3 evals/pcbworld/run_unplaced.py --base d3b-v3 --name tracemaker-place \
      --cmd 'tracemaker-place {in} -o {out} --mode full --threads 8' --pile centre \
      [--backends tracemaker,freerouting:2.1.0] [--time 60] [--jobs 3]

{in} is the unplaced board, {out} the placed board the command must write. Results:
evals/pcbworld/results/<base>~<name>/. Re-running resumes.
"""
import argparse, concurrent.futures as cf, json, shlex, shutil, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_d3  # noqa: E402


def run_board(row, a, work_root):
    bid = row['board']
    work = work_root / bid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    src = a.data / bid
    shutil.copy(src / f'{run_d3.STEM}_unrouted.kicad_pcb', work / 'designer.kicad_pcb')
    for n in ('designer', 'board'):
        shutil.copy(src / f'{run_d3.STEM}.kicad_pro', work / f'{n}.kicad_pro')
    out = {'board': bid, 'u0': row['u0']}
    subprocess.run(['/usr/bin/python3', str(HERE / 'unplace.py'), str(work / 'designer.kicad_pcb'), '-o', str(work / 'unplaced.kicad_pcb'), '--pile', a.pile],
                   capture_output=True)
    argv = [x.replace('{in}', str(work / 'unplaced.kicad_pcb')).replace('{out}', str(work / 'board.kicad_pcb')) for x in shlex.split(a.cmd)]
    t0 = time.time()
    try:
        with open(work / 'place.log', 'w') as log:
            subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, cwd=work, timeout=a.place_timeout)
    except (subprocess.TimeoutExpired, OSError):
        pass
    out['place_s'] = round(time.time() - t0, 1)
    if not (work / 'board.kicad_pcb').exists():
        return {**out, 'failed': 'placer wrote no board'}
    bare = run_d3.drc(work / 'board.kicad_pcb', work / 'board.drc.json')
    out['placement_drv'] = len(bare.get('violations', []))  # before any routing: overlaps, parts off the board
    with open(work / 'route_eval.log', 'w') as log:
        subprocess.run([sys.executable, str(run_d3.SCRIPTS / 'route_eval.py'), str(work / 'board.kicad_pcb'), '--backends', a.backends, '--time', str(a.time)],
                       stdout=log, stderr=subprocess.STDOUT, cwd=work)
    runs = sorted((work / 'route-evals').glob('2*/results.json'))
    cands = []
    for r in (json.loads(runs[-1].read_text())['results'] if runs else []):
        dj = runs[-1].parent / f"{r['backend'].replace(':', '-')}.drc.json"
        if r['ok'] and dj.exists():
            cands.append({**run_d3.pcbworld_row(r['candidate'], dj, row['u0']), 'from': r['backend']})
    if not cands:
        return {**out, 'failed': 'no router produced a board'}
    return {**out, **min(cands, key=run_d3.select_key), 'by_backend': {c['from']: c for c in cands}}


def summarize(rows, base_rows, meta):
    ref = {r['board']: r['methods'].get('circuit-skills', {}) for r in base_rows}
    n = len(rows)
    ok = [r for r in rows if not r.get('failed')]
    mean = lambda xs: statistics.mean(xs) if xs else float('nan')
    line = lambda name, ms: f"| {name} | {sum(1 for m in ms if m.get('cp')) / n:.2f} | {sum(m.get('rout', 0) for m in ms) / n:.2f} | {mean([m['drv'] for m in ms if 'drv' in m]):.1f} | {mean([m['wl_mm'] for m in ms if 'wl_mm' in m]):.0f} | {mean([m['vias'] for m in ms if 'vias' in m]):.1f} |"
    lines = [f"# Unplaced D3 · {meta['run']}", '', f"{n} boards · placer `{meta['cmd']}` · routed with `{meta['backends']}`, {meta['time']} s per backend", '',
             '| placement → router | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias |', '|---|---|---|---|---|---|',
             line(f"designer ({meta['base']}, best of its backends)", [ref[r['board']] for r in rows]), line(f"{meta['name']} (best of the backends)", ok)]
    for be in meta['backends'].split(','):
        lines.append(line(f"{meta['name']} → {be}", [r['by_backend'][be] for r in ok if be in r.get('by_backend', {})]))
        base = [b['methods'][be] for b in base_rows if be in b['methods'] and not b['methods'][be].get('failed')]
        if base:
            lines.append(line(f'designer → {be}', base))
    lines += ['',
             f"Placer failed on {n - len(ok)} boards; {sum(1 for r in ok if r.get('placement_drv'))} placed boards had DRC errors before routing. "
             f"Mean placement time {mean([r['place_s'] for r in rows]):.1f} s.", '',
             '## Boards', '', '| board | designer | ' + meta['name'] + ' | placement DRC | place s |', '|---|---|---|---|---|']
    cell = lambda m: 'failed' if not m or m.get('failed') else ('✓ ' if m['cp'] else '') + f"{m['rout']:.2f} · {m['drv']} drv ({m.get('from', '')})"
    lines += [f"| {r['board']} | {cell(ref[r['board']])} | {cell(r)} | {r.get('placement_drv', '')} | {r['place_s']} |" for r in rows]
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--cmd', required=True)
    p.add_argument('--pile', choices=['beside', 'centre'], default='beside')
    p.add_argument('--backends', default='tracemaker,freerouting:2.1.0')
    p.add_argument('--time', type=int, default=60)
    p.add_argument('--place-timeout', type=int, default=1800)
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--limit', type=int)
    p.add_argument('--data', type=Path, default=run_d3.DATA)
    a = p.parse_args()
    base_rows = [json.loads(l) for l in (HERE / 'results' / a.base / 'per_board.jsonl').read_text().splitlines() if l.strip()][:a.limit]
    run = f'{a.base}~{a.name}'
    out = HERE / 'results' / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'per_board.jsonl'
    rows = {r['board']: r for r in map(json.loads, path.read_text().splitlines())} if path.exists() else {}
    todo = [r for r in base_rows if r['board'] not in rows]
    print(f'{run}: {len(todo)} of {len(base_rows)} boards to run', flush=True)
    with cf.ThreadPoolExecutor(a.jobs) as pool, open(path, 'a') as sink:
        for i, f in enumerate(cf.as_completed([pool.submit(run_board, r, a, run_d3.CACHE / 'runs' / run) for r in todo]), 1):
            r = f.result()
            rows[r['board']] = r
            sink.write(json.dumps(r) + '\n')
            sink.flush()
            print(f"  [{i}/{len(todo)}] {r['board'][:40]:40s} " + (r['failed'] if r.get('failed') else f"{'✓' if r['cp'] else ' '} rout {r['rout']:.2f} drv {r['drv']} ({r['from']})"), flush=True)
    meta = {'run': run, 'base': a.base, 'name': a.name, 'cmd': a.cmd.replace(str(Path.home()), '~'), 'pile': a.pile, 'backends': a.backends, 'time': a.time}
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'summary.md').write_text(summarize([rows[r['board']] for r in base_rows if r['board'] in rows], base_rows, meta))
    print('\n' + (out / 'summary.md').read_text().split('## Boards')[0])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
