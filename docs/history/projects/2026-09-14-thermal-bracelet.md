# thermal-bracelet — battery-free wrist TEG harvester: thermal model, ngspice deck, CAD and Blender renders

- **Dates:** 2026-09-14 19:37 → 2026-09-15 08:07 (UTC, transcript clock; git commits show local time, UTC−7) · **Sessions:** `33eaf94a` (dir `~/sandbox/dnuke-art/thermal-bracelet`) · **Repo:** [dnuke-art/thermal-bracelet](https://github.com/dnuke-art/thermal-bracelet) (public; commits `be373f4`, `0c33f02`) · **Skills used:** kickoff, **circuit-sim**, build123d-machine, build123d-part, product-design (pcb-layout and pcb-3d-render were *not* used; no PCB was laid out)

## Goal

A bracelet that lights an LED from body heat alone, with no battery. The generator is the FTED S095A105022 flexible thermoelectric strip (105×22 mm) worn on a 185 mm band. Dan's v1 picks: **harvest plus a storage-cap blink** (TEG → LTC3108 boost → store cap → hysteretic LED pulser), and "done" means **a finished, giveable piece**. Requests during the session: a schematic, a performance estimate, CAD, how much power is really available, the charge time for addressable fairy lights, contact and placement questions, Blender hero renders, and a public repo.

This session is the second worked use of the **circuit-sim** pattern after plasma-art: one parametric ngspice deck with a Falstad netlist generated from it. It also exposed a Blender headless failure that pcb-3d-render does not yet document.

## Timeline

- **2026-09-14 19:37** Kickoff. Dan gave his bracelet length (185 mm), saved as a user memory.
- **2026-09-15 02:23** Dan linked the FTED product page. WebFetch got 403 (problem 1), so the page was fetched with curl and a browser user agent. The spec-table images were downloaded and read: about 40 mV/K and 1.6 Ω, sold as a *cooler*. Kickoff questions settled the power path and the definition of done. `BRIEF.md`.
- **02:29** "Save everything. Make a schematic and performance estimate. Also let's start modeling it." circuit-sim, build123d-machine and build123d-part were loaded, with the plasma-art `sim/` folder as the reference layout. The CAD was handed to a background subagent: `machine_params.py`, six mate-placed parts, `machine.py`, OpenSCAD renders and a render log. The LTC3108 datasheet fetch failed (problem 2), so its application values were written **from memory and flagged**.
- **~02:30–02:47** Built `sim/thermal_model.py`, a coupled Seebeck + Peltier + Joule model on a resistance network from skin to air, solved with fsolve. Also `sim/harvester.cir`, an ngspice deck with a behavioural LTC3108 and a real pulser (problem 3), `sim/harvester_plot.py` for the ΔT sweep, `sim/falstad_gen.py` to generate the pulser-stage Falstad netlist from the deck, a `sim/Makefile`, and `docs/schematic.py` (schemdraw, installed during the session). The schematic took three iterations (problem 5). The thermal model was revised to solve the *loaded* ΔT (problem 4). First finding: the module gets **about 4% of the gradient from core to room**, and the converter starts at roughly 0.8 K across the module under load. Indoors with no movement, it does not start.
- **02:49** Dan: "did you read the datasheet?" The answer was no. The datasheet was then found on a Farnell mirror. Curves G03, G04 and G07 were cropped at 300 dpi and read, and the model was recalibrated (problem 2). The start threshold dropped to 0.63 K for a typical part. A worst-case part (50 mV start) needs 1.8 K, which only happens outdoors.
- **03:01** Fairy lights: `sim/fairy_budget.py` produced `docs/fairy_lights_table.md`. The conclusion was rare bursts only. Idle pixel current (~0.7 mA/pixel) and supercap leakage outweigh the harvest.
- **04:45** Art framing: "the physics is the content." The pulse rate reads out the temperature gradient.
- **04:47** Pushed public to the **dnuke-art** org. Commit **`be373f4`**, 39 files. Vendor PDFs were gitignored (decision).
- **05:17–05:20** Contact and placement analysis. The rigid ring will not make contact (problem 7). The proposed v2: TEG centred on the volar side with a 10–15° radial offset, 20–30 mm up from the wrist crease, bonded to a 0.5 mm aluminium spreader, elastic straps on the back of the wrist, and the pod acting as the buckle. This was not built.
- **06:49** "Nicer blender render." product-design skill loaded. A forked agent built `cad/glb_export.py` and `cad/render_hero.py`, a hero render and a 36-frame turntable (problems 8, 10).
- **06:59–07:04** Follow-up renders segfaulted every time with the `blender` on PATH, version 5.2.0 (problem 9). They were re-run with `/opt/blender-5.0.1`. A `--no-wrist` GLB mix-up came up along the way (problem 11). The product view became the README lead image.
- **07:17** Dan: "My workstation crashed" (problem 12). The assistant confirmed nothing was lost.
- **07:18** Commit **`0c33f02`**: renders, GLB export and turntable. The README now opens with the renders.
- **07:54** Dan: the datasheet "was saying huge currents like 6A." This is cooler-mode input, not generator output (problem 6). An event-energy budget followed.
- **07:56** Wrote `sim/event_budget.py`, `docs/energy_budget.md` and `docs/design_notes.md`. **Left uncommitted**: `git status` still shows them untracked, with README modified.
- **08:04** `/compact`; the session ended.

## Problems and fixes

1. **FTED product page blocked WebFetch**
   - *Symptom:* `The server returned HTTP 403 Forbidden.`
   - *Resolution:* `curl -A "Mozilla/5.0 …" -H "Accept-Language: ko,en"` returned 200. The spec data turned out to be **images**, not text, so they were pulled from the CDN and read visually. Specification-page guesses such as `/spec` redirected to the home page. Saved as `docs/datasheets/FTED_S095A105022_*.png`.

2. **LTC3108 datasheet unreachable, so the first numbers were from memory**
   - *Symptom:* WebFetch to analog.com timed out after 60000 ms. curl to analog.com returned `000 0` (connection refused from this host). The Mouser URL returned a 13 KB non-PDF, Adafruit and Farnell (first URL) returned 404, and RS returned 403. A DigiKey HTML datasheet later returned 410 Gone.
   - *What was done first:* The model and schematic shipped with LTC3108 values from memory, explicitly flagged as unverified: 20 mV start and 2.5 Ω input resistance. Dan asked "did you read the datasheet?"
   - *Resolution:* A WebSearch result pointed to a Farnell mirror (`farnell.com/datasheets/1751951.pdf`, rev C 3108fc). Text was extracted with pdftotext, and pages 4–5 were rendered with pdftoppm at 300 dpi to crop curves G03 (IVOUT/efficiency), G04 (input resistance) and G07 (IVOUT vs Voc). The datasheet changed the answer: R_in is **4–6 Ω at low VIN, not 2.5 Ω**, so the start threshold moved from 0.82 K to 0.63 K and delivered power roughly doubled. Start voltage is **20 mV typical / 50 mV maximum**, so a worst-case part needs 1.82 K. The G07 cross-check says "doesn't start" for the indoor no-movement case, so that case is treated as a coin flip, to be settled by screening several parts on the bench.
   - *Landed:* `sim/thermal_model.py` (converter block cites "datasheet rev C, curves G03/G04/G07"), `sim/harvester.cir`, `docs/performance.md`, `docs/datasheets/` (curve crops committed, PDFs gitignored).

3. **No SPICE model for the LTC3108**
   - *Root cause:* There is no public transistor-level model, and the resonant step-up oscillator is impractical to simulate at system timescales (inferred).
   - *Resolution:* A behavioural model: a resistive input port R_in(VIN) from G04, plus a power-conserving output current source P_out(VIN) from G03, feeding a real store-and-pulser stage (TLV3691 Schmitt referenced to VLDO/2, DMG1012T MOSFET, 470 Ω, LED). The ngspice sweep agreed with the thermal model on the start threshold. Landed in `sim/harvester.cir`.

4. **The first thermal model used open-circuit ΔT**
   - *Symptom:* The module's ΔT was computed without load, which overstated input voltage.
   - *Root cause:* Harvest current pumps heat back across the module (the Peltier term), which costs about 20% of the gradient. Loaded ΔT is about 0.85 × open-circuit.
   - *Resolution:* fsolve over Th, Tc and VIN with full Seebeck + Peltier + Joule coupling. Tables now report both open-circuit and loaded ΔT. Landed in `sim/thermal_model.py`.

5. **Schematic generation took several layout passes, and the Falstad generator had a duplicated block**
   - *Symptom:* In schemdraw, the C1/C2 taps from the transformer secondary to the LTC3108 pins and the TEG label collided or routed badly. Three rewrites, each checked by viewing the PNG. `falstad_gen.py` contained two `net = [HEADER, …]` blocks left over from drafting.
   - *Resolution:* A vertical tap column for C1 and C2, the TEG label moved to a separate `Label` element, and shortened leads. The duplicate block was removed with a scripted edit, and the store rail was moved to y=96 so the MOSFET posts line up. Landed in `docs/schematic.py` and `sim/falstad_gen.py`.

6. **Cooler-mode datasheet misread ("6 A")**
   - *Symptom:* Dan found the spec table confusing: 6 A at 12.4 V.
   - *Root cause:* FTED specifies the part as a Peltier cooler, so those numbers are *input* drive. As a generator it behaves as about 40 mV/K behind 1.6 Ω, with P_max = Voc²/4R. That gives 250 µW at 1 K, 1 mW at 2 K and 25 mW at 10 K. The real limit is that the wrist gives the module only 0.7–2 K.
   - *Landed:* `docs/energy_budget.md` and `sim/event_budget.py`, which give repeat rates for an LED blink, a BLE advertisement, e-paper and pixel bursts. Uncommitted at session end.

7. **Rigid CAD ring cannot make thermal contact**
   - *Symptom:* CAD v1 is a rigid circle with a stand-in clasp. A 0.5 mm air gap adds ~0.02 m²K/W, about five times the module's own thermal resistance.
   - *Status:* A v2 mechanism was designed in prose: bonded 0.5 mm aluminium spreader, elastic straps on the back of the wrist, ~3–5 N band tension, and the pod as a ladder-lock buckle. It was written into `docs/design_notes.md` (uncommitted). **CAD v2 was not built.**

8. **Blender 5 compositor API removed (again), and an intermittent OCIO crash despite `LC_ALL=C`**
   - *Symptom (from the subagent):* No `Scene.node_tree`, so the bloom/glare setup failed. Separately, **one render in six crashed in libOpenColorIO (`sscanf` in the AgX setup) even with `LC_ALL=C LANG=C`**.
   - *Resolution:* Glow is faked with a red point light 1.2 mm above the LED lens. The turntable loop retries up to 3× and checks for 36 frames.
   - *Significance:* This contradicts the pcb-3d-render claim that `LC_ALL=C` fixes the OCIO segfault. On this machine it reduces the crash rate but does not eliminate it. pcb-3d-render's Gotchas section does not yet say so.

9. **Blender 5.2.0 on PATH segfaults deterministically when run headless**
   - *Symptom:* Every `blender -b -P cad/render_hero.py` run with `~/.local/bin/blender` (Blender 5.2.0 LTS) gave `Segmentation fault (core dumped)`. Six retries failed before `/tmp/blender.crash.txt` was read.
   - *Root cause:* The backtrace shows `libze_loader.so.1(zeInitDrivers)` called from `libur_adapter_level_zero_v2.so` / `libur_loader.so (urAdapterGet)`. The crash is in the **oneAPI / Level Zero GPU device probe**, not in OCIO or the script.
   - *Resolution:* Use `/opt/blender-5.0.1-linux-x64/blender` explicitly. The README run line was pinned to it with a comment, and a feedback memory was saved (`feedback-blender-headless-version.md`). No workaround for 5.2 itself was attempted (for example disabling the oneAPI backend).
   - *Where it landed:* Project README and session memory only. **Not in circuit-skills pcb-3d-render** (gap).

10. **Shell material read as black-on-black**
    - *Symptom:* The specified dark anodized aluminium (0.12 base) disappeared against the black silicone straps and pod.
    - *Resolution:* Changed to brushed natural aluminium (0.46, metallic 1, roughness 0.28). Since the band is the generator's cold side, the look is also accurate. Landed in `cad/glb_export.py`.

11. **`--no-wrist` GLB still contained the wrist prop**
    - *Symptom:* `bracelet_nowrist.glb` listed a `wrist` geometry.
    - *Root cause (inferred):* The command chain ran `glb_export.py --no-wrist`, then copied `bracelet.glb` over `bracelet_nowrist.glb`, then re-exported with the wrist. The copy picked up a with-wrist file.
    - *Resolution:* `glb_export.py --no-wrist` was re-run directly, the geometry list was verified to have no `wrist`, and `render_inside.png` was re-rendered. It became the README lead image.

12. **Workstation crash after the GPU render session**
    - *Symptom:* Dan reported a crash about 10 minutes after the last render. Uptime showed 5 minutes.
    - *Root cause:* Never found. GPU load beforehand is suggestive but not evidence. The previous boot's journal was offered but not pulled.
    - *Status:* Nothing was lost; all outputs were on disk with pre-crash timestamps. The work was committed right after as `0c33f02`.

## Decisions and reversals

- **Power path:** TEG → LTC3108 (1:100) → 1000 µF store → TLV3691 Schmitt pulser → red LED, with 2 mJ blinks. No battery, no MCU. Ruled out: plastic shells over the TEG (they add more thermal resistance than the module itself) and coin supercaps (2–10 µA leakage is comparable to the entire indoor harvest).
- **Reversal:** "indoor-still never starts", based on remembered LTC3108 values, became "marginal, coin flip" once the real datasheet was read.
- **Fairy lights** demoted to rare bursts: 10–20 pixels, power-gated, a 0.2 s twinkle. **E-paper** was identified as the strongest alternative to the single LED, because the image holds with no standing power.
- **Art direction:** the pulse rate is the content. Bare metal, and visibly no battery.
- **Vendor PDFs gitignored** for copyright reasons. Curve crops are committed because the model reads from them.
- **Renders:** brushed aluminium replaced anodized; Blender 5.0.1 is used instead of 5.2.0.

## Outcome

A public design-study repo (`be373f4`, `0c33f02`) containing the brief, schematic, coupled thermal-electrical model, ngspice deck with Falstad generator, fairy-light budget, build123d CAD v1 with a render log, and Blender product, on-wrist and turntable renders. Modelled harvest with an aluminium band: about 50 µW indoors when still, ~90 µW indoors when moving, ~280 µW walking at 15 °C, ~535 µW walking at 5 °C. That gives one blink every 42/24/7/4 s respectively. Nothing was ordered or measured. The bench measurement in the brief (open-circuit and loaded voltage on the wrist, bare, with aluminium, and walking) is the next step. CAD v2 was not built, and the energy budget and design notes are uncommitted. No PCB was designed, so pcb-layout and pcb-enclosure-fit had no role yet.

## Pointers

- `sim/thermal_model.py`, `sim/harvester.cir`, `sim/harvester_plot.py`, `sim/falstad_gen.py`, `sim/fairy_budget.py`, `sim/event_budget.py` (uncommitted), `sim/Makefile`
- `docs/schematic.py`, `docs/performance.md`, `docs/energy_budget.md` and `docs/design_notes.md` (both uncommitted), `docs/datasheets/` (curve crops)
- `cad/machine_params.py`, `cad/machine.py`, `cad/glb_export.py`, `cad/render_hero.py`, `cad/renders/bracelet/INDEX.md`
- Session memory (local): `feedback-blender-headless-version.md` (Blender 5.2 oneAPI segfault)
