# Plasma Art — touch-reactive plasma tendril and globe art; the birthplace and worked example of the `circuit-sim` skill

- **Dates:** 2026-06-25 07:55 → 22:34 (main build-out), 2026-07-05 22:47 → 2026-07-06 00:04 (self-oscillating ZVS sim, docs, publish), 2026-08-28 20:30–20:33 (repo move) · **Sessions:** `ef5008b1` (dir `/home/dan/sandbox/dnewcome/plasma-art`, now `/home/dan/sandbox/dnuke-art/plasma-art`) · **Repo:** `dnewcome/plasma-art` → transferred to **`dnuke-art/plasma-art`** (public) · **Skills used:** **created `circuit-sim`** (2026-06-25 22:16) and used it 2026-07-05; `move-project` (2026-08-28)

## Goal
Plan and build plasma art. Dan started with a 15 kV / 30 mA magnetic neon-sign transformer and asked about pumps, gas and glassblowing. He settled on **touch-reactive tendrils** in his own filled glass. The electronics then became the creative focus. The chosen design is an **MCU-driven (ESP32 MCPWM) half-bridge → series-resonant flyback**, with 2–3 independent-frequency channels. Dan wanted to *see the circuit work* before buying parts. That produced the ngspice sims, the deck-to-Falstad generator, and the `circuit-sim` skill, whose stated purpose is: "for all of my electronics projects I'm going to want to do a lot of simulations before doing component selection and board design."

## Timeline
- **2026-06-25 07:55–08:06: NST vs. tendrils.**
  - A 60 Hz magnetic NST cannot make tendrils, which need tens of kHz and a single electrode.
  - Dan chose tendrils, fill-your-own blanks, and a magnetic NST (sidelined).
  - Project memory `plasma-art-direction.md` was saved.
- **14:54–17:29: Research docs.**
  - Pump choice: direct-drive 2-stage HVAC pump plus foreline trap.
  - Toroid vs. Lissajous video, Bill Parker history, globe and tube buying.
  - EEFL external electrodes, phosphor coatings.
  - Files: `README.md`, `plasma-tendril-art-plan.md`, `effects-and-physics.md`, `buying-guide.md`, `history-and-attribution.md`, `driver-build.md`, `vacuum-rig.md`.
- **17:30–17:50: Driver architecture.**
  - Dan picked "Full MCU-driven half-bridge" with MCU-animated patterns and manual knobs: `driver-schematic.md` (ESP32 MCPWM, UCC27201A, Cs plus flyback, Rsense → LM393 fault).
  - Dan bought a 4″ plasma toy as a test load.
  - Multi-channel spec: 2–3 channels, independent frequency, zones in **one shared-gas piece** → `multi-channel.md`.
- **18:31–18:49: First ngspice sims.**
  - Tools found: ngspice 44.2, numpy 2.4.4, scipy 1.17.1, matplotlib 3.10.8.
  - `sim/tank_ac.cir` gives **f₀ 46.3 kHz, gain ×489**. `tank_tran.cir` gives **7.63 kV peak secondary from 36 V, 11.74 A primary**.
  - `plot.py` adds a Cs→f₀ map.
- **19:07–19:11: `two_channel.cir`.** Two channels at 45 and 52 kHz into a shared gas node give **~40% crosstalk (39.4% / 40.7%) and a 7 kHz beat**.
- **19:41–19:56: Firmware.** PlatformIO skeleton with a portable `plasma_engine.h`, host-tested with g++ (STEADY/SWEEP/BREATHE/STROBE/BEAT), and an MCPWM layer behind `PLASMA_DRIVE_ENABLED=0`.
- **20:01–20:19: `zvs.cir`.** A VDMOS half-bridge at 36 V and 55 kHz with 400 ns deadtime. **ZVS achieved** (v(sw) −0.29 V at low-side turn-on, 36.08 V at high-side turn-on). FET loss is ~0.46 W total (Irms 1.85 A). `F_RES[]` in the firmware was moved above resonance.
- **20:20–21:15: `system_demo.py`.** The firmware engine's frequencies are mapped through the real `tank_ac.dat` curve to glow, rendered as `system_demo.mp4` (300 frames at 20 fps) plus a montage. Dan asked how to view it; answered with `xdg-open` / `ffplay` via the `!` prefix.
- **21:20–21:47: Falstad.**
  - Hand-written netlists (`falstad_lc_resonance.txt`, `falstad_resonant_driver.txt`) were authored "offline", unverified.
  - **Dan: "can we generate the falstad file programmatically from our netlist?"** That led to `sim/falstad_gen.py`, which parses `.param` and R/L/C from `tank_ac.cir` and later emits a MOSFET `falstad_zvs.txt` from `zvs.cir`.
- **21:30–21:41: BOM and tools.** `driver-bom.md` (~$65–100 for one channel, ~$120–190 for three). Dan has a PSU but no scope, so a $10 USB logic analyzer covers the gate/deadtime check.
- **21:51–22:08: Local CircuitJS1 target, then a bug.**
  - Dan wanted the Makefile to launch local CircuitJS1 (`pfalstad/circuitjs1`, `?cct=` param). Targets `circuitjs*`, `falstad`, `falstad-url` were added.
  - Dan then hit a Makefile inline-comment bug himself.
- **22:09–22:26: `circuit-sim` skill created.**
  - Written to `~/.claude/skills/circuit-sim/SKILL.md`, using `mujoco-sim` as a format template only.
  - Dan's feedback during the turn: (a) "unrelated to mujoco really, it's for general circuit sim"; (b) circuit → physics coupling is wanted eventually, but co-simulating is "a lot… maybe we can get there eventually", so a "Handoff to physics sim (keep them separate — for now)" section was added; (c) **use online Falstad**, so the Makefile default became `https://www.falstad.com/circuit/circuitjs.html`.
  - Memory `circuit-sim-workflow.md` was saved.
- **22:25**: Nine minutes after creation, the haptic-drumstick session (`37e9a6b9`) loaded the new skill. This was the first reuse.
- **22:33–22:34**: `/compact`.
- **2026-06-27 09:45**: The skill was copied into this repo (`circuit-skills` commit `8f488ba` "circuit-skills: pcb-layout + circuit-sim"). It is byte-identical to `~/.claude/skills/circuit-sim/SKILL.md` today.
- **2026-07-05 22:47–23:18: Self-oscillating ZVS.**
  - "I have a plasma globe now… easiest circuit?" The answer was a ZVS (Mazzilli) flyback driver.
  - "simulate it now so I can see it working": loaded `circuit-sim` and wrote `sim/zvs_royer.cir`.
  - About 20 minutes of convergence and magnetics fights (problems 12–17) ended with a working model: **40.00 kHz, ZVS, ~2.61 kV secondary** at Vin = 12 V. Added `make royer`.
- **23:18–2026-07-06 00:04: Q&A, docs and publish.**
  - Flyback sourcing; the toy's own transformer (blocking oscillator); TV flyback caveats (turns ratio in the hundreds gives 10–20 kV; diode-split = DC).
  - Dan's HV parts stash (stun-gun, arc-lighter and cylindrical HV modules) and Amazon "ZVS Driver Module 12–30 V" boards (= mass-produced Mazzilli) went into `driver-quickstart.md`; memory `plasma-hv-parts-on-hand.md`.
  - `.gitignore` excludes `sim/*.dat` (35 MB). Commit `5dbc464` (43 files), `gh repo create plasma-art --public`.
- **2026-08-28 20:30–20:33: Move to the dnuke-art org.**
  - Ran the `move-project` skill: transferred `dnewcome/plasma-art` → `dnuke-art/plasma-art` and repointed the remote.
  - Found and sed-rewrote hardcoded absolute paths in 10 `sim/` files.
  - The condensed transcript ends before the folder move. The folder does now live at `/home/dan/sandbox/dnuke-art/plasma-art`.

## Problems and fixes
1. **The video Dan linked could not be read.**
   - **Symptom:** `WebFetch` on the YouTube URL returned only footer and legal text, with no creator or description.
   - **Root cause:** YouTube page content is not in the fetched HTML.
   - **Resolution:** worked around. The page title ("Class E HFSSTC Toroid Doughnut Plasma Globe generating a stable ring in Xenon") plus web search identified it as a xenon **toroid**, not the voice-coil Lissajous effect Dan remembered. The two effects were documented separately.
   - **Landed:** `effects-and-physics.md`.
2. **Amazon listing details missing.**
   - **Symptom:** the WebFetch of the multicolor tube (`B0CKFKDHNQ`) had no description section.
   - **Resolution:** answered from physics (inside phosphor coating) and confirmed by Dan's own guess.
   - **Landed:** `effects-and-physics.md`.
3. **README edit failed.**
   - **Symptom:** `String to replace not found in file.`
   - **Root cause:** stale table text from an earlier edit.
   - **Resolution:** fixed by re-reading and re-editing.
4. **High-Q tank gives absurd step-up.**
   - **Symptom:** `tank_tran` gave 7.63 kV from a 36 V bus, ×489 gain at f₀, 11.74 A peak primary. Simulated f₀ was 46.3 kHz against the analytic 49.5 kHz.
   - **Root cause:** light-load, high-Q resonance. The transformer and load pull f₀ down.
   - **Resolution:** a design guidance rather than a fix: run slightly *off* resonance, current-limiting is mandatory, and Q drops once the tube strikes.
   - **Landed:** `sim/README.md` and the SKILL.md pitfall "High-Q + light load → absurd sim step-up".
5. **Shared-gas multi-channel cannot give crisp zones.**
   - **Symptom:** ~40% crosstalk (electrode 1: 1648.3 V own + 648.7 V leaked; electrode 2: 1532.1 V + 622.9 V) and a 7 kHz beat.
   - **Root cause:** the shared plasma node couples the channels. A per-channel series R trades voltage crosstalk against current injection.
   - **Resolution:** a design finding. The beat |f₁−f₂| becomes a "tempo knob" (firmware BEAT mode). "Interaction art vs crisp zones (separate gas volumes)" is **still open**.
   - **Landed:** `multi-channel.md`, `sim/README.md`.
6. **numpy 2 removed `trapz`.**
   - **Symptom:** `AttributeError: module 'numpy' has no attribute 'trapz'. Did you mean: 'trace'?` in `zvs_plot.py`.
   - **Resolution:** fixed with `sed s/np.trapz(/np.trapezoid(/`.
   - **Landed:** `zvs_plot.py`; SKILL.md pitfall #1.
7. **MOSFET current probe unreliable.**
   - **Symptom:** `i(Mxxx)` for MOSFETs is unreliable in ngspice (stated when building `zvs.cir`; no error text captured).
   - **Resolution:** fixed with 0 V sense sources in each drain (`VsenseH`, `VsenseL`).
   - **Landed:** `zvs.cir`; SKILL.md "MOSFET-level" section and pitfalls.
8. **Hand-authored Falstad netlists were unverified.**
   - **Symptom:** the assistant "authored these offline — I can't run Falstad in this environment to pixel-check the wiring".
   - **Root cause:** pixel coordinates were placed by hand with no headless Falstad.
   - **Resolution:** fixed in approach. Dan asked to generate them from the deck, which gave `falstad_gen.py`. This became the skill's north star: "ONE parametric SPICE deck is the source of truth; the Falstad netlist is GENERATED from it".
   - **Landed:** `sim/falstad_gen.py`; SKILL.md "Pass 1".
9. **SPICE inline comment leaked into the parser.**
   - **Symptom:** a traceback in `num()` → `eval(...)` while parsing the `.param kc=0.97 ; coupling (flyback = loose)` line.
   - **Root cause:** inline `;` comments were not stripped before `eval`.
   - **Resolution:** fixed with `raw.split(';')[0].split('$')[0].strip()`, skipping `*` lines.
   - **Landed:** `falstad_gen.py`; SKILL.md pitfall "SPICE parse: strip inline comments".
10. **Falstad MOSFET geometry.**
    - **Symptom:** the generated `falstad_zvs.txt` may have gate sources not landing on MOSFET gate posts.
    - **Root cause:** Falstad's MOSFET gate-post geometry and gate phase are version-sensitive, and the result could not be verified headless.
    - **Resolution:** worked around with "import, then nudge" plus a manual 5-minute build recipe. **Not verified in a browser** in the transcript.
    - **Landed:** `sim/README.md`; SKILL.md pitfall "Falstad `?cct=` … MOSFET gate posts … version-sensitive".
11. **Makefile inline comments corrupted variables. Dan hit this one himself.**
    - **Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: 'sim/falstad_resonant_driver  .txt'` from `make falstad-url`.
    - **Root cause:** `CCT ?= falstad_resonant_driver  # …` folds the trailing spaces into the value. `PAGE` was also corrupted, putting spaces inside the URL.
    - **Resolution:** fixed by putting comments on their own lines. Verified `…/circuitjs.html?cct=%24…`.
    - **Landed:** `Makefile`; SKILL.md "File layout & Makefile" and pitfall.
12. **Self-oscillating ZVS, failure 1: timestep too small at the centre tap.**
    - **Symptom:** `doAnalyses: TRAN: Timestep too small; time = 2.22163e-10, timestep = 2.5e-20: trouble with node "ct"`.
    - **Root cause:** three windings coupled at k = 0.98 make the inductance matrix near-singular, and the centre-tap node has no capacitance to ground.
    - **Tried:** `Cct ct 0 1n` plus kc = 0.96 → `trouble with pwrmos-instance ma`. Then looser `.options` with `rshunt=1e7`, `gmin=1e-8` → same error.
    - **Resolution:** see 13.
13. **Self-oscillating ZVS, failure 2: the hard start kick.**
    - **Symptom:** solver abort at t ≈ 0.3–0.8 ns.
    - **Root cause:** `.ic v(gA)=8` with drain B at 0 instantly forward-biases the cross-coupling diode, a discontinuity the solver cannot step through.
    - **Resolution:** fixed with a soft ramped kick `Istart 0 gA PULSE(0 40m 0 0.3u 0.3u 1.5u 0)` plus `.options reltol=2e-3 abstol=1e-8 vntol=1e-5 chgtol=1e-11 gmin=1e-8 rshunt=1e7`. Converged with 40,073 rows.
    - **Landed:** `sim/zvs_royer.cir`. **Not in SKILL.md.**
14. **Self-oscillating ZVS, failure 3: oscillating on the leakage mode.**
    - **Symptom:** "oscillates" at **279.98 kHz** (target ~40 kHz) with **0.01 kV** secondary.
    - **Tried:**
      - kpp = 0.999: 904.91 kHz, HARD switching.
      - kpp 0.99, ksec 0.95, Cload 3 pF, Rsec 1 kΩ: 534.95 kHz, 0.04 kV.
      - Cct 1 nF → 10 pF: still 534.98 kHz, 0.00 kV.
    - **Root cause:** finally identified as the **inter-half leakage** 2·L0·(1−kpp) ≈ 0.8 µH. Both half-windings were dotted at the centre tap, so the resonant cap saw them *opposing* rather than the full ~159 µH.
    - **Resolution:** see 15–17.
15. **Self-oscillating ZVS, failure 4: fixing the dots killed oscillation.**
    - **Symptom:** after reversing `La`'s node order, the circuit ran at 5.00 kHz with 0 switching edges ("check switching").
    - **Root cause:** the dot sense needed for an aiding tank inverted the feedback loop.
    - **Resolution:** abandoned that variant.
16. **Self-oscillating ZVS, failure 5: the two-choke variant will not start.**
    - **Symptom:** 5.00 kHz with 0 edges, even with a hard differential seed and asymmetric gate resistors. The node dump shows dA ≈ 0.01–1.2 V and dB ≈ 3–5 V for 400 µs.
    - **Root cause:** a single primary across the drains shorts them at DC, so MA latches on and the tank is never shock-excited.
    - **Resolution:** abandoned. Only the centre-tap geometry forces alternation.
17. **Self-oscillating ZVS, failure 6: the coupling matrix is not positive definite.**
    - **Symptom:** a sign brute-force over (k1, k2, k3) ran 6 combos, 3 of which were `SIM-FAIL`. Loosening k1 to 0.5–0.85 with opposite-sign secondary coupling made all 6 `SIM-FAIL`: `is not positive definite` / `trouble with node "da#internal"`.
    - **Root cause:** a secondary that sees the push-pull flux needs opposite-sign coupling to the two halves. At |k1| near 1 that matrix is not positive semidefinite, and the configuration that is PSD and oscillates rings on leakage.
    - **Resolution:** fixed by abandoning the 3-winding coupled model.
      - **Uncoupled** primary halves (tank = La+Lb+Cres).
      - **Ideal-transformer behavioral source** `Bhv hv 0 V = {Nsec}*(v(dB)-v(dA))`, with Nsec = 60.
      - Real VDMOS FETs on the primary.
      - Result: 54.99 kHz, ZVS, 3.04 kV. Then Cres 0.2 µF plus `Rtank dA dB 800`, because the B-source does not load the primary back and the drain crept above π·Vin.
    - **Final:** **40.00 kHz, drain peak 43.9 V settling ~36 V (theory π·12 = 37.7 V), 2.61 kV secondary, ZVS (2.31 V / 2.39 V at turn-on).**
    - **Landed:** `sim/zvs_royer.cir`, `zvs_royer_plot.py`, `make royer`, `sim/README.md`.
    - **Gap:** none of problems 12–17 (soft-start instead of hard `.ic`, `rshunt`, leakage-mode diagnosis, PSD coupling trap, B-source ideal transformer) were added to `circuit-sim/SKILL.md`. The skill is unchanged since 2026-06-27.
18. **TV flyback overdrives a globe.**
    - **Symptom:** none (analysis). A TV flyback's turns ratio is in the hundreds, so a 12 V ZVS gives 10–20 kV against the 2–4 kV a globe wants.
    - **Resolution:** advice: keep Vin ≤ 12 V and current-limit. The offered "ratio ~300 sim" was **never run** (open).
    - **Landed:** `driver-quickstart.md`.
19. **Firmware not hardware-validated.**
    - **Symptom:** `drive_mcpwm.cpp` is a "REFERENCE IMPLEMENTATION" for the Arduino-ESP32 3.x / IDF 5.x MCPWM API, whose names shifted across 5.0–5.3. The fault is software-polled.
    - **Resolution:** **still open.** Validate against the installed core, add a hardware MCPWM brake before real power (TODO in code). The default build is safe (`PLASMA_DRIVE_ENABLED=0`).
    - **Landed:** `firmware/`.
20. **No oscilloscope.**
    - **Symptom:** Dan has a PSU, no scope.
    - **Resolution:** worked around. A $10 24 MHz USB logic analyzer (sigrok/PulseView) checks complementary gates and the 300 ns deadtime. The PSU current limit catches shoot-through. ZVS itself is trusted from the sim.
    - **Landed:** `driver-bom.md`, `driver-schematic.md`.
21. **Hardcoded absolute paths broke on the move.**
    - **Symptom:** `git grep` found `/home/dan/sandbox/dnewcome/plasma-art` in 10 tracked files: `HERE = …/sim` in `plot.py`, `plot_two_channel.py`, `system_demo.py`, `zvs_plot.py`, `zvs_royer_plot.py`, and `wrdata /abs/path/…dat` in the 5 `.cir` decks.
    - **Root cause:** sims written with absolute output paths.
    - **Resolution:** sed-rewritten to `/home/dan/sandbox/dnuke-art/plasma-art`. **Still open:** those 10 edits are **uncommitted** in the working tree as of 2026-10-01, and the paths are still absolute rather than relative.
    - **Landed:** local working tree only.

## Decisions and reversals
- **Effect:** tendrils, not uniform glow, toroid or Lissajous. The **magnetic NST was sidelined** to companion neon pieces.
- **Driver:** ZVS + flyback was first documented as a quick start, then superseded by an **MCU-driven half-bridge** for creative control, extended to 2–3 independent-frequency channels. On 2026-07-05 the **self-oscillating ZVS came back** as the "drive the globe tonight" path.
- **Brightness = detune above resonance.** Operating above f₀ keeps ZVS, so `F_RES[]` is 49–51 kHz against a ~46 kHz peak. Dimming and soft-switching reinforce each other.
- **Falstad:** hand-placed → **generated from the deck** (Dan's call) → local CircuitJS1 via Makefile (Dan's request) → **online Falstad by default** (Dan's reversal the same evening; local kept as `FALSTAD=` override).
- **Skill scope:** `circuit-sim` is **standalone**, not coupled to mujoco or CAD. Circuit ↔ physics co-sim was **deferred**: one-way handoff by default, lumped ODE if needed.
- **ngspice plays the LTspice role.** LTspice is only for vendor-model checks; it is GUI- and Windows-first.
- **ZVS self-oscillator magnetics:** a physical 3-winding coupled model was **abandoned** for uncoupled halves plus an ideal B-source step-up. The decision was pragmatic: ZVS stays physical, only the HV relation is idealised.

## Outcome
- A complete `sim/` suite, runnable with `make sim`, `make royer`, `make demo`, `make falstad-gen` and `make falstad CCT=…`:
  - Resonance 46.3 kHz, ×489 gain, Cs→f₀ map (0.022 µF → 156.5 kHz … 1 µF → 23.2 kHz).
  - Shared-gas crosstalk ~40%, 7 kHz beat.
  - Driven-bridge ZVS at 55 kHz, 0.46 W.
  - Self-oscillating ZVS at 40 kHz, 2.61 kV.
  - System demo mp4.
  - Generated Falstad netlists and URLs.
- Host-tested firmware engine.
- Ten-plus design docs including the BOM and quickstart.
- **The `circuit-sim` skill**, created here, names this project's `sim/` as its worked example.
- Repo `dnuke-art/plasma-art` with a single commit `5dbc464`.
- Not built in hardware during the recorded sessions.

## Pointers
- Repo: `/home/dan/sandbox/dnuke-art/plasma-art`.
  - `sim/`: `tank_ac.cir`, `tank_tran.cir`, `two_channel.cir`, `zvs.cir`, `zvs_royer.cir`, `falstad_gen.py`, `*_plot.py`, `system_demo.py`, `README.md`.
  - `firmware/`, `Makefile`, `driver-*.md`, `multi-channel.md`.
- Skill: `circuit-skills/circuit-sim/SKILL.md` (commit `8f488ba`, 2026-06-27); source `~/.claude/skills/circuit-sim/SKILL.md`.
- Memories: `~/.claude/projects/-home-dan-sandbox-dnewcome-plasma-art/memory/` (`plasma-art-direction.md`, `circuit-sim-workflow.md`, `plasma-hv-parts-on-hand.md`). These are under the pre-move path; whether `move-project` renamed them is not shown in the condensed transcript.
- **Follow-ups for the skill:**
  - Fold in the `zvs_royer` lessons (problems 12–17).
  - Add a "use relative paths / `HERE = dirname(__file__)`" rule (problem 21).
  - Commit the path fix in the plasma-art repo.
