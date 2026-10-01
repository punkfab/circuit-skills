# circuit-skills — project history

The record of every board and simulation the circuit skills (pcb-layout, circuit-sim, pcb-enclosure-fit,
pcb-3d-render) were built on or used for: what was attempted, what broke, what the cause turned out to be,
what was abandoned. Written 2026-10-01 from the Claude Code session transcripts plus each project's git
history, so the work can be walked back.

## Start here

- **[problems.md](problems.md)** — every recurring problem, grouped (tscircuit export, Freerouting, KiCad
  automation, placement, finishing, verification gates, fab/BOM, simulation, rendering, process), with
  status and where the fix lives.
- **[open-items.md](open-items.md)** — what is still unsolved, and lessons that never made it into a skill.
- **[skill-evolution.md](skill-evolution.md)** — each skill commit and the project it came from.
- **[research/4-layer-planes.md](research/4-layer-planes.md)** — the GND/PWR-plane problem with Freerouting.

## Timeline

| Dates | Project | What | Skills | File |
|---|---|---|---|---|
| 2026-06-22→23 | sbs-synth | RP2350 cap-touch synth; tscircuit modules; where the placement-first method was worked out | (pre-repo) | [projects/2026-06-22-sbs-synth.md](projects/2026-06-22-sbs-synth.md) |
| 2026-06-24 | eurorack | Eurorack VCO module: ngspice + scripted KiCad (SWIG) + Freerouting + printed panel | (pre-repo) | [projects/2026-06-24-eurorack.md](projects/2026-06-24-eurorack.md) |
| 2026-06-25 | plasma-art | Resonant half-bridge / ZVS plasma driver; circuit-sim written here | circuit-sim | [projects/2026-06-25-plasma-art.md](projects/2026-06-25-plasma-art.md) |
| 2026-06-25 | haptic-drumstick | Solenoid driver sim + MuJoCo mechanism; first reuse of circuit-sim | circuit-sim | [projects/2026-06-25-haptic-drumstick.md](projects/2026-06-25-haptic-drumstick.md) |
| 2026-06-25→29 | flexisette | Cassette-shaped flex PCB behind a printed shell; most pcb-layout tooling born here | pcb-layout, pcb-enclosure-fit | [projects/2026-06-25-flexisette.md](projects/2026-06-25-flexisette.md) |
| 2026-06-30 | flex-led-matrix | Parametric flexible LED matrix; JLC cost model; pcb-3d-render born here | pcb-layout, pcb-3d-render | [projects/2026-06-30-flex-led-matrix.md](projects/2026-06-30-flex-led-matrix.md) |
| 2026-06-30→07-01 | einhander | 4-layer RP2040 USB-MIDI keypad; the 4-layer Freerouting recipe; shipped hand-finished | pcb-layout | [projects/2026-06-30-einhander.md](projects/2026-06-30-einhander.md) |
| 2026-09-14 | thermal-bracelet | Thermoelectric harvester (LTC3108) sim + product renders | circuit-sim | [projects/2026-09-14-thermal-bracelet.md](projects/2026-09-14-thermal-bracelet.md) |
| 2026-09-25→26 | circuit-decimator | Component-level circuit-sim audio plugins, ngspice as reference | circuit-sim | [projects/2026-09-25-circuit-decimator.md](projects/2026-09-25-circuit-decimator.md) |
| 2026-09-29 | ir-harness | Audio impulse-response measurement harness (adjacent; no skill loaded) | — | [projects/2026-09-29-ir-harness.md](projects/2026-09-29-ir-harness.md) |
| 2026-09-28→10-01 | einhander rerun | Unattended re-route vs the shipped board; found the DSN mirror bug | pcb-layout | [projects/2026-10-01-einhander-rerun.md](projects/2026-10-01-einhander-rerun.md) |

## Five things the history says

1. **Placement sets routing difficulty** — confirmed on every board; the north star held.
2. **The generator's exports were the biggest hidden cost.** Dropped pours, ignored via sizes, missing
   cutouts, fragmented nets, a malformed DSN `(wiring)`, and mirrored DSN images — the last one was mistaken
   for router weakness for three months.
3. **Success signals lied repeatedly** (exit 0, "1 passed", 0 parts read as faithful, CLEAN with open nets).
   Every fix was an independent gate; trust the gate, then audit the gate.
4. **Freerouting is a good signal router and a poor power router.** 4-layer planes remain the open problem.
5. **Lessons leak out of the skills** — circuit-decimator, thermal-bracelet and plasma-art's later work
   never fed back; the deployed pcb-layout copy drifted from the repo until it was symlinked.

## How this was compiled (to dig deeper)

Sessions were found by scanning `~/.claude/projects/*/*.jsonl` for actual tool use (Skill calls to these
skills; Bash commands running `tsci`, `freert`, `kicad-cli`, `ngspice`, `pcbnew`, the routing scripts) —
16 transcripts, 13 after removing duplicates from moved project dirs. Each was condensed (user messages,
assistant text, tool calls and errors) and read in full; facts were cross-checked against each repo's git
log. Every project file lists its session ids, so the raw transcript is
`~/.claude/projects/<project-dir>/<session-id>*.jsonl` on Dan's machine. Transcript timestamps are UTC; git
commit times are local (UTC−7). Inferences are marked "(inferred)".
