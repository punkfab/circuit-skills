# Research note — GND/PWR planes on 4-layer boards with Freerouting

**Status (2026-10-01): open.** The working recipe routes power as traces and pours the planes afterwards;
the planes are partly redundant. A plane-fanout pre-pass is the proposed next step (not yet built).

## The problem

On a 4-layer board we want **In1 = GND, In2 = 3V3** as solid planes, every power pad dropping straight to
its plane through a via, and **only signals** on F.Cu/B.Cu. Freerouting (the autorouter in the pipeline)
can't produce that. Dan's conclusion after einhander (July): it "was just not capable of keeping separate
ground and power planes on the middle layers", and he considered forking it or writing a router.

## What was tried (einhander, 2026-06-30 → 07-01, Freerouting 2.2.4)

| Strategy | Result | Why it fails |
|---|---|---|
| Relabel inner layers `(type power)`, keep GND/PWR in the netlist | Signals stay off inner layers, but GND/PWR are snaked as **156 GND + 98 V3V3 segments** on F.Cu/B.Cu | Relabel only excludes signals; the router still treats power nets as ordinary nets on outer layers |
| Drop GND/PWR from the routed netlist (`dsn_drop_nets.py`) | 42 signals routed clean, **18 QFN/decap power pads unconnected** | Discrete pads can take via-in-pad, but fine-pitch QFN pins (0.5 mm pitch) can't fit a JLC-legal 0.6 mm via; they need dogbone escapes only the router was placing |
| Declare DSN `(plane GND …)` (`add_dsn_planes.py`) | **0 plane vias, ~48 nets unrouted** | 2.2.4 parses `(plane …)` (`io/specctra/parser/Plane.class`) but never fans pads out to it |
| **Shipped recipe:** keep GND/PWR routed, pour inner zones in KiCad, finish corners, local GND pour under the QFN | Fabbable board | Power still travels mostly as outer-layer traces; planes only catch what reaches them by via |

## Measured state (2026-10-01)

GND + 3V3 copper on **signal layers**: shipped board **484.5 mm**, unattended rerun **507.0 mm** — about
**36 %** of all track on the rerun board (1421 mm). The DSN mirror fix (`dsn_split_sides.py`) does not
change this; it fixed a different defect.

## Findings that matter for a fix

- **Fixed vias don't stall Freerouting 2.2.4; fixed wires do.** Bisection on 2026-10-01: a DSN with only
  pre-placed `(via … (type fix))` routed normally (3 passes, exit 0); any fixed wires (even 10) stalled it.
- Freerouting is good at what's left once power is removed: on einhander, signals-only routed clean.
- The hard pads are the QFN power pins (RP2040 IOVDD/DVDD), not the two-pin decaps.
- `add_local_zone.py <ref> GND F.Cu` (a local pour under the QFN) already ties QFN ground pins into copper
  on their own layer without any wires.

## Options

1. **Plane-fanout pre-pass (recommended next step).** Our own code, a few hundred lines:
   - every GND/3V3 pad: via-in-pad where it fits (the pad is already that net's copper — no short risk on
     its own layer); collision-checked against foreign copper on both outer layers;
   - fine-pitch QFN pins: a short dogbone to a via outside the pad row *or* a local pour (no wires);
   - emit the vias as fixed `(wiring (via …))` in the DSN, drop GND/3V3 from the netlist, let Freerouting
     route signals only, pour the planes in KiCad.
   - **Risk:** dogbone stubs are wires — fixed wires stalled 2.2.4. The local-pour route avoids wires.
   - **Metric:** GND/3V3 on signal layers 507 mm → ~0, with shorts/unconnected no worse than today.
2. **Fork Freerouting** to implement plane fanout. It's a large Java codebase and we'd own the fork.
3. **Write a router.** Maze search, rip-up/retry, DRC-aware costs — all to get one missing feature.

Only go to 2 or 3 if the pre-pass fails.

## Pointers

- pcb-layout SKILL.md — "Layer stackup strategy — the high-pin-count lever" (the corrected recipe),
  "Fanning GND/PWR pads to the plane WITHOUT shorting", "Freerouting tail dead-ends".
- Scripts: `add_plane.py`, `add_local_zone.py`, `fanout_planes.py`, `finish_iter.py`, `stitch_planes.py`,
  `add_dsn_planes.py` (record of the failed `(plane …)` approach), `dsn_4layer_planes.py`.
- Project history: [../projects/2026-06-30-einhander.md](../projects/2026-06-30-einhander.md),
  [../projects/2026-10-01-einhander-rerun.md](../projects/2026-10-01-einhander-rerun.md).
