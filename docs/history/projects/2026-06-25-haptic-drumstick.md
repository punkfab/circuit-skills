# Haptic Drumstick — a drumstick that physically rebounds off a virtual drum (CAD + MuJoCo + solenoid-driver sim)

- **Dates:** 2026-06-25 17:55 → 23:09, plus a publish on 2026-06-30 20:29–21:00 · **Sessions:** `37e9a6b9` (dir `/home/dan/sandbox/dnewcome/haptic-drumstick`) · **Repo:** published as `dnewcome/haptic-drumstick` (public, all rights reserved); today the local clone is `/home/dan/sandbox/audiodestrukt/haptic-drumstick` with remote `audiodestrukt/haptic-drumstick` (moved after this session) · **Skills used:** `kickoff`, `build123d-part`, **`circuit-sim`** (loaded at 22:25, about 9 minutes after it was created in the plasma-art session). The session also *created* the `mujoco-sim` skill.

## Goal
An IMU-sensed drumstick whose inertial actuator gives a physical "bounce" off a virtual surface, for experimental performance. Most of the session is mechanical: build123d CAD and a MuJoCo sim, which became the `mujoco-sim` skill. The **circuit work** came last. It is a parametric ngspice sim of the solenoid's peak-and-hold drive (low-side N-FET plus flyback, diode vs zener clamp) that shares coil R and L with the MuJoCo EM model, plus a generated Falstad URL. It was aligned to the brand-new `circuit-sim` skill conventions.

## Timeline
- **2026-06-25 17:55–18:13**: Kickoff and physics discussion.
  - The first slice was to test the haptic illusion in isolation.
  - Dan proposed a solenoid-slammed counterweight ("mechanical click is totally fine"), mounted behind the hand fulcrum.
  - Asymmetric drive was chosen: fast slam, then gentle PWM-braked return.
  - Parts list included a logic-level N-FET (IRLZ44N) with a flyback diode.
- **18:33–18:42**: `cad/drumstick.py` (build123d): body 22×22×405 mm and cap, both watertight and single-body, plus a section PNG. The CAD put the solenoid bore *axial*.
- **18:42–19:14**: `sim/drumstick_sim.py`, a MuJoCo 3.9.0 bench with a coupled solenoid EM model (coil current ODE, F = K·i²/gap²). First result was too weak, then recalibrated. Headline: **transverse rear kick 1.556 mm tip rebound; axial on-centerline exactly 0.0 mm**.
- **19:14–20:09**: Dan asked for a physics-sim skill. `~/.claude/skills/mujoco-sim/SKILL.md` was written and smoke-tested against the real STL, which found the `inertia="exact"` gotcha.
- **20:12–21:49**:
  - The sim loads the real mesh (66.9 g, tip rebound 2.434 mm).
  - Makefile `make sim`.
  - `make interactive` (mujoco.viewer) with a headless `--selftest`.
  - Hand/fulcrum visual.
  - Control-pane sliders via zero-gear actuators.
  - `slug_pos_mm` slider and a position sweep (12 mm from butt gives 4.01 mm tip; at the fulcrum, 0.00).
- **21:53–22:09**: "What about the drive circuit?" Peak-and-hold topology proposed. **Dan chose "Simulate it (ngspice + Falstad)"** over a KiCad schematic.
- **22:12–22:22**: `circuit/driver_sim.py` written and run. Coil R and L were imported from `drumstick_sim.Params`: coil_R = 4.0 Ω, coil_L = 2 mH, V = 12 V, slam 6 ms, drag duty 0.18. Results: slam 2.82 A, hold 0.37 A, diode flyback peak 12.8 V, zener flyback peak 40.3 V. Two PNGs, `driver.cir`, `driver_falstad.txt`.
- **22:24–22:28**: The `circuit-sim` skill "just surfaced" and was loaded. Aligned to it by adding the `?cct=` Falstad share URL (`build/driver_falstad_url.txt`), `make circuit` / `make falstad`, and an analytic cross-check (12/(0.2+4+0.05) = 2.82 A analytic = 2.82 A sim).
- **22:33–23:09**: `/compact`, then wrap-up. Two project memories were saved. Open threads: VDMOS part selection, MCU firmware, flipping the CAD bore to transverse, BRIEF.md.
- **2026-06-30 20:29–21:00**:
  - `.gitignore` (excludes `build/`, 5.2 MB of regenerable artifacts) and README.
  - Commit `e3ad395`, `gh repo create haptic-drumstick --public`.
  - Dan declined a LICENSE and kept the repo public. Commit `8b9877a` adds an explicit all-rights-reserved notice.

## Problems and fixes
1. **EM force far too weak; the slug never slammed.**
   - **Symptom:** first run `peak_F 0.397 N, peak_tip_mm 0.121`.
   - **Root cause:** `force_K` was calibrated for the closed gap. At the 9 mm starting gap, F ∝ 1/gap² is tiny, so the slug never crossed before the pulse ended.
   - **Resolution:** fixed. `force_K = 7.0e-5` (about 8 N at 9 mm) with a `force_cap = 50 N` clamp. Result: peak_F 50 N, tip 1.556 mm.
   - **Landed:** the `Params` dataclass in `sim/drumstick_sim.py`. "Calibrate at the operating gap" went into the `mujoco-sim` skill.
2. **`imageio` missing, so the GIF was skipped.**
   - **Symptom:** `(gif skipped: No module named 'imageio')`.
   - **Resolution:** fixed with `pip install imageio` (2.37.3).
3. **`$SCRATCH` unset.**
   - **Symptom:** `/bin/bash: line 25: /mesh_smoketest.py: Permission denied`.
   - **Root cause:** the variable was not set in that shell.
   - **Resolution:** fixed by using the explicit scratchpad path.
4. **MuJoCo mesh inertia ignores the hollow bore.**
   - **Symptom:** trimesh gave 0.0669 kg; MuJoCo's default gave 0.0826 kg. Modes: `convex` 0.0904, `legacy` 0.0826, `shell` 21.5941 kg, `exact` 0.0669. With no `scale`: 82,554,540 kg (a mm→m units bug).
   - **Root cause:** the default mesh inertia fills cavities.
   - **Resolution:** fixed with `inertia="exact"` on the `<mesh>` and `scale="0.001 0.001 0.001"`. With the real inertia and centre of mass, tip rebound changed **1.56 → 2.43 mm** (about 35%).
   - **Landed:** `mujoco-sim` SKILL.md pitfalls and `sim/drumstick_sim.py`.
5. **The CAD bore cannot produce rebound.**
   - **Symptom:** axial on-centerline gives `peak_tip_mm 0.0` in every configuration and at every slug position.
   - **Root cause:** an on-axis reaction passes through the wrist pivot, so the moment arm is zero.
   - **Resolution:** a design finding. **Still open:** `cad/drumstick.py` is still axial ("flip the CAD bore axial → transverse" is an open thread).
   - **Landed:** README, project memory.
6. **Refactor regression.**
   - **Symptom:** `NameError: name 'duty' is not defined` in the batch sim after factoring out `coil_force`.
   - **Resolution:** fixed by restoring `duty = duty_of(t, p)`.
   - **Landed:** `drumstick_sim.py`.
7. **Interactive viewer cannot be shown headless.**
   - **Symptom:** the session has no display.
   - **Resolution:** worked around with `--selftest` (2.43 mm, identical to batch). The GL window only runs on Dan's desktop. A `MUJOCO_GL` glfw-vs-osmesa note went into the skill; the condensed transcript does not show the exact error Dan reported.
   - **Landed:** `sim/drumstick_interactive.py`, `mujoco-sim` skill.
8. **Viewer Control pane empty.**
   - **Symptom:** Dan said config setpoints did not appear in the Control pane. The complaint is referenced at 21:30; the message itself is not in the condensed log.
   - **Root cause:** the pane only shows *actuators*; the forces came from `qfrc_applied`.
   - **Resolution:** fixed with seven zero-gear `<motor>` actuators: drive_V, spring_k, grip_k, gap0_mm, drag_duty, strike_hz, slug_pos_mm. They are read each step and are physics-inert (batch result unchanged at 2.434 mm).
   - **Landed:** `drumstick_sim.py`, `mujoco-sim` skill pitfalls.
9. **Selftest mislabel.**
   - **Symptom:** printed "peak coil current=0.00A".
   - **Resolution:** fixed by relabelling as "final coil current".
10. **Drive-circuit sim predates the skill's conventions.**
    - **Symptom:** the first `driver_sim.py` emitted Falstad *text* only: no `?cct=` URL, no `make falstad`, no analytic gate.
    - **Root cause:** built before the `circuit-sim` skill was visible to this session. The skill was created at 22:16 in a parallel session.
    - **Resolution:** fixed by adding all three. The URL round-trip decode was checked (12 lines, header `$ 1 5e-06 10.634 50 …`). **Opening it in Falstad was not verified.**
    - **Deliberate deviation:** the deck stayed in `circuit/` rather than the skill's `sim/`, because `sim/` is the MuJoCo sim.
    - **Landed:** `circuit/driver_sim.py`, `Makefile`.
11. **The ideal switch hides switching loss.**
    - **Symptom:** the FET is modelled as an ideal switch with Rds 0.05 Ω, so there are no switching-loss or gate-charge numbers.
    - **Root cause:** a modelling choice.
    - **Resolution:** **still open.** The planned next step was to swap in a VDMOS model and choose a FET by loss and Vds against the 40 V zener clamp.
    - **Landed:** README "open threads".
12. **Form factor.**
    - **Symptom:** a Ø14 mm solenoid will not fit in a 14–15 mm stick.
    - **Resolution:** worked around with a Ø22 mm rear pod.
    - **Status:** open (shrink later).

## Decisions and reversals
- **Inertial voice coil → solenoid-slam counterweight**, after Dan accepted the click. The actuator moved **behind the fulcrum**, then **butt-ward**. The sweep showed rebound rising from 0 mm at the fulcrum to 4.01 mm at 12 mm from the butt.
- **Drive circuit: simulate first (ngspice + Falstad) rather than draw a KiCad schematic.** Dan's choice, consistent with "sim before parts".
- **Shared constants across domains:** coil_R and coil_L come from the MuJoCo `Params`, so drive → current → force stays consistent.
- **Flyback clamp is a design knob, not a fixed part:**
  - Freewheel diode: gentle release, FET sees about 13 V.
  - Zener/TVS (SMBJ33A suggested): sharp release, FET sees about 40 V, which sets the FET rating.
- **Licensing:** public, explicitly "all rights reserved". Dan said "I might want to make money from this one". Flipping the repo private was offered and declined.

## Outcome
- **Circuit:** `make circuit` produces waveforms, a clamp comparison, `driver.cir`, Falstad text and a share URL.
  - Slam 2.82 A (analytic = sim), hold 0.37 A.
  - Force ∝ i²: about 8 A² in the slam versus about 0.14 A² in the hold. The hold only pins the slug, which matches the mechanical finding.
- **Mechanical:** `make sim`, `make interactive`, `make cad`.
- The session produced the **`mujoco-sim` skill**. It *consumed* the `circuit-sim` skill and was its first reuse outside plasma-art. No `circuit-sim` changes were made from here.
- Commits `e3ad395`, `8b9877a`.

## Pointers
- Repo: `/home/dan/sandbox/audiodestrukt/haptic-drumstick`.
  - `circuit/driver_sim.py`: the circuit work; generates `build/driver*.{cir,png,txt}` and `driver_falstad_url.txt`.
  - `sim/drumstick_sim.py`, `sim/drumstick_interactive.py`, `cad/drumstick.py`, `Makefile`.
- Project memory: `~/.claude/projects/-home-dan-sandbox-dnewcome-haptic-drumstick/memory/` (written under the pre-move path).
- Relevance to `circuit-sim`: an independent validation that the skill's "one parametric deck + generated Falstad URL + analytic sanity gate" pattern transfers. It also exercises the skill's "Handoff to physics sim — one-way" section in reverse, with the physics model supplying the circuit's L and R.
