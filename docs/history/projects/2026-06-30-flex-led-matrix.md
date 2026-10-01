# flex-led-matrix — parametric addressable RGB flex panel, JLCPCB cost model, and the origin of `pcb-3d-render`

- **Dates:** 2026-06-30 03:11 → 2026-07-01 00:17 (UTC, transcript clock; git commits show local time, UTC−7) · **Sessions:** `b7581a8f` (dir `~/sandbox/dnewcome/flex-led-matrix`) · **Repo:** [dnewcome/flex-led-matrix](https://github.com/dnewcome/flex-led-matrix) (public; commits `af5f160`, `324b9dd`) · **Skills used:** kickoff, pcb-layout, product-design; **created** pcb-3d-render (circuit-skills commit `6db19bc`)

## Goal

Dan wanted a large display tiled from his own flexible LED panels, fabbed and assembled in bulk (~100 boards) at JLCPCB. He wanted a parametric design so he could get prices for different configurations. The baseline was 8×32 pixels per board. A hard requirement emerged early: panels must **index into a grid through registration holes in the flex**. Getting perfect alignment between panels is the reason for not using LED strips. The session became a cost investigation: price a baseline, check it against a real JLC quote, then decide whether to build. The last part of the session added 3D renders to the README, and from that work Dan asked for a new circuit-skills skill, `pcb-3d-render`.

## Timeline

- **2026-06-30 03:11** Empty dir, no git. Kickoff skill. The assistant pointed out that "addressable" and "HUB75" are different architectures; Dan had named both.
- **04:36–04:50** Dan picked addressable smart pixels. He asked "why not WS2805?" The assistant checked the datasheet: 5-channel RGBCCT, 12/24 V, external IC. Dan chose RGB only, integrated, cost first. Baseline: WS2812B-2020 (LCSC C965555), ~5 mm pitch, 2-layer flex. Dan added the registration-hole requirement. `BRIEF.md` and memory entries were written.
- **04:56** pcb-layout skill loaded. Decision: **do not route a 512-part board in tscircuit just to get a price.** JLC prices from board area and flex options (fab) plus unique parts and joint count (assembly). So the assistant wrote a Python generator (`gen/generate.py`) that emits a JLC BOM and CPL, the fab parameters, a cost rollup and a preview SVG. JLC's published PCBA and FPC rates were fetched by WebFetch.
- **05:02** First estimate: **$23.64/board, $2,364 for 100**, with LEDs at 59%. Dan: "a lot more than I thought." `gen/sweep.py` was added. The model's hard floor was $6.46/board, so Dan's $5 target was out of reach for 256 integrated pixels.
- **05:21** Dan: the boards must be flex, the panel stays 160×40 mm, and the target is $10/board. Which architecture buys more pixels? `gen/density.py` answered: addressable gets ~1.7× more pixels per dollar than HUB75 at qty 100. The reason is that bare RGB LEDs on LCSC (~$0.062) cost as much as or more than WS2812B-2020s.
- **05:33** Dan challenged the FPC assembly fixture charge ($189 assumed). The assistant re-checked: the charge is real but applies only to thin-flex assembly and is one-time NRE. The 8-fixture count was a guess (problem 3).
- **05:41–05:47** A **placement-only KiCad board** came from `gen/kicad_board.py`, using footprints with the correct pad count. kicad-cli exported Gerbers, drill and CPL into `out/jlc_gerbers.zip`.
- **06:05–06:23** Dan reported "they don't have the LEDs," then that he already had Standard PCBA selected. Root cause: catalog stock is not the same as assembly-ready stock (problem 4). The invented connector part was removed from the BOM (problem 5).
- **06:29–06:35** Dan: "gotta find a cheaper LED." Prices were compared on LCSC. SK6805-EC15 was cheapest at $0.0511. The XINGLIGHT "clone" was the most expensive at $0.0649.
- **06:35–06:46** Dan pasted the **real itemized JLC quote: $2,286.88 ($22.86/board)**. The model was 3.4% off in total, but its breakdown was wrong (problem 6). The generator was recalibrated against the quote and reproduced it to $0.01.
- **06:51–07:00** Dan doubted that LEDs at $0.020 were realistic, then said he could get $0.023 consigned. Calibrated result: **256 px at ~$10.5/board, ~$1,050 for 100**, with caps at 1:2.
- **07:05–07:23** Dan repositioned the product as a 2D registerable replacement for LED strips, not a HUB75 competitor. Rule of thumb: board ≈ $2.31 + px × $0.032. Dan buys strips at retail, so the decision was **go** for boards of 128 px or more. A side discussion covered rigid art shapes: shape complexity is free, and for many different shapes in small quantities, bare fab plus hand soldering beats JLC assembly. `NOTES.md` was written and the project paused.
- **23:18** Dan: "make some pretty 3d renders and add to README." The product-design skill was loaded. `gen/render_model.py` built a curved emissive GLB with trimesh and rendered it with the skill's `blender_render.py`. The pixels came out looking matte (problem 8), so a tuned `gen/blender_panel.py` was written. That hit the Blender 5 compositor API break (problem 9) and a SIGPIPE from `| head` (problem 10). Three renders resulted: hero, grid and profile. Dan also asked for a detailed README on pricing tradeoffs and a public repo. Commit **`af5f160`** was pushed public.
- **23:36** Dan: "too many renderings… I want some 3d views of the PCBA from tscircuit." A tscircuit project was set up. `tsci init` failed in a non-TTY shell (problem 11). C965555 and C1525 were imported with real CAD models. The GLB export failed with `PackSolver2 ran out of iterations` (problem 12) and was fixed by pinning `schX/schY`. Two Blender PCBA renders were made with a new `--studio` mode. Grid and profile renders were dropped. Commit **`324b9dd`**.
- **23:59** Dan: "you should have been able to do 3d renders directly in tscircuit right?" Confirmed: `tsci snapshot --3d` with `--camera-preset` exists and was missed (problem 13).
- **2026-07-01 00:04–00:17** Dan: keep the Blender shots, and add 3D rendering to circuit-skills as a skill. The assistant created `pcb-3d-render/SKILL.md` and `scripts/blender_panel.py` (emission boost generalized to any emissive material), documented the previously unlisted `pcb-enclosure-fit` in the repo README, and committed and pushed **`6db19bc`**. The repo was then at `~/sandbox/dnewcome/circuit-skills`, remote `dnewcome/circuit-skills`; it later moved to punkfab (inferred from the current repo path). The skill was also copied into `~/.claude/skills/`.

## Problems and fixes

1. **Cost question needed a price, but a 512-part board is beyond tscircuit**
   - *Symptom:* 256 LEDs, 256 caps and connectors make ~520 parts. The pcb-layout skill warns that ~50 parts can choke tscircuit's PCB pipeline.
   - *Root cause:* JLC's price does not depend on routing quality, only on area, layers, flex options, unique parts and joints.
   - *Tried / resolution:* The generator was written in Python with a deterministic serpentine grid, not in tscircuit. Later, `gen/kicad_board.py` wrote a minimal KiCad 9 `.kicad_pcb` with placed stand-in footprints (correct pad count, no routing). kicad-cli exported the Gerbers and drill files. DRC reported 811 violations (silk and clearance noise on an unrouted board), which were ignored for quoting.
   - *Landed:* `gen/generate.py`, `gen/kicad_board.py`, `out/jlc_gerbers.zip` (flex-led-matrix `af5f160`). Status: worked. JLC accepted the bundle and quoted it.

2. **Density solver crashed and HUB75 "never fit"**
   - *Symptom:* `density.py` printed `B) HUB75 : (no grid fits $10)` at every fab price, then `TypeError: 'NoneType' object is not subscriptable`. An earlier `cd gen` also failed with "No such file or directory" because the shell cwd had been reset.
   - *Root cause:* The pitch sweep stopped at 8 mm, but HUB75's fixed overhead only fits at sparser grids. The sensitivity print had no guard for a `None` result.
   - *Resolution:* Sweep widened to 2–20 mm and a None guard added. HUB75 then fit, e.g. 64 px at 9.5 mm against addressable 110 px at $4 fab. Landed in `gen/density.py`.

3. **FPC assembly fixture cost overstated (Dan's challenge)**
   - *Symptom:* The model charged 8 × $23.57 = $189 NRE, which Dan didn't recognize from past flex orders.
   - *Root cause:* The fixture is an *assembly-only* carrier for thin flex (0.4/0.6 mm), so fab-only orders never show it. The count of 8 was a guess.
   - *Resolution:* The real quote showed **$49.25** (~2 fixtures). The model was recalibrated to `jlc_fixtures=2`. Dan's skepticism was correct.

4. **"They don't have the LEDs": catalog stock is not assembly stock**
   - *Symptom:* JLC's quote tool showed WS2812B-2020 C965555 as unavailable. `tsci search --jlcpcb` reported 360,285 in stock.
   - *First wrong theory:* The Economic PCBA restricted library. Dan said he already had Standard selected.
   - *Root cause:* The JLC part page showed **"In Stock: 0 · Available Order Qty: 17 · Extended · only available for Standard PCBA · needs an assembly fixture."* `tsci search` and LCSC report *catalog* stock, not the SMT-ready bin.
   - *Resolution:* At 25,600 LEDs, the realistic options are pre-order or consignment. Recorded in memory (`jlc-assembly-part-availability.md`) and the README warning "Catalog stock ≠ assembly-ready stock." This is a general caveat for pcb-layout's "stock-check first" step (inferred: the skill does not yet mention it).

5. **Invented placeholder connector rejected by JLC**
   - *Symptom:* The BOM line `C2829380` was not found.
   - *Root cause:* The assistant had made up the part number as a cost placeholder and flagged it at the time.
   - *Resolution:* `conn_count=0` now drops the connector from the BOM (the interconnect design was deferred). Landed in `gen/generate.py`.

6. **Cost model total was right but the breakdown was wrong**
   - *Symptom:* Estimate $23.64 against real $22.86 (3.4%). But the estimate had flex fab at $6/board against real **$1.45**, and LED price at $0.0496 against real **~$0.0709** (JLC applied no volume discount). LEDs and caps were 81% of the real total, not 59%.
   - *Resolution:* All parameters were recalibrated to the itemized quote: setup $25.56, stencil $8.21, $0.00132/joint, feeders $1.53, fixtures 2, flex $1.45. The model reproduced $22.87. This reversed an earlier claim that "$10 buys only 110 px." Landed in `gen/generate.py` (CALIBRATED comments) and the README.

7. **Over-optimistic LED price**
   - *Symptom:* The assistant presented "$10 at 256 px with $0.020 LEDs." Dan: "I don't think I'm going to find these for .020."
   - *Resolution:* Re-run at $0.030–0.071, then locked at Dan's sourced **$0.023**, giving ~$10.5/board. Status: the design point depends on the $0.023 quote, which was unconfirmed when the session ended.

8. **Emissive LEDs rendered as matte tiles**
   - *Symptom:* The first hero render from the product-design skill's `blender_render.py` made the pixels look unlit.
   - *Root cause:* The studio key light and world fill washed out the emission, and there was no bloom.
   - *Resolution:* A new `gen/blender_panel.py` boosts emission strength (`--emit 12–18`), uses a dark, moody world and lowers the key light. AgX handles highlight rolloff. Landed in `pcb-3d-render/scripts/blender_panel.py` (emission-tuning gotcha).

9. **Blender 5 compositor API removed**
   - *Symptom:* `AttributeError: 'Scene' object has no attribute 'node_tree'` when adding fog-glow bloom.
   - *Root cause:* The Blender 5 compositor API changed and `scene.node_tree` no longer exists.
   - *Resolution:* The compositor block is wrapped in try/except and skipped (`bloom: skipped …`). Glow comes from emission alone. Not re-implemented with the new API. Landed in pcb-3d-render SKILL.md "Gotchas."

10. **Renders silently not written: SIGPIPE from `| head`**
    - *Symptom:* The grid and profile runs printed only the HIP warning, and no PNG appeared.
    - *Root cause:* `blender … | grep … | head -2`. Once `head` closed the pipe, SIGPIPE killed Blender mid-render.
    - *Resolution:* Pipe through `tail` instead, or not at all. Landed in pcb-3d-render SKILL.md "Never pipe Blender's stdout through `head`."

11. **`tsci init` unusable non-interactively**
    - *Symptom:* `error: unknown option '-y'`, then an inquirer prompt crashing with `ERR_USE_AFTER_CLOSE: readline was closed`, including when answers were fed on stdin.
    - *Root cause:* The init command is interactive-only, and the pcb-layout skill's `npx tsci init -y` instruction is stale (inferred from the error).
    - *Resolution:* Manual setup with `npm init -y` and `npm install -D tscircuit @tscircuit/cli @types/react react` (tsci 0.0.1976), then `tsci import C965555` and `tsci import C1525`. Status: worked around. It is not recorded whether pcb-layout's setup snippet was corrected.

12. **tscircuit layout solver limit at 512 components**
    - *Symptom:* `tsci export -f glb` failed with `Matchpack layout solver failed: PackSolver2 failed: PackSolver2 ran out of iterations`.
    - *Root cause:* PCB positions were given but schematic positions were not, so the schematic auto-layout tried to pack 512 parts.
    - *Resolution:* Pin `schX/schY` on every part. The export then succeeded (377 KB GLB). Landed in `tscircuit/index.tsx` and pcb-3d-render SKILL.md Path A ("At 256+ components tscircuit's schematic solver dies").

13. **Missed the native tscircuit 3D renderer**
    - *Symptom:* Dan asked whether tscircuit could render directly.
    - *Root cause:* Only `tsci export --help` had been checked, not the full command list.
    - *Resolution:* `tsci snapshot index.tsx --3d --update` (with `--camera-preset`) writes `__snapshots__/index-3d.snap.png` plus PCB and schematic SVGs. Dan still preferred the Blender shots. Both paths became pcb-3d-render's "Decide the path" table (Path A native, Path B Blender).

14. **OCIO locale segfault (pre-empted, not hit here)**
    - Every Blender call in this session used `LC_ALL=C LANG=C` "per the known OCIO gotcha," which came from the product-design skill. No OCIO crash occurred in this session, but the workaround went into pcb-3d-render as "ALWAYS `LC_ALL=C LANG=C`." Later evidence: the thermal-bracelet session found this does not fully cure the crash.

## Decisions and reversals

- **Architecture:** addressable smart pixels, integrated, RGB only (WS2805 and WS2815 considered and rejected on cost). Confirmed by the density solver.
- **Price before routing:** placement-only Gerbers were used for the quote. Production routing, the interconnect and power entry (~15 A/panel at 5 V full white) stayed deferred.
- **"$10 → 110 px" reversed** after calibration to the real quote. **"$10 at 256 px with $0.02 LEDs" withdrawn** after Dan's pushback. The final design point is $0.023 consigned LEDs, caps 1:2, ~$10.5/board.
- **"Cheaper clone" myth reversed:** on LCSC the XINGLIGHT clone was the most expensive part.
- **Product repositioned** as a strip replacement at strip-like density (go decision against retail strip prices), not a HUB75 competitor.
- **Renders:** three stylized renders were cut to one, plus two tscircuit-derived PCBA renders done in Blender. Native `tsci snapshot --3d` was found but not used in the README, at Dan's choice.

## Outcome

A public repo with a parametric generator calibrated to a real JLC quote ($22.86/board as JLC-sourced, ~$10.5 projected with consigned LEDs), sweep and density solvers, a placement-only JLC upload bundle, a tscircuit PCBA project, and a README with the full pricing analysis and three renders. No production board was routed and no order was placed; the project was paused. As a side product, the **`pcb-3d-render`** skill (SKILL.md and `scripts/blender_panel.py`) was added to circuit-skills, with this project as its worked example.

## Pointers

- flex-led-matrix: `gen/generate.py`, `gen/sweep.py`, `gen/density.py`, `gen/kicad_board.py`, `gen/render_model.py`, `gen/blender_panel.py`, `tscircuit/index.tsx`, `BRIEF.md`, `NOTES.md`, `README.md`, `out/`
- circuit-skills: `pcb-3d-render/SKILL.md` (Path A/B, Gotchas), `pcb-3d-render/scripts/blender_panel.py`, commit `6db19bc`
- Session memory (local): `jlc-assembly-part-availability.md`, `tscircuit-3d-snapshot.md`, `baseline-cost-finding.md`
