#!/usr/bin/env python3
"""Figures for the placement-hints post: python3 evals/corpus/figs_hints.py <board id> <out dir>"""
import json, os, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'pcb-layout' / 'scripts'))
import placement_score
CACHE = Path(os.getenv('CIRCUIT_SKILLS_CACHE', Path.home() / '.cache/circuit-skills')) / 'corpus' / 'score_study'
BG, FG, DIM, MAG, TEAL, GREY, CYAN = '#07070c', '#e8e8f0', '#9a9ab0', '#ff2d95', '#2a7080', '#5c5c7a', '#19e3ff'
plt.rcParams.update({'font.size': 10, 'text.color': FG, 'font.family': 'DejaVu Sans'})
bid, out = sys.argv[1], Path(sys.argv[2])
rows = {json.loads(l)['variant']: json.loads(l) for l in (HERE / 'hints_study.jsonl').read_text().splitlines() if json.loads(l)['board'] == bid}
hint_text = (CACHE / bid / 'h2.hints').read_text()
named = {l.split()[0] for l in hint_text.splitlines() if l and not l.startswith('#')}


def draw(ax, variant, title):
    b = placement_score.read_board((CACHE / bid / f'{variant}.kicad_pcb').read_text())
    x0, y0, x1, y1 = b['bbox']
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='#3a3a50', lw=1.5))
    nets = {}
    for p in b['pads']:
        if p['net']:
            nets.setdefault(p['net'], []).append((p['x'], p['y']))
    for pts in nets.values():
        if 2 <= len(pts) <= 6:
            for a, c in zip(pts, pts[1:]):
                ax.plot([a[0], c[0]], [a[1], c[1]], color='#2c2c44', lw=0.5, zorder=1)
    for p in b['parts']:
        bx = p['bbox']
        hot = p['ref'] in named
        ax.add_patch(Rectangle((bx[0] + 0.3, bx[1] + 0.3), max(0.5, bx[2] - bx[0] - 0.6), max(0.5, bx[3] - bx[1] - 0.6), fc=MAG if hot else TEAL, ec=BG, lw=0.6, alpha=0.95 if hot else 0.75, zorder=2))
        if hot and (bx[2] - bx[0]) * (bx[3] - bx[1]) > 30:
            ax.text((bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2, p['ref'], ha='center', va='center', fontsize=7.5, color=BG, fontweight='bold', zorder=3)
    r = rows[variant]
    ax.set_title(title, color=CYAN, loc='left', fontsize=12, pad=8)
    ax.text(x0, y1 + (y1 - y0) * 0.035, f"{round(100 * r['rout'])}% routed · {r['drv']} DRC errors" + (' · clean' if r['clean'] else ''), color=DIM, fontsize=9.5, va='top')
    ax.set_xlim(x0 - 1, x1 + 1); ax.set_ylim(y1 + (y1 - y0) * 0.09, y0 - 1)
    ax.set_aspect('equal'); ax.axis('off')


fig, axes = plt.subplots(1, 4, figsize=(16, 5.6), gridspec_kw={'left': 0.015, 'right': 0.99, 'top': 0.9, 'bottom': 0.04, 'wspace': 0.05, 'width_ratios': [1, 1, 1, 0.95]})
draw(axes[0], 'designer', "The designer's placement")
draw(axes[1], 'pk2', 'Placed from scratch, no hints')
draw(axes[2], 'h2', 'Placed from scratch, with the hints')
ax = axes[3]; ax.axis('off'); ax.set_facecolor(BG)
ax.set_title('The hints', color=CYAN, loc='left', fontsize=12, pad=8)
lines = [l for l in hint_text.splitlines() if l and not l.startswith('#')]
ax.text(0, 0.98, '\n'.join(lines[:22]) + ('\n…' if len(lines) > 22 else ''), family='DejaVu Sans Mono', fontsize=9.2, va='top', color=FG, transform=ax.transAxes, linespacing=1.45)
fig.patch.set_facecolor(BG)
fig.savefig(out / 'boards.jpg', dpi=100, facecolor=BG, pil_kwargs={'quality': 90})
print(out / 'boards.jpg')
