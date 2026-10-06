#!/usr/bin/env python3
"""Figures for the TraceMaker comparison post: python3 evals/pcbworld/figs_tracemaker.py <out dir>"""
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(sys.argv[1])
BG, FG, DIM, MAG, MAG2, TEAL, GREY, CYAN = '#07070c', '#e8e8f0', '#9a9ab0', '#ff2d95', '#b0206c', '#2a7080', '#5c5c7a', '#19e3ff'
plt.rcParams.update({'font.size': 11, 'text.color': FG, 'axes.labelcolor': FG, 'xtick.color': DIM, 'ytick.color': FG, 'font.family': 'DejaVu Sans'})


def panel(ax, title, rows, first):
    names = [r[0] for r in rows][::-1]
    ax.barh(range(len(rows)), [r[1] for r in rows][::-1], color=[r[2] for r in rows][::-1], height=0.64)
    for i, r in enumerate(rows[::-1]):
        ax.text(r[1] + 0.015, i, f'{r[1]:.2f}', va='center', color=DIM if r[2] == GREY else FG, fontweight='bold' if r[2] == MAG else 'normal')
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(names if first else [])
    if first:
        for lab, r in zip(ax.get_yticklabels(), rows[::-1]):
            lab.set_color(MAG if r[2] == MAG else DIM if r[2] == GREY else FG)
    ax.set_xlim(0, 1.13)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_title(title, color=CYAN, loc='left', fontsize=13, pad=12)
    ax.set_facecolor(BG)
    ax.grid(axis='x', color='#1c1c2a', lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#3a3a50')


def save(fig, name, note):
    fig.patch.set_facecolor(BG)
    fig.text(0.01, 0.015, note, color=DIM, fontsize=9.5)
    fig.savefig(OUT / name, dpi=100, facecolor=BG, pil_kwargs={'quality': 90})


rows = lambda d, b, t, f21, f22, ts, y: [("Designer's own routing", d, GREY), ('circuit-skills, best of backends', b, MAG), ('TraceMaker', t, TEAL),
                                         ('Freerouting 2.1.0', f21, MAG2), ('Freerouting 2.2.4', f22, MAG2), ('tscircuit capacity autorouter', ts, MAG2),
                                         ('circuit-skills, a day earlier', y, GREY)]
fig, axes = plt.subplots(1, 3, figsize=(15, 6.2), gridspec_kw={'left': 0.19, 'right': 0.985, 'top': 0.9, 'bottom': 0.11, 'wspace': 0.08})
panel(axes[0], 'D3-A · 99 small boards', rows(1.00, 1.00, 0.99, 0.87, 0.73, 0.21, 0.78), True)
panel(axes[1], 'D3-B · 10 medium boards', rows(1.00, 1.00, 1.00, 0.80, 0.60, 0.00, 0.70), False)
panel(axes[2], 'D3-C · 10 large boards', rows(0.90, 0.90, 0.90, 0.30, 0.30, 0.00, 0.20), False)
save(fig, 'scores.jpg', "Clean pass: fully connected and zero KiCad DRC errors under each board's own rules. One run per router, same machine, same judge.")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={'left': 0.27, 'right': 0.98, 'top': 0.87, 'bottom': 0.15, 'wspace': 0.08})
pr = lambda a, b, c, d: [("Designer's placement", a, GREY), ("TraceMaker's placer", b, TEAL), ('Our annealer + untangle, part level', c, MAG), ("TraceMaker's placer → tscircuit router", d, MAG2)]
panel(axes[0], 'Clean pass', pr(1.00, 0.50, 0.10, 0.00), True)
panel(axes[1], 'Connections routed', pr(1.00, 0.85, 0.94, 0.60), False)
save(fig, 'placement.jpg', '10 medium boards, every part re-placed from scratch, then routed with the best of three routers (last row: one router).')

fig, axes = plt.subplots(1, 2, figsize=(12, 6.27), gridspec_kw={'left': 0.25, 'right': 0.98, 'top': 0.88, 'bottom': 0.1, 'wspace': 0.08})
panel(axes[0], 'D3-B · 10 medium boards', rows(1.00, 1.00, 1.00, 0.80, 0.60, 0.00, 0.70), True)
panel(axes[1], 'D3-C · 10 large boards', rows(0.90, 0.90, 0.90, 0.30, 0.30, 0.00, 0.20), False)
save(fig, 'card.jpg', 'Clean-pass rate on real boards from PCBWorld D3. Same machine, same KiCad DRC judge.')
