#!/usr/bin/env python3
"""run_external.py — score another autorouter on the same D3 boards, next to a stored run_d3 run.

An external router is any command that takes a KiCad board and writes a routed one. It is run on
each board's unrouted file, judged exactly as run_d3 judges our own backends (stock kicad-cli DRC,
error level, the board's own .kicad_pro), and added to a copy of the base run's rows as one more
method. It never enters the "circuit-skills" best-of row.

  python3 evals/pcbworld/run_external.py --base d3a-v2 --name tracemaker \
      --cmd '/path/to/tracemaker route {in} -o {out} --time 60 --threads 8 --no-kb'

{in} and {out} are replaced with the board paths. Results: evals/pcbworld/results/<base>+<name>/.
Re-running resumes. time_s is the command's wall time.
"""
import argparse, concurrent.futures as cf, json, os, shlex, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_d3  # noqa: E402


def run_board(row, name, cmd, data, work_root, timeout):
    bid = row['board']
    work = work_root / bid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    src = data / bid
    pro = src / f'{run_d3.STEM}.kicad_pro'
    shutil.copy(src / f'{run_d3.STEM}_unrouted.kicad_pcb', work / 'board.kicad_pcb')
    for n in ('board', 'out'):
        shutil.copy(pro, work / f'{n}.kicad_pro')
    argv = [a.replace('{in}', str(work / 'board.kicad_pcb')).replace('{out}', str(work / 'out.kicad_pcb')) for a in shlex.split(cmd)]
    t0 = time.time()
    try:
        with open(work / 'route.log', 'w') as log:
            r = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, cwd=work, timeout=timeout)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = 'timeout'
    dt = round(time.time() - t0, 1)
    out = work / 'out.kicad_pcb'
    if not out.exists():
        return bid, {'failed': True, 'exit': code, 'time_s': dt}
    return bid, {**run_d3.pcbworld_row(out, run_d3.drc(out, work / 'out.drc.json'), row['u0']), 'time_s': dt}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base', required=True, help='a stored run_d3 run, e.g. d3a-v2')
    p.add_argument('--name', required=True, help='method name for the external router')
    p.add_argument('--cmd', required=True, help='command with {in} and {out}')
    p.add_argument('--jobs', type=int, default=3)
    p.add_argument('--timeout', type=int, default=600, help='kill the command after this many seconds')
    p.add_argument('--data', type=Path, default=run_d3.DATA)
    a = p.parse_args()
    base = HERE / 'results' / a.base
    meta = json.loads((base / 'meta.json').read_text())
    rows = [json.loads(l) for l in (base / 'per_board.jsonl').read_text().splitlines() if l.strip()]
    out = HERE / 'results' / f'{a.base}+{a.name}'
    out.mkdir(parents=True, exist_ok=True)
    done_path = out / f'{a.name}.jsonl'
    done = dict(json.loads(l) for l in done_path.read_text().splitlines() if l.strip()) if done_path.exists() else {}
    work_root = run_d3.CACHE / 'runs' / f'{a.base}+{a.name}'
    todo = [r for r in rows if r['board'] not in done]
    print(f'{a.name} on {a.base}: {len(todo)} of {len(rows)} boards to run · {out}', flush=True)
    with cf.ThreadPoolExecutor(a.jobs) as pool, open(done_path, 'a') as sink:
        futs = [pool.submit(run_board, r, a.name, a.cmd, a.data, work_root, a.timeout) for r in todo]
        for n, f in enumerate(cf.as_completed(futs), 1):
            bid, m = f.result()
            done[bid] = m
            sink.write(json.dumps([bid, m]) + '\n')
            sink.flush()
            print(f"  [{n}/{len(todo)}] {bid[:40]:40s} " + ('failed' if m.get('failed') else f"{'✓' if m['cp'] else ' '} rout {m['rout']:.2f} drv {m['drv']} {m['time_s']}s"), flush=True)
    for r in rows:
        if r['board'] in done:
            r['methods'][a.name] = done[r['board']]
    (out / 'per_board.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    meta = {**meta, 'run': f'{a.base}+{a.name}', 'external': {a.name: a.cmd.replace(str(Path.home()), '~')}}
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'summary.md').write_text(run_d3.summarize(rows, meta['split'], meta))
    print('\n' + (out / 'summary.md').read_text().split('\n\nPCBWorld paper')[0])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
