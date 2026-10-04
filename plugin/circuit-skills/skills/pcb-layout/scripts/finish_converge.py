#!/usr/bin/env python3
"""finish_converge.py — close the routing tail on a FROZEN board, monotonically.

Do NOT re-route while running this. For each unconnected pad, try a fix and keep it
ONLY if it strictly reduces `unconnected` without increasing `shorts` (else undo and
try the next option). Prints the running (shorts, unconnected) after every step so the
convergence is visible and can't silently thrash.

  PLANE net (GND/V3V3): stitch via at an offset that passes DRC (tries directions/distances).
  point-to-point net (VBUS/CC): small local copper pour spanning that pad + its nearest same-net pads.
"""
import json
import math
import re
import subprocess

import kipy
from kipy.board_types import Track, Via, Zone, BoardLayer
from kipy.geometry import Vector2, PolyLine, PolyLineNode, PolygonWithHoles

BOARD = "index.circuit.kicad_pcb"
PLANE = {"GND", "V3V3"}
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
DISTS = [700_000, 1000_000, 1300_000, 1700_000, 2200_000]

b = kipy.KiCad().get_board()
nets = {n.name: n for n in b.get_nets() if n.name}
padof, bynet, fpc = {}, {}, {}
for fp in b.get_footprints():
    ref = fp.reference_field.text.value
    fpc[ref] = fp.position
    for pd in fp.definition.pads:
        nm = pd.net.name if pd.net else ""
        padof[(ref, str(pd.number))] = (pd.position, nm)
        bynet.setdefault(nm, []).append(pd.position)


def drc():
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", "build/drc.json", BOARD],
                   capture_output=True)
    d = json.load(open("build/drc.json"))
    sh = sum(1 for v in d.get("violations", []) if v["type"] in ("shorting_items", "tracks_crossing"))
    un = []
    for v in d.get("unconnected_items", []):
        pd = next((i["description"] for i in v["items"] if i["description"].startswith("Pad")), "")
        m = re.match(r"Pad (\S+) \[(.+?)\] of (\S+)", pd)
        if m:
            un.append((m.group(3), m.group(1), m.group(2)))
    return sh, un


def keep_or_undo(items, sh_before, un_before):
    created = b.create_items(items)
    b.refill_zones(); b.save()
    sh, un = drc()
    if sh <= sh_before and len(un) < un_before:
        return True, sh, un
    if created:
        b.remove_items(created)
    b.refill_zones(); b.save()
    return False, sh_before, None


sh, un = drc()
print(f"baseline: shorts={sh} unconnected={len(un)}")
targets = list(un)
for ref, num, net in targets:
    sh, un = drc()
    if not any(u[0] == ref and u[1] == num for u in un):
        continue                                    # already connected by an earlier fix
    nb = len(un)
    pos = padof[(ref, num)][0]
    fixed = False
    if net in PLANE:                                # stitch via at a DRC-clean offset
        c = fpc[ref]
        rx, ry = pos.x - c.x, pos.y - c.y
        rd = math.hypot(rx, ry) or 1
        order = [(rx / rd, ry / rd)] + DIRS
        for dist in DISTS:
            for ux, uy in order:
                ud = math.hypot(ux, uy) or 1
                vp = Vector2.from_xy(int(pos.x + ux / ud * dist), int(pos.y + uy / ud * dist))
                via = Via(); via.position = vp; via.diameter = 450_000; via.drill_diameter = 250_000; via.net = nets[net]
                tr = Track(); tr.start = pos; tr.end = vp; tr.width = 200_000; tr.layer = BoardLayer.BL_F_Cu; tr.net = nets[net]
                ok, sh, u2 = keep_or_undo([via, tr], sh, nb)
                if ok:
                    un, fixed = u2, True
                    break
            if fixed:
                break
    else:                                           # local pour: this pad + nearest same-net pads
        near = sorted(bynet.get(net, []), key=lambda p: (p.x - pos.x) ** 2 + (p.y - pos.y) ** 2)[:3]
        m = 1_500_000
        x0, x1 = min(p.x for p in near) - m, max(p.x for p in near) + m
        y0, y1 = min(p.y for p in near) - m, max(p.y for p in near) + m
        for layer in (BoardLayer.BL_F_Cu, BoardLayer.BL_B_Cu):
            pl = PolyLine()
            for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
                pl.append(PolyLineNode.from_xy(int(x), int(y)))
            pl.closed = True
            poly = PolygonWithHoles(); poly.outline = pl
            z = Zone(); z.outline = poly; z.layers = [layer]; z.net = nets[net]
            z.name = f"{net}_local"; z.priority = 2
            ok, sh, u2 = keep_or_undo([z], sh, nb)
            if ok:
                un, fixed = u2, True
                break
    print(f"  {ref}.{num} [{net:5}]: {'OK  ' if fixed else 'skip'} -> shorts={sh} unconnected={len(un)}")

print(f"FINAL: shorts={sh} unconnected={len(un)}")
