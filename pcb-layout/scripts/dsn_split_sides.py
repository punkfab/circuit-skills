#!/usr/bin/python3
"""dsn_split_sides.py — fix tscircuit's DSN when one footprint is used on BOTH board sides.

tscircuit's specctra-dsn export dedupes images by footprint name ("simple_capacitor:2.85x1.4_mm").
The FIRST instance defines the image — if that one is layer="bottom", the image gets mirrored pin
X and [B] (B.Cu) padstacks, and every TOP-side instance of the same footprint silently inherits
them. Freerouting then routes those parts as if they were on the bottom and mirrored: the SES lands
B.Cu traces on the WRONG pads, no via -> "unconnected" + cross-net shorts after injection
(einhander: C_IN/C_OUT/C_LED shared the 0805 image with bottom-side C11 -> 1 short + 6 unconnected,
previously hand-patched by coordinate in fix_ldo_planes.py / patch_stragglers.py).

The exported .kicad_pcb is correct per part, so it is the truth. Compare every DSN pin in ABSOLUTE
board coordinates (place + rotated image pin) against pcbnew's absolute pad position + copper side;
any part that disagrees gets a private image rebuilt from the KiCad pads (+ a side-swapped padstack
clone if needed) and its place moved into it. Idempotent.

usage: /usr/bin/python3 dsn_split_sides.py <board.kicad_pcb> <board.dsn>   (rewrites the DSN in place)
Needs KiCad's pcbnew module (system python, not a pyenv/venv one).
"""
import math, re, statistics, sys
import pcbnew

board, dsn = sys.argv[1], sys.argv[2]
D = open(dsn).read()
B = pcbnew.LoadBoard(board)

# ---- KiCad truth: ref -> (pos_mm, {pad: (abs_x_mm, abs_y_mm, side)}) --------------------------
kfp = {}
for fp in B.GetFootprints():
    pads = {}
    for p in fp.Pads():
        if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD: continue
        q = p.GetPosition()
        pads[p.GetNumber()] = (q.x / 1e6, q.y / 1e6, 'B' if p.IsOnLayer(pcbnew.B_Cu) else 'F')
    q = fp.GetPosition()
    kfp[fp.GetReference()] = ((q.x / 1e6, q.y / 1e6), pads)

# ---- DSN images / places ---------------------------------------------------------------------
imgs = {}
for im in re.finditer(r'\(image "([^"]+)"\n((?:\s+\(pin [^\n]*\n)+)', D):
    imgs[im.group(1)] = [(m.group(1), m.group(2), float(m.group(3)), float(m.group(4)))
                         for m in re.finditer(r'\(pin (\S+) (\S+) ([-\d.e]+) ([-\d.e]+)\)', im.group(2))]
PLACE = re.compile(r'\(place (\S+?)_source_component_\d+ ([-\d.e]+) ([-\d.e]+) (front|back) ([-\d.e]+)')
places = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(5))) for m in PLACE.finditer(D)}

# DSN (um, y-up) -> KiCad (mm, y-down): kicad = (ox + x/1000, oy - y/1000); offset from the parts.
common = [r for r in places if r in kfp]
ox = statistics.median(kfp[r][0][0] - places[r][0] / 1000 for r in common)
oy = statistics.median(kfp[r][0][1] + places[r][1] / 1000 for r in common)

def side_of(ps): return 'B' if '[B]' in ps else 'F' if '[T]' in ps else None

def pin_abs(place, x, y):
    px, py, rot = place; c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return ox + (px + x * c - y * s) / 1000, oy - (py + x * s + y * c) / 1000

def mismatch(img, ref):
    pads = kfp[ref][1]
    for ps, pin, x, y in imgs[img]:
        if pin not in pads: continue
        kx, ky, ks = pads[pin]; ax, ay = pin_abs(places[ref], x, y)
        if (side_of(ps) and side_of(ps) != ks) or abs(ax - kx) > 0.002 or abs(ay - ky) > 0.002:
            return True
    return False

def local_pin(ref, pin):            # KiCad abs pad -> DSN image-local um (undo place offset + rotation)
    kx, ky, _ = kfp[ref][1][pin]; px, py, rot = places[ref]
    dx, dy = (kx - ox) * 1000 - px, -(ky - oy) * 1000 - py
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return round(dx * c + dy * s, 4), round(-dx * s + dy * c, 4)

pstacks = set(re.findall(r'\(padstack "([^"]+)"', D))
def clone_padstack(ps, to_side):
    global D
    new = ps.replace('[B]', '[T]') if to_side == 'F' else ps.replace('[T]', '[B]')
    if new not in pstacks:
        m = re.search(r'\n(\s*)\(padstack "' + re.escape(ps) + r'"\n[\s\S]*?\n\1\)', D)
        body = m.group(0).replace(ps, new)
        body = body.replace('B.Cu', 'X.Cu').replace('F.Cu', 'B.Cu').replace('X.Cu', 'F.Cu')
        D = D.replace(m.group(0), m.group(0) + body, 1)
        pstacks.add(new)
    return new

new_images, fixed = [], []
for cm in list(re.finditer(r'\n(\s*)\(component "([^"]+)"\n((?:\s+\(place [^\n]*\n)+)(\s*)\)', D)):
    ind, img, plines = cm.group(1), cm.group(2), cm.group(3)
    if img not in imgs: continue
    keep, moved = [], []
    for pl in plines.splitlines(keepends=True):
        m = PLACE.search(pl); ref = m.group(1) if m else None
        (moved if ref in kfp and ref in places and mismatch(img, ref) else keep).append((ref, pl))
    if not moved: continue
    blocks = f'\n{ind}(component "{img}"\n' + ''.join(pl for _, pl in keep) + f'{ind})' if keep else ''
    for ref, pl in moved:
        nimg = f'{img}@{ref}'; pins = []
        for ps, pin, _, _ in imgs[img]:
            if pin not in kfp[ref][1]: continue
            ks = kfp[ref][1][pin][2]
            nps = clone_padstack(ps, ks) if side_of(ps) and side_of(ps) != ks else ps
            lx, ly = local_pin(ref, pin)
            pins.append(f'      (pin {nps} {pin} {lx} {ly})\n')
        new_images.append(f'    (image "{nimg}"\n' + ''.join(pins) + '    )\n')
        blocks += f'\n{ind}(component "{nimg}"\n{pl}{ind})'
        fixed.append(f'{ref} ({img})')
    D = D.replace(cm.group(0), blocks, 1)

if new_images:
    D = re.sub(r'(\n\s*\(library\n)', lambda m: m.group(1) + ''.join(new_images), D, count=1)
open(dsn, 'w').write(D)
print(f"dsn_split_sides: {len(fixed)} part(s) given a private image (shared image disagreed with KiCad pads)"
      + (': ' + ', '.join(fixed) if fixed else ''))
