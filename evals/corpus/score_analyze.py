#!/usr/bin/env python3
"""score_analyze.py — score every placement measure against the routed outcomes of score_study.py route."""
import itertools, json, math, os, re, statistics, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / 'pcb-layout' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import placement_score  # noqa: E402

CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'corpus'
GND = re.compile(r'(^|/)(A|D|P)?(GND|VSS)\w*$', re.I)
FEATS = ['congestion_max', 'congestion_p95', 'over_capacity_pct', 'crossings', 'mst_mm', 'escape_ratio',  # what placement_score reports today
         'crossings_per_net', 'mst_norm', 'overlaps', 'off_board_pads', 'decap_mm', 'placement_drv']       # candidates


def features(board, row):
    s = placement_score.score(str(board))
    b = placement_score.read_board(Path(board).read_text())
    x0, y0, x1, y1 = b['bbox']
    area = max(1e-6, (x1 - x0) * (y1 - y0))
    nets = max(1, s['signal_nets'])
    f = {'congestion_max': s['congestion']['max'], 'congestion_p95': s['congestion']['p95'], 'over_capacity_pct': s['congestion']['over_capacity_pct'],
         'crossings': s['ratsnest']['crossings'], 'mst_mm': s['ratsnest']['mst_mm'], 'escape_ratio': max([e['ratio'] or 0 for e in s['escape']], default=0),
         'crossings_per_net': s['ratsnest']['crossings'] / nets, 'mst_norm': s['ratsnest']['mst_mm'] / (nets * math.sqrt(area)),
         'placement_drv': row.get('placement_drv', 0)}
    # Bodies as pad extents (read_board pads the box by 0.5 mm; take it back off), same side only.
    boxes = [(p['side'], p['bbox'][0] + 0.5, p['bbox'][1] + 0.5, p['bbox'][2] - 0.5, p['bbox'][3] - 0.5) for p in b['parts']]
    f['overlaps'] = sum(1 for a, c in itertools.combinations(boxes, 2)
                        if a[0] == c[0] and min(a[3], c[3]) - max(a[1], c[1]) > 0.05 and min(a[4], c[4]) - max(a[2], c[2]) > 0.05)
    f['off_board_pads'] = sum(1 for p in b['pads'] if p['net'] and not (x0 - 0.1 <= p['x'] <= x1 + 0.1 and y0 - 0.1 <= p['y'] <= y1 + 0.1))
    # Decoupling: a two-pad C with one pad on ground; distance from its other pad to the nearest pad of that net on a part with 6+ pads.
    big = defaultdict(list)
    for part in b['parts']:
        if len(part['pads']) >= 6:
            for pad in part['pads']:
                if pad['net']:
                    big[pad['net']].append((pad['x'], pad['y']))
    d = []
    for part in b['parts']:
        pads = [p for p in part['pads'] if p['net']]
        if part['ref'].startswith('C') and len(part['pads']) == 2 and len(pads) == 2 and sum(bool(GND.search(p['net'])) for p in pads) == 1:
            hot = next(p for p in pads if not GND.search(p['net']))
            if big.get(hot['net']):
                d.append(min(math.dist((hot['x'], hot['y']), q) for q in big[hot['net']]))
    f['decap_mm'] = statistics.mean(d) if d else 0.0
    return f


def auc(pos, neg):
    if not pos or not neg:
        return None
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def main():
    rows = [json.loads(l) for l in (HERE / 'score_study.jsonl').read_text().splitlines()]
    rows = [r for r in rows if not r.get('failed')]
    cache_path = HERE / 'score_features.jsonl'
    cache = {(r['board'], r['variant']): r['f'] for r in map(json.loads, cache_path.read_text().splitlines())} if cache_path.exists() else {}
    with open(cache_path, 'a') as sink:
        for r in rows:
            k = (r['board'], r['variant'])
            if k not in cache:
                try:
                    cache[k] = features(CACHE / 'score_study' / r['board'] / f"{r['variant']}.kicad_pcb", r)
                except (Exception, SystemExit) as e:
                    cache[k] = None
                sink.write(json.dumps({'board': k[0], 'variant': k[1], 'f': cache[k]}) + '\n')
    rows = [{**r, 'f': cache[(r['board'], r['variant'])]} for r in rows if cache.get((r['board'], r['variant']))]
    for r in rows:
        r['f']['placement_drv'] = r.get('placement_drv', 0)
    by_board = defaultdict(list)
    for r in rows:
        by_board[r['board']].append(r)
    # Pairs of placements of the same board whose routed outcome differs: the better one should score lower.
    better = lambda a, c: (a['clean'], a['rout'], -a['drv']) > (c['clean'], c['rout'], -c['drv'])
    pairs = [(a, c) for rs in by_board.values() for a, c in itertools.permutations(rs, 2) if better(a, c) and (a['rout'] - c['rout'] > 0.02 or a['clean'] != c['clean'])]
    out = ['# Which placement measures predict a clean route?', '',
           f"{len(by_board)} corpus boards, {len(rows)} placements, each routed by TraceMaker and judged by KiCad DRC.", '',
           '| placement | n | clean | connections routed | DRC errors before routing |', '|---|---|---|---|---|']
    for v in ['designer', 'swap25', 'swap100', 'pk', 'tm']:
        rs = [r for r in rows if r['variant'] == v]
        if rs:
            out.append(f"| {v} | {len(rs)} | {sum(r['clean'] for r in rs) / len(rs):.2f} | {statistics.mean(r['rout'] for r in rs):.2f} | {statistics.mean(r.get('placement_drv', 0) for r in rs):.1f} |")
    out += ['', f'Lower is better for every measure. **Pairwise**: of {len(pairs)} pairs of placements of the same board with different outcomes, how often the measure ranks the better one lower (0.50 = a coin). '
            '**AUC**: across all placements, the chance a placement that did not route clean scores worse than one that did.', '',
            '| measure | pairwise | AUC | pairwise, legal placements only |', '|---|---|---|---|']
    legal = [(a, c) for a, c in pairs if a['f']['placement_drv'] == 0 and c['f']['placement_drv'] == 0]
    pw = lambda ps, key: (sum((key(c) > key(a)) + 0.5 * (key(c) == key(a)) for a, c in ps) / len(ps)) if ps else None
    fmt = lambda v: '–' if v is None else f'{v:.2f}'
    table = []
    for k in FEATS:
        key = lambda r, k=k: r['f'][k]
        table.append((k, pw(pairs, key), auc([key(r) for r in rows if not r['clean']], [key(r) for r in rows if r['clean']]), pw(legal, key)))
    # A combined score: logistic regression on within-board feature differences, cross-validated by board.
    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import GroupKFold
        # One measure per idea (the raw and normalised forms are collinear), and nothing that needs KiCad's DRC.
        use = ['crossings_per_net', 'mst_norm', 'congestion_max', 'over_capacity_pct', 'overlaps', 'off_board_pads', 'decap_mm']
        y = np.array([1] * len(pairs) + [0] * len(pairs))
        groups = np.array([a['board'] for a, c in pairs] * 2)
        dropped = []
        while True:  # every measure is "lower is better": one the fit wants to reward is dropped, not kept with a negative weight
            logt = lambda r: np.array([math.log1p(max(0.0, r['f'][k])) for k in use])
            X = np.array([logt(c) - logt(a) for a, c in pairs] + [logt(a) - logt(c) for a, c in pairs])
            m = LogisticRegression(fit_intercept=False, C=1.0, max_iter=2000).fit(X, y)
            w = dict(zip(use, m.coef_[0]))
            worst = min(w, key=w.get)
            if w[worst] >= 0:
                break
            dropped.append(worst)
            use = [k for k in use if k != worst]
        accs = []
        for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
            accs.append(LogisticRegression(fit_intercept=False, C=1.0, max_iter=2000).fit(X[tr], y[tr]).score(X[te], y[te]))
        comb = lambda r: float(sum(w[k] * math.log1p(max(0.0, r['f'][k])) for k in use))
        table.append(('**combined (fit on all)**', pw(pairs, comb), auc([comb(r) for r in rows if not r['clean']], [comb(r) for r in rows if r['clean']]), pw(legal, comb)))
        extra = ['', f"Combined score: logistic regression on log(1 + measure) differences between two placements of a board. Held-out pairwise accuracy, 5 folds split by board: **{statistics.mean(accs):.2f}** (folds {', '.join(f'{x:.2f}' for x in accs)}).",
                 '', (f"Dropped because the fit gave them a negative weight (it would reward a worse value): {', '.join(dropped)}. " if dropped else '') +
                 'Weights (per unit of log(1 + measure); positive = worse): ' + ', '.join(f'{k} {v:+.2f}' for k, v in sorted(w.items(), key=lambda kv: -abs(kv[1])))]
        (HERE / 'score_weights.json').write_text(json.dumps({'transform': 'log1p', 'weights': {k: round(float(v), 4) for k, v in w.items()}, 'pairs': len(pairs), 'boards': len(by_board), 'cv_pairwise': round(statistics.mean(accs), 3)}, indent=1) + '\n')
    except ImportError:
        extra = ['', '(sklearn not available: no combined score)']
    out += [f'| {k} | {fmt(a)} | {fmt(b)} | {fmt(c)} |' for k, a, b, c in sorted(table, key=lambda t: -(t[1] or 0))]
    out += extra + ['', f'{len(legal)} of the pairs are between two placements with no DRC errors before routing.']
    (HERE / 'score_study.md').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
