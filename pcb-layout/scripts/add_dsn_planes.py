#!/usr/bin/env python3
"""add_dsn_planes.py — declare GND/V3V3 as Specctra POWER PLANES in the DSN.

The right way to carry GND/V3V3 on a 4-layer board: don't drop them from the router
(that also deletes the short pin->decap escapes fine-pitch QFN power pins need, and
leaves you hand-placing fanout vias), and don't let the router string long cross-board
ground traces either. Instead declare each as a (plane) on its inner layer. Freerouting
2.2.4 parses (plane ...) (app/freerouting/io/specctra/parser/Plane.class) and then, for
a plane net, connects every pad to the plane with a SHORT escape + fanout via placed
collision-aware — exactly what we want, and no long traversal traces.

Assumes the inner layers are already (type power) (dsn_4layer_planes.py --relabel-power)
and GND/V3V3 are still in the (network). Inserts a rectangular plane polygon (board
boundary, inset) per net into (structure).

    python3 add_dsn_planes.py build/index.dsn GND=In1.Cu V3V3=In2.Cu [--inset 500]
"""
import re
import sys

dsn = sys.argv[1]
specs = [a for a in sys.argv[2:] if "=" in a]
inset = int(sys.argv[sys.argv.index("--inset") + 1]) if "--inset" in sys.argv else 500
t = open(dsn).read()

# board boundary rectangle (DSN units)
mb = re.search(r'\(boundary\s*\(path \S+ \S+\s+([-\d.\s]+)\)', t)
nums = [float(x) for x in mb.group(1).split()]
xs, ys = nums[0::2], nums[1::2]
x0, y0, x1, y1 = min(xs) + inset, min(ys) + inset, max(xs) - inset, max(ys) - inset
rect = f"{int(x0)} {int(y0)} {int(x1)} {int(y0)} {int(x1)} {int(y1)} {int(x0)} {int(y1)} {int(x0)} {int(y0)}"

planes = ""
for spec in specs:
    base, layer = spec.split("=")
    # resolve the real DSN net id (NAME or NAME_source_net_N)
    m = re.search(r'\(net\s+"(' + re.escape(base) + r'(?:_source_net_\d+)?)"', t)
    if not m:
        print(f"  net {base} not found in DSN; skipping"); continue
    nid = m.group(1)
    planes += f'\n    (plane "{nid}" (polygon {layer} 0 {rect}))'

# insert planes right after the (boundary ...) block, inside (structure)
i = t.index("(boundary")
depth = 0; e = i
while e < len(t):
    if t[e] == "(":
        depth += 1
    elif t[e] == ")":
        depth -= 1
        if depth == 0:
            break
    e += 1
t = t[:e + 1] + planes + t[e + 1:]
open(dsn, "w").write(t)
print(f"declared {len(specs)} plane(s): {specs} (inset {inset}u)")
