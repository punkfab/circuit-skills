#!/usr/bin/env python3
"""route_eval.py — route one board with every available backend, score every candidate the same
way, rank them, and keep the results so approaches can be compared run after run.

  python3 route_eval.py <project dir | board.kicad_pcb> [--backends LIST] [--time S] [--apply]

Backends (default: every one available here):
  freerouting           route4.sh with Freerouting (needs freert224 / FREERT)
  fastroute             route4.sh with FastRoute (needs FASTROUTE_BIN)
  tscircuit[:PRESET]    route4.sh with the design's own tscircuit router (default preset auto_local)
  srj[:all|outer|auto]  route_srj.mjs: tscircuit's capacity autorouter on the KiCad board itself
  current               the board as it is now (a baseline, never re-routed)

A project directory (index.circuit.tsx + node_modules) runs the full route4.sh pipeline per backend
in its own copy of the project (node_modules linked, this skill's scripts), so planes, fab rules and
the gates are applied identically; the project itself is not touched. A bare .kicad_pcb can only use
srj and current. Each candidate is scored with KiCad DRC (the project's rules, JLCPCB if none),
dfm_check, check_floating, critical routing when a policy exists, and routing metrics, then ranked:

  shorts+crossings, open nets, DFM actionable, floating pads, size violations (track width, via,
  drill, annular), clearance + hole clearance, vias, track length    (lower is better, in order)

Results go to <project>/route-evals/<run>/ (candidates, logs, results.json, summary.md) and one
line per candidate is appended to <project>/route-evals/history.jsonl. --apply copies the best
candidate over the project's board (the previous board is kept in the run folder).
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKIP_COPY = {'node_modules', 'build', 'dist', 'fab', 'renders', 'route-evals', '.git', 'results'}
SIZE = {'track_width', 'via_diameter', 'drill_out_of_range', 'annular_width'}
CLEAR = {'clearance', 'hole_clearance', 'copper_edge_clearance', 'hole_to_hole'}
SHORT = {'shorting_items', 'tracks_crossing'}


def which(cmd):
    return shutil.which(cmd) is not None


def available():
    found = ['current']
    if os.getenv('FREERT') or Path.home().joinpath('.local/bin/freert224').exists():
        found.append('freerouting')
    if os.getenv('FASTROUTE_BIN') or which('fastroute'):
        found.append('fastroute')
    found.append('tscircuit:auto_local')
    srj = Path(os.getenv('CAPACITY_AUTOROUTER') or HERE / 'srj') / 'node_modules' / '@tscircuit' / 'capacity-autorouter'
    if srj.exists():
        found += ['srj:all', 'srj:outer']
    return found


def run(cmd, cwd, log, env=None, timeout=None):
    t0 = time.monotonic()
    with open(log, 'w') as out:
        try:
            code = subprocess.run(cmd, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, env={**os.environ, **(env or {})}, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = -9
    return code, round(time.monotonic() - t0, 1)


# ---- scoring ------------------------------------------------------------------------------
def metrics(board):
    text = Path(board).read_text()
    nets = {m.group(1): m.group(2) for m in re.finditer(r'\(net (\d+) "([^"]*)"\)', text)}
    zone_nets = set(re.findall(r'\(zone\s*\(net \d+\)\s*\(net_name "([^"]+)"', text))
    total = zone = 0.0
    segs = 0
    for m in re.finditer(r'\(segment\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\)[\s\S]*?\(net (\d+)\)', text):
        x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4))
        d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        total += d
        segs += 1
        if nets.get(m.group(5)) in zone_nets:
            zone += d
    vias = len(re.findall(r'\(via\b', text))
    return {'track_mm': round(total, 1), 'segments': segs, 'vias': vias, 'plane_net_track_mm': round(zone, 1)}


def score(board, workdir):
    board = Path(board)
    pro = board.with_suffix('.kicad_pro')
    if not pro.exists():
        # No rules beside it: score against JLCPCB minimums like every other candidate.
        src = next(iter(sorted(board.parent.glob('*.kicad_pro'))), None)
        if src:
            shutil.copy(src, pro)
        subprocess.run([sys.executable, str(HERE / 'apply_fab_rules.py'), str(pro), '--fab', 'jlcpcb'], capture_output=True)
    drc_json = Path(workdir) / (board.stem + '.drc.json')
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--severity-error', '--units', 'mm', '-o', str(drc_json), str(board)], capture_output=True)
    drc = json.loads(drc_json.read_text()) if drc_json.exists() else {'violations': [], 'unconnected_items': []}
    counts = Counter(v['type'] for v in drc.get('violations', []))
    dfm = subprocess.run([sys.executable, str(HERE / 'dfm_check.py'), str(board)], capture_output=True, text=True).stdout
    dfm_actionable = sum(int(n) for n in re.findall(r'ACTIONABLE[^:]*:\s*(\d+)', dfm))
    flo = subprocess.run([sys.executable, str(HERE / 'check_floating.py'), str(board)], capture_output=True, text=True)
    floating = 0 if flo.returncode == 0 else max(1, len(re.findall(r'^\s+\S+\.\S+', flo.stdout, re.M)))
    s = {
        'shorts': sum(counts[k] for k in SHORT),
        'unconnected': len(drc.get('unconnected_items', [])),
        'dfm_actionable': dfm_actionable,
        'floating': floating,
        'size_violations': sum(counts[k] for k in SIZE),
        'clearance': sum(counts[k] for k in CLEAR),
        'drc': dict(counts),
        **metrics(board),
    }
    policy = Path(str(board)[:-len('.kicad_pcb')] + '.routing-policy.json')
    if policy.exists():
        py = os.getenv('CIRCUIT_SKILLS_KICAD_PYTHON', '/usr/bin/python3')
        s['critical_routing_ok'] = subprocess.run([py, str(HERE / 'check_critical_routing.py'), str(board)], capture_output=True).returncode == 0
    s['clean'] = s['shorts'] == 0 and s['unconnected'] == 0 and s['dfm_actionable'] == 0 and s['floating'] == 0 and s['size_violations'] == 0 and s['clearance'] == 0
    return s


def rank_key(s):
    if s is None:
        return (float('inf'),)
    return (s['shorts'], s['unconnected'], s['dfm_actionable'], s['floating'], s['size_violations'], s['clearance'], s['vias'], s['track_mm'])


# ---- running a backend ---------------------------------------------------------------------
def project_copy(project, dest):
    dest.mkdir(parents=True)
    for item in project.iterdir():
        if item.name in SKIP_COPY or item.name.endswith('.lck') or item.name.startswith('~'):
            continue
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, dest / item.name, **({'symlinks': True} if item.is_dir() else {}))
    if (project / 'node_modules').exists():
        (dest / 'node_modules').symlink_to(project / 'node_modules')
    if (dest / 'scripts').exists():
        shutil.rmtree(dest / 'scripts')
    shutil.copytree(HERE, dest / 'scripts', ignore=shutil.ignore_patterns('node_modules', '__pycache__'), symlinks=True)
    srj_modules = HERE / 'srj' / 'node_modules'
    if srj_modules.exists():
        (dest / 'scripts' / 'srj' / 'node_modules').symlink_to(srj_modules)


def route_project(project, backend, work, seconds):
    """route4.sh in a copy of the project; returns (board, code, seconds)."""
    name, _, opt = backend.partition(':')
    copy = work / backend.replace(':', '-')
    project_copy(project, copy)
    env = {'MAXT': str(seconds), 'DISPLAY': os.environ.get('DISPLAY', ':0')}
    if name == 'tscircuit':
        env.update(ROUTER='tscircuit', TSCIRCUIT_AUTOROUTER=opt or 'auto_local')
    elif name == 'srj':
        env.update(ROUTER='srj', SRJ_LAYERS=opt or 'auto')
    else:
        env.update(ROUTER=name)
    code, secs = run(['bash', 'scripts/route4.sh'], copy, work / f'{backend.replace(":", "-")}.log', env, timeout=seconds * 3 + 300)
    return copy / 'index.circuit.kicad_pcb', code, secs


def route_board(board, backend, work, seconds):
    _, _, opt = backend.partition(':')
    out = work / f'{backend.replace(":", "-")}.kicad_pcb'
    code, secs = run(['node', str(HERE / 'route_srj.mjs'), str(board), '-o', str(out), '--layers', opt or 'auto', '--time', str(seconds)],
                     work, work / f'{backend.replace(":", "-")}.log', timeout=seconds + 300)
    pro = board.with_suffix('.kicad_pro')
    if pro.exists() and out.exists():
        shutil.copy(pro, out.with_suffix('.kicad_pro'))
    return out, code, secs


def versions():
    v = {}
    try:
        v['circuit_skills'] = subprocess.run(['git', '-C', str(HERE), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except OSError:
        pass
    pkg = HERE / 'srj' / 'node_modules' / '@tscircuit' / 'capacity-autorouter' / 'package.json'
    if pkg.exists():
        v['capacity_autorouter'] = json.loads(pkg.read_text())['version']
    return v


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('target', type=Path)
    p.add_argument('--backends', help='comma-separated; default: every available one')
    p.add_argument('--time', type=int, default=int(os.getenv('MAXT', '300')), help='per-backend routing limit, seconds')
    p.add_argument('--apply', action='store_true', help='copy the best candidate over the board')
    a = p.parse_args()

    target = a.target.expanduser().resolve()
    if target.is_dir():
        project = target if (target / 'index.circuit.tsx').exists() else target / 'pcb'
        board = project / 'index.circuit.kicad_pcb'
        is_project = (project / 'index.circuit.tsx').exists()
    else:
        board, project, is_project = target, target.parent, False
    if not board.exists():
        p.error(f'no board at {board}')
    backends = a.backends.split(',') if a.backends else available()
    if not is_project:
        dropped = [b for b in backends if b.split(':')[0] not in ('srj', 'current')]
        if dropped:
            print(f'(a bare board can only use srj and current; skipping {", ".join(dropped)})')
        backends = [b for b in backends if b.split(':')[0] in ('srj', 'current')]

    run_id = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    evals = project / 'route-evals'
    work = evals / run_id
    work.mkdir(parents=True)
    print(f'route_eval: {board} · {", ".join(backends)} · results in {work}')
    results = []
    for backend in backends:
        t0 = time.monotonic()
        if backend == 'current':
            cand = work / 'current.kicad_pcb'
            shutil.copy(board, cand)
            if board.with_suffix('.kicad_pro').exists():
                shutil.copy(board.with_suffix('.kicad_pro'), cand.with_suffix('.kicad_pro'))
            code, secs = 0, 0.0
        elif is_project:
            cand, code, secs = route_project(project, backend, work, a.time)
        else:
            cand, code, secs = route_board(board, backend, work, a.time)
        s = score(cand, work) if code == 0 and cand.exists() else None
        r = {'backend': backend, 'ok': s is not None, 'exit': code, 'route_s': secs, 'candidate': str(cand) if s else None, 'score': s}
        results.append(r)
        brief = 'failed (see log)' if s is None else f"shorts {s['shorts']} · open {s['unconnected']} · dfm {s['dfm_actionable']} · size {s['size_violations']} · clearance {s['clearance']} · vias {s['vias']} · {s['track_mm']} mm"
        print(f'  {backend:22s} {brief}  ({round(time.monotonic() - t0)}s)')

    ranked = sorted(results, key=lambda r: rank_key(r['score']))
    for i, r in enumerate(ranked, 1):
        r['rank'] = i
    best = ranked[0] if ranked and ranked[0]['ok'] else None
    meta = {'run': run_id, 'board': str(board), 'project': is_project, 'time_limit_s': a.time, 'versions': versions(), 'best': best['backend'] if best else None}
    (work / 'results.json').write_text(json.dumps({**meta, 'results': ranked}, indent=1) + '\n')

    lines = [f'# Route eval {run_id}', '', f'Board: `{board}`  ', f'Versions: {meta["versions"]}', '',
             '| # | backend | shorts | open | DFM | floating | size | clearance | vias | track mm | plane-net mm | route s |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in ranked:
        s = r['score']
        if s is None:
            lines.append(f"| {r['rank']} | {r['backend']} | failed (exit {r['exit']}) | | | | | | | | | {r['route_s']} |")
        else:
            lines.append(f"| {r['rank']} | {r['backend']}{' ✓' if s['clean'] else ''} | {s['shorts']} | {s['unconnected']} | {s['dfm_actionable']} | {s['floating']} | {s['size_violations']} | {s['clearance']} | {s['vias']} | {s['track_mm']} | {s['plane_net_track_mm']} | {r['route_s']} |")
    lines += ['', 'Ranked by shorts+crossings, open nets, DFM actionable, floating pads, size violations, clearance, vias, track length. ✓ = no blocking or fab issue at all.']
    (work / 'summary.md').write_text('\n'.join(lines) + '\n')
    with open(evals / 'history.jsonl', 'a') as h:
        for r in ranked:
            h.write(json.dumps({**meta, **r}) + '\n')

    print('\n'.join(lines[6:]))
    if best:
        print(f'\nbest: {best["backend"]} -> {best["candidate"]}')
        if a.apply and best['backend'] != 'current':
            shutil.copy(board, work / 'previous.kicad_pcb')
            shutil.copy(best['candidate'], board)
            print(f'applied: {board} (previous board kept as {work / "previous.kicad_pcb"})')
    return 0 if best else 1


if __name__ == '__main__':
    raise SystemExit(main())
