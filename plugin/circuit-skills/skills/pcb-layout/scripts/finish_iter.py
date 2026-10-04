#!/usr/bin/env python3
"""finish_iter.py — close the last unconnected pads, DRC-verified.

For each unconnected PLANE (GND/V3V3) pad: try a stitch via in several offset
directions/distances and KEEP the first placement that adds no short/crossing
(DRC is the oracle). For point-to-point pads (e.g. VBUS): route a track to the
nearest same-net pad, likewise DRC-verified. Anything that can't be placed
cleanly is left unconnected (reported) rather than shorting the board.
"""
import json
import math
import re
import subprocess

import kipy
from kipy.board_types import Track, Via, BoardLayer
from kipy.geometry import Vector2

BOARD = "index.circuit.kicad_pcb"
PLANE = {"GND", "V3V3"}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
DISTS = [700_000, 1000_000, 1300_000, 1700_000]

b = kipy.KiCad().get_board()
nets = {n.name: n for n in b.get_nets() if n.name}
padof, bynet = {}, {}
for fp in b.get_footprints():
    ref = fp.reference_field.text.value
    for pd in fp.definition.pads:
        nm = pd.net.name if pd.net else ""
        padof[(ref, str(pd.number))] = (pd.position, nm)
        bynet.setdefault(nm, []).append((ref, str(pd.number), pd.position))


def bad_count():
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", "build/drc.json", BOARD],
                   capture_output=True)
    d = json.load(open("build/drc.json"))
    return sum(1 for v in d.get("violations", []) if v["type"] in ("shorting_items", "tracks_crossing")), d


def unconn():
    _, d = bad_count()
    out = []
    for v in d.get("unconnected_items", []):
        pd = next((i["description"] for i in v["items"] if i["description"].startswith("Pad")), "")
        m = re.match(r"Pad (\S+) \[(.+?)\] of (\S+)", pd)
        if m:
            out.append((m.group(3), m.group(1), m.group(2)))
    return out


def try_items(items, base):
    created = b.create_items(items)  # server-assigned handles — remove THESE, not the originals
    b.refill_zones(); b.save()
    n, _ = bad_count()
    if n <= base:
        return True
    if created:
        b.remove_items(created)
    b.refill_zones(); b.save()
    return False


base, _ = bad_count()
for ref, num, net in unconn():
    if (ref, num) not in padof:
        continue
    pos, _ = padof[(ref, num)]
    ok = False
    if net in PLANE:
        for dist in DISTS:
            for dx, dy in DIRS:
                d = math.hypot(dx, dy)
                vp = Vector2.from_xy(int(pos.x + dx / d * dist), int(pos.y + dy / d * dist))
                via = Via(); via.position = vp; via.diameter = 450_000; via.drill_diameter = 250_000; via.net = nets[net]
                tr = Track(); tr.start = pos; tr.end = vp; tr.width = 200_000; tr.layer = BoardLayer.BL_F_Cu; tr.net = nets[net]
                if try_items([via, tr], base):
                    ok = True; break
            if ok:
                break
    else:
        cands = sorted([p for p in bynet.get(net, []) if (p[0], p[1]) != (ref, num)],
                       key=lambda p: (p[2].x - pos.x) ** 2 + (p[2].y - pos.y) ** 2)
        for _r, _n, tp in cands[:3]:
            for layer in (BoardLayer.BL_F_Cu, BoardLayer.BL_B_Cu):
                tr = Track(); tr.start = pos; tr.end = tp; tr.width = 200_000; tr.layer = layer; tr.net = nets[net]
                if try_items([tr], base):
                    ok = True; break
            if ok:
                break
    print(f"  {ref}.{num} [{net}]: {'OK' if ok else 'left unconnected'}")

print(f"final DRC shorts/crossings: {bad_count()[0]}")
