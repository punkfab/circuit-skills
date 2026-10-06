#!/usr/bin/env python3
"""place_hints.py — the placement-hint language: parse it, and derive it from an existing placement.

A hint says roughly where a part goes, the way you would say it to someone at a whiteboard. The model is
reladraw's (github.com/reladraw/reladraw): positions are relative, there are no coordinates, and a gap is
a minimum. Hints are soft: the placer weighs them against wirelength and reports the ones it did not meet.

    # comments start with a hash
    group psu: U4 L1 C5 C6          # keep these together; the name can be used like a part
    U1    center                    # a region: center, top, bottom, left, right, top-left, ... bottom-right
    J1    on edge left              # against that board edge
    psu   bottom-left
    U2    right of U1  level with U1
    U3    below U1 and U2  gap: wide      # several targets: against the box around them
    C1    near U1.7  within: 2      # a pad; within is edge-to-edge mm (default 2)
    Y1    near U1    weight: 3      # this one matters three times as much
    J2    rotate 90                 # pin the rotation
    R1, R2  above U5  column with U5

  directions   left of, right of, above, below (as seen from the top, like the board on screen)
  alignment    level with T (same row), column with T (same column)
  gaps         gap: none | tight | normal | wide | <mm>     (0, 0.5, 1.5, 4 mm; a minimum, edge to edge)

  python3 place_hints.py derive board.kicad_pcb [--level 1|2|3] > board.hints     # needs pcbnew
      1  anchors only: every part that sits against a board edge, on that edge; big parts (8+ pads) in
         their region of the board
      2  + how the big parts sit relative to each other (left of / below / level with)
      3  + each small part "near" the big part it sits beside
"""
import math, re, sys

REGIONS = {'center', 'top', 'bottom', 'left', 'right', 'top-left', 'top-right', 'bottom-left', 'bottom-right'}
GAPS = {'none': 0.0, 'tight': 0.5, 'normal': 1.5, 'wide': 4.0}


class HintError(ValueError):
    pass


def parse(text, refs, pads=None):
    """-> hints for place_kicad.mjs. refs: {reference: part index}; pads: {reference: {pad number: [dx, dy]}}."""
    groups, hints = {}, []

    def parts_of(name, line):
        if name in groups:
            return groups[name]
        if name in refs:
            return [refs[name]]
        raise HintError(f'line {line}: no part or group named {name}')

    def target(tokens, line):
        names = [t.rstrip(',') for t in tokens if t != 'and']
        if len(names) == 1 and '.' in names[0] and names[0] not in refs:
            ref, pad = names[0].rsplit('.', 1)
            if ref not in refs or pad not in (pads or {}).get(ref, {}):
                raise HintError(f'line {line}: no pad {names[0]}')
            return {'pad': [refs[ref], pads[ref][pad]]}
        return {'parts': sorted({i for n in names for i in parts_of(n, line)})}

    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        m = re.match(r'group\s+([\w.-]+)\s*:\s*(.+)$', line)
        if m:
            groups[m.group(1)] = sorted({i for n in re.split(r'[\s,]+', m.group(2).strip()) for i in parts_of(n, ln)})
            hints.append({'kind': 'group', 'parts': groups[m.group(1)], 'text': line})
            continue
        tok = re.sub(r':\s+', ':', line).split()
        subj, more = [], True
        while tok and more:  # "R1, R2 above U5": subjects run on while each ends in a comma
            more = tok[0].endswith(',')
            subj.append(tok.pop(0).rstrip(','))
        parts = sorted({i for n in subj for i in parts_of(n, ln)})
        clauses, i = [], 0
        while i < len(tok):
            t = tok[i]
            take = lambda j: next((k for k in range(j, len(tok)) if tok[k] in ('left', 'right', 'above', 'below', 'level', 'column', 'near', 'on', 'rotate') or ':' in tok[k] or tok[k] in REGIONS), len(tok))
            if t in ('left', 'right') and i + 1 < len(tok) and tok[i + 1] == 'of':
                j = take(i + 2); clauses.append({'kind': 'dir', 'arg': t, 'target': target(tok[i + 2:j], ln)}); i = j
            elif t in ('above', 'below'):
                s = i + 2 if i + 1 < len(tok) and tok[i + 1] == 'of' else i + 1
                j = take(s); clauses.append({'kind': 'dir', 'arg': t, 'target': target(tok[s:j], ln)}); i = j
            elif t in ('level', 'column') and i + 1 < len(tok) and tok[i + 1] == 'with':
                j = take(i + 2); clauses.append({'kind': 'level', 'arg': 'y' if t == 'level' else 'x', 'target': target(tok[i + 2:j], ln)}); i = j
            elif t == 'near':
                j = take(i + 1); clauses.append({'kind': 'near', 'target': target(tok[i + 1:j], ln)}); i = j
            elif t == 'on' and tok[i + 1:i + 2] == ['edge'] and tok[i + 2:i + 3] and tok[i + 2] in ('left', 'right', 'top', 'bottom'):
                clauses.append({'kind': 'edge', 'arg': tok[i + 2]}); i += 3
            elif t == 'rotate' and tok[i + 1:i + 2] and tok[i + 1] in ('0', '90', '180', '270'):
                clauses.append({'kind': 'rotate', 'arg': int(tok[i + 1])}); i += 2
            elif t in REGIONS:
                clauses.append({'kind': 'region', 'arg': t}); i += 1
            elif t.startswith(('gap:', 'within:')) and clauses:
                v = t.split(':', 1)[1]
                if v not in GAPS and not re.fullmatch(r'\d+(\.\d+)?', v):
                    raise HintError(f'line {ln}: {t}: use none, tight, normal, wide or a number of mm')
                clauses[-1]['gap'] = GAPS.get(v, None) if v in GAPS else float(v); i += 1
            elif t.startswith('weight:'):
                for c in clauses:
                    c['weight'] = float(t.split(':', 1)[1])
                i += 1
            else:
                raise HintError(f'line {ln}: cannot read "{t}" in: {line}')
        if not clauses:
            raise HintError(f'line {ln}: nothing said about {", ".join(subj)}')
        for c in clauses:
            if c.get('target', {}).get('parts') and set(c['target']['parts']) & set(parts):
                raise HintError(f'line {ln}: {", ".join(subj)} is placed against itself')
            hints.append({**c, 'parts': parts, 'text': line})
    return hints


def derive(board_path, level=2):
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    import pcbnew
    b = pcbnew.LoadBoard(str(board_path))
    e = b.GetBoardEdgesBoundingBox()
    mm = pcbnew.ToMM
    x0, y0, w, h = mm(e.GetLeft()), mm(e.GetTop()), mm(e.GetWidth()), mm(e.GetHeight())
    P = []
    for f in b.GetFootprints():
        if f.IsLocked() or not any(p.GetNetCode() > 0 for p in f.Pads()) or not f.GetReference():
            continue
        bb = f.GetBoundingBox(False)
        P.append({'ref': f.GetReference(), 'pads': f.GetPadCount(), 'x': mm(bb.GetCenter().x), 'y': mm(bb.GetCenter().y),
                  'box': (mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom()))})
    if len({p['ref'] for p in P}) < len(P):  # duplicate references cannot be named
        seen = set(); P = [p for p in P if not (p['ref'] in seen or seen.add(p['ref']))]
    conn = lambda p: re.match(r'(J|P|CN|CON|USB|X)\d', p['ref'])
    hugs = lambda p: [s for s, d in (('left', p['box'][0] - x0), ('right', x0 + w - p['box'][2]), ('top', p['box'][1] - y0), ('bottom', y0 + h - p['box'][3])) if d <= 1.0]
    big = sorted([p for p in P if p['pads'] >= 8 or conn(p) or hugs(p)], key=lambda p: -p['pads'])
    out = [f'# derived from {board_path.name if hasattr(board_path, "name") else board_path}, level {level}']
    edge_of = {}
    for p in big:
        d = {'left': p['box'][0] - x0, 'right': x0 + w - p['box'][2], 'top': p['box'][1] - y0, 'bottom': y0 + h - p['box'][3]}
        side = min(d, key=d.get)
        if hugs(p) or (conn(p) and d[side] <= 2.0):  # against an edge: that is mechanical, whatever the part is
            edge_of[p['ref']] = side
            along = (p['y'] - y0) / h if side in ('left', 'right') else (p['x'] - x0) / w
            where = ('top' if along < 1 / 3 else 'bottom' if along > 2 / 3 else '') if side in ('left', 'right') else ('left' if along < 1 / 3 else 'right' if along > 2 / 3 else '')
            region = {('left', 'top'): 'top-left', ('left', 'bottom'): 'bottom-left', ('right', 'top'): 'top-right', ('right', 'bottom'): 'bottom-right',
                      ('top', 'left'): 'top-left', ('top', 'right'): 'top-right', ('bottom', 'left'): 'bottom-left', ('bottom', 'right'): 'bottom-right'}.get((side, where), side)
            out.append(f"{p['ref']}  " + '  '.join(f'on edge {s}' for s in (hugs(p) or [side])) + f'  {region}')
        else:
            col = 'left' if (p['x'] - x0) / w < 1 / 3 else 'right' if (p['x'] - x0) / w > 2 / 3 else ''
            row = 'top' if (p['y'] - y0) / h < 1 / 3 else 'bottom' if (p['y'] - y0) / h > 2 / 3 else ''
            out.append(f"{p['ref']}  {'-'.join(x for x in (row, col) if x) or 'center'}")
    if level >= 2:
        inner = [p for p in big if p['ref'] not in edge_of]
        for k, p in enumerate(inner[1:], 1):
            q = min(inner[:k], key=lambda q: math.dist((p['x'], p['y']), (q['x'], q['y'])))
            dx, dy = p['x'] - q['x'], p['y'] - q['y']
            rel = ('right of' if dx > 0 else 'left of') if abs(dx) >= abs(dy) else ('below' if dy > 0 else 'above')
            minor = abs(dy) if abs(dx) >= abs(dy) else abs(dx)
            align = (' level with ' if abs(dx) >= abs(dy) else ' column with ') + q['ref'] if minor < 1.5 else ''
            out.append(f"{p['ref']}  {rel} {q['ref']}{align}")
    if level >= 3 and big:
        gap = lambda p, q: math.hypot(max(0, q['box'][0] - p['box'][2], p['box'][0] - q['box'][2]), max(0, q['box'][1] - p['box'][3], p['box'][1] - q['box'][3]))
        names = {p['ref'] for p in big}
        for p in P:
            if p['ref'] in names:
                continue
            q = min(big, key=lambda q: gap(p, q))
            if gap(p, q) <= 4.0:
                out.append(f"{p['ref']}  near {q['ref']}  within: {max(1, math.ceil(gap(p, q) + 0.5))}")
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('step', choices=['derive'])
    ap.add_argument('board', type=Path)
    ap.add_argument('--level', type=int, default=2, choices=[1, 2, 3])
    a = ap.parse_args()
    sys.stdout.write(derive(a.board, a.level))
