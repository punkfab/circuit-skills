# Open items — unsolved problems and lessons not yet in the skills (as of 2026-10-01)

## Unsolved engineering problems

1. **4-layer GND/PWR planes** — Freerouting won't fan out to inner planes; 36 % of einhander's track is
   power on signal layers. Proposed: plane-fanout pre-pass with fixed vias.
   → [research/4-layer-planes.md](research/4-layer-planes.md)
2. **Freerouting drops a net silently** (einhander QSPI_SCLK after the DSN fix) and **leaves USB_DP one
   pad short**. Root cause unknown. → [rerun](projects/2026-10-01-einhander-rerun.md)
3. **No working automated tail pass** — frozen-wiring second pass stalls Freerouting 2.2.4. Options: a
   small finisher that routes only open nets around existing copper, or hand-route.
4. **`pcbnew.ExportSpecctraDSN` — conflicting evidence.** Eurorack (KiCad 9.0.3) got it to work once the
   output folder existed; flexisette and the 2026-10-01 rerun (folder existed) got `False`. pcb-layout
   SKILL.md says "NO automation of the DSN export — period". Worth a minimal repro (blank board vs a
   tscircuit-exported board) before trusting either.
5. **flexisette tail** — 10 unconnected incl. DIN in a congested cap cluster; GND-pad vias shorting
   against Freerouting stubs; JLC DFM dangers deferred; board 102.2 mm vs shell 100.5 mm.
6. **Placement edits don't flow back into the routing DSN** automatically (flexisette roadmap).
7. **3D body/keycap collisions** aren't gated (courtyards are smaller than bodies) — einhander tact vs
   keyswitch. Candidate pcb-enclosure-fit gate.

## Lessons not yet in a skill

### pcb-layout
- `tsci init -y` is not a valid option and interactive `init` crashes in a non-TTY shell (flex-led-matrix);
  the Setup snippet at SKILL.md `:38` is stale → use `npm init` + `npm install`.
- JLC **catalog stock ≠ assembly-ready stock**; check the part page's assembly availability.
- Big regular arrays (≈256+ parts): pin `schX/schY` or the schematic packer runs out of iterations; or
  generate the KiCad board directly (flex-led-matrix `gen/`).

### circuit-sim (unchanged since `8f488ba`, 2026-06-27)
- Self-oscillating ZVS / Royer convergence recipe: soft ramped kick, `rshunt`, avoid k≈1 coupling
  matrices ("not positive definite") — use uncoupled halves + ideal B-source transformer
  (plasma-art `sim/zvs_royer.cir`); dot-convention errors produce plausible-but-wrong leakage modes.
- ngspice is **non-deterministic when run in parallel** on B-source hysteresis decks → run sequentially,
  `OMP_NUM_THREADS=1` (circuit-decimator).
- `.tran` with brace expressions → "TSTOP is invalid"; `.func` "no such function" → precompute `.param`.
- F/E-source transformer polarity mistakes show up as "timestep too small"; a shunt inductor loop with an
  E-source is singular → add 1e-12 Ω series R.
- Fade stimulus in over a few cycles (abrupt sine start leaves core remanence).
- Always keep an analytic cross-check; sim-vs-sim agreement can hide solver spikes (ir-harness).

### pcb-3d-render
- `LC_ALL=C` makes the OCIO segfault rarer, not gone (~1 in 6 still crash) → retry loop.
- Blender 5.2.0 segfaults on every headless run (oneAPI / Level Zero device probe) → pin the binary
  (`/opt/blender-5.0.1`).

### General / process
- `pkill -f <pattern>` matches its own shell (hit in 3 projects) — kill by PID.
- Absolute paths in project scripts break on repo moves; plasma-art `sim/` still has them.

## Uncommitted / unpushed work found while compiling this

- flexisette: speaker sim + chamber work (2026-06-29) and post-move path fixes uncommitted.
- thermal-bracelet: `docs/design_notes.md`, `docs/energy_budget.md` uncommitted.
- circuit-decimator: `f6ffcbc` unpushed; `move-project --final` cleanup never run (punkfab path is a
  symlink).
- plasma-art: rewritten `sim/` paths uncommitted (and still absolute).
