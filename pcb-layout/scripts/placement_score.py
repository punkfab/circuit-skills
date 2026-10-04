#!/usr/bin/env python3
"""placement_score.py — how routable is this placement, before any router runs?

  python3 placement_score.py board.kicad_pcb [--cell 1.0] [--json out.json] [--svg out.svg]

Routing difficulty is decided by placement, so score the placement itself (existing tracks are
ignored). The measures are the routability estimates chip placement has used for decades, adapted
to a PCB:

  congestion  RUDY (rectangular uniform wire density): each net's estimated wire length is spread
              evenly over its pads' bounding box, plus one escape stub per pin in the pin's own cell,
              summed on a grid of `--cell` mm cells and divided by what the cell can carry (routing
              layers x free area, in track pitches). Hotspots are clusters of the board's top-decile
              cells: the estimate RANKS cells well but its absolute scale is not calibrated (einhander
              peaks at 0.8 yet every router fails there). Nets carried by an inner-layer plane are left
              out (they drop vias, they don't cross the board).
  ratsnest    total minimum-spanning-tree wire length and how many ratsnest lines of different nets
              cross: crossings become vias or detours.
  escape      for each fine-pitch part (>= 16 pads, pitch <= 0.65 mm): signal pins that must leave it
              against the routing channels around its outline. Above 1.0 its pins cannot all get out
              on the routing layers.

Prints a summary and the hotspots (connected over-capacity regions) with the parts in them; --json
writes everything (the grid too) for route_eval.py --analyze; --svg writes a heat map. All numbers
are estimates for comparing placements of the same board, not absolute pass/fail.
"""
import argparse, json, math, re, sys
from pathlib import Path


# ---- KiCad ---------------------------------------------------------------------------------
def parse(text):
    stack = [[]]
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '(':
            l = []; stack[-1].append(l); stack.append(l); i += 1
        elif c == ')':
            stack.pop(); i += 1
        elif c == '"':
            j, s = i + 1, []
            while j < n and text[j] != '"':
                if text[j] == '\\':
                    s.append(text[j + 1]); j += 2
                else:
                    s.append(text[j]); j += 1
            stack[-1].append(''.join(s)); i = j + 1
        elif c in ' \n\t\r':
            i += 1
        else:
            j = i
            while j < n and text[j] not in ' \n\t\r()':
                j += 1
            stack[-1].append(text[i:j]); i = j
    return stack[0][0]


def kids(e, name):
    return [c for c in e if isinstance(c, list) and c and c[0] == name] if isinstance(e, list) else []


def kid(e, name):
    k = kids(e, name)
    return k[0] if k else None


def num(e, i=1):
    try:
        return float(e[i])
    except (TypeError, IndexError, ValueError):
        return math.nan


def rot(x, y, deg):  # KiCad: +deg is CCW on screen, Y down
    t = math.radians(deg)
    return x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t)


def read_board(text):
    root = parse(text)
    copper = [l[1] for l in (kid(root, 'layers') or [])[1:] if isinstance(l, list) and len(l) > 1 and str(l[1]).endswith('.Cu')]
    zones = [z for z in kids(root, 'zone') if not kid(z, 'keepout')]
    plane_nets = set()
    for z in zones:
        layers = (kid(z, 'layers') or [])[1:] + (kid(z, 'layer') or [])[1:]
        name = (kid(z, 'net_name') or [None, None])[1]
        if name and any(re.match(r'In\d+\.Cu$', l) for l in layers):
            plane_nets.add(name)
    pads, parts = [], []
    for fp in kids(root, 'footprint'):
        at = kid(fp, 'at')
        fx, fy, fr = num(at, 1), num(at, 2), (num(at, 3) if at and len(at) > 3 else 0.0)
        ref = next((p[2] for p in kids(fp, 'property') if len(p) > 2 and p[1] == 'Reference'), '?')
        mine = []
        for pad in kids(fp, 'pad'):
            pat = kid(pad, 'at')
            ox, oy = rot(num(pat, 1), num(pat, 2), fr)
            size = kid(pad, 'size')
            w, h = num(size, 1), num(size, 2)
            a = num(pat, 3) if pat and len(pat) > 3 else 0.0
            if abs(math.sin(math.radians(a))) > 0.7:
                w, h = h, w
            if kid(pad, 'primitives'):  # custom pad: a generous box around its primitives
                xs = [num(xy, 1) for g in kid(pad, 'primitives')[1:] for xy in kids(kid(g, 'pts') or [], 'xy')]
                ys = [num(xy, 2) for g in kid(pad, 'primitives')[1:] for xy in kids(kid(g, 'pts') or [], 'xy')]
                if xs:
                    w, h = max(w, max(xs) - min(xs)), max(h, max(ys) - min(ys))
            layers = (kid(pad, 'layers') or [])[1:]
            net = kid(pad, 'net')
            netname = net[2] if net and len(net) > 2 else ''
            p = {'ref': ref, 'pad': pad[1] if len(pad) > 1 else '', 'x': fx + ox, 'y': fy + oy, 'w': w, 'h': h,
                 'type': pad[2] if len(pad) > 2 else 'smd', 'through': '*.Cu' in layers or (len(pad) > 2 and 'thru' in str(pad[2])),
                 'net': '' if netname.startswith('unconnected-') else netname}
            pads.append(p); mine.append(p)
        if mine:
            xs = [p['x'] for p in mine]; ys = [p['y'] for p in mine]
            parts.append({'ref': ref, 'x': fx, 'y': fy, 'pads': mine, 'bbox': (min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5)})
    x0 = y0 = math.inf; x1 = y1 = -math.inf
    for g in root:
        if isinstance(g, list) and str(g[0]).startswith('gr_') and (kid(g, 'layer') or [None, None])[1] == 'Edge.Cuts':
            if g[0] == 'gr_circle' and kid(g, 'center') and kid(g, 'end'):  # a round board: center +- radius
                c, e = kid(g, 'center'), kid(g, 'end')
                r = math.dist((num(c, 1), num(c, 2)), (num(e, 1), num(e, 2)))
                x0, x1, y0, y1 = min(x0, num(c, 1) - r), max(x1, num(c, 1) + r), min(y0, num(c, 2) - r), max(y1, num(c, 2) + r)
                continue
            for k in ('start', 'end', 'mid', 'center'):
                p = kid(g, k)
                if p:
                    x0, x1, y0, y1 = min(x0, num(p, 1)), max(x1, num(p, 1)), min(y0, num(p, 2)), max(y1, num(p, 2))
            for xy in kids(kid(g, 'pts') or [], 'xy'):
                x0, x1, y0, y1 = min(x0, num(xy, 1)), max(x1, num(xy, 1)), min(y0, num(xy, 2)), max(y1, num(xy, 2))
    if not math.isfinite(x0):
        raise SystemExit('no Edge.Cuts outline')
    rules = {'trace': 0.2, 'clearance': 0.15}
    return {'copper': copper, 'plane_nets': plane_nets, 'pads': pads, 'parts': parts, 'bbox': (x0, y0, x1, y1), 'rules': rules}


def read_rules(board_path, rules):
    pro = Path(str(board_path)[:-len('.kicad_pcb')] + '.kicad_pro')
    try:
        cls = next(c for c in json.loads(pro.read_text())['net_settings']['classes'] if c.get('name') == 'Default')
        rules['trace'] = cls.get('track_width') or rules['trace']
        rules['clearance'] = cls.get('clearance') or rules['clearance']
    except (OSError, KeyError, StopIteration, ValueError):
        pass
    return rules


# ---- measures ------------------------------------------------------------------------------------
def steiner_factor(n):
    """Expected wire length / half-perimeter of the bounding box for an n-pin net (Cheng 1994, approx.)."""
    return 1.0 if n <= 3 else min(2.8, 1.0 + 0.09 * (n - 3) ** 0.85)


def mst(points):
    """Prim's minimum spanning tree: list of (i, j) edges."""
    n = len(points)
    if n < 2:
        return []
    inside, best, edges = {0}, {j: (math.dist(points[0], points[j]), 0) for j in range(1, n)}, []
    while best:
        j = min(best, key=lambda k: best[k][0])
        d, i = best.pop(j)
        edges.append((i, j)); inside.add(j)
        for k in best:
            dk = math.dist(points[j], points[k])
            if dk < best[k][0]:
                best[k] = (dk, j)
    return edges


def crosses(a, b, c, d):
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


PIN_WEIGHT = 1.0


def score(board_path, cell=1.0, pin_weight=None):
    global PIN_WEIGHT
    if pin_weight is not None:
        PIN_WEIGHT = pin_weight
    text = Path(board_path).read_text()
    b = read_board(text)
    rules = read_rules(board_path, b['rules'])
    pitch = rules['trace'] + rules['clearance']
    inner_planes = bool(b['plane_nets']) and any(l.startswith('In') for l in b['copper'])
    layers = 2 if inner_planes or len(b['copper']) <= 2 else len(b['copper'])
    x0, y0, x1, y1 = b['bbox']
    nx, ny = max(1, math.ceil((x1 - x0) / cell)), max(1, math.ceil((y1 - y0) / cell))
    demand = [[0.0] * nx for _ in range(ny)]
    blocked = [[0.0] * nx for _ in range(ny)]

    def cells(ax, ay, bx, by):
        # Clamped both ways: a pad drawn outside the outline (seen on real boards) lands in the edge cell.
        clamp = lambda v, n: min(n - 1, max(0, v))
        i0, i1 = clamp(int((ax - x0) / cell), nx), clamp(int((bx - x0) / cell), nx)
        j0, j1 = clamp(int((ay - y0) / cell), ny), clamp(int((by - y0) / cell), ny)
        return i0, i1, j0, j1

    # Pads take routing area: through-hole on every routing layer, SMD on one.
    for p in b['pads']:
        share = 1.0 if p['through'] else 1.0 / layers
        i0, i1, j0, j1 = cells(p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)
        area = (p['w'] + rules['clearance']) * (p['h'] + rules['clearance'])
        n = (i1 - i0 + 1) * (j1 - j0 + 1)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                blocked[j][i] += share * area / n / (cell * cell)

    nets = {}
    for p in b['pads']:
        if p['net']:
            nets.setdefault(p['net'], []).append(p)
    signal = {k: v for k, v in nets.items() if len(v) >= 2 and k not in b['plane_nets']}
    total_mst = total_hpwl = 0.0
    segments = []
    for name, pts in signal.items():
        xs = [p['x'] for p in pts]; ys = [p['y'] for p in pts]
        w, h = max(max(xs) - min(xs), cell), max(max(ys) - min(ys), cell)
        hpwl = (max(xs) - min(xs)) + (max(ys) - min(ys))
        total_hpwl += hpwl
        wire = hpwl * steiner_factor(len(pts))
        # RUDY: the net's wire area (length x pitch) spread uniformly over its box.
        density = wire * pitch / (w * h)
        i0, i1, j0, j1 = cells(min(xs), min(ys), min(xs) + w, min(ys) + h)
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                demand[j][i] += density
        # Pin density: every pin needs its own escape out of its cell, which the box-spread above
        # dilutes away around fine-pitch parts. One pitch-wide stub per pin, in the pin's cell.
        for p in pts:
            i0, _, j0, _ = cells(p['x'], p['y'], p['x'], p['y'])
            demand[j0][i0] += PIN_WEIGHT * pitch * cell / (cell * cell)
        coords = [(p['x'], p['y']) for p in pts]
        for i, j in mst(coords):
            total_mst += math.dist(coords[i], coords[j])
            segments.append((name, coords[i], coords[j]))
    crossings = sum(1 for a in range(len(segments)) for c in range(a + 1, len(segments))
                    if segments[a][0] != segments[c][0] and crosses(segments[a][1], segments[a][2], segments[c][1], segments[c][2]))

    util = [[demand[j][i] / max(0.05, layers - min(blocked[j][i], layers - 0.05)) for i in range(nx)] for j in range(ny)]
    flat = sorted(v for row in util for v in row)
    p95 = flat[int(0.95 * (len(flat) - 1))]
    over = sum(1 for v in flat if v > 1.0)

    # Hotspots: 8-connected regions of this board's most congested cells (the top decile of cells that
    # carry any wiring), with the parts whose pads sit in them. Relative on purpose: the estimate ranks
    # cells well (on einhander 78-100% of every router's defects fell in its top-20% cells) but its
    # absolute scale is not calibrated, so "over 1.0" is not a reliable line.
    loaded = sorted(v for row in util for v in row if v > 0)
    hot = max(loaded[int(0.9 * (len(loaded) - 1))] if loaded else 1.0, 0.02)
    core = max(loaded[int(0.97 * (len(loaded) - 1))] if loaded else 1.0, hot)  # hotspots name the cores
    seen, hotspots = set(), []
    for j in range(ny):
        for i in range(nx):
            if util[j][i] >= core and (i, j) not in seen:
                stack, region = [(i, j)], []
                seen.add((i, j))
                while stack:
                    a, c = stack.pop(); region.append((a, c))
                    for da in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            q = (a + da, c + dc)
                            if 0 <= q[0] < nx and 0 <= q[1] < ny and q not in seen and util[q[1]][q[0]] >= core:
                                seen.add(q); stack.append(q)
                xs = [a for a, _ in region]; ys = [c for _, c in region]
                box = (x0 + min(xs) * cell, y0 + min(ys) * cell, x0 + (max(xs) + 1) * cell, y0 + (max(ys) + 1) * cell)
                refs = sorted({p['ref'] for p in b['pads'] if box[0] <= p['x'] <= box[2] and box[1] <= p['y'] <= box[3]})
                hotspots.append({'cells': len(region), 'peak': round(max(util[c][a] for a, c in region), 2),
                                 'box': [round(v, 2) for v in box], 'parts': refs})
    hotspots.sort(key=lambda h: -h['cells'] * h['peak'])
    hotspots = [h for h in hotspots if h['cells'] >= 1][:12]

    # Escape pressure of fine-pitch parts.
    escape = []
    for part in b['parts']:
        sp = [p for p in part['pads'] if not p['through']]
        if len(sp) < 16:
            continue
        # Pitch along a row of pins: pads sharing a row (same y, or same x), neighbour to neighbour.
        rows = {}
        for p in sp:
            rows.setdefault(('y', round(p['y'], 1)), []).append(p['x'])
            rows.setdefault(('x', round(p['x'], 1)), []).append(p['y'])
        steps = [b2 - a2 for v in rows.values() if len(v) >= 3 for a2, b2 in zip(sorted(v), sorted(v)[1:]) if b2 - a2 > 0.05]
        if not steps or min(steps) > 0.65:
            continue
        must = sum(1 for p in sp if p['net'] and p['net'] not in b['plane_nets'])
        bx0, by0, bx1, by1 = part['bbox']
        channels = 2 * ((bx1 - bx0) + (by1 - by0)) / pitch * layers
        escape.append({'ref': part['ref'], 'pins': len(sp), 'signal_pins': must, 'pitch': round(min(steps), 3),
                       'ratio': round(must / channels, 2) if channels else None})
    escape.sort(key=lambda e: -(e['ratio'] or 0))

    return {
        'board': str(board_path), 'cell_mm': cell, 'routing_layers': layers, 'plane_nets': sorted(b['plane_nets']),
        'pitch_mm': round(pitch, 3), 'signal_nets': len(signal),
        'congestion': {'max': round(flat[-1], 2), 'p95': round(p95, 2), 'over_capacity_cells': over,
                       'over_capacity_pct': round(100 * over / len(flat), 1), 'hot_threshold': round(hot, 3), 'hot_cells': sum(1 for v in flat if v >= hot), 'core_threshold': round(core, 3)},
        'ratsnest': {'mst_mm': round(total_mst, 1), 'hpwl_mm': round(total_hpwl, 1), 'crossings': crossings},
        'escape': escape, 'hotspots': hotspots,
        'grid': {'x0': x0, 'y0': y0, 'nx': nx, 'ny': ny, 'util': [[round(v, 3) for v in row] for row in util]},
    }


def heat_svg(s, board_text):
    g = s['grid']
    cell = s['cell_mm']
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{g["x0"]} {g["y0"]} {g["nx"] * cell} {g["ny"] * cell}" style="background:#0d1117">']
    for j, row in enumerate(g['util']):
        for i, v in enumerate(row):
            if v < 0.2 * s['congestion']['hot_threshold']:
                continue
            t = min(v / (2 * s['congestion']['hot_threshold']), 1.0)
            r, gg, bb = int(40 + 215 * t), int(160 - 120 * t), int(90 - 60 * t)
            out.append(f'<rect x="{g["x0"] + i * cell:.2f}" y="{g["y0"] + j * cell:.2f}" width="{cell}" height="{cell}" fill="rgb({r},{gg},{bb})" fill-opacity="{0.25 + 0.6 * t:.2f}"/>')
    for h in s['hotspots']:
        x0, y0, x1, y1 = h['box']
        out.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="none" stroke="#ffffff" stroke-width="0.25" stroke-dasharray="0.8 0.5"/>')
    for p in read_board(board_text)['pads']:
        out.append(f'<rect x="{p["x"] - p["w"] / 2:.2f}" y="{p["y"] - p["h"] / 2:.2f}" width="{p["w"]:.2f}" height="{p["h"]:.2f}" fill="#c9ced4" fill-opacity="0.55"/>')
    out.append('</svg>')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('board', type=Path)
    ap.add_argument('--cell', type=float, default=1.0)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--svg', type=Path)
    a = ap.parse_args()
    s = score(a.board, a.cell)
    c, r = s['congestion'], s['ratsnest']
    print(f"placement_score {a.board.name}: {s['signal_nets']} signal nets on {s['routing_layers']} routing layers"
          f"{' (planes: ' + ', '.join(s['plane_nets']) + ')' if s['plane_nets'] else ''}, pitch {s['pitch_mm']} mm")
    print(f"  congestion  max {c['max']}  p95 {c['p95']}  hot (top decile) >= {c['hot_threshold']}, cores (top 3%) >= {c['core_threshold']}; over 1.0: {c['over_capacity_cells']} cells")
    print(f"  ratsnest    {r['mst_mm']} mm MST, {r['crossings']} crossings")
    for e in s['escape']:
        print(f"  escape      {e['ref']}: {e['signal_pins']} signal pins at {e['pitch']} mm pitch, demand/channels {e['ratio']}")
    for h in s['hotspots'][:6]:
        print(f"  hotspot     {h['cells']} cells, peak {h['peak']} at {h['box']}: {', '.join(h['parts'][:10]) or '(no pads)'}")
    if a.json:
        a.json.write_text(json.dumps(s) + '\n')
    if a.svg:
        a.svg.write_text(heat_svg(s, a.board.read_text()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
