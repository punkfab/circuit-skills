#!/usr/bin/env python3
"""run_d3.py — PCBWorld's D3 real-board benchmark as an eval for circuit-skills.

PCBWorld (LG AI Research, KDD 2026 workshop, github.com/LGAI-Research/PCBWorld) takes 678 open-source
PCBench boards, keeps every part where its designer put it, strips the routing, and asks a router to
put it back. Each result is scored by KiCad DRC against the board's own design rules. That is exactly
the job route_eval.py does, so every routing backend circuit-skills has is run on the same boards and
scored the way the paper scores its baselines (Freerouting, KiCadRoutingTools, OrthoRoute, GPT-5.4
tool-calling agents and a PPO policy):

  CP     clean pass: fully connected and zero error-level DRC violations (the headline)
  Rout.  routability: 1 - open ratsnest edges / open edges on the bare board (0 bare, 1 connected)
  DRV    error-level DRC violations      WL  routed copper, mm      Vias      Time  routing seconds

Every backend's candidate is kept, and "circuit-skills" is the best candidate per board (CP first,
then routability, DRV, vias, length), the way the paper keeps the best of five rollouts. The
designer's own routing is scored too ("reference"; the paper's Reference row has CP 1.00). The
placement score (placement_score.py) of each bare board is recorded next to the outcome, so the
hand-finish-or-re-place diagnosis can be checked against hundreds of real boards.

  python3 evals/pcbworld/run_d3.py --split d3a [--limit N] [--boards ID,...] [--backends LIST]
                                   [--time S] [--jobs N] [--data DIR] [--run NAME]
  python3 evals/pcbworld/run_d3.py --summarize <run>      # rebuild summary.md from per_board.jsonl

Data: build the set once with PCBWorld's own chain (stock KiCad 9 works; see README.md), then point
--data (or PCBWORLD_D3) at its pcbench/exacad_sorted folder. Splits come from the vendored d3.json:
d3a = easy/test (99 boards), d3b = medium/test (10), d3c = hard/test (10); d3a-all / d3b-all /
d3c-all are the full difficulty tiers (100 / 286 / 292). Candidates and logs go to
~/.cache/circuit-skills/pcbworld/runs/<run>/; per_board.jsonl and summary.md go to
evals/pcbworld/results/<run>/. Re-running with the same --run resumes: finished boards are skipped.
"""
import argparse, concurrent.futures as cf, datetime, json, os, shutil, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / 'pcb-layout' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import placement_score  # noqa: E402
import route_eval  # noqa: E402

CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'pcbworld'
DATA = Path(os.getenv('PCBWORLD_D3', CACHE / 'pcbench/exacad_sorted'))
SPLITS = {'d3a': ('easy', 'test'), 'd3b': ('medium', 'test'), 'd3c': ('hard', 'test'),
          'd3a-all': ('easy', 'train'), 'd3b-all': ('medium', 'train'), 'd3c-all': ('hard', 'train')}
STEM = 'processed_v9_guide_v3'
DEFAULT_BACKENDS = 'freerouting,srj:outer,srj:all'

# PCBWorld Table 3 (@5 protocol; Freerouting and RL are 4-seed means). D3-A = 99 boards, D3-B = 10.
PAPER = {
    'd3a': {'Reference': (1.00, 1.00, None), 'Freerouting 2.1.0': (0.80, 0.91, 7.09), 'KiCadRoutingTools': (0.74, 0.94, 0.65),
            'OrthoRoute': (0.02, 0.53, 2.20), 'GPT-5.4 agent': (0.65, 0.91, 231.15), 'GPT-5.4-mini agent': (0.28, 0.72, 56.85),
            'PPO': (0.86, 0.95, 1.83), 'PPO (w/o finish)': (0.94, 0.99, 3.05)},
    'd3b': {'Reference': (1.00, 1.00, None), 'Freerouting 2.1.0': (0.78, 1.00, 9.94), 'KiCadRoutingTools': (0.20, 0.86, 3.27),
            'OrthoRoute': (0.00, 0.44, 9.30), 'GPT-5.4 agent': (0.00, 0.62, 865.83), 'GPT-5.4-mini agent': (0.00, 0.61, 422.06),
            'PPO': (0.45, 0.85, 10.77), 'PPO (w/o finish)': (0.42, 0.87, 14.44)},
}


def board_ids(split, limit=None, only=None):
    d3 = json.loads((HERE / 'd3.json').read_text())
    tier, part = SPLITS[split]
    ids = list(d3[tier][part])
    if only:
        ids = [i for i in ids if any(i.startswith(o) for o in only)]
    return ids[:limit] if limit else ids


def drc(board, out_json):
    """Error-level DRC against the board's own .kicad_pro (beside it), as PCBWorld scores."""
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-error', '--units', 'mm', '-o', str(out_json), str(board)],
                   capture_output=True)
    return json.loads(Path(out_json).read_text())


def pcbworld_row(board, drc_json, u0):
    d = drc_json if isinstance(drc_json, dict) else json.loads(Path(drc_json).read_text())
    drv = len(d.get('violations', []))
    open_edges = len(d.get('unconnected_items', []))
    m = route_eval.metrics(board)
    return {'cp': open_edges == 0 and drv == 0, 'rout': round(max(0.0, 1 - open_edges / u0), 4) if u0 else 1.0,
            'drv': drv, 'open': open_edges, 'wl_mm': m['track_mm'], 'vias': m['vias']}


def select_key(r):
    """Best candidate: clean pass, then routability, DRV, vias, length (the paper keeps the best rollout)."""
    return (not r['cp'], -r['rout'], r['drv'], r['vias'], r['wl_mm'])


def run_board(bid, data, work_root, backends, seconds):
    src = data / bid
    work = work_root / bid
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    pro = src / f'{STEM}.kicad_pro'
    for name, pcb in (('board', f'{STEM}_unrouted.kicad_pcb'), ('reference', f'{STEM}.kicad_pcb')):
        shutil.copy(src / pcb, work / f'{name}.kicad_pcb')
        shutil.copy(pro, work / f'{name}.kicad_pro')
    bare = drc(work / 'board.kicad_pcb', work / 'board.drc.json')
    u0 = len(bare.get('unconnected_items', []))
    row = {'board': bid, 'u0': u0, 'methods': {}}
    ref = pcbworld_row(work / 'reference.kicad_pcb', drc(work / 'reference.kicad_pcb', work / 'reference.drc.json'), u0)
    row['methods']['reference'] = {**ref, 'time_s': None}
    try:
        ps = placement_score.score(str(work / 'board.kicad_pcb'))
        row['placement'] = {'congestion_max': ps['congestion']['max'], 'congestion_p95': ps['congestion']['p95'],
                            'over_capacity_pct': ps['congestion']['over_capacity_pct'], 'hotspots': len(ps['hotspots']),
                            'crossings': ps['ratsnest']['crossings'], 'mst_mm': ps['ratsnest']['mst_mm'], 'signal_nets': ps['signal_nets'],
                            'escape_ratio': max([e['ratio'] or 0 for e in ps['escape']], default=0)}
    except Exception as e:  # the routing result stands without the placement score
        row['placement'] = {'error': str(e)}
    log = work / 'route_eval.log'
    with open(log, 'w') as out:
        subprocess.run([sys.executable, str(SCRIPTS / 'route_eval.py'), str(work / 'board.kicad_pcb'), '--backends', backends, '--time', str(seconds)],
                       stdout=out, stderr=subprocess.STDOUT, cwd=work)
    runs = sorted((work / 'route-evals').glob('2*/results.json'))
    if runs:
        res = json.loads(runs[-1].read_text())
        row['diagnosis'] = res.get('diagnosis', {}).get('recommendation')
        for r in res['results']:
            label = r['backend'].replace(':', '-')
            dj = runs[-1].parent / f'{label}.drc.json'
            if r['ok'] and dj.exists():
                row['methods'][r['backend']] = {**pcbworld_row(r['candidate'], dj, u0), 'time_s': r['route_s']}
            else:
                row['methods'][r['backend']] = {'failed': True, 'exit': r.get('exit'), 'time_s': r.get('route_s')}
    routed = [(k, v) for k, v in row['methods'].items() if k != 'reference' and not v.get('failed')]
    if routed:
        k, v = min(routed, key=lambda kv: select_key(kv[1]))
        row['methods']['circuit-skills'] = {**v, 'from': k, 'time_s': sum(x.get('time_s') or 0 for kk, x in row['methods'].items() if kk != 'reference')}
    return row


# ---- aggregation ---------------------------------------------------------------------------------
def method_stats(rows, method):
    """Paper semantics: a failed or missing candidate counts as not clean, routability 0."""
    got = [r['methods'].get(method, {}) for r in rows]
    ok = [m for m in got if m and not m.get('failed')]
    n = len(rows)
    return {'n': n, 'ran': len(ok),
            'cp': sum(1 for m in ok if m['cp']) / n if n else 0,
            'rout': sum(m['rout'] for m in ok) / n if n else 0,
            'drv': statistics.mean(m['drv'] for m in ok) if ok else None,
            'wl': statistics.mean(m['wl_mm'] for m in ok) if ok else None,
            'vias': statistics.mean(m['vias'] for m in ok) if ok else None,
            'time': statistics.mean(m['time_s'] for m in ok if m.get('time_s') is not None) if any(m.get('time_s') is not None for m in ok) else None}


def auc(scores_pos, scores_neg):
    """P(a failing board scores higher than a clean one); 0.5 = no signal."""
    if not scores_pos or not scores_neg:
        return None
    wins = sum((p > q) + 0.5 * (p == q) for p in scores_pos for q in scores_neg)
    return wins / (len(scores_pos) * len(scores_neg))


def summarize(rows, split, meta):
    fmt = lambda v, f='{:.2f}': '–' if v is None else f.format(v)
    methods = ['reference'] + sorted({k for r in rows for k in r['methods']} - {'reference', 'circuit-skills'}) + ['circuit-skills']
    lines = [f"# PCBWorld {split.upper()} · {meta['run']}", '',
             f"{len(rows)} boards · backends `{meta['backends']}` · {meta['time']} s per backend · {meta['versions']}", '',
             '| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |', '|---|---|---|---|---|---|---|---|']
    for m in methods:
        s = method_stats(rows, m)
        name = {'circuit-skills': '**circuit-skills (best of all backends)**', 'reference': 'reference (designer\'s routing)'}.get(m, m)
        lines.append(f"| {name} | {fmt(s['cp'])} | {fmt(s['rout'])} | {fmt(s['drv'], '{:.1f}')} | {fmt(s['wl'], '{:.0f}')} | {fmt(s['vias'], '{:.1f}')} | {fmt(s['time'], '{:.1f}')} | {s['ran']}/{s['n']} |")
    paper = PAPER.get(split.split('-')[0]) if not split.endswith('-all') else None
    if paper:
        lines += ['', f'PCBWorld paper, Table 3, {split.upper()} (@5: best of five rollouts; Freerouting and PPO are 4-seed means):', '',
                  '| method | CP ↑ | Rout. ↑ | time s |', '|---|---|---|---|']
        lines += [f'| {k} | {v[0]:.2f} | {v[1]:.2f} | {fmt(v[2], "{:.1f}")} |' for k, v in paper.items()]
    wins = {}
    for r in rows:
        best = r['methods'].get('circuit-skills', {})
        if best.get('cp'):
            wins[best['from']] = wins.get(best['from'], 0) + 1
    if wins:
        lines += ['', 'Clean boards by the backend that produced the kept candidate: ' + ', '.join(f'{k} {v}' for k, v in sorted(wins.items(), key=lambda kv: -kv[1]))]
    # Does the placement score see trouble coming? Clean vs not, on the best candidate.
    scored = [r for r in rows if 'error' not in r.get('placement', {}) and 'circuit-skills' in r['methods']]
    if scored:
        bad = [r for r in scored if not r['methods']['circuit-skills']['cp']]
        good = [r for r in scored if r['methods']['circuit-skills']['cp']]
        lines += ['', '## Does the placement score predict it?', '',
                  f'{len(good)} boards came back clean and {len(bad)} did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):', '',
                  '| placement metric (bare board) | AUC | mean, clean | mean, not clean |', '|---|---|---|---|']
        for key in ('congestion_max', 'congestion_p95', 'over_capacity_pct', 'crossings', 'escape_ratio', 'signal_nets', 'mst_mm'):
            a = auc([r['placement'][key] for r in bad], [r['placement'][key] for r in good])
            mg = statistics.mean(r['placement'][key] for r in good) if good else None
            mb = statistics.mean(r['placement'][key] for r in bad) if bad else None
            lines.append(f'| {key} | {fmt(a)} | {fmt(mg)} | {fmt(mb)} |')
        diag = {}
        for r in scored:
            d = (r.get('diagnosis') or 'none').split(' ')[0].split(':')[0]
            diag.setdefault(d, [0, 0])[0 if r['methods']['circuit-skills']['cp'] else 1] += 1
        lines += ['', 'route_eval diagnosis vs outcome: ' + ', '.join(f'{k}: {v[0]} clean / {v[1]} not' for k, v in sorted(diag.items()))]
    lines += ['', '## Boards', '', '| board | u0 | ' + ' | '.join(methods[1:]) + ' |', '|---|---|' + '---|' * (len(methods) - 1)]
    for r in rows:
        cells = []
        for m in methods[1:]:
            v = r['methods'].get(m)
            if not v:
                cells.append('')
            elif v.get('failed'):
                cells.append('failed')
            else:
                cells.append(('✓ ' if v['cp'] else '') + f"{v['rout']:.2f} · {v['drv']} drv" + (f" ({v['from']})" if m == 'circuit-skills' else ''))
        lines.append(f"| {r['board']} | {r['u0']} | " + ' | '.join(cells) + ' |')
    lines += ['', 'Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board\'s own .kicad_pro, single run per backend (the paper reports @5).']
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--split', choices=sorted(SPLITS), default='d3a')
    p.add_argument('--limit', type=int)
    p.add_argument('--boards', help='comma-separated board ids or numeric prefixes (0018,0100)')
    p.add_argument('--backends', default=DEFAULT_BACKENDS, help=f'route_eval backends (default {DEFAULT_BACKENDS})')
    p.add_argument('--time', type=int, default=60, help='per-backend routing limit, seconds (default 60)')
    p.add_argument('--jobs', type=int, default=3, help='boards routed at once (default 3)')
    p.add_argument('--data', type=Path, default=DATA)
    p.add_argument('--run', help='run name (default <split>-<timestamp>); an existing run resumes')
    p.add_argument('--summarize', metavar='RUN', help='only rebuild summary.md for an existing run')
    p.add_argument('--rediagnose', metavar='RUN', help="re-run route_eval's diagnosis on a stored run, then summarize")
    a = p.parse_args()

    if a.rediagnose:  # re-judge stored runs with the current diagnosis, no routing
        out = HERE / 'results' / a.rediagnose
        rows = [json.loads(l) for l in (out / 'per_board.jsonl').read_text().splitlines() if l.strip()]
        for r in rows:
            runs = sorted((CACHE / 'runs' / a.rediagnose / r['board'] / 'route-evals').glob('2*/results.json'))
            if runs:
                res = json.loads(runs[-1].read_text())
                r['diagnosis'] = route_eval.diagnose(runs[-1].parent, res['results'], res['board'])['recommendation']
        (out / 'per_board.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        a.summarize = a.rediagnose
    if a.summarize:
        out = HERE / 'results' / a.summarize
        meta = json.loads((out / 'meta.json').read_text())
        rows = [json.loads(l) for l in (out / 'per_board.jsonl').read_text().splitlines() if l.strip()]
        (out / 'summary.md').write_text(summarize(rows, meta['split'], meta))
        print((out / 'summary.md').read_text())
        return 0
    if not a.data.is_dir():
        p.error(f'no D3 data at {a.data}: build it with PCBWorld\'s tools/quickstart/prepare_pcbench.sh (see evals/pcbworld/README.md)')
    ids = board_ids(a.split, a.limit, a.boards.split(',') if a.boards else None)
    missing = [i for i in ids if not (a.data / i / f'{STEM}_unrouted.kicad_pcb').exists()]
    if missing:
        p.error(f'{len(missing)} board(s) missing under {a.data}, e.g. {missing[0]}')
    run = a.run or f"{a.split}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out, work = HERE / 'results' / run, CACHE / 'runs' / run
    out.mkdir(parents=True, exist_ok=True)
    meta = {'run': run, 'split': a.split, 'backends': a.backends, 'time': a.time, 'data': str(a.data), 'versions': route_eval.versions()}
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    per_board = out / 'per_board.jsonl'
    done = {json.loads(l)['board'] for l in per_board.read_text().splitlines() if l.strip()} if per_board.exists() else set()
    todo = [i for i in ids if i not in done]
    print(f'PCBWorld {a.split}: {len(ids)} boards ({len(done)} done) · {a.backends} · {a.time}s · {a.jobs} at once · {out}', flush=True)
    t0 = time.monotonic()
    with cf.ThreadPoolExecutor(a.jobs) as pool, open(per_board, 'a') as sink:
        futs = {pool.submit(run_board, b, a.data, work, a.backends, a.time): b for b in todo}
        for n, f in enumerate(cf.as_completed(futs), 1):
            b = futs[f]
            try:
                row = f.result()
            except Exception as e:
                row = {'board': b, 'u0': 0, 'methods': {}, 'error': repr(e)}
            sink.write(json.dumps(row) + '\n')
            sink.flush()
            best = row['methods'].get('circuit-skills', {})
            print(f"  [{n}/{len(todo)}] {b[:48]:48s} {'CLEAN' if best.get('cp') else 'open ' + str(best.get('open', '?')) + ' drv ' + str(best.get('drv', '?'))}"
                  f"  ({best.get('from', '-')}, {round(time.monotonic() - t0)}s)", flush=True)
    rows_by = {json.loads(l)['board']: json.loads(l) for l in per_board.read_text().splitlines() if l.strip()}
    rows = [rows_by[i] for i in ids if i in rows_by]
    (out / 'summary.md').write_text(summarize(rows, a.split, meta))
    print('\n' + (out / 'summary.md').read_text().split('## Boards')[0])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
