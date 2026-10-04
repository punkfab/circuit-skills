#!/usr/bin/env python3
"""stitch_planes.py — tie every unconnected GND/V3V3 copper island to its inner plane.

A plane net (GND/V3V3) is meant to be joined THROUGH the plane, so a track island with
no via to the plane reads as 'unconnected' in DRC even though it's the same net. For each
such island DRC reports, drop a stitching via on it (same net) -> it joins the plane and
thereby the rest of the net. Monotonic: same-net vias can't create a short.

Reads build/drc.json (run kicad-cli drc first). Run over IPC (pcbnew open).
"""
import json
import time

import kipy
from kipy.board_types import Via
from kipy.geometry import Vector2

PLANE = {"GND", "V3V3"}
NM = 1_000_000

b = None
for _ in range(20):
    try:
        b = kipy.KiCad().get_board(); break
    except Exception:
        time.sleep(2)
if b is None:
    raise SystemExit("no IPC")
nets = {n.name: n for n in b.get_nets() if n.name}

d = json.load(open("build/drc.json"))
seen = set()
added = []
for v in d.get("unconnected_items", []):
    for it in v.get("items", []):
        desc = it.get("description", "")
        pos = it.get("pos", {})
        # only stitch Track islands of a plane net
        net = None
        for pn in PLANE:
            if f"[{pn}]" in desc and desc.strip().startswith("Track"):
                net = pn
        if not net:
            continue
        key = (round(pos["x"], 2), round(pos["y"], 2), net)
        if key in seen:
            continue
        seen.add(key)
        via = Via()
        via.position = Vector2.from_xy(int(pos["x"] * NM), int(pos["y"] * NM))
        via.diameter = 600_000
        via.drill_diameter = 300_000
        via.net = nets[net]
        added.append(via)
        print(f"  stitch {net} via @({pos['x']:.2f},{pos['y']:.2f})")

if added:
    b.create_items(added)
    b.refill_zones()
    b.save()
print(f"added {len(added)} stitching vias")
