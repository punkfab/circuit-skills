# How the skills evolved — commit by commit, and where each piece came from

| Date | Commit | Change | Born in |
|---|---|---|---|
| 2026-06-22→23 | — (before the repo) | Placement-first method, "every autorouter is immature", modular `<subcircuit>` blocks, `sequential-trace`, Decap helper + pin-map generator, stock-check, tscircuit-as-generator / KiCad-as-finisher | [sbs-synth](projects/2026-06-22-sbs-synth.md) (`PCB_WORKFLOW.md`, `TOOL_CHOICE.md`) |
| 2026-06-25 | — (local skill) | circuit-sim written: two-pass Falstad → ngspice, one SPICE deck as source of truth, Falstad generated from the deck | [plasma-art](projects/2026-06-25-plasma-art.md); first reused in [haptic-drumstick](projects/2026-06-25-haptic-drumstick.md) |
| 2026-06-26 | — (local skill) | fab rulesets, outline-check | [flexisette](projects/2026-06-25-flexisette.md) |
| 2026-06-27 | `8f488ba` | Repo created: pcb-layout (SKILL + rules + 17 scripts: route.sh, freeroute.sh, apply_ses_ipc, add_plane, merge_nets, add_cutout_keepouts, drc_check, outline-check, place-sweep, …) + circuit-sim | sbs-synth, flexisette, plasma-art |
| 2026-06-27 | `a3498aa` | Headless IPC routing; 3-gate placement convergence (outline → courtyard → unrouted) | flexisette |
| 2026-06-27 | `201608f` | `autoplace.mjs` block autoplacer + unit tests | flexisette |
| 2026-06-27 | `e2a80ea` | outline-check `ALLOW_IN_CUTOUT` (display behind a window) | flexisette (OLED) |
| 2026-06-27 | `c94e495` | Window-keepout polygon fix; `apply_fab_rules.py` (DRC to fab minimums: 216 → 23) | flexisette |
| 2026-06-28 | `76b4735` | pcb-enclosure-fit skill; surgical short-fix; edge-over-cut DRC bucket | flexisette |
| 2026-06-28 | `c33adf9` | Round-trip floorplan loop (positions-as-data, variants, connector edge) | flexisette |
| 2026-06-28 | `c9b2af4` | `untangle.mjs` (part rotation to shorten the ratsnest) | flexisette |
| 2026-06-30 | `6db19bc` | pcb-3d-render skill (`tsci snapshot --3d` vs GLB → Blender) | [flex-led-matrix](projects/2026-06-30-flex-led-matrix.md) |
| 2026-07-01 | `8e75d2a` | 4-layer recipe (`route4.sh`, freert224/JDK 25, `dsn_4layer_planes`), NPTH keepouts, `check_floating`, `dfm_check`, `add_local_zone`, `fanout_planes`, fab bundle + BOM | [einhander](projects/2026-06-30-einhander.md) |
| 2026-09-28 | — | Repo transferred `dnewcome` → `punkfab` (move-project skill) | [rerun](projects/2026-10-01-einhander-rerun.md) |
| 2026-10-01 | `d064432` | `dsn_split_sides.py` (DSN mirror bug), `drc_check` unconnected = blocking, finishers synced from einhander, Freerouting dead-ends documented | [einhander rerun](projects/2026-10-01-einhander-rerun.md) |

## Projects that used the skills but fed nothing back

- **circuit-decimator** (2026-09-25→26) — loaded circuit-sim once; ~15 ngspice lessons, none in the skill.
- **thermal-bracelet** (2026-09-14) — circuit-sim + Blender; Blender 5.2 / OCIO findings not in pcb-3d-render.
- **eurorack** (2026-06-24) — its own KiCad-SWIG pipeline + Freerouting; predates the repo.
- **ir-harness** (2026-09-29) — adjacent (audio measurement), no skill loaded.

See [open-items.md](open-items.md) for the backlog.
