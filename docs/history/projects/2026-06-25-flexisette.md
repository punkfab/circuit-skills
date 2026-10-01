# flexisette — a cassette-shaped PCB music object, and where most of `pcb-layout`'s routing machinery came from

- **Dates:** 2026-06-25 16:11 → 2026-06-29 18:15, plus a repo/folder move on 2026-07-23 (UTC, transcript clock; git commits record local time, UTC−7, and are converted to UTC below) · **Sessions:** `933b73da` (dir `~/sandbox/dnewcome/flexisette`, later moved to `~/sandbox/punkfab/flexisette`; sub-dirs `pcb/`, `cad/`, `render/`, `sim/speaker_reflex` got their own session folders), `605c7ce9` (dir `…/flexisette/pcb`, a short side session) · **Repo:** [punkfab/flexisette](https://github.com/punkfab/flexisette) (created as `dnewcome/flexisette` on 2026-06-27, transferred 2026-07-23; 18 commits `ef99dd9`…`284eb4e`) · **Skills used:** kickoff, update-config, build123d-machine, build123d-part, pcb-layout, circuit-sim; **created** featuretree (06-26), pcb-enclosure-fit (06-28), move-project (07-23); **created the circuit-skills repo itself** (`8f488ba`, 06-27) and fed it commits `a3498aa` through `c9b2af4`.

## Goal

Dan wanted a physical way to release his music and visuals: a flex-PCB object shaped like a cassette, playing his music on its own, with a screen, and cheap to vary per "drop." The kickoff settled on a standalone player (ESP32-S3) with the rule "freeze the electronics, vary the cosmetics and content." The work then moved through concept specs and Blender renders, then build123d CAD of a printable cassette shell derived from vendor STLs, then a real PCB: ESP32-S3-WROOM-1, a 0.96″ SSD1306 OLED glowing through the cassette's tape window, a MAX98357A I2S amp, and USB-C/TP4056/LiPo/ME6211 power, all on the real cassette outline with its window, reel holes, screw holes and head-notch. Most of the session went into getting that board **routed automatically**. Dan's stated requirement (06-27 00:56): "I want you to do as much routing as possible first so the layout can be adjusted for fewer errors. I want this to be automated." Every gotcha was to be folded into the `pcb-layout` skill (a standing instruction saved to memory 06-27 00:21). The session closed with a 3D fit-check against the printed parts, JLCPCB fab files, and a speaker-enclosure simulation.

## Timeline

**Concept and renders (06-25)**
- **16:11** Kickoff skill. Dan chose "Standalone player (hardware drops)." Over the next hour the idea grew into a 2-board sandwich, then a flex J-card. Dan asked for motion and static displays plus NFC.
- **16:22–16:57** Five parallel sourcing agents covered motion displays, e-paper, NFC, MCU/audio/storage and power/connectors, plus later a tape-head agent. The resulting frozen-engine BOM: ESP32-S3-WROOM-1-N16R8, a QSPI AMOLED, MAX98357A, NTAG I2C, and JLC flex.
- **17:33–17:51** `PARTS.md` and four form-factor specs (A deck / B slim / C flex / D flex J-card). WebFetch/WebSearch were allow-listed globally in `~/.claude/settings.json` because Dan was tired of per-domain prompts.
- **18:07–18:56** Blender 5.0.1 at `/opt` with OptiX on an RTX 4070 SUPER. `render/build_render.py` rendered all four specs in about 4 s each, after fixes (problems 1–4).
- **19:16–20:06** Dan wanted the cassette's separate head-holes "third part." eric c's #176745 shell had it molded in. The Minecraft remix (#836410) had `side-1/2-insert.stl`, confirmed as the separate part. This became `assets/DOWNLOADS.md` (problem 5). The build123d-machine skill was used for a PCB + spacer + PCB stack (`cad/machine.py`, 100.5×64×12 mm).
- **20:09–22:25** Spacer variants (dummy/head-ready). A Makefile with `make blend` GUI targets. The `make blend` crash and the OCIO segfault were found and fixed (problems 7–8).

**Mechanical CAD (06-25 23:16 → 06-26 16:07)**
- **23:16–06-26 07:47** A long misunderstanding of what Dan meant by the insert (problem 10). It ended with Dan's explicit spec: frame = 9 mm shell − 2×1.57 mm PCB = 5.86 mm, profile extracted from the vendor shell STL by projection, thick corner bosses with blind tap-in pilots from each face. A printed face panel. The insert was made by fusing the two halves with side-2 flipped 180° about Z. Renamed bridge → protrusion → `insert` (the vendor's word).
- **06-26 06:44–07:08** Dan asked for editable FreeCAD files. The assistant found Dan's `software-mfg/featuretree` IR→FreeCAD system and, at his request, packaged it as the **featuretree skill**, adding a polygon-sketch primitive. `make freecad` emitted `frame/panel/insert.FCStd`; build123d and FreeCAD volumes matched to 0.1 mm³ (problem 11).
- **16:07** Dan was printing parts and had mated the insert by hand in Onshape.
- **16:11–18:55** Dan: "use the rest api to get onshape working with featuretree." A long BTM-format fight ended with a switch to `onpy` (problem 12). Committed to the featuretree repo as `d5a1b6f`.

**PCB generation and the measured loop (06-26 19:05 → 23:47)**
- **19:05–19:16** Tape window measured at 21.2×12 mm; a 0.96″ SSD1306 (active area 21.7×10.9) fits it. `display/tape_anim.py` renders a 128×64 1-bit winding animation; `pcb/board_outline.py` produces the outline.
- **19:32–19:50** "Use our pcb skill." No skill was named `pcb`. After checking circuit-sim and an artnode memory, the **pcb-layout** skill (from sbs-synth) was loaded. Dan picked I2S amp + speaker and LiPo + USB-C. He also asked that the subcircuit approach and the "iterate until routing runs faster" loop become tooling inside pcb-layout, not prose.
- **20:03–20:30** tscircuit 0.0.1963 was installed. Every active part was stock-checked on JLC (all deep-stocked) and imported. Four modules: power / mcu / audio / display. **`routecheck.sh`, `place-sweep.mjs` and `module-scaffold.sh` were written, debugged (problems 13–14) and copied into `~/.claude/skills/pcb-layout/scripts/`, with a new "measured iteration loop" section in its SKILL.md.** Result: audio 0, display 0, mcu 2, power 6→3 unrouted.
- **20:33–21:59** Composed onto the cassette `<board outline>` and exported to KiCad: 435 DRC violations. Dan chose "fix at the tscircuit source." The fix was `lib/fab.tsx` with a `{...JLCPCB}` preset spread into every subcircuit (problem 16), and the skill gained **`rules/` (fab.tsx + jlcpcb/pcbway/oshpark `.kicad_dru`)**.
- **22:07–22:37** Dan: parts sit in the bottom cutout. This produced **`outline-check.mjs`**: 16 parts off-board → 0. Added to the skill.
- **22:38–23:47** Dan couldn't see how to finish in KiCad (problem 18). He asked to integrate Freerouting. **`freeroute.sh`**: DSN → freert → SES, 0 unrouted in about 5 s. Added to the skill.

**The SES-import wall (06-26 23:54 → 06-27 06:50)**
- **23:54–06-27 02:29** KiCad would not import the SES (problem 20). Duplicate refdes (problem 21) and the EPAD (problem 22) were fixed. A SWIG text-injector `apply_ses.py` reached 31 unrouted and was abandoned (problem 23). The repo went public as `dnewcome/flexisette` (`ef99dd9`, 01:44); KiCad junk got committed and was then removed (`8902d40`, problem 24). Dan: "bake all of this into the skill," plus his two recurring complaints: copper pours, and 4-layer boards with Freerouting.
- **05:24–06:50** Dan installed xvfb. Automating the Specctra export failed every way it was tried (problem 25). Runaway Java processes pegged the CPU (problem 26). A web search confirmed `ExportSpecctraDSN` has been reported broken since 2020 and that the SWIG bindings are deprecated in KiCad 9.

**IPC breakthrough and fabbable board (06-27 06:52 → 06-28 06:02)**
- **06:52–07:44** Dan: "Ok so let's use the new IPC then." kipy over `/tmp/kicad/api.sock` worked (problem 27). Root cause of the earlier GND mess: **tscircuit `<copperpour>` does not export** (problem 28). This gave **`add_plane.py` and `apply_ses_ipc.py`**: 519 tracks/vias injected with 0 unmapped nets, and **`index.circuit.kicad_pcb` routed in place for the first time.** The skill gained the sections "Automate KiCad headless via the IPC API" and "Layer stackup strategy (2L pour vs 4L planes as zones)."
- **07:48–08:54** Named-net fix and **`merge_nets.py`** (problem 29). The interior holes had been missing (problem 31). **`drc_check.py`** and **`add_cutout_keepouts.py`**. Courtyard overlaps 7 → 0. Dan then critiqued the approach: "we keep trying to route with the same component layout and we aren't iteratively applying heuristics to the layout." That led to **`route.sh`** (one-command pipeline), the modular-vs-non-modular section, and placement heuristics in the skill.
- **16:42–16:46** **circuit-skills repo created** (local `~/sandbox/dnewcome/circuit-skills`, public `dnewcome/circuit-skills`, `8f488ba`) holding pcb-layout and circuit-sim.
- **16:50–21:35** The heuristic placement grind (problems 33–35). Audio next to mcu took unrouted 16→5; power next to mcu took it 5→1; then the restructure with all cutouts kept, which passed **all three gates (outline ✓, courtyard 0, fast-route 2 unrouted)**. Routed via IPC. Commit `9aa73bb` (21:27). **circuit-skills `a3498aa` "headless IPC routing + 3-gate placement convergence"** (21:34).
- **21:36–22:35** Dan asked for an autoplacer. **`autoplace.mjs`** (block-level simulated annealing on HPWL with the three gates as hard penalties) plus 10 unit tests (problem 36). flexisette `5f5874f`/`f524af7`; **circuit-skills `201608f`.**
- **22:38–23:30** The OLED became a placed part (back layer, 27×27 silkscreen body over the window). **`outline-check` `ALLOW_IN_CUTOUT`** (circuit-skills **`e2a80ea`**). A keepout-respecting route converged. flexisette `876853f`.
- **23:35–06-28 06:02** Dan: one trace still crosses the OLED window. That was the window-keepout regex bug (problem 38). **`apply_fab_rules.py`** took cosmetic DRC 216→23 (problem 40). flexisette `6cdd4e1`; **circuit-skills `c94e495`.**

**Finishing, fit and fab (06-28 06:08 → 20:24)**
- **06:08–07:27** Surgical short fixes (problem 41). Dan asked whether Freerouting is deterministic. Real shorts 3→0.
- **07:31–08:13** Live-IPC finishing: GND-pad vias collided with stray stubs (problem 42). Dan spotted copper outside the board edge (problem 43) and asked "is it just you using regex?" (problem 44).
- **16:27–16:57** Root-cause fix: U1 block `pcbX -40 → -38`, clean re-route, edge-over-cut 5→0, shorts 0 again.
- **17:16–18:46** Gerbers via kicad-cli. **3D fit-check** (`cad/import_pcb.py`, `cad/render_fit.py`, `make fit`). Dan chose a new skill: **pcb-enclosure-fit** was created and cross-linked from pcb-layout and build123d-machine. The tscircuit 3D path was corrected (problem 47). **`make fab`** (Gerbers + BOM + CPL). Dan ran JLC's online DFM (problem 49).
- **19:04–19:14** "Commit everything and push": flexisette `245030b`, **circuit-skills `76b4735`** (pcb-enclosure-fit + surgical short-fix + edge-over-cut DRC).
- **19:19–19:47** Dan: tighten iteration speed, support per-release board variants, round-trip hand edits, and put connectors on the edges. **`sync_positions.py` / `apply_placement.py`** with `placement/<variant>.json` and `make place/sync/variant` (problem 50). flexisette `0c55221`, **circuit-skills `c33adf9`.**
- **19:50–20:24** **`untangle.mjs`** part-level rotation pass plus 7 tests (problem 51). flexisette `096a3a6`, **circuit-skills `c9b2af4`.**
- **21:47–22:21** Validation: ratsnest crossings 51→36 (29% fewer), signal wirelength 943→815 mm. Planning docs only (Dan: "plan this feature but don't build anything"): `placement-constraints.md` and `roadmap.md` (`e1ff34f`).

**OLED 3D, docs, speaker (06-29)**
- **00:00–03:47** `cad/oled.py` (the module has no CDN 3D model); `merge_oled_glb.py` merges it into tscircuit's GLB; `make show`; the Blender assembly render now picks up the real board and the OLED (`8becbf0`, `5ad3424`, `959e6f5`).
- **03:50–04:38** "We need a massive amount of documentation." Four parallel drafting agents plus the main assistant wrote 11 docs, 2,250 lines, in `docs/` (`b0218f4`). The drafting surfaced real discrepancies (problem 53).
- **05:43–06:41** Speaker design. A feature-ideas TODO for tape-deck playback (hub encoder + head-emulation coil). A Thiele-Small ngspice model via the circuit-sim skill (problems 54–56). Decision: face-firing, sealed, PUI AS01808AO (`dc2342d`, `676db07`, `284eb4e`).
- **06:42–17:23** Speaker chamber CAD (problems 57–59). The head-emulation discussion concluded: use a real tape head (doc only). Dan paused at 18:14. **The speaker CAD and sim updates were never committed.**

**Move (07-23)**
- **17:40–18:49** Dan: move to the punkfab org, move the local folder and session, and "write a skill for moving projects." **move-project skill** written. GitHub transfer `dnewcome/flexisette → punkfab/flexisette`, origin repointed, 8 hard-coded `/home/dan/sandbox/dnewcome/flexisette` paths rewritten, folder and six `~/.claude/projects/-home-dan-sandbox-dnewcome-flexisette*` dirs renamed. The condensed log ends during the verification step. The current repo state confirms the move landed. The path rewrites, speaker work and render changes are still uncommitted in the working tree (verified with `git status`).

## Problems and fixes

### Renders and concept tooling

1. **Blender spec renders broke in several ways.**
   - **Symptoms:** First render blown out (pure-white background). Spec C: `AttributeError: 'NoneType' object has no attribute 'deform_method'`. Spec D: art floated below the panel, then white streaks after weld+bend. Spec C's gold reels vanished.
   - **Root causes:** Lighting too hot. A modifier was added to a parented Empty. Bending text curves smeared them. A BEVEL modifier ate the small welded ring geometry, and an X-axis bend sank the reels into the board.
   - **What worked:** AgX + exposure −0.8 + dark studio. `_weld()` joins the art into the board mesh before bending. D rebuilt as a flat card with a separate folded spine. Bevel removed after welding; bend axis switched to Y.
   - **Status / landed:** Fixed in `render/build_render.py`.
2. **Minor tool-input errors.**
   - **Symptoms:** AskUserQuestion rejected 5 options (`too_big … <=4`). Two Printables WebFetches failed with `Parse Error: Header overflow`.
   - **Status:** Questions re-asked with 4 options. License and author logged as **TBD** in `assets/DOWNLOADS.md`. Never resolved in-session.
3. **Assembly mate math.**
   - **Symptom:** `TypeError: unsupported operand type(s) for *: 'Part' and 'Pos'` in `cad/machine.py`.
   - **Root cause:** Wrong operand order when composing mates.
   - **Fix:** For a simple vertical stack, use param-derived Z datums (which the build123d-machine skill allows).
4. **`make blend` GUI launch crashed at line 224.**
   - **Root cause:** `bpy.context.object` is `None` when a script runs at GUI startup, because the window context isn't ready yet.
   - **Fix:** A `_new()` helper using `view_layer.objects.active`, with a fallback to the last scene object, in all render scripts. The scripts auto-render only when `bpy.app.background` is set.
   - **Status:** The GUI path was not reproduced, because xvfb-run wasn't installed then.
5. **Which file is the "third part"?** eric c's shell has the head features molded into each half. The Minecraft remix's `side-1-insert.stl` (70.15×8.8×16) is the separate piece, confirmed by measurement and renders.
6. **Rendered part floated 4.4 m in the air.** `o.dimensions` was read *after* scaling. Fix: capture the height before scaling, in `render_frame.py`.
7. **Blender 5.0.1 segfault.**
   - **Symptom:** No traceback, `Writing: /tmp/blender.crash.txt`, make `Error 139`. Backtrace in `libOpenColorIO.so.2.4` → `sscanf`.
   - **What was tried:** `LC_ALL=C` alone seemed to fix it, then crashed again under make. Measured: 5 OK / 1 crash out of 6 runs (about 17%).
   - **Fix:** `render/blender_render.sh` retry wrapper (`LC_ALL=C`, `ATTEMPTS=5`). It caught a crash on the next clean build and the build still exited 0.
   - **Root cause:** Never found beyond "flaky native crash in OCIO's AgX LUT."
   - **Where it landed:** The same gotcha appears in the later pcb-3d-render skill's description.
8. **Later claim that "Blender isn't on this machine."**
   - On 06-28 17:35 and 06-29 03:46 the assistant said Blender wasn't available and that renders happen on Dan's "GPU box," because `which blender` failed.
   - On 06-25 Blender 5.0.1 had run locally at `/opt/blender-5.0.1-linux-x64/blender` with OptiX. The claim was wrong; Blender just wasn't on PATH (inferred). It was never corrected in-session, so the Blender assembly render stayed stale (06-26 vintage).

### Mechanical CAD and featuretree

9. **Frame/screw details.**
   - Shell thickness changed from 12 mm to Dan's 9 mm: `CASSETTE_T=9`, `SPACER_GAP=5.86`.
   - Back-to-back M3 heat-sets can't fit in 5.86 mm, and Dan wanted no through-hole or nut. Fix: Ø7 bosses with blind Ø1.7×2.5 mm pilots from each face, leaving a 0.86 mm web, for M2 thread-forming screws.
   - Outline and screw positions are extracted from `side-1-plain.stl` via `mesh.projected()`: 35-point outline, 7 holes.
10. **The insert was misread three times.**
    - **Attempt 1 (clean parametric `head_frame.py`):** Dan said "that doesn't look right."
    - **Attempt 2 (back-fill one half, union into the spacer as `spacer_solid.py`):** wrong; it was meant to be a separate print.
    - **Attempt 3 (fuse the halves without a flip):** "still looks totally wrong." Dan reset the scope to just the frame.
    - **What finally worked (06-26 07:36):** Dan explained the halves "fit together flipped over to form a hollow shell." The assistant tried rotX/rotY/rotZ flips with a manifold union, rendered all three, and rotZ produced the trapezoid. Dan had also done the mate by hand in Onshape.
    - **Lesson (as recorded):** "stop guessing and read the vendor's own assembly." The STEP showed the halves laid out flat for printing, not assembled.
    - **Landed:** `cad/insert.py`.
11. **FreeCAD export issues (featuretree skill).**
    - Headless `.FCStd` files opened all-hidden in the GUI. Fix: set App-level `Visibility` (Body + tip only) before save, in `featuretree/fc_build.py`, committed `d5a1b6f`.
    - Dan thought the panel looked 2D. It is 1.57 mm thick (volume ÷ area confirmed it).
    - The insert had no feature tree because it was a fused mesh. Fix: reverse-engineered as a front-silhouette `profile → pad` (9195.5 mm³ solid).
12. **Onshape REST emitter.**
    - **Symptoms, in order:**
      - `409 "Free accounts only allow access to public documents"`. Fix: create public docs.
      - `400 "Error processing json"` with the flat `btType` form. The `{type,typeName,message}` envelope then parsed.
      - `400 "Error in input" code 9999`, even for an *empty* sketch. Plane referenced by transient ID (`JDC`, verified via FeatureScript eval): still failed.
      - `Accept: */*` with flat form: back to the parse error.
    - **Resolution:** Switched to the `onpy` library. Further snags there:
      - `onpy.configure()` always prompts, so it hit `EOFError`. Fix: write `~/.onpy/config.json` and skip `configure()`.
      - Default units are inches (radius 15 → 0.381 m). METRIC means *meters*, so scale mm×0.001.
      - The plate sample worked. The real panel **timed out at 2 min**, because onpy makes one API call per sketch segment.
      - Sketches arrive under-defined because onpy has no constraint API.
    - **Status:** Plate works. Panel unresolved (suggested fix: emit circles as circles and simplify the outline; not done). Under-defined sketches accepted. Junk public docs left in Onshape (the key has no delete scope). API credentials are kept outside the repos.

### PCB generation and the measured loop

13. **`routecheck` was over-strict.** It marked audio as failing on tscircuit's generic `⚠ Build completed with errors`, which exits 0 for benign unconnected NC/mounting pads. Fix: count only specific fatal patterns. Landed in `routecheck.sh`.
14. **`place-sweep` reported false zero unrouted.**
    - **Symptom:** Every candidate position scored 0 unrouted, while the trusted routecheck said 6.
    - **First theory (wrong):** `execSync` maxBuffer truncation. Switching to a log file revealed the real error.
    - **Root cause:** The log said `timeout: failed to execute process`. `timeout 120 PATH=… tsci` makes `timeout` try to exec `PATH=…` as the program.
    - **Fix:** Pass PATH via the child `env`. True counts then came out 6/6/4, and moving R_CC1 to (−22,4) and R_CC2 to (−19,4) took power 6→3.
    - **Landed:** The gotcha is in SKILL.md "Gotchas the loop itself taught."
15. **Placement regressions caught by the loop.** A TP4056 EP via didn't take, and power went 5→6. An "edge-aware" button move took mcu 1→2. Both were left as the hand-finish tail.
16. **Export not fab-legal.**
    - **Symptom:** KiCad DRC found 435 violations and 12 unconnected: 80× each `via_diameter`/`drill_out_of_range`/`clearance`/`annular_width`, 37 shorting, 31 mask bridge, 23 edge. Vias were 0.3/0.2 mm; tracks 0.05–0.12 mm.
    - **Root cause:** Board-level `minTraceWidth`/`via*` props don't reach subcircuits, which each have their own autorouter. tscircuit also ignores the via-size props entirely.
    - **Fix:** `lib/fab.tsx` `JLCPCB` preset spread into every board and subcircuit. Tracks became 0.15 mm; vias stayed 0.3/0.2, so via size is a KiCad-side step. KiCad custom rules can only tighten, not loosen.
    - **Side gotcha:** `tsci export` names its output `index.circuit.kicad_pcb` whatever the input, which overwrote the composed board once.
    - **Landed:** Skill `rules/` + "DRC rulesets (default: JLCPCB)."
17. **Parts placed in the head-notch.**
    - **Symptom:** Dan: "the router didn't respect the board outline, there are parts in the cutout at the bottom." The power block sat at y=−23, inside the notch.
    - **Root cause:** tscircuit has no keep-in. Its `pcb_component_outside_board_error` is buried under the generic build message, and cutout overlap isn't checked at all.
    - **Fix:** `outline-check.mjs`. 16 parts off-board → 3 + 2 in a cutout → 0.
    - **Landed:** Skill script + "board-outline rule."
18. **KiCad workflow confusion.**
    - Dan couldn't find the to-do list. The assistant's first answer was over-complicated; it is the DRC dialog.
    - 45° traces: KiCad routes at 45° by default; tscircuit's router is orthogonal.
    - "Isn't KiCad without an autorouter?" Correct. The assistant had loosely said "autorouter-off export" when it meant tscircuit's router.
19. **tscircuit `autorouter="freerouting"` preset doesn't drive a local Freerouting.** It falls back (7 unrouted) and throws `Multiple subcircuit connectivity keys found … PcbCopperPourRender`. Fix: an explicit `tsci export -f specctra-dsn` → `freert` → `.ses` (`freeroute.sh`), which reached 0 unrouted with 19–21 vias in about 5 s.

### The SES import wall (06-26/27)

20. **The routed SES would not import into KiCad.**
    - **Symptoms:** GUI import error `expecting 'a symbol or number' in index.ses line 77 offset 21`; after patching that, `Reference 'R1_source_component_1' not found`.
    - **Root causes:**
      - Freerouting writes an empty `(host_version )`. Fix: patch it with `sed` in `freeroute.sh`.
      - The SES was routed from *tscircuit's* DSN, so its refs are foreign to KiCad.
      - Every automated alternative was blocked: `kicad-cli` has no Specctra command; headless `pcbnew.ExportSpecctraDSN` returns `False`; `ImportSpecctraSES` throws `'SwigPyObject' object is not iterable` (also after stripping `_source_component_N` ids).
      - tscircuit's `auto_cloud` router is hosted Freerouting (`internal-freerouting.fly.dev`) and returned HTTP 500 three times.
    - **Interim:** the bad SES was renamed `index.measure.ses.DO-NOT-IMPORT`. The 3-click GUI path (export DSN → `freeroute.sh` → import → save) was documented.
    - **Status:** Superseded by IPC (problem 27).
21. **Duplicate reference designators** (`U1`, `C1`, `R1`, `C_BULK` ×2) from module-local names. Fix: globally unique refs. A remaining empty-ref 0-pad `tscircuit:Unknown` per `<cutout>` is benign. Landed as a skill pitfall.
22. **ESP32 EPAD only partly grounded.** Dan asked about pads under the module. GND covered pads 1, 40, 41; split paste pads 42–49 were unconnected. Fix: tie all of them to GND. Landed as a skill pitfall ("thermal pads import as a split grid").
23. **SWIG text-injector `apply_ses.py`.**
    - **Results:** 500 segments + 19 vias placed, but 82 unrouted / 131 shorts. Zone refill, then geometric net assignment → 31/51. Union-find → 31/53, almost all V3V3↔GND.
    - **Theory at the time:** the GND pour couldn't be reconstructed. The later diagnosis was guessed net assignment plus the missing pour (problem 28).
    - **Status:** Abandoned. Kept in the skill as an "OBSOLETE SWIG relic."
24. **KiCad cruft committed to the public repo** (`_autosave-*`, `.lck`, a stray module `.kicad_pcb`). Removed and gitignored in `8902d40`.
25. **Automating the Specctra export under xvfb.**
    - **Setup:** Dan installed xvfb. `ExportSpecctraDSN` still returned False, with `GetBoard()` None (it needs the app frame).
    - **Tried, all failed:**
      - An action plugin plus xdotool clicks. The GTK menu grab ate synthetic clicks, and keyboard navigation didn't work either.
      - A `wx.CallLater` auto-run. `GetBoard()` returned a board with `fps=0`.
      - `LoadBoard` inside the app: export still False.
      - Widening Xvfb to 2200×1200: pcbnew crashed (no window manager).
    - **Final test:** pcbnew was launched on Dan's real `:0` display and Dan clicked the plugin. The trace showed `run fps=36 … export ok=False`, so the binding itself is broken.
    - **Confirmation:** a KiCad forum thread "ExportSpecctraDSN() broken in nightly?" (2020); SWIG bindings deprecated in KiCad 9, removed in 11.
    - **Status:** Abandoned. Plugin deleted. The skill records "NO automation of the DSN export — period."
26. **CPU fan pegged.**
    - **Symptom:** Two orphaned Freerouting Java processes at 101% CPU for 23–33 min, spawned by the plugin experiments; the assistant blamed an empty or missing DSN.
    - **Fix:** `pkill`. That also killed the KiCad Dan had just reopened, which the assistant apologized for.
    - **Side session `605c7ce9`** (06-27 06:41, started as a memory-extraction hook) blamed a stray ImageMagick `convert` instead and never measured CPU. The main session's `ps` measurement is the reliable one (inferred).
    - **Landed:** The pass-cap / "never grind" guidance in `freeroute.sh` and the skill.

### IPC routing and board cleanup (06-27)

27. **Getting kipy to connect.**
    - **Symptoms:** `"api": {"enable_server": false}` by default. `ConnectionError: Connection refused`. Stale `/tmp/kicad/api.sock` and `api.lock`.
    - **Root cause:** The Bash tool reaps `setsid` background children, so pcbnew launched that way died.
    - **Fix:** Enable the server in `kicad_common.json`, clear stale lock/sock, and launch pcbnew as a harness-managed background task.
    - **Landed:** Skill IPC section.
28. **The KiCad board had zero copper zones.**
    - **Root cause:** `<copperpour>` declared in every module is silently dropped by `tsci export -f kicad_pcb` (`grep -c '(zone'` → 0). This is why GND was being routed as a tangle of tracks, matching Dan's earlier "issues with copper pours" and the 4-layer complaint.
    - **Fix:** `add_plane.py` adds zones via IPC. kipy's `Zone.outline` getter raises `IndexError` on an empty zone, so the code builds a `PolygonWithHoles` itself. It warns when a pour fills as more than 1 island (B.Cu filled as 3 islands while signals also used B.Cu; later 1).
    - **Landed:** Skill pour pitfalls + the layer-stackup section, including "4-layer: planes are ZONES, route signals only."
29. **False shorts from fragmented nets.**
    - **Root cause:** tscircuit scopes `net.X` per subcircuit, so one signal exports as several net codes. SDA had 5; V3V3 had 9.
    - **What was tried:** Named nets in source (still fragmented). Re-netting pads via IPC `update_items` (doesn't stick).
    - **Fix:** `merge_nets.py`, a file-level rename by base name: 72 nets → 23.
    - **Bug in the first version:** the net-table scan didn't stop at the footprints, so it deleted *pad* net lines (`Pad 1 [<no net>] of R2`). Fixed to scan only the contiguous table block. Shorts went 81 → 6.
    - **Landed:** Skill "modular vs non-modular" section + the merge script.
30. **`apply_ses_ipc.py` defects.**
    - Vias took KiCad's default size (38 `via_diameter`/`annular`). Fix: parse the size from the `Via[0-1]_600:300_um` padstack.
    - A fresh DSN used a `_source_component_N` infix, leaving 9 nets unmapped. Fix: a regex strip.
    - Endpoint-snapping to pad centres was tried and backfired (crossings 0→7, more shorts, unconnected unchanged). Reverted and documented in-code.
31. **Interior holes missing from the board.**
    - Dan pointed out the hub circles and screw holes. `cassette_outline.json` held only the exterior ring; `panel._rings()` had 7 holes.
    - The assistant first claimed the window cutout hadn't exported either. Dan disagreed, and it was in fact a `gr_poly` the loop-parser ignored.
    - Polygon `<cutout>`s exported **0** shapes. Fix: rect for the window, circles for reels and screws, from `lib/cassette_holes.json`.
    - **Landed:** Skill pitfall "interior board holes get dropped, then routed across."
32. **Keepouts.** A `<cutout>` is not a DSN keepout. Fix: `patch_dsn_keepout.py`, then generalized to `add_cutout_keepouts.py` (auto-detects interior Edge.Cuts shapes). With keepouts on, routing went **2 → 15–17 unrouted** because the hole-filled centre blocked the mcu↔audio buses. That is a floorplan problem.
33. **Freerouting v2.1.0 behaviour, and v2.2.4.**
    - **Symptoms in v2.1.0:** `-mp`/`-oit` are ignored. `router.max_passes: 9999` in `/tmp/freerouting/freerouting.json` and in the working directory are both ignored. It writes the SES **only on convergence** and otherwise oscillates at 1–17 unrouted until the timeout (`rc=124`, no SES).
    - **Upgrade attempt:**
      - v2.2.4 needs Java 25 (`UnsupportedClassVersionError … 69.0 … up to 65.0`). Temurin JRE 25 was downloaded to `~/.local/share/jdk25` without sudo.
      - v2.2.4 detected `DISPLAY` and popped a GUI on Dan's screen.
      - Once headless, its parser rejected the tscircuit DSN: `padstack name expected at 'V3V3'`, `DSN structure parsing failed`.
    - **Resolution:** Pin v2.1.0. Give a well-placed board a long window (150–280 s) to converge. Fall back to a no-keepout route plus a geometric crossing check.
    - **Landed:** `freeroute.sh` header + SKILL.md "Pin Freerouting v2.1.0."
34. **Heuristic placement broke outline validity.**
    - Audio next to mcu took unrouted 16→5; power next to mcu took it 5→1. But the outline gate wasn't run, and Dan noticed parts back in the notch and U1 over a reel.
    - The earlier analysis had filtered outline points to `y<−25`, which hid the notch, and claimed "the bottom edge is clean (no head notch)."
    - **Fix:** Grind the three gates in order (outline → courtyard → unrouted); `outline-check` wired into `route.sh` as step 2.
    - Dan asked whether 4-layer would make the cutouts work. Answer: through-cuts remove copper on all layers; 4-layer only relieves congestion.
35. **The hard re-floorplan with every cutout kept** (Dan: "Keep everything as cutouts").
    - The mcu block was 33 mm wide but the left region is 24 mm. Fix: stack the support parts above U1.
    - Breakout headers J_IO/J_I2S/J_PWR were redundant once buses use named nets and programming is over USB. Dan chose "drop all three": courtyard 14→10.
    - Reset/boot buttons were dropped too (esptool resets over USB-CDC). Result: courtyard 0, outline ✓, fast-route 2 unrouted, converged route 1 unrouted / 244 wires.
    - **Landed:** Skill "map the clear regions first / narrow a too-wide block / drop redundant parts."
36. **Autoplacer bugs.**
    - `find dist … | head -1` picked a module's `circuit.json`, giving "1 blocks, 0 edges." Fix: use `dist/<base>/circuit.json`.
    - From a random scramble it reached in-board placement but left 5 courtyard overlaps. Random restarts were added; final convergence is a hand finish.
    - `node --test tests/` was mis-parsed as a module in node v24 (`Cannot find module …/tests`). Fix: glob `tests/*.test.mjs` (`f524af7`).
37. **OLED as a placed part.**
    - No JLC part exists, so a custom `<chip footprint>` was written with platedholes plus a silkscreen body. An edit accidentally dropped the `<subcircuit>` opening tag, causing a JSX error.
    - outline-check flagged it over the window. Fix: `ALLOW_IN_CUTOUT` (default `OLED`), circuit-skills `e2a80ea`.
38. **One trace still crossed the OLED window.**
    - The earlier check tested only track *endpoints*, so a segment passing through the window with both ends outside was missed.
    - **Root cause:** `add_cutout_keepouts.py`'s `gr_poly` regex required `)` immediately after the last `(xy …)`, but the export has a newline there. **The window had never been kept out**; only the six circles had.
    - **Fix:** `\s*` before the `)`. 7 interiors now detected, 14 keepout rects, segment-intersection check 0. Commit `6cdd4e1` / circuit-skills `c94e495`.
39. **"Unrouted" vs "unconnected" (1 vs 15).** Explained: Freerouting counts ratlines; KiCad counts missing pad connections. The pour rescues some; injection slop can add some.
40. **Hundreds of false DRC violations.**
    - **Root cause:** KiCad defaults are stricter than JLC: Default net class clearance 0.2 mm, `min_copper_edge_clearance` 0.5, min text 0.8. kipy can't set net classes; the rules live in `.kicad_pro`.
    - **Fix:** `apply_fab_rules.py`. Cosmetic violations 216→23.
    - **Side effect, discovered later:** downgrading silk/cosmetic severities hid issues that JLC's DFM caught (problem 49).

### Finishing the tail (06-28)

41. **Three real shorts after injection** (2× V3V3 over U1's EN pad, 1× VBAT through C_IN's GND pad).
    - **What was tried:**
      - Global DSN clearance 150→250: 17 unrouted, never converged.
      - Targeted `smd_wire`/`pin_wire` 250 (honoured): 52–88 unrouted.
      - Manual text edits, first round: U1's pads are 1.5 mm wide in X (x[50.5,52.0]), so the nudge to 51.95 was still inside the pad. The VBAT L-detour ran through Q1's VSYS pad, then the next one clipped an unseen VSYS via.
    - **Determinism answer given:** same DSN + settings → same SES (fixed seed); time-capped runs are not reproducible. So re-rolling the router is pointless; change the input instead.
    - **Resolution:** Obstacle-aware surgical reroutes using real pad geometry. V3V3 exits east at x=52.3; VBAT threads the 0.6 mm gap between the C_IN pad and the via ring. Shorts 3→0.
    - **Landed:** SKILL.md "Fixing a handful of residual shorts … surgically," circuit-skills `76b4735`.
42. **GND vias at GND pads created new shorts.**
    - **Symptoms:** First pass: unconnected 13→9 but 7 new shorts. After the re-route: 11→6 with 7 new shorts. Power-pad vias: 6 shorts + 2 crossings.
    - **Root cause:** Freerouting had left short foreign-net B.Cu stubs ("droppings"). It ran each cap's power feed down the GND pad's column, about 1 mm off.
    - **Status:** Reverted each time to the clean state. Only R_CC2's via survived. The cap cluster plus **DIN** stayed unrouted (**still open: 10 unconnected**). Point-in-polygon pour checks were judged unreliable because of thermal-relief voids.
43. **Copper over the board edge was classified as cosmetic.**
    - Dan: "there's a trace outside of the board cut on the left side around the esp32." DRC showed `copper_edge_clearance` with `actual=0.0 mm`: a 20.9 mm GND F.Cu spine entirely off-board, and DIN/EN at 0.017 mm.
    - **Root cause:** U1 sat 0.6 mm from the left edge, and the router used that strip as a highway.
    - **Fixes:**
      - `drc_check.py` now promotes edge violations with gap ≤ 0.05 mm to blocking "edge-over-cut" (it also hit a `sorted(dict)` TypeError, fixed with `key=`).
      - Deleting the off-board GND spine was correct. Shifting DIN/EN made 6 new shorts with SDA/V3V3 (four nets in 0.62 mm), so that was reverted.
      - Root-cause fix (Dan chose it): `McuBlock pcbX -40 → -38` and a clean `route.sh` re-run. Edge-over-cut 5→0, BCK/WS now routed, 2 new pad-clip shorts fixed surgically on the first try.
    - **Landed:** circuit-skills `76b4735`.
44. **"Is it just you using regex in the kicad file?"** Answer: pass/fail always came from `kicad-cli pcb drc` JSON; regex was used to *locate* things, and was fragile (problem 38 was a regex bug). Inspection moved to kipy typed objects (`get_tracks()`, `get_shapes()`). `kiutils` was named as the offline option but isn't installed.
45. **pcbnew relaunch failures.** A stale `/tmp/kicad/api.lock` with no socket, and a launch that died inside a compound command. Fix: remove lock/sock, launch as a tracked background task, poll `kipy.KiCad().get_board()` until it connects.

### Fit, fab, round-trip (06-28/29)

46. **Board vs shell mismatches surfaced by the 3D fit-check.**
    - `kicad-cli pcb export step` exits non-zero on warnings even when the file is written.
    - KiCad is Y-down, so the importer mirrors Y.
    - Board outline 102.2 mm vs `SHELL_W=100.5` (+1.7 mm overhang): **open**.
    - The printed panel's window is taller than the board cutout (green sliver above the OLED): **open**.
    - **Landed:** pcb-enclosure-fit skill (`import_pcb.py`, `render_fit.py`).
47. **Wrong claim that the KiCad STEP is bare because tscircuit has no 3D.**
    - Dan: "I thought tscircuit had a 3d viewer built in?" `tsci export -f glb|step` carries 30 CDN models.
    - The export prints a `PcbCopperPourRender` async error, which is benign.
    - `tsci` mangles an absolute `-o` path (strips the leading `/`). Fix: pass a path relative to `pcb/`.
    - tscircuit's frame is Y-up, so no flip is needed.
    - The OLED has no CDN model. Fix: model it in `cad/oled.py` and merge into the GLB with `cad/merge_oled_glb.py` (Y-up conversion, 45 → 47 meshes).
    - **Landed:** Corrected in pcb-enclosure-fit ("two 3D sources").
48. **Where are the files?** Dan was repeatedly confused about where renders live. Speaker renders had been written to `/tmp`. Fix: renders go in `cad/build/` and `pcb/build/` (gitignored), plus a `make show` target.
49. **JLC DFM vs KiCad DRC.**
    - JLC's check took about 10 min the first time; the assistant attributed this to internal cutouts or queueing (inferred). The second run finished.
    - The report flagged: PTH→trace 0.04 mm Danger ×3 (USB-C NPTH posts vs GND/VBUS); pad→edge 0.07 mm Danger ×2 (not pinpointed; KiCad doesn't flag it); silk Danger 59+17+58; annular warnings ×44. "Trace to board edge: Good."
    - **Root cause of the gap:** the severity downgrades from problem 40 hid silk issues, and JLC reads the raw Gerbers.
    - **Status:** Deferred to a "production-clean pass." Fine for a fit prototype. `make fab` (Gerbers zip + BOM 18 parts/29 designators + CPL 30; OLED listed as hand-assembled).
50. **Round-trip fidelity check gave a false pass.**
    - The first check reported "30 parts, 0 mismatched → FAITHFUL ✓," but the sync had read **0** parts.
    - **Root cause:** A fresh `tsci export` writes `(layer F.Cu)` unquoted with the name on the next line; a KiCad-saved board writes `(layer "F.Cu")`.
    - **Fix:** Tolerant regex. Then 30/30 parts, 0 drift.
    - A commit initially staged the wrong path (`placement/` instead of `pcb/placement/`). Re-done.
    - **Landed:** circuit-skills `c33adf9`.
51. **`untangle.mjs` dropped no power nets.** It printed `fanout>NaN`, so 0 power nets were dropped (arg-parse bug). Fixed, and a gate check was added so a rotation can't push a part off-outline or onto a cutout. Result: 14% shorter signal wirelength, 11 parts rotated. **Landed:** circuit-skills `c9b2af4`.
52. **Placement round-trip doesn't reach the routing DSN** (found during validation). `route.sh` applies `placement/<V>.json` to the board but exports the DSN from the `.tsx`. **Open**, recorded in `docs/roadmap.md`.
53. **Discrepancies found by the docs pass.** Stale `machine_params` thickness comments ("~12 mm", "8.8") vs `SPACER_GAP=5.86`; wrong step labels in `route.sh`; no `make route`; GLB not wired into `make fit`; `apply_ses.py`/`patch_dsn_keepout.py` still present. **Open**, recorded in `docs/roadmap.md`.

### Speaker (06-29)

54. **Sim result bugs.**
    - Fb detector picked 20 Hz (the low-frequency asymptote). Fix: search a 150–900 Hz band; found 412 Hz.
    - **Sign error:** radiated sum `Ud+Up` should be `Ud−Up`. With it fixed, "port lifts low-mids −5 dB" became **~0 dB benefit** over sealed at 6 cm³.
    - The 1 W drive level was absurd for the driver: excursion-limited at about 13 mW.
    - ngspice vs analytic matched to 0.00% throughout.
55. **Driver sizes.** Drivers with full published T-S (Dayton CE4895: 48×95×52 mm) don't fit a 9 mm cassette. Dan chose face-firing, sealed, PUI AS01808AO (Vas/Qts unpublished, so estimated).
56. **Wrong Fs.** The sim used Fs = 320 Hz from a DigiKey highlight page. The part datasheet (AS01808AO-3-R) says **420 Hz ±20%** (420 Hz–14 kHz, aluminium diaphragm, 2.5 mm thick). The knee moved from ~666 to ~874 Hz: midrange presence, not bass.
57. **Chamber not watertight** at first (flange face coincident with the cavity wall; bosses tangent). Fix: real volume overlaps, bosses fused after hollowing.
58. **Chamber was the wrong shape.** Dan: "it's not the shape of the insert." It had been a 45×40 slab; the insert is a 16×70.2×9 mm bar. Fix: carve the chamber from `insert.stl` with a manifold boolean, keeping a slot for a coil (Dan chose "share"). Back-volume reported as ~3.6 cm³; one render script printed "carved volume 4.86" (not reconciled). Display rounding showed 3.6 as "4" (fixed with `:g`).
59. **Head emulation.** A flat or flex coil can't work at audio frequencies (V ∝ jωΦ needs a concentrated soft core). Decision: use a real tape head; documented in `docs/feature-ideas.md`. **The speaker CAD, sim retarget and docs from 06-29 06:42 onward are uncommitted.**

## Decisions and reversals

- **Architecture:** standalone player over companion-key (Dan chose it knowing drops get harder). Display: 0.96″ SSD1306 in the tape window, not the 1.91″ AMOLED from sourcing. Audio: MAX98357A + speaker. Power: LiPo + USB-C.
- **Insert:** clean parametric → back-filled half unioned to spacer → separate fused print → *flipped* halves fused (final). The vendor name "insert" was kept.
- **Routing back into KiCad:** tscircuit `sequential-trace` → in-tool `freerouting` preset (fails) → DSN→freert→GUI SES import (fails: foreign ids) → SWIG text-injector (abandoned) → xvfb/plugin automation (abandoned: binding broken) → **kipy IPC injection (kept)**. The skill's "every autorouter is immature → hand-route" stance was softened to "Freerouting is a good *finisher* on a well-placed board."
- **Fab rules:** fix at the tscircuit source (Dan's choice). Tracks fixed there; vias are KiCad-side.
- **Copper pour:** from tscircuit `<copperpour>` (silently dropped) → zone added via IPC.
- **Modular breakout headers:** used for per-block routing, then dropped once named nets plus `merge_nets` worked.
- **Cutouts:** all kept as real keep-outs (Dan: "If I want to remove something I will remove it from the svg board outline").
- **Freerouting version:** tried v2.2.4, pinned v2.1.0.
- **Finishing shorts:** global clearance bump (rejected) → surgical edits. GND-pad vias (reverted twice). Edge strip: nudge (reverted) → move U1 2 mm and re-route.
- **Severity downgrades:** helped triage, but hid real silk issues; JLC DFM is the fab gate.
- **Fit-check home:** a new pcb-enclosure-fit skill rather than folding into pcb-layout or build123d-machine (Dan's choice).
- **Placement constraints feature:** planned only, per Dan.
- **Speaker:** bass-reflex folded port → sealed (sim showed ~0 dB benefit). Forward-firing → face-firing. Free-standing slab → carved from the insert, shared with a coil slot. Coil → real tape head.

## Outcome

The board is prototype-fabbable: 0 shorts, 0 crossings, 0 copper over the cut, keepouts clean, placement passes all three gates. **10 nets remain unconnected**, including **DIN** (no audio without it) and the LDO decoupling cluster, so the board is not electrically complete. JLC DFM dangers remain (USB-C PTH clearance, 2 pad-to-edge, silk). Fab files, the 3D fit-check with the OLED, and an 11-doc set exist. The project spawned or grew three skills (featuretree, pcb-enclosure-fit, move-project) and provided most of `pcb-layout`'s machinery that now lives in circuit-skills:

- the measured loop;
- fab rulesets;
- `outline-check` (including `ALLOW_IN_CUTOUT`);
- `freeroute.sh` and the v2.1.0 pin;
- IPC `add_plane`/`apply_ses_ipc`;
- `merge_nets`, `add_cutout_keepouts`, `drc_check` (with edge-over-cut), `apply_fab_rules`;
- `route.sh`, the 3-gate method, `autoplace`, the round-trip/variants loop and `untangle`, with tests.

The speaker is a modest midrange design waiting for a driver purchase and T-S measurement. The repo now lives at `punkfab/flexisette`.

## Pointers

- Repo: `~/sandbox/punkfab/flexisette`. Key files: `pcb/index.circuit.tsx`, `pcb/modules/*.circuit.tsx`, `pcb/scripts/{route.sh,freeroute.sh,apply_ses_ipc.py,add_plane.py,merge_nets.py,add_cutout_keepouts.py,drc_check.py,apply_fab_rules.py,outline-check.mjs,autoplace.mjs,untangle.mjs,sync_positions.py,apply_placement.py,gen_bom_cpl.py}`, `pcb/placement/default.json`, `cad/{frame,panel,insert,oled,speaker,import_pcb,render_fit}.py`, `render/blender_render.sh`, `sim/speaker_reflex/reflex.py`, `docs/{architecture,pcb-toolchain,placement,roadmap,placement-constraints,feature-ideas}.md`.
- flexisette commits (UTC): `ef99dd9` 06-27 01:44 · `8902d40` 02:25 · `9aa73bb` 21:27 · `5f5874f` 22:33 · `f524af7` 22:35 · `876853f` 23:30 · `6cdd4e1` 06-28 06:01 · `245030b` 19:11 · `0c55221` 19:47 · `096a3a6` 20:24 · `e1ff34f` 22:21 · `8becbf0` 06-29 00:16 · `5ad3424` 00:23 · `959e6f5` 03:47 · `b0218f4` 04:37 · `dc2342d` 05:53 · `676db07` 06:21 · `284eb4e` 06:41.
- circuit-skills commits from this work (UTC): `8f488ba` 06-27 16:45 (repo created) · `a3498aa` 21:34 · `201608f` 22:35 · `e2a80ea` 23:30 · `c94e495` 06-28 06:01 · `76b4735` 19:13 · `c33adf9` 19:45 · `c9b2af4` 20:24.
- featuretree repo: `dnewcome/featuretree` `d5a1b6f` (Onshape backend + FreeCAD visibility fix).
- Transcripts: `…/condensed/2026-06-25_punkfab-flexisette_933b73da.md` (main), `…/2026-06-27_punkfab-flexisette-pcb_605c7ce9.md` (CPU side session).
