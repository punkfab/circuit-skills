#!/usr/bin/env python3
"""hints_analyze.py — what do placement hints buy? Reads hints_study.jsonl (score_study.py route --rows hints_study.jsonl
--variants designer,pk2,h1,h2,h3) and the placed boards in the cache; writes hints_study.md."""
import json, math, os, re, statistics, subprocess, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / 'pcb-layout' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import placement_score  # noqa: E402
CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'corpus' / 'score_study'
NAMES = {'designer': "designer's placement", 'pk2': 'no hints', 'h1': 'level 1: anchors (edges and regions)', 'h2': 'level 2: + relations between big parts', 'h3': 'level 3: + small parts near their big part'}


def main():
    rows = [json.loads(l) for l in (HERE / 'hints_study.jsonl').read_text().splitlines()]
    by = defaultdict(dict)
    for r in rows:
        by[r['board']][r['variant']] = r
    full = {b: v for b, v in by.items() if all(k in v and not v[k].get('failed') for k in NAMES)}
    feats = {}
    for b in full:
        ref = placement_score.read_board((CACHE / b / 'designer.kicad_pcb').read_text())
        where = {p['ref']: (p['x'], p['y']) for p in ref['parts']}
        big = {p['ref'] for p in ref['parts'] if len(p['pads']) >= 8}
        diag = math.dist(ref['bbox'][:2], ref['bbox'][2:])
        for v in NAMES:
            f = CACHE / b / f'{v}.kicad_pcb'
            s = placement_score.score(str(f))
            got = {p['ref']: (p['x'], p['y']) for p in placement_score.read_board(f.read_text())['parts']}
            d = [math.dist(got[r], where[r]) / diag for r in big if r in got]
            log = CACHE / b / f'{v}.place.log'
            m = re.search(r'hints (\d+)/(\d+) met', log.read_text()) if log.exists() else None
            feats[(b, v)] = {'compare': s['compare']['score'], 'wire': s['ratsnest']['mst_mm'], 'crossings': s['ratsnest']['crossings'],
                             'moved': statistics.mean(d) if d else None, 'hints': int(m.group(2)) if m else 0, 'met': int(m.group(1)) if m else 0}
    n = len(full)
    mean = lambda xs: statistics.mean(xs) if xs else float('nan')
    out = ['# What do placement hints buy?', '',
           f"{n} corpus boards. Hints are derived from each designer's placement at three levels of detail (place_hints.py derive), every part is then placed from "
           'scratch by place_kicad.py, routed by TraceMaker (20 s) and judged by KiCad DRC.', '',
           '| placement | clean | connections routed | DRC errors before routing | hints per board (met) | big parts: distance from the designer | wire vs designer | crossings vs designer | compare score beats no-hints |',
           '|---|---|---|---|---|---|---|---|---|']
    for v, name in NAMES.items():
        rs = [full[b][v] for b in full]
        fs = [feats[(b, v)] for b in full]
        ref = [feats[(b, 'designer')] for b in full]
        base = [feats[(b, 'pk2')] for b in full]
        moved = [f['moved'] for f in fs if f['moved'] is not None]
        hints = f"{mean([f['hints'] for f in fs]):.0f} ({100 * sum(f['met'] for f in fs) / max(1, sum(f['hints'] for f in fs)):.0f}%)" if any(f['hints'] for f in fs) else '–'
        out.append(f"| {name} | {mean([r['clean'] for r in rs]):.2f} | {mean([r['rout'] for r in rs]):.3f} | {mean([r.get('placement_drv', 0) for r in rs]):.1f} | {hints} | "
                   f"{100 * mean(moved):.0f}% of the board diagonal | {statistics.median(f['wire'] / max(1e-6, g['wire']) for f, g in zip(fs, ref)):.2f}x | "
                   f"{statistics.median((f['crossings'] + 1) / (g['crossings'] + 1) for f, g in zip(fs, ref)):.2f}x | "
                   + ('–' if v == 'pk2' else f"{sum(f['compare'] < g['compare'] for f, g in zip(fs, base))}/{n}") + ' |')
    out += ['', '"Distance from the designer": how far each part with 8 or more pads ends up from where the designer put it, as a share of the board diagonal. '
            '"Wire" and "crossings": ratsnest length and crossings relative to the designer\'s placement (median over boards; below 1 is shorter or fewer). '
            '"Compare score": placement_score.py\'s fitted score; the count is boards where the hinted placement scores better than the unhinted one.']
    (HERE / 'hints_study.md').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
