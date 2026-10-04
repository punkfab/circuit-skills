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
the gates are applied identically; the project itself is not touched. A bare .kicad_pcb (any KiCad
board, e.g. the PCBWorld benchmark in evals/pcbworld) can use srj, current, and freerouting/fastroute
through KiCad's own Specctra export and import (route_kicad_dsn.py); tscircuit needs the project. Each candidate is scored with KiCad DRC (the project's rules, JLCPCB if none),
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


def score(board, workdir, label=None):
    board = Path(board)
    pro = board.with_suffix('.kicad_pro')
    if not pro.exists():
        # No rules beside it: score against JLCPCB minimums like every other candidate.
        src = next(iter(sorted(board.parent.glob('*.kicad_pro'))), None)
        if src:
            shutil.copy(src, pro)
        subprocess.run([sys.executable, str(HERE / 'apply_fab_rules.py'), str(pro), '--fab', 'jlcpcb'], capture_output=True)
    drc_json = Path(workdir) / f'{label or board.stem}.drc.json'  # one per candidate: project candidates share a file name
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
    name, _, opt = backend.partition(':')
    out = work / f'{backend.replace(":", "-")}.kicad_pcb'
    if name in ('freerouting', 'fastroute'):
        # KiCad's own Specctra export/import: works on any KiCad board, not just tscircuit DSNs.
        py = os.getenv('CIRCUIT_SKILLS_KICAD_PYTHON', '/usr/bin/python3')
        cmd = [py, str(HERE / 'route_kicad_dsn.py'), str(board), '-o', str(out), '--backend', name, '--time', str(seconds)]
    else:
        cmd = ['node', str(HERE / 'route_srj.mjs'), str(board), '-o', str(out), '--layers', opt or 'auto', '--time', str(seconds)]
    code, secs = run(cmd, work, work / f'{backend.replace(":", "-")}.log', timeout=seconds + 300)
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



# ---- diagnosis: hand-finish or re-place? --------------------------------------------------------
DEFECT_TYPES = SHORT | CLEAR | SIZE


def defect_points(drc_json):
    """Positions of a candidate's blocking and fab defects (first item of each)."""
    try:
        d = json.loads(Path(drc_json).read_text())
    except (OSError, ValueError):
        return []
    pts = [(v['type'], v['items'][0]['pos']['x'], v['items'][0]['pos']['y']) for v in d.get('violations', []) if v['type'] in DEFECT_TYPES and v.get('items')]
    pts += [('unconnected', u['items'][0]['pos']['x'], u['items'][0]['pos']['y']) for u in d.get('unconnected_items', []) if u.get('items')]
    return pts


def diagnose(run_dir, results, board, hand_max=10, region_mm=3.0):
    """Placement score + where each candidate fails -> a recommendation.

    Two signals decide it. (1) Agreement: regions where most routers fail point at the placement;
    routers failing in different places is router luck. (2) Congestion: defects in the placement's
    hot cells (top decile of RUDY) point at the placement too. A best candidate with few defects
    outside both is worth finishing by hand."""
    sys.path.insert(0, str(HERE))
    import placement_score
    ps = placement_score.score(str(board))
    g, cell = ps['grid'], ps['cell_mm']
    hot = ps['congestion']['hot_threshold']
    pads = placement_score.read_board(Path(board).read_text())['pads']

    def util(x, y):
        i, j = int((x - g['x0']) / cell), int((y - g['y0']) / cell)
        return g['util'][j][i] if 0 <= i < g['nx'] and 0 <= j < g['ny'] else 0.0

    routed = [r for r in results if r['ok'] and r['backend'] != 'current']
    per = {}
    regions = {}
    for r in routed:
        label = r['backend'].replace(':', '-')
        pts = defect_points(Path(run_dir) / f'{label}.drc.json')
        per[r['backend']] = pts
        for _, x, y in pts:
            regions.setdefault((int(x // region_mm), int(y // region_mm)), set()).add(r['backend'])
    need = max(2, -(-len(routed) // 2))  # at least half the routers, and at least two
    agree = []
    for (i, j), who in regions.items():
        if len(who) >= need:
            x0, y0 = i * region_mm, j * region_mm
            parts = sorted({p['ref'] for p in pads if x0 - 1 <= p['x'] <= x0 + region_mm + 1 and y0 - 1 <= p['y'] <= y0 + region_mm + 1})
            agree.append({'at': [x0, y0, x0 + region_mm, y0 + region_mm], 'routers': len(who), 'hot': util(x0 + region_mm / 2, y0 + region_mm / 2) >= hot or any(util(x0 + a, y0 + b) >= hot for a in (0.5, 1.5, 2.5) for b in (0.5, 1.5, 2.5)), 'parts': parts})
    agree.sort(key=lambda a: (-a['routers'], -a['hot']))

    best = next((r for r in sorted(routed, key=lambda r: rank_key(r['score']))), None)
    out = {'placement': {k: ps[k] for k in ('congestion', 'ratsnest', 'escape', 'hotspots', 'routing_layers', 'plane_nets')},
           'agreement_regions': agree, 'hand_max': hand_max}
    if not best:
        out['recommendation'] = 're-place: no router produced a candidate'
        return out
    b = best['score']
    pts = per.get(best['backend'], [])
    in_hot = sum(1 for _, x, y in pts if util(x, y) >= hot)
    blocking = b['shorts'] + b['unconnected'] + b['dfm_actionable'] + b['floating'] + b['size_violations']
    remaining = blocking + b['clearance']
    hot_share = in_hot / len(pts) if pts else 0.0
    hot_agree = [a for a in agree if a['hot']]
    out.update(best=best['backend'], remaining=remaining, defects_in_hot_cells=round(hot_share, 2))
    if remaining == 0:
        rec = f"order-ready candidate: {best['backend']} passes every gate; review it and run check_board before ordering"
    elif remaining <= hand_max and not (hot_agree and hot_share >= 0.5):
        rec = f"hand-finish {best['backend']}: {remaining} item(s), {round(100 * hot_share)}% in congested cells, no placement hotspot that most routers fail in"
    else:
        parts = sorted({p for a in (hot_agree or agree)[:4] for p in a['parts']})
        hs = '; '.join(f"{', '.join(h['parts'][:6])}" for h in ps['hotspots'][:3])
        rec = (f"re-place before finishing: {remaining} item(s) left on the best candidate ({best['backend']}), "
               f"{round(100 * hot_share)}% of them in congested cells"
               + (f"; {len(hot_agree)} region(s) where {need}+ of {len(routed)} routers fail in a hotspot, around {', '.join(parts[:12])}" if hot_agree else '')
               + (f". Placement hotspots: {hs}" if hs else '')
               + ". Give those parts room (spread, rotate, move decoupling off the escape) and re-run.")
    out['recommendation'] = rec
    return out


def write_diagnosis(run_dir, diag):
    lines = ['', '## Hand-finish or re-place?', '', f"**{diag['recommendation']}**", '']
    c = diag['placement']['congestion']
    lines.append(f"Placement: congestion peak {c['max']}, hot cells {c['hot_cells']} (>= {c['hot_threshold']}), ratsnest {diag['placement']['ratsnest']['mst_mm']} mm with {diag['placement']['ratsnest']['crossings']} crossings.")
    for h in diag['placement']['hotspots'][:5]:
        lines.append(f"- hotspot (peak {h['peak']}, {h['cells']} cells) at {h['box']}: {', '.join(h['parts'][:10])}")
    if diag['agreement_regions']:
        lines += ['', 'Where most routers fail (3 mm regions):']
        for a in diag['agreement_regions'][:8]:
            lines.append(f"- {a['routers']} routers at {a['at']}{' (hot)' if a['hot'] else ''}: {', '.join(a['parts'][:10])}")
    with open(Path(run_dir) / 'summary.md', 'a') as f:
        f.write('\n'.join(lines) + '\n')
    res = json.loads((Path(run_dir) / 'results.json').read_text())
    res['diagnosis'] = diag
    (Path(run_dir) / 'results.json').write_text(json.dumps(res, indent=1) + '\n')

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('target', type=Path, help='project dir or board; with --analyze, a route-evals/<run> folder')
    p.add_argument('--backends', help='comma-separated; default: every available one')
    p.add_argument('--time', type=int, default=int(os.getenv('MAXT', '300')), help='per-backend routing limit, seconds')
    p.add_argument('--apply', action='store_true', help='copy the best candidate over the board')
    p.add_argument('--analyze', action='store_true', help='diagnose an existing run folder: hand-finish or re-place?')
    p.add_argument('--hand-max', type=int, default=10, help='most remaining items still worth finishing by hand (default 10)')
    a = p.parse_args()

    target = a.target.expanduser().resolve()
    if a.analyze:
        res = json.loads((target / 'results.json').read_text())
        diag = diagnose(target, res['results'], res['board'], a.hand_max)
        write_diagnosis(target, diag)
        print(diag['recommendation'])
        return 0
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
        bare = ('srj', 'current', 'freerouting', 'fastroute')
        dropped = [b for b in backends if b.split(':')[0] not in bare]
        if dropped:
            print(f'(a bare board cannot use {", ".join(dropped)}: it needs the tscircuit project; skipping)')
        backends = [b for b in backends if b.split(':')[0] in bare]

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
        s = score(cand, work, backend.replace(':', '-')) if code == 0 and cand.exists() else None
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
    if sum(1 for r in results if r['ok'] and r['backend'] != 'current') >= 1:
        try:
            diag = diagnose(work, ranked, board, a.hand_max)
            write_diagnosis(work, diag)
            print(f"\n{diag['recommendation']}")
        except Exception as e:  # the ranking stands without the diagnosis
            print(f'\n(diagnosis skipped: {e})')
    if best:
        print(f'\nbest: {best["backend"]} -> {best["candidate"]}')
        if a.apply and best['backend'] != 'current':
            shutil.copy(board, work / 'previous.kicad_pcb')
            shutil.copy(best['candidate'], board)
            print(f'applied: {board} (previous board kept as {work / "previous.kicad_pcb"})')
    return 0 if best else 1


if __name__ == '__main__':
    raise SystemExit(main())
