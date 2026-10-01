#!/usr/bin/env python3
"""finish_tail.py — close the routing tail Freerouting left, via the KiCad IPC API.

For each DRC `unconnected` pad:
  * PLANE net (GND/V3V3) -> drop a stitch via at the pad so it reaches its inner plane.
  * point-to-point net   -> run an F.Cu track to the nearest same-net pad.
Then refill zones + save. Re-run `drc_check.py` after to see what's left.

  python3 finish_tail.py [board.kicad_pcb]   (default index.circuit.kicad_pcb)
"""
import json
import re
import subprocess
import sys

import kipy
from kipy.board_types import Track, Via, BoardLayer

args = [a for a in sys.argv[1:] if not a.startswith("--")]
VIAS_ONLY = "--vias-only" in sys.argv
BOARD = args[0] if args else "index.circuit.kicad_pcb"
PLANE = {"GND", "V3V3"}
VIA_PAD, VIA_DRILL, TRK_W = 450_000, 250_000, 200_000  # nm

b = kipy.KiCad().get_board()
nets = {n.name: n for n in b.get_nets() if n.name}

padof = {}          # (ref, num) -> (pos, net_name)
by_net = {}         # net_name -> [(ref, num, pos)]
for fp in b.get_footprints():
    ref = fp.reference_field.text.value
    for pd in fp.definition.pads:
        net = pd.net.name if pd.net else ""
        padof[(ref, str(pd.number))] = (pd.position, net)
        by_net.setdefault(net, []).append((ref, str(pd.number), pd.position))

subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", "build/drc.json", BOARD],
               capture_output=True)
drc = json.load(open("build/drc.json"))

items, did, vias, trks = [], set(), 0, 0
for v in drc.get("unconnected_items", []):
    paddesc = next((i.get("description", "") for i in v.get("items", [])
                    if i.get("description", "").startswith("Pad ")), None)
    if not paddesc:
        continue
    m = re.match(r"Pad (\S+) \[(.+?)\] of (\S+)", paddesc)
    if not m:
        continue
    num, net, ref = m.group(1), m.group(2), m.group(3)
    key = (ref, num)
    if key in did or key not in padof:
        continue
    did.add(key)
    pos, _ = padof[key]
    if net in PLANE:
        via = Via()
        via.position = pos
        via.diameter = VIA_PAD
        via.drill_diameter = VIA_DRILL
        via.net = nets[net]
        items.append(via); vias += 1
    elif not VIAS_ONLY:
        cands = [p for p in by_net.get(net, []) if (p[0], p[1]) != key]
        if not cands:
            continue
        tgt = min(cands, key=lambda p: (p[2].x - pos.x) ** 2 + (p[2].y - pos.y) ** 2)
        t = Track()
        t.start = pos
        t.end = tgt[2]
        t.width = TRK_W
        t.layer = BoardLayer.BL_F_Cu
        t.net = nets[net]
        items.append(t); trks += 1

created = b.create_items(items)
b.refill_zones()
b.save()
print(f"finish_tail: stitch vias={vias}, pad-to-pad tracks={trks}, created={len(created)} -> saved")
