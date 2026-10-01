# Problem catalog — every recurring problem across the circuit-skills projects

One line per problem, grouped by where it bites. **Status:** ✅ fixed · 🔧 worked around · ❌ abandoned ·
⏳ open. **Where** is the script / skill section / commit that holds the fix. Full context (symptoms, exact
errors, what was tried) is in the project files under [projects/](projects/) — the project column links there.

Projects: [sbs](projects/2026-06-22-sbs-synth.md) · [euro](projects/2026-06-24-eurorack.md) ·
[flex](projects/2026-06-25-flexisette.md) · [haptic](projects/2026-06-25-haptic-drumstick.md) ·
[plasma](projects/2026-06-25-plasma-art.md) · [ein](projects/2026-06-30-einhander.md) ·
[led](projects/2026-06-30-flex-led-matrix.md) · [brace](projects/2026-09-14-thermal-bracelet.md) ·
[deci](projects/2026-09-25-circuit-decimator.md) · [ir](projects/2026-09-29-ir-harness.md) ·
[rerun](projects/2026-10-01-einhander-rerun.md)

## 1. tscircuit (generator) — export defects and solver limits

The single biggest source of lost time. **tscircuit's exports silently drop or corrupt geometry; every
export needs an independent gate.**

| Problem | Proj | Root cause | Status | Where |
|---|---|---|---|---|
| Top-side parts routed as mirrored bottom-side parts (shorts/opens clustered on a few 2-pin parts) | ein, rerun | DSN `(image)` deduped by footprint name; first instance (bottom-side C11) defines it | ✅ 2026-10-01 | `dsn_split_sides.py`, SKILL "Mixed-side footprints" (`d064432`) |
| `<copperpour>` missing from the KiCad board (0 zones) | flex, ein | pour dropped on export | 🔧 | `add_plane.py` via IPC |
| Via size props ignored; board props don't reach subcircuits (435 DRC on export) | flex | tsci export behaviour | 🔧 tracks via `lib/fab.tsx`, vias KiCad-side | `rules/fab.tsx`, `apply_fab_rules.py` |
| Polygon cutouts export as 0 shapes; outline JSON exterior-only | flex | export limitation | 🔧 rect/circle holes only | SKILL pitfall |
| Malformed DSN `(wiring)` (85 bogus power vias, `padstack name expected at 'V3V3'`); all layers `(type signal)` | ein | DSN exporter | ✅ | `dsn_4layer_planes.py` |
| Cross-subcircuit nets fragmented (false shorts: SDA 5 nets, V3V3 9) | flex, ein | per-subcircuit net scoping | ✅ `merge_nets.py` (KiCad only); ein flattened to global nets | `merge_nets.py`, SKILL "Modular vs non-modular" |
| Duplicate refdes across modules | flex | module-local names | ✅ | SKILL pitfall |
| Full ~50-part board hangs at "Created 24 sub-solvers" (12 min, exit 137, 0 traces) | sbs | never isolated | 🔧 split into `<subcircuit>` modules | SKILL "Modular vs non-modular" |
| Default capacity-mesh router "ran out of iterations", 0 traces | sbs | capacity-autorouter | ✅ `autorouter="sequential-trace"` | SKILL routing recipe |
| sequential-trace output dirty (1113 DRC, 39 shorts, 35 crossings) | sbs | greedy router | ❌ as final router; keep placement, route elsewhere | TOOL_CHOICE / SKILL "Tool choice" |
| `layoutMode="pack"` stacks every part | sbs | immature auto-layout | ❌ → code placement, later `autoplace.mjs` | `201608f` |
| In-tool `autorouter="freerouting"` doesn't drive local Freerouting | flex | preset falls back | ❌ | SKILL "Finishing the routing tail" |
| 512-part board: layout solver / PackSolver2 out of iterations | led | schematic auto-layout runs even for PCB-only parts; ~256-part limit | 🔧 pin `schX/schY`; generator + KiCad for big arrays | pcb-3d-render Path A |
| No keep-in: parts placed in notch / cutout / off-board (16 off-board) | flex | tscircuit has no keep-in; error buried | ✅ | `outline-check.mjs` |
| `tsci export` always writes `index.circuit.kicad_pcb`; absolute `-o` path mangled | flex | CLI | 🔧 | pcb-enclosure-fit `import_pcb.py` |
| `tsci help/check` silent when piped; `env: bun not found`; `--pcb-png` is boolean; `tsci init -y` unknown / init crashes in non-TTY | sbs, led | CLI quirks | 🔧 | SKILL setup (⚠ `tsci init` snippet still stale) |
| Built-in `usb_c` has no ports/footprint; sequential-trace needs explicit footprints | sbs | parts engine | ✅ import TYPE-C-31-M-12 | `imports/` |
| ESP32 EPAD pads 42–49 floating | flex | split paste pads | ✅ | SKILL pitfall |

## 2. Freerouting (router)

| Problem | Proj | Root cause | Status | Where |
|---|---|---|---|---|
| Can't keep GND/PWR on inner planes (power snaked on F/B.Cu: 156+98 segments; 507 mm in 2026-10 rerun) | ein, rerun | no plane fanout; `(type power)` only excludes signals; `(plane …)` parsed but ignored | ⏳ | [research/4-layer-planes.md](research/4-layer-planes.md) |
| v2.1.0: never stops / ignores pass caps; writes SES only at 0 unrouted; maze NPE at 4 unrouted | flex, ein | v2.1.0 bugs | 🔧 2-layer: capped `freeroute.sh`; 4-layer: v2.2.4 | `freeroute.sh`, `route4.sh` |
| v2.2.4 class file v69 → needs JDK 25; rejected tsci DSN on flexisette | flex, ein | version | ✅ `~/jdk25` + `freert224` wrapper | SKILL |
| SES won't import: empty `(host_version )` | flex | Freerouting writes it empty | ✅ sed patch (superseded by IPC injection) | `freeroute.sh` |
| `-i/-o` flags rejected ("input and output must be specified") | euro | flags are `-de/-do` | ✅ | — (stale memory note was wrong) |
| Runaway Java at 100 % CPU after plugin experiments (pkill also killed Dan's KiCad) | flex | uncapped GUI/plugin runs | ✅ "never grind" + caps/timeouts | SKILL "Cap the router" |
| Routes straight across NPTH holes (11 traces on ein) | flex, ein | NPTH has no copper → no obstacle | ✅ | `add_npth_keepouts.py`, SKILL "Two traps" |
| Lands opposite-layer copper on SMD pads with no via (floating pads) | ein | (2026-10: largely the DSN mirror bug) | ✅ detector | `check_floating.py` |
| "Non-deterministic" tail | ein, rerun | it's deterministic per DSN; inputs were changing | ✅ corrected | SKILL heuristics (`d064432`) |
| Silently omits a net from the SES while reporting completion (QSPI_SCLK) | rerun | never found; deterministic for that DSN | ⏳ | SKILL "Freerouting tail dead-ends" |
| Frozen wiring (tail-only 2nd pass) stalls after 0–2 passes; fixed vias OK | rerun | never found | ❌ | `pcb-rerun/scripts/dsn_freeze_ses.py` (dead end) |
| v2.4.1: 1376 violations, ~90 s/optimizer pass | rerun | — | ❌ stay on 2.2.4 | SKILL |
| Pad-clip shorts where the router squeezes past wide pads | flex | clearance at pads | ✅ surgical fix (clearance bumps failed) | SKILL surgical short-fix (`76b4735`) |
| DSN routed at 0.15 mm vs netclass 0.20 → 198 clearance violations; vias below JLC min | ein | rule mismatch | ✅ | `apply_fab_rules.py`, fanout via 0.6/0.3 |

## 3. KiCad automation (SWIG, IPC/kipy, kicad-cli)

| Problem | Proj | Root cause | Status | Where |
|---|---|---|---|---|
| No headless Specctra round-trip (SWIG `ImportSpecctraSES` throws, GUI plugin fails) | flex | SWIG binding broken / deprecated in KiCad 9 | ❌ → IPC injection | `apply_ses_ipc.py`, SKILL IPC section |
| `pcbnew.ExportSpecctraDSN` returns False | flex, rerun | **unresolved** — eurorack got it working once the output folder existed; rerun failed with an existing folder | ⏳ conflicting evidence | [projects/2026-06-24-eurorack.md](projects/2026-06-24-eurorack.md), [rerun](projects/2026-10-01-einhander-rerun.md) |
| SWIG text injector guessed nets → 31 unrouted / ~50 shorts | flex | geometric net guessing | ❌ | `apply_ses.py` (obsolete) |
| kipy "connection refused" | flex | API server off by default; Bash reaps `setsid`; stale lock | ✅ | SKILL IPC section |
| IPC server dies between shell calls; sandbox exit 144 | ein | GUI process lifetime | ✅ one process per call | `apply_fix.sh`, `diag_ipc.sh` |
| `create_items` handles vs originals; `get_tracks()` has no vias | ein | kipy API | ✅ documented | SKILL kipy gotchas |
| Injector via size / 9 unmapped nets (`_source_component` infix); snapping backfired | flex | naming | ✅ (snapping reverted) | `apply_ses_ipc.py` |
| `pcbnew` not importable from pyenv; inserting dist-packages first shadows numpy | euro, rerun | system-only module | ✅ append path / use `/usr/bin/python3` | `toolkit/_env.py`, `dsn_split_sides.py` shebang |
| `SetCopperEdgeClearance` AttributeError; fields come back as `SwigPyObject`; `fp.Remove()` segfault | euro | KiCad 9.0.3 SWIG API | ✅ | eurorack `pcb.py` |
| NewBoard clearances 0 → GND pour 0 mm from NPTH; rule-area blocks pads | euro | defaults | ✅ pour-only keepouts | eurorack `pcb.py` |
| `kicad-cli drc` never failed the build; stray `.rpt` | euro | defaults | ✅ `--exit-code-violations --output` | eurorack Makefile |

## 4. Placement

| Problem | Proj | Root cause | Status | Where |
|---|---|---|---|---|
| Routing fails → it's placement (MCU QSPI 16 → 3 unrouted by edge-aware placement) | sbs, flex, ein | placement sets routing difficulty | ✅ the north star | SKILL "Placement is the whole game" |
| Decaps crowd the QFN escape on 2 layers | sbs, ein | caps under/at the pins | ✅ `Decap` helper + bottom side; keep under-QFN clear on 4-layer | `place.tsx`, SKILL heuristics |
| Optimising routability shoved blocks into the notch / onto a reel | flex | outline gate skipped | ✅ 3-gate order (outline → courtyard → unrouted) | `route.sh`, SKILL (`a3498aa`) |
| Courtyard overlaps → real GND/PWR shorts | ein | tight passives; outline-check can't see courtyards | ✅ run `drc_check` courtyard early | SKILL |
| Floorplan doesn't fit (33 mm block in 24 mm region) | flex | redundant parts | ✅ | `9aa73bb` |
| Board area too tight (QFN band 13 mm → ~12 unrouted; 19–25 mm → ~5) | ein | density | ✅ | SKILL heuristics |
| GPIO "escape" reassignment made it worse (37 incomplete) | ein | wrong orientation guess | ❌ reverted | — |
| Placement nudges in KiCad don't reach the routing DSN | flex | `route.sh` exports DSN from `.tsx` | ✅ partly: positions-as-data round-trip | `sync_positions.py`/`apply_placement.py` (`c33adf9`) |
| Ratsnest tangles from part rotation | flex | — | ✅ | `untangle.mjs` (`c9b2af4`) |
| Keyswitch vs tactile 3D collision not caught | ein | courtyards smaller than bodies/keycaps | 🔧 moved parts; no gate | pcb-enclosure-fit territory |

## 5. Finishing the tail

| Problem | Proj | Root cause | Status | Where |
|---|---|---|---|---|
| Blind finishers add shorts (16/11/8; 33 plane-vs-signal) | ein | copper in congested corners | ✅ DRC-verified / monotonic finishers | `finish_iter.py`, `finish_converge.py`, `fanout_planes.py` |
| Finisher reported OK but connected nothing (B.Cu track to F.Cu pad, no via) | ein | acceptance checked shorts only | ✅ | SKILL note |
| Hard-coded-coordinate patches (`fix_ldo_planes`, `patch_stragglers`, `reconnect_j14`) broke on re-route and hid the root cause | ein, rerun | DSN mirror bug (2026-10 finding) | ✅ superseded | SKILL "Don't hardcode finisher coordinates" |
| GND-pad vias create shorts with stray foreign stubs | flex | Freerouting stubs | ⏳ | — |
| 10 unconnected incl. DIN in a congested cap cluster | flex | — | ⏳ | — |
| One net can't cross a corridor | ein | topology | ✅ 0 Ω jumper / local pour (Dan's idea) | SKILL heuristics |

## 6. Verification gates that lied

Recurring pattern: **a success signal that isn't** — fixed each time by an independent check.

| Problem | Proj | Status | Where |
|---|---|---|---|
| "Fully routed" with 16/10/4 unrouted (trace counts, "1 passed", exit 0) | sbs | ✅ grep "Could not find a route" + DRC | `routecheck.sh` |
| place-sweep read an empty log as 0 unrouted (`timeout PATH=… tsci` couldn't exec) | flex | ✅ | `place-sweep.mjs` |
| Round-trip fidelity "pass" with 0 parts read (quoted vs unquoted layer token) | flex | ✅ | `sync_positions.py` |
| Window-crossing check only looked at endpoints; gr_poly regex missed newlines | flex | ✅ | `add_cutout_keepouts.py` (`c94e495`) |
| Copper over the board edge bucketed as cosmetic | flex | ✅ | `drc_check.py` edge-over-cut (`76b4735`) |
| NPTH `hole_clearance actual 0.000` bucketed as fab/cosmetic | ein | ✅ documented | SKILL "Two traps" |
| `drc_check` printed CLEAN with unconnected > 0 (≥ 8 times in July) | ein, rerun | ✅ 2026-10-01 | `drc_check.py` (`d064432`) |
| KiCad DRC passes a via 0.04 mm from a mount hole | ein | ✅ | `dfm_check.py` (`8522e8a`) |
| Severity downgrades hid real JLC DFM dangers | flex | ⏳ deferred | flexisette `docs/fabrication.md` |

## 7. Fab bundle, BOM, sourcing

| Problem | Proj | Status | Where |
|---|---|---|---|
| Parts too scarce at JLC (BS8116A-3: 25, RP2354A: 184) | sbs | ✅ swapped parts | SKILL stock-check |
| Catalog stock ≠ assembly-ready stock (360k listed, "In Stock 0" for assembly) | led | 🔧 pre-order/consign | ⚠ not in skill |
| Invented placeholder LCSC number | led | ✅ | — |
| JLC "error processing BOM" (extra column, blank rows, `Ω`) | ein | ✅ | `gen_bom.py` (`5ec62e3`) |
| CPL/BOM designator mismatch; CPL headers | ein | ✅ | `make_fab.sh` (`bb8aef8`) |
| Gerber zip missed copper layers (`*.gbr` glob) | ein | ✅ | `make_fab.sh` |
| Cost model off in the breakdown (fixture $189 vs $49.25 quote) | led | ✅ recalibrated to a real quote | flex-led-matrix `gen/generate.py` |

## 8. Simulation (ngspice, Falstad) — mostly NOT in the circuit-sim skill yet

| Problem | Proj | Status | Where |
|---|---|---|---|
| Hand-placed Falstad netlists drift from the deck | plasma | ✅ generate Falstad from the SPICE deck | circuit-sim north star |
| `i(Mxxx)` unreliable | plasma | ✅ 0 V sense sources | circuit-sim |
| `np.trapz` gone in numpy 2 | plasma | ✅ | circuit-sim |
| Makefile inline comment → trailing spaces in a filename | plasma | ✅ | circuit-sim |
| Self-oscillating ZVS: "timestep too small", parasitic leakage modes, coupling matrix "not positive definite" | plasma | ✅ soft ramped kick, `rshunt`, uncoupled halves + ideal B-source transformer | ⚠ `zvs_royer.cir` only — not in skill |
| ngspice non-deterministic when run in parallel (4.81 % vs 0.062 % THD) | deci | 🔧 sequential, `OMP_NUM_THREADS=1` | ⚠ not in skill |
| `.tran` brace expressions → "TSTOP is invalid"; `.func` "no such function" | deci | 🔧 literals / `.param` | ⚠ not in skill |
| F-source polarity → "timestep too small"; shunt-L + E-source → singular matrix | deci | ✅ node order / 1e-12 Ω series R | ⚠ not in skill |
| Core remanence from abrupt sine start | deci | ✅ 4-cycle fade-in | ⚠ not in skill |
| Behavioural op-amp pole at 100 Hz gave wrong VCO amplitude | euro | ✅ µs pole | eurorack `models.spice` |
| Sim-vs-sim agreement hid DK-solver spikes (27 V on a 9 V circuit) | ir | ⏳ | ir-harness |
| Default MuJoCo mesh inertia overstates mass (82.6 vs 66.9 g) | haptic | ✅ `inertia="exact"` | mujoco-sim skill |

## 9. Rendering (Blender, GLB) — pcb-3d-render / pcb-enclosure-fit

| Problem | Proj | Status | Where |
|---|---|---|---|
| Blender 5 removed `scene.node_tree` (compositor) | led, brace | 🔧 skip bloom / point-light glow | pcb-3d-render Gotchas |
| OCIO segfault (~1 in 6 runs) even with `LC_ALL=C` | flex, brace | 🔧 retry loop | ⚠ skill says LC_ALL=C fixes it — only partial |
| Blender 5.2.0 segfaults every headless run (oneAPI/Level Zero probe) | brace | 🔧 pin `/opt/blender-5.0.1` | ⚠ not in skill |
| `\| head` SIGPIPE kills Blender mid-render | led | ✅ | pcb-3d-render Gotchas |
| Emissive LEDs render matte | led | ✅ emit boost + dark world | `blender_panel.py` |
| Claimed tscircuit has no 3D (it does: `tsci snapshot --3d`, `export -f glb`) | flex, led | ✅ | pcb-3d-render "Decide the path" |
| OLED missing from GLB (no CDN model) | flex | ✅ | flexisette `merge_oled_glb.py` |
| Stale GLB after a move | ein | ✅ `make glb` | einhander Makefile |

## 10. Process, environment, repos

| Problem | Proj | Status | Where |
|---|---|---|---|
| `pkill -f <pattern>` kills its own shell | sbs, deci, rerun | ✅ match exact PID/subcommand | — (recurs; worth a global note) |
| bun child re-parented and survives kill | sbs | ✅ kill the bun PID | — |
| Deployed skill copy drifted from the repo | ein, rerun | ✅ symlink `~/.claude/skills/pcb-layout` → repo; sync 2026-10-01 | `8e75d2a`, `d064432` |
| Absolute paths break after repo moves | plasma, sbs, deci, flex | 🔧 move-project skill; plasma `sim/` still absolute | ⏳ plasma-art |
| Parallel sessions editing one repo clobbered each other | deci | ✅ diff before commit | — |
| KiCad junk committed to a public repo | flex | ✅ `.gitignore` | `8902d40` |
| Memory note had wrong Freerouting flags | euro | ✅ | — |
