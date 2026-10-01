# einhander — one-handed RP2040 USB-MIDI keypad: enclosure, 4-layer board, and the routing fight that built the 4-layer recipe

- **Dates:** 2026-06-30 → 2026-07-01 · **Sessions:** `40fca752` (dir `-home-dan-sandbox-dnewcome-einhander`) · **Repo:** `dnewcome/einhander` at the time, now `audiodestrukt/einhander` (local `/home/dan/sandbox/audiodestrukt/einhander`); skill changes landed in `dnewcome/circuit-skills`, now `punkfab/circuit-skills` · **Skills used:** kickoff, build123d-machine, pcb-layout (plus the tscircuit skill that `tsci init` installs)
- **Times** below are the transcript's UTC timestamps. Dan's local time was PDT (UTC−7), which is the time git shows: commit `a3c4d01` "18:13 −0700" is 01:13 UTC on 07-01.
- **Commits from this session:** einhander `a3c4d01`, `7711f02`, `e4d6953`, `5ec62e3`, `f6af3b8`, `bb8aef8`, `69f833b`, `25b3421`, `e523a20`, `c29fd89`, `8522e8a`; circuit-skills `8e75d2a`.
- **Later work:** [2026-10-01-einhander-rerun.md](2026-10-01-einhander-rerun.md) re-ran this pipeline unattended. It found the real cause of the "dense LDO corner" (see Problem 14) and made `drc_check.py` count unconnected items as blocking (circuit-skills `d064432`, einhander `7ddbb42`).

## Goal

Dan's opening request: "this is a one handed hardware device for music control and sequencing. I want to put 2 rows of 4 key switches on top and a thumbwheel on the side and maybe a button. I need to make a pcb for this and control software for a microcontroller to run it." Earlier concept work in memory described an MC-303-inspired groovebox: 8 keys mapped 1:1 to tracks/patterns/hotcues, a thumb SHIFT, and the thumbwheel as the answer to one-handed parameter-lock value entry.

Dan's scope decisions (AskUserQuestion, 17:49): **pure USB-MIDI controller** and **wired USB-C**. That means an RP2040 board with no standalone sequencer and no wireless. Firmware and the thumbwheel daughterboard were deferred and never started in this session.

## Timeline

**2026-06-30, enclosure**
- **17:21–17:23**: Empty project directory, with prior concept work in memory. Claude ran the kickoff skill and asked four questions (where the logic runs, the thumbwheel's job, keycaps, what "done" means). Dan skipped them: "Let's come up with a cad prototype of this."
- **17:33–17:44**: build123d-machine layout (`cad/machine_params.py`, `top_shell.py`, `bottom_shell.py`, `components.py`, `machine.py`, `snap.sh`). Defaults: right-handed bar, 8× MX at 19.05 mm pitch shifted toward the pinky, EC11 on the left wall turning on a horizontal axis, SHIFT button behind it, two-piece shell. Both shells came out as single watertight bodies (97.2 × 63 mm). Assembly envelope 100 × 63 × 39 mm. Render log frame 0001 written. No problems.

**2026-06-30, PCB placement**
- **17:48–18:12**: "start the pcb". Architecture fixed: RP2040 (C2040) + W25Q16 flash + 12 MHz crystal + AP2112K 3.3 V LDO + TYPE-C-31-M-12 USB-C (with 5.1 k CC pulldowns) + 8 keys on direct GPIO + EC11/SHIFT broken out to a 5-pin `J_THUMB` header for a side-wall daughterboard + one WS2812 + BOOTSEL/RESET.
- **18:13–18:30**: tscircuit scaffold (`tsci init`), pcb-layout helper scripts copied in, JLC stock check (all healthy), `tsci import` of 7 parts. Custom `lib/KeySwitch.tsx` Cherry-MX footprint (2 plated contacts + a 4 mm centre hole + two 1.7 mm alignment holes, all NPTH). Board split into **modular** `<subcircuit>` blocks (`modules/mcu.circuit.tsx`, `modules/power.circuit.tsx`) because of the 56-pin QFN, per the skill's guidance at the time.
- **18:31–18:39**: Builds clean except "Failed to route net islands" for V3V3/GND (26 unrouted, dismissed as plane-handled). Placement cleanup: BOOT/RESET moved to the front edge, passives to the bottom layer, R_CC2 pulled back inside the outline. outline-check passed. Render `pcb/renders/0001-placement.png`.

**2026-06-30, routing (2-layer, then 4-layer)**
- **20:15**: "route it". `route.sh` ran with `merge_nets` (51 fragments → 19 nets), but Freerouting v2.1.0 stuck at **4 unrouted** and wrote no SES (Problem 3).
- **20:33–20:40**: Root cause: the modular blocks fragmented the nets inside the DSN. **Flattened to one global net scope.** Dan agreed that inter-block connectors are redundant on one PCB.
- **20:43–21:01**: With correct nets the 2-layer route stuck at **11 unrouted**, with 78 `maze_search` exceptions (GND 43 pins, V3V3 24 pins). Claude offered a layer-count choice; Dan rejected the dialog to ask questions first.
- **22:12**: Dan: "go 4 layer but remember that freerouting has issues with labeling the layers, it always tries to route signals on the gnd and power layers."
- **22:13–22:45**: First 4-layer DSN experiments on v2.1.0 (Problem 5): relabel In1/In2 as `(type power)`, add `(plane …)` defs, strip tscircuit's malformed `(wiring)` section, drop GND/V3V3 entirely (signals only), and a 4-layer signals-only diagnostic. None converged; the best was 3–4 unrouted.
- **22:49–22:55**: Tried an "escape-aware" GPIO reassignment (keys → GPIO18–25). It made things worse (37 incomplete) and was reverted.
- **22:57–23:12**: Kept GND/V3V3 in the netlist with the inner layers relabelled `(type power)`. Stuck at 4 unrouted with a v2.1.0 maze `NullPointerException`. v2.2.4 failed on Java 21 (class-file version 69).
- **23:21**: Claude started removing the keyswitch NPTH holes to test the NPE theory. Dan interrupted: "Update java". Temurin JDK 25 was installed user-local in `~/jdk25`, with wrapper `~/.local/bin/freert224`.
- **23:26–23:28**: **v2.2.4 routed 104/107 connections in 18 s** and wrote a partial SES (248 wires on F/B only, 36 power vias). Planes added and SES injected. DRC: 3 courtyard overlaps and 4 shorts.
- **23:29–23:46**: Placement fixes and new `scripts/route4.sh`. Result: 256 wires, 33 vias, 0 overlaps, 1 short, 10 unconnected. `dsn_4layer_planes.py`, `dsn_drop_nets.py` and `route4.sh` were copied into the deployed skill, and SKILL.md got the v2.2.4/JDK 25 guidance plus a "working 4-layer flow".

**2026-06-30 23:49 → 2026-07-01 01:09, the first "finish" (LDO/USB-C corner)**
- Dan: "go ahead and finish it." This started a long run of finisher attempts: `finish_tail.py`, `fanout_planes.py`, `finish_iter.py`, placement nudges, moving R_CC to the bottom, **enlarging the back band** (board 91 × 68, enclosure `MARGIN_B` 12 → 24), 0805 caps, and stub removal. It ended with a **local VBUS copper pour**: 0 shorts / 0 unconnected at **01:09**. Details in Problem 14.
- **00:40–01:08**: Placement heuristics, kipy gotchas and a "jumper / local pour" heuristic (Dan's suggestion) added to the deployed SKILL.md.

**2026-07-01, fab bundle and publishing**
- **01:11–01:14**: JLC zip rebuilt after the first one was incomplete (Problem 19). `git init`; public repo `dnewcome/einhander` created. Commit **`a3c4d01`**.
- **01:15**: **`7711f02`**: README images.
- **01:34–01:49**: BOM generator; JLC "error processing BOM" fixed; CPL format fixed. Commits **`e4d6953`**, **`5ec62e3`**. `gen_bom.py` and `make_fab.sh` copied into the skill.
- **01:51–02:16**: PCBWay MPN BOM (`--fab pcbway`). Commit **`f6af3b8`**.
- **02:17–02:27**: JLC complaint about CPL designators missing from the BOM, so the CPL is now filtered to BOM designators. Magenta-dot question. PCBA GLB via `tsci export -f glb`. Commit **`bb8aef8`**.
- **02:27–04:00**: EasyEDA markings explained. Cherry MX 3D model (C3316924) attached to KeySwitch. Blender 5.0.1 preview. Commit **`69f833b`**.
- **04:26–04:41**: Dan spotted keyswitch↔tact-switch interference in the 3D view (Problem 26). Makefile + `scripts/render_glb.py`. Commit **`25b3421`**.

**2026-07-01, second finish (after moving BOOT/RESET) and the real defects**
- **04:42–04:56**: Dan chose "Move them to the back band". Three placements were tried (Problem 26). Dan then suggested sliding the LDO cluster left into the USB-C/LDO gap: CLEAN route with 4 unconnected.
- **04:57–05:17**: Second finishing run. Dan at **05:00**: "you were flip flopping between 0 and 1 unrouted several times, were you aware of that?" `finish_converge.py` (monotonic) was written. VBUS still would not close: the 0 Ω jumper made it worse, and spreading the LDO cluster regressed to 2 shorts + 1 unconnected.
- **05:29**: Dan: "are there vias on the pads for c_out? It doesn't make sense that there's a part on top of the board and traces on the back for an smd device". `inspect_pads.py` confirmed top-side C_IN/C_OUT were reached only by B.Cu traces of the *wrong* net (Problem 15).
- **05:41–06:19**: `check_floating.py`. GND/V3V3 inventory: 156 GND / 98 V3V3 trace segments on signal layers. `fix_ldo_planes.py` was blocked by IPC/sandbox failures (Problem 17); `apply_fix.sh` fixed that. `stitch_planes.py`. Result: 0 shorts / 0 unconnected.
- **06:20–06:24**: A full DRC read (not just shorts/unconnected) exposed **11 signal traces through mechanical NPTH holes** and a clearance-rule mismatch (Problems 18–20). Dan chose a "Systemic re-route".
- **06:24–06:54**: Corrected pipeline: `add_npth_keepouts.py`, plane-strategy experiments (Problem 21), the final "keep power routed + pour + finish corners" recipe, `fix_ldo_planes.py`/`patch_stragglers.py` for the LDO corner, and Dan's RP2040 local GND pour (`add_local_zone.py`). `drc_check`: CLEAN, 0 unconnected.
- **06:55–07:03**: SKILL.md 4-layer section corrected (the "relabel = auto-fanout" claim reversed), NPTH, wrong-side-pad and collision-aware-fanout sections added, memory corrected, render `0004-routed-clean-planes.png`.
- **07:05–07:13**: Dan reported a stale GLB (Problem 27); regenerated.
- **07:14**: "push everything". Commit **`e523a20`**; `.lck` files gitignored.
- **07:18–15:28**: Dan shared the JLC DFM report: a GND via 0.041 mm from J1's mount hole (Problem 28). Fixed after several detours. Commit **`c29fd89`**.
- **15:36–15:40**: "Ok let's add this final check to the skill". `dfm_check.py` became `make_fab.sh` step [0]. Commit **`8522e8a`**.
- **15:50**: Dan asked about a LoRA post-training for the skill; Claude advised against it (see Decisions).
- **20:03–20:23**: Dan: "Are there uncommitted changes to circuit-skills? the last change to pcb-layout is 3 days ago". Deployed-copy drift found (Problem 30). Synced, committed **circuit-skills `8e75d2a`**, `~/.claude/skills/pcb-layout` replaced with a symlink into the repo, pushed.

## Problems and fixes

### 1. `tsci build --pcb-png` produced nothing
- **Symptom:** `tsci build index.circuit.tsx --pcb-png build/index_pcb.png` exited 1 and wrote no PNG.
- **Root cause:** No such working flag in this tsci version (inferred from the help output).
- **Resolution:** `tsci export -f pcb-svg --show-courtyards` + ImageMagick `convert`.
- **Where:** Ad-hoc commands only.

### 2. Parts outside the outline (R_CC2), twice
- **Symptom:** outline-check reported "R_CC2 extends outside board boundaries by 0.32 mm" at 18:36, and later "by 1.5 mm" (23:29) after it was moved to dodge J1's courtyard.
- **Root cause:** The power block sits on the back edge; hand coordinates.
- **Resolution:** Moved the resistor each time. outline-check is step [2] of `route4.sh`, a placement gate.

### 3. Modular subcircuits fragmented the nets in the DSN, so Freerouting never saw the inter-block links
- **Symptom:** `route.sh` printed "merging 51 fragment codes → 19 canonical nets", then Freerouting v2.1.0 sat at **4 unrouted** for 400+ passes ("Restoring an earlier board…", score 982.79) and wrote no SES. The DSN had `GND_source_net_2`, `GND_source_net_29`, `KEY0_source_net_13` + `KEY0_source_net_33`, and so on.
- **Root cause:** Each `<subcircuit>` scopes its own nets. `merge_nets.py` repairs the **KiCad board** but not the **DSN** that Freerouting reads, so the key→MCU and USB→MCU links were not connections at all in the DSN.
- **Tried:** The modular pattern would need breakout headers plus top-level traces. Rejected as redundant on one PCB, which Dan independently confirmed.
- **Resolution:** **Flattened to one global net scope.** The blocks became position-parameterized fragments (`<McuBlock ox oy/>`), and the DSN check then showed one net each for GND, V3V3, KEY0…
- **Where:** einhander `pcb/modules/*.circuit.tsx`. The skill already had "Modular vs non-modular"; this case reinforced the non-modular default when Freerouting does the routing.

### 4. 2-layer Freerouting stalled: GND/V3V3 as tracks through the QFN band
- **Symptom:** With correct nets, stuck at **11 unrouted** (score 970.85), with **78** internal `AutorouteEngine.autoroute_connection: Exception in maze_search_algo.find_connection` errors. The DSN showed GND with 43 pins and V3V3 with 24.
- **Root cause:** No plane in the 2-layer DSN, so the router tried to run all power and ground as tracks through a 13 mm-deep RP2040 band.
- **Resolution:** Dan chose **4-layer**, with the warning that Freerouting routes signals onto GND/power layers unless they are labelled.
- **Where:** Memory `freerouting-4layer-plane-labeling.md`; SKILL.md "Layer stackup strategy".

### 5. Getting Freerouting v2.1.0 to treat the inner layers as planes (four dead ends)
- **Symptom:** tscircuit exports every copper layer as `(type signal)`, both in the DSN and in the `.kicad_pcb` stackup.
- **Tried, in order:**
  1. `dsn_4layer_planes.py`: relabel In1/In2 as `(type power)` and insert `(plane "GND…" (polygon In1.Cu …))` / V3V3 on In2. Result: still started at ~67–70 unrouted and stalled at 12 (GND/V3V3 still routed as tracks).
  2. Found that tscircuit emits a **malformed `(wiring)` section with 85 pre-placed power vias** `(via (path …)(net "V3V3"))`. This was the source of the warning `Wiring.read_via_scope: padstack name expected at 'V3V3'`. Stripped it in `dsn_4layer_planes.py`. The warning went away, but the planes were still ignored (68 → 47 unrouted in the first passes).
  3. **Signals only** (`dsn_drop_nets.py GND V3V3`). The first version over-matched and dropped 157 entries ("GND", "GND", …), producing a corrupted DSN and an empty SES. Fixed to drop exactly 2 nets (56 signal nets left, parens balanced). Result: 36 → **3–4 unrouted**, settled, 2 maze errors.
  4. A 4-layer signals-only diagnostic (relabel undone so signals could use all 4 layers): still **3 unrouted**. Claude concluded it was "not a layer problem" but a few hard connections.
  5. Claude briefly argued that the `(type power)` relabel itself made Freerouting ignore the plane, and tested planes on signal-type layers (22:42). This was superseded by the v2.2.4 result.
- **Resolution:** None on v2.1.0. See Problems 6–8.

### 6. "Escape-aware" GPIO reassignment made routing worse
- **Symptom:** Keys moved from GPIO0–7 to GPIO18–25 (thinking those faced the switches after the 270° rotation). The SES then had only 16 wires and 2 vias, and the JSON report showed `incomplete_count: 37`.
- **Root cause:** Claude's guess about which RP2040 edge faces the switches after tscircuit's 270° rotation was wrong. Claude first read the non-empty `sig.ses` as "converged" and only then found the 37-incomplete report.
- **Resolution:** Reverted to GPIO0–7 (keys), 8–11 (encoder/SHIFT).
- **Where:** `pcb/modules/mcu.circuit.tsx`.

### 7. Freerouting v2.1.0 NPE and no partial SES; v2.2.4 needed JDK 25
- **Symptom:** With GND/V3V3 kept and the inner layers `(type power)`, v2.1.0 reached **4 unrouted**, then threw `NullPointerException` (`TileShape … null`) in the maze search, oscillated, and never wrote an SES (v2.1.0 only writes one at 0 unrouted). The `freerouting-2.2.4.jar` that was present failed with `UnsupportedClassVersionError … class file version 69.0 … only recognizes … 65.0` on Java 21.
- **Tried:** Claude started removing the KeySwitch NPTH holes to test whether they triggered the NPE. Dan rejected the tool call and said "Update java"; the holes were restored. `sudo apt` was not available non-interactively.
- **Resolution:** Temurin JDK 25 downloaded from the Adoptium API into `~/jdk25`, plus wrapper `~/.local/bin/freert224` (`-Djava.awt.headless=true -Dgui.enabled=false`). **v2.2.4: 107 → 3 unrouted in 9 passes / 18 s, no NPE, wrote a partial SES (248 wires, all F.Cu/B.Cu, 36 vias).**
- **Where:** SKILL.md "Finishing the routing tail" (v2.1.0 vs v2.2.4 guidance, currently around lines 348–349); `route4.sh` calls `freert224`.

### 8. The `(type power)` + keep-power-nets recipe "worked" but was later shown to be wrong
- **Symptom (at the time, 23:27):** v2.2.4 kept signals off In1/In2 and placed power vias. Claude concluded that relabelling makes Freerouting **auto-fan-out each power pin to the plane**, and wrote that into SKILL.md and memory as "the working 4-layer flow".
- **Root cause (found 05:55–06:44):** Freerouting still routed GND and V3V3 as full trace networks on F.Cu/B.Cu (Problem 16). The vias were incidental, not plane fanout.
- **Resolution:** SKILL.md step 3 rewritten as "⚠️ CORRECTED (einhander, verified — this reverses earlier advice)" (currently around line 478), and memory rewritten "CORRECTED". See Problem 21 for the strategy that was finally used.

### 9. Courtyard overlaps caused real shorts
- **Symptom:** First 4-layer inject (23:28): overlaps C9↔R_BOOT, D1↔C_LED, R_CC2↔J1, giving **4 real shorts** (GND–V3V3, CC1–V3V3, DVDD–BOOT_BTN, CC2–GND). Later overlaps: C_LED↔Y1 (00:32), C_OUT↔SW_RST, SW_RST↔SW_BOOT (04:47–04:52).
- **Root cause:** Tight hand placement; outline-check does not check courtyards.
- **Resolution:** Moved the parts. SKILL.md: "Gotcha order that bit on einhander: run `drc_check.py` (courtyard) BEFORE celebrating".

### 10. The habit of re-routing after every tweak
- **Symptom:** Small placement changes moved the tail around (10 → 15 → 12 → 6 unconnected) instead of shrinking it. Claude called it "the autorouter being non-deterministic".
- **Tested (00:44–00:51):** Five identical `route4.sh` runs gave identical results (2 shorts, 5 unconnected).
- **Root cause:** Freerouting is deterministic for a fixed source. The variance came from Claude's own placement changes between runs, and from interleaving whole-board re-routes (`route4.sh`) with kipy edits to the live board.
- **Resolution:** "Freeze one baseline; finish deterministically", in SKILL.md "Dense high-pin-count placement heuristics" (currently around lines 526–542). The 2026-10-01 rerun later added a determinism nuance.

### 11. Naive finishers made it worse (pad-to-pad tracks, via-in-pad, blind offset vias)
- **Symptom:** On the 1 short + 10 unconnected baseline:
  - `finish_tail.py` straight pad-to-pad tracks: unconnected went to 0, but **16 shorts + 9 crossings** (tracks across the USB-C pad row).
  - Vias only (stitch via at the pad): **11 shorts**. The through-via's B.Cu ring bridged the dangling B.Cu tracks Freerouting had left.
  - First `fanout_planes.py` (via 0.75 mm outboard + stub): **8 shorts**.
- **Root cause:** Copper added blindly into a congested corner. The B.Cu tracks at those pads were themselves an artifact (see Problem 14, later finding).
- **Resolution:** `finish_iter.py` uses DRC as the oracle: try candidates and keep one only if the short count does not rise. It first crashed with "no valid items to delete" (Problem 12). Then `finish_converge.py` (05:03): keep a fix only if unconnected strictly drops and shorts don't rise, printing the running count.
- **Where:** einhander `pcb/scripts/finish_tail.py`, `finish_iter.py`, `finish_converge.py`. Synced to the skill only on 2026-10-01 (`d064432`).

### 12. kipy API traps
- `b.remove_items(originals)` failed with "no valid items to delete". `create_items()` returns server-side handles, and those are what must be removed.
- **pcbnew's IPC server died between shell calls**: `kipy.errors.ConnectionError: Failed to connect to KiCad: Connection refused`, many times from 00:04 onward. Workaround at the time: relaunch pcbnew at the top of each call.
- `board.get_tracks()` **does not return vias**. Use `board.get_vias()`. This made the via-deletion code a silent no-op (Problem 28).
- kipy's padstack drill API returned nothing, so hole geometry is parsed from the `.kicad_pcb` text (oval drills included).
- **Where:** SKILL.md "kipy gotchas" (currently around line 548) and around line 641 (`get_vias`).

### 13. Point-to-point finisher reported "OK" without connecting
- **Symptom:** `finish_iter.py` said "C_IN.1 [VBUS]: OK", but DRC still showed `Track [VBUS] on B.Cu … || Pad 1 [VBUS] of C_IN on F.Cu`. It had laid a B.Cu track to an F.Cu SMD pad with no via.
- **Root cause:** Acceptance only checked that shorts did not rise, not that the item connected.
- **Resolution:** Later finishers check shorts *and* unconnected. SKILL.md: "a point-to-point finisher must add a VIA when … it routes on the other layer".

### 14. The "dense LDO corner": C_IN / C_OUT / C_LED / VBUS that would not close (two whole sessions of hand patching)
- **Symptom (recurring from 23:28 06-30 to 06:48 07-01):** The unconnected list kept naming the same top-side parts, each time paired with a **B.Cu** track: `Pad 1 [V3V3] of C_LED on F.Cu || Track [V3V3] on B.Cu`, `Pad 2 [GND] of C_IN on F.Cu || Track [GND] on B.Cu`, and the same for C_OUT, C_IN.1 VBUS, and (early on) R_CC1/R_CC2. Shorts were GND↔V3V3 and GND↔VBUS at C_OUT/C_IN, from long F.Cu power tracks (28.9 mm V3V3, 10.8 mm V3V3, 8.4 mm GND) clipping the cap pads.
- **What the July session believed:** The USB-C/LDO power corner was "too dense", "at Freerouting's density limit", with "intrinsically hard" CC/power escapes.
- **Tried (every step):**
  1. Spread the power block (R_CC to x=8.5, U3/C_IN/C_OUT shifted right). Same 1 short + 10 unconnected.
  2. `finish_tail.py` tracks and vias (Problem 11): worse.
  3. R_CC directly above the connector, LDO moved. 15 unconnected (crowded the USB D± channel). Reverted to 2 shorts + 9 unconnected.
  4. `fanout_planes.py` offset vias: 8 shorts.
  5. **R_CC1/R_CC2 on the bottom layer under their CC pins, LDO cluster spread right.** 0 shorts / 12 unconnected (`RESULT: CLEAN ✓`). The tail moved to USB_DM/DP, QSPI and DVDD at the RP2040.
  6. **Enlarged the back band:** `KEY_CENTER_Y` 1.5 → 7.5, board 91 × 68 mm, enclosure `MARGIN_B` 12 → 24, RP2040 decaps moved off the under-QFN escape into rows above and below the chip. Down to 6 unconnected, but new overlaps (C_LED on Y1) and edge clearances. After fixing those: CLEAN, **6 unconnected**, all on C_IN/C_OUT/C_LED/VBUS.
  7. C_IN/C_OUT/C_LED changed **0402 → 0805** so a via would fit beside each pad. No change ("still routes C_OUT's V3V3 via 0.3 mm from the GND pad").
  8. Deleted Freerouting's V3V3 stub at C_OUT + `finish_iter.py`. 0 shorts, 1 unconnected (VBUS).
  9. VBUS: straight F.Cu C_IN.1 → U3.1 connected it but added 4 shorts. Five DRC-verified candidates (straight, bends, B.Cu via-bridge) gave 3–7 shorts each. An over-rip removed *all* VBUS tracks (5 unconnected). C_IN moved next to U3 VIN: still 1 short every way.
  10. **Local VBUS copper pour** around C_IN + U3 VIN. **0 shorts / 0 unconnected at 01:09**, committed as `a3c4d01` "DRC-clean".
  11. After the BOOT/RESET move (04:56), the same tail came back (C_LED, C_IN, VBUS). `finish_converge` closed 3 of 4. VBUS failed all four paths (B via-bridge straight/bend: 3–6 shorts; F straight: 2). A **0 Ω jumper `R_VBUS`** (Dan's idea, net `VBUS_J`) made it worse (3 unconnected) and was reverted. Spreading C_IN/U3/C_OUT to x=8/16/24 gave 2 shorts + 1 unconnected.
  12. 05:34: `inspect_pads.py` showed C_OUT.1 (V3V3) touched only by a **B.Cu GND** trace, C_OUT.2 (GND) by **B.Cu V3V3**, and C_IN pads likewise swapped, with no vias (Problem 15). The session's attribution: "it's Freerouting, not our edits", since the B.Cu wires are in the `.ses` (39 SES vias + 2 added).
  13. `fix_ldo_planes.py`: deleted **27** GND/V3V3 tracks/stubs inside a **hardcoded LDO bounding box (104,126)–(127,132)**, added plane vias at U3.2/U3.5/C_OUT.1/C_OUT.2/C_IN.2, and routed VBUS to a **hardcoded rail point (105.78, 131.08)**. Then `stitch_planes.py` (2 GND island vias). Result: 0/0 (06:18).
  14. After the systemic re-route (06:47) the same pattern returned (1 GND↔V3V3 short at C_OUT, 5 unconnected at C_LED/C_IN/C_OUT with B.Cu tracks). `fix_ldo_planes.py` was re-run; its hardcoded VBUS point was now stale, so **`patch_stragglers.py`** re-aimed VBUS at the real rail end (108.91, 131.08) and deleted 5 orphan GND/V3V3 stubs. A `fanout_planes` pass picked up J1.14. Result: 0/0 (06:51).
- **Resolution at the time:** Hand patches tied to fixed coordinates (`fix_ldo_planes.py`, `patch_stragglers.py`, both left only in einhander, not promoted to the skill). Board shipped as `e523a20`.
- **Later finding (2026-10-01):** The corner was never too dense. **tscircuit's `specctra-dsn` export dedupes footprint images by name**, so top-side caps sharing a footprint name with a bottom-side part inherited the **mirrored B.Cu image**: the top-side 0805 caps C_IN/C_OUT/C_LED took the image of bottom-side 0805 **C11**. Freerouting therefore believed these pads were on B.Cu, and mirrored, so pad 1 and pad 2 swapped in X. That explains every symptom above: B.Cu wires ending on F.Cu pads, the *wrong net* at each pad (Problem 15), and stubs that no placement or footprint change could fix.
  - Note: the 0805 change in step 7 put these caps on exactly C11's image name.
  - Before that change they were 0402, as were the bottom-side RP2040 decaps (C1–C10, C9), and R_CC1/R_CC2 showed the same symptom while top-side. Moving R_CC to the bottom at step 5 coincided with them leaving the list, and on 07-01 06:40 `check_floating` flagged bottom-side `R_CC2.2` reached only by F.Cu. **(inferred)** The same image dedupe was at work on the 0402 parts.
  - Fix: `dsn_split_sides.py` (`route4.sh` step 2a, circuit-skills `d064432`). The unattended rerun went from 1 short + 6 unconnected to 0 shorts + 2 unconnected. See [2026-10-01-einhander-rerun.md](2026-10-01-einhander-rerun.md); SKILL.md "Mixed-side footprints: the DSN mirrors top-side parts" (currently around line 562).

### 15. "Part on top, traces on the back": the floating-cap observation and `check_floating.py`
- **Symptom (Dan, 05:29):** C_OUT is top-side SMD, but the only copper at its pads was on B.Cu.
- **Evidence:** `inspect_pads.py C_OUT C_IN U3`: C_OUT.1 V3V3 ← B.Cu GND trace; C_OUT.2 GND ← B.Cu V3V3; C_IN.1 VBUS ← B.Cu GND; C_IN.2 GND ← B.Cu VBUS; no vias. U3 was fine.
- **Tool built:** `check_floating.py` flags an SMD pad reached only by opposite-layer copper with no via. On the same board at 05:41 it reported **"OK — every SMD pad is reached on its own layer or via a fanout via"**, and Claude reinterpreted the finding as "real but not floating". The detector and `inspect_pads` disagreed; the session did not reconcile this. (inferred: endpoint-matching differences between the two scripts.)
  - The gate did fire later on `R_CC2.2 [GND] pad on B.Cu, but only ['F.Cu'] copper reaches it` (06:40).
  - The commit message for `e523a20` still says "two decaps were floating".
- **Root cause:** The DSN image mirroring of Problem 14 (later finding). In July it was attributed to Freerouting.
- **Where:** `check_floating.py` and `inspect_pads.py` in the skill (`8e75d2a`). SKILL.md "Two traps that pass a shorts-only check but break the board" (currently around line 597). `route4.sh` runs `check_floating` in its verify step.

### 16. GND/V3V3 routed as hundreds of traces on the signal layers despite inner planes
- **Symptom (Dan: why ground traces on top when there is a whole layer?):** Inventory showed **GND: 156 segments (46 F.Cu, 110 B.Cu), 5 vias; V3V3: 98 segments, 7 vias; VBUS: 15**.
- **Root cause:** GND/V3V3 were still in the routed netlist (Problem 8), so Freerouting treated them as signals. (Later finding: the long power tracks clipping C_OUT were also shaped by the mirrored-image bug in Problem 14.)
- **Resolution:** Partly avoidable. See Problem 21 for why GND could not be removed from the signal layers entirely. GND dropped to 137 segments with 10 plane vias after `fix_ldo_planes`. The 2026-10-01 baseline measured 484.5 mm of GND/V3V3 still on signal layers in the shipped board.

### 17. Driving pcbnew from scripts: process death and sandbox kills (exit 144)
- **Symptom:**
  - `DISPLAY=:0 setsid pcbnew … &` returned, but no process existed when the script connected ("could not connect to KiCad IPC — is pcbnew open on the board?").
  - Launching pcbnew as a separate background task: the process vanished.
  - Launch + fix in one call: `Exit code 144` with all stdout lost. The same happened with the sandbox disabled.
  - A `pkill -f 'pcbnew index'` inside a compound command also killed its own process group (exit 144).
- **Diagnosis:** `scripts/diag_ipc.sh` logged everything to `build/diag.log` (which survives a hard kill). kipy connected fine (`CONNECT OK nets=32`, socket `/tmp/kicad/api.sock`) once pcbnew was started inside the same foreground call and the script waited for the socket.
- **Resolution:** `scripts/apply_fix.sh <script> [args]`: launch pcbnew, wait for `/tmp/kicad/api.sock`, run the script, log to `build/<script>.log`, kill pcbnew. Arguments pass through since 06:53.
- **Related:** `pkill -f freerouting` killed its own shell earlier (the command line contained "freerouting"), so freerouting runs were killed with `pkill java` instead. The harness also blocked `sleep 45` polling; until-loops and background tasks were used.
- **Where:** `apply_fix.sh`, `diag_ipc.sh` (skill, `8e75d2a` / `d064432`); SKILL.md "kipy over IPC dies between shell calls".

### 18. Eleven signal traces routed through mechanical NPTH holes (the board was never fabricable)
- **Symptom:** A full DRC read at 06:23 found `hole_clearance: 20`, nine of them `actual 0.000 mm`: Track KEY0–KEY7 through keyswitch pole/alignment holes (SW1–SW8), and VBUS through J1's USB-C mount hole. A drill through a track leaves an open net.
- **Root cause:** NPTH pads have no copper, so the DSN gives Freerouting no obstacle. `add_cutout_keepouts.py` only handled Edge.Cuts shapes. `drc_check.py` filed `hole_clearance` under "RULE/FAB/COSMETIC", which is why every earlier "CLEAN", including the `a3c4d01` commit, hid it. Dan noted the same bug had hit flexisette.
- **Resolution:** `add_npth_keepouts.py`: 30 NPTH holes (8 × 4 mm poles, 16 × 1.7 mm alignment pins, 4 × 2.4 mm mount holes, 2 × 0.8 mm USB posts) became 120 keepout rects on all 4 layers (`--margin 0.3 --min-hole 0.5`), as `route4.sh` step [5]. After re-route: hole_clearance 20 → 2, and those 2 are J1's own pad-to-post spacing.
- **Where:** Skill `add_npth_keepouts.py`; SKILL.md "Two traps…".

### 19. Clearance mismatch (198 violations) and undersized vias
- **Symptom:** `clearance: 198`, all "netclass 'Default' clearance 0.2000 mm; actual 0.15–0.18 mm". Also `via_diameter: 2`, `drill_out_of_range: 2`.
- **Root cause:** The DSN rule (`clearance 150`) let Freerouting route at 0.15 mm, while KiCad's Default netclass asked for 0.20. The finisher vias were 0.45/0.25 mm, below JLC's 0.6/0.3.
- **Resolution:** `apply_fab_rules.py --fab jlcpcb` added to `route4.sh` (Default clearance 0.127, track 0.15, copper-edge 0.2, min text 0.25). `fanout_planes.py` vias resized to 0.6/0.3.

### 20. `drc_check.py` printed CLEAN while nets were open
- **Symptom:** `RESULT: CLEAN ✓` was reported with unconnected > 0 at:
  - 07-01 00:23 (12), 00:34 (6), 00:59 (1), 01:04 (5)
  - 01:06 (1); the 00:59/01:06 states were then called "Almost there"
  - 05:08 (1), 05:12 (1), 05:14 (3)
  - Earlier "CLEAN" results also hid hole_clearance and clearance (Problems 18–19).
  The claims of a finished board at 01:09/01:10 and 06:54–06:56 did have unconnected = 0, but the 01:09 board still had traces through holes.
- **Root cause:** `drc_check.py` counted only placement, shorts, crossings and edge as blocking; unconnected was informational.
- **Resolution:** Not fixed in July. **Later (2026-10-01):** `drc_check.py` now treats unconnected as blocking (circuit-skills `d064432`, einhander `7ddbb42`).

### 21. Plane strategies in the systemic re-route: three failures before the shipped recipe
After Dan chose "Systemic re-route (recommended)" (06:24):
1. **Drop GND/V3V3 from the DSN + blind `fanout_planes.py`.** Freerouting routed 42 nets to 0 in 3 s with all holes avoided, but **32–33 shorts**, 25 of them a fanout via or 0.75 mm stub on signal copper (V3V3 via on ENC_A, a stub across QSPI_SD2, two vias 0.4 mm apart). Freerouting had been placing those fanout vias collision-aware before; the replacement was blind.
2. **Drop + collision-aware fanout** (via-in-pad first, offset only to clear spots). The first run hit `NameError: B` (a typo). Result: **34 pads connected, 18 unplaced** (U1.1/10/19/22/33/42/44/48/49 + C1/C4/C5/C7/C15 pads), 20 unconnected, R_CC2.2 floating. The RP2040's 0.5 mm-pitch power pins cannot take a 0.6 mm via-in-pad; they need short routed dogbone escapes to their decaps, and dropping the nets deleted those.
3. **Declare GND/V3V3 as Specctra planes** (`add_dsn_planes.py GND=In1.Cu V3V3=In2.Cu`, after confirming `Plane.class` / `PlaneViaCost` in the v2.2.4 jar). Freerouting 94 nets → **48 unrouted, 0 fanout vias**, and GND wires up to 13 mm long. It parses `(plane)` but does not dogbone-fan-out to it.
4. **Shipped recipe ("Path X"):** keep GND/V3V3 routed as normal nets, keep `(type power)` on the inner layers (signals stay off), add NPTH keepouts, pour the In1/In2 zones, apply fab rules, then finish the corners: `fix_ldo_planes` + `fanout_planes` + `patch_stragglers` + `fanout_planes`. Then Dan's **RP2040 local GND pour** (`add_local_zone.py U1 GND F.Cu --margin 1.2`, 9.3 × 9.2 mm). Final: 0 shorts / 0 unconnected / 0 overlaps, `hole_clearance` 2 (J1-inherent).
- Claude noted mid-way: "I'm flip-flopping on the routing strategy — exactly what you flagged before."
- **Where:** SKILL.md step 3 "CORRECTED" lists relabel-and-keep, drop, and DSN-plane as the three approaches that fail on their own. "Fanning GND/PWR pads to the plane WITHOUT shorting (collision-aware, not blind)" is currently around line 620. `route4.sh` step [4] comment.

### 22. Incomplete JLC Gerber zip
- **Symptom:** The first zip used a `*.gbr *.drl` glob, which missed KiCad's `.gtl/.gbl/.g1/.g2/.gts/.gbs/.gto/.gbo/.gtp/.gbp/.gm1`.
- **Resolution:** An explicit list (4 copper + masks + silk + paste + edge + drill + `.gbrjob`, 13 files), later generated by `make_fab.sh`.

### 23. JLC "error processing BOM"
- **Root cause:**
  1. An extra `Note` column.
  2. Rows with a blank LCSC number for hand-solder parts.
  3. Non-ASCII `Ω` (`10kΩ`, `5.1kΩ`).
- **Resolution:** `gen_bom.py` emits exactly `Comment, Designator, Footprint, JLCPCB Part #`, ASCII only, assembled parts only (27). Hand-solder parts (11) go to `<name>-handsolder.csv`. Passive LCSC numbers were stock-checked (C1525, C15850, C1548, C52923, C49678, C28323, C25744, C11702, C25905).
- **Follow-up bug:** The hand-solder file was named `index.circuit-handsolder.csv`; fixed to derive the prefix from the BOM name. Commit `5ec62e3`.

### 24. CPL format, then CPL/BOM designator mismatch
- **Symptom:**
  1. KiCad's `Ref,Val,Package,PosX,PosY,Rot,Side` header, plus empty-designator rows for the mount holes.
  2. JLC: "SW_RST, SW5, … J_THUMB … designators don't exist in the BOM file."
- **Resolution:** CPL remapped to `Designator, Mid X, Mid Y, Layer, Rotation` with empty refs dropped, then filtered to exactly the BOM's designators (27). In `make_fab.sh` the BOM is now built before the CPL. Commits `5ec62e3`, `bb8aef8`.

### 25. Misidentified magenta dots in JLC's viewer
- Claude first said the dots were the board's 42 vias (it counted vias by net). Dan corrected it: they are JLC's pin-1/orientation markers. Claude suggested checking polarized-part rotations (U1, U2, U3, D1, J1) and offered a rotation-correction pass. **Not done in this session.**
- The EasyEDA markings on 3D models: the models come from `modelcdn.tscircuit.com/easyeda_models/`; cosmetic only.

### 26. Keyswitch vs BOOT/RESET tact-switch collision, invisible to courtyard DRC
- **Symptom (Dan, 04:26, from the GLB):** Front-row MX body reached y=24.8 and the keycap y=26.0, while the tacts at y=27 reached down to y=24.0: about 0.8 mm of body overlap and about 2 mm of keycap overlap. The MX model scale was verified at 15.6 × 15.6 mm. An earlier trimesh check had read the wrong axis (the GLB is Y-up).
- **Root cause:** Physical bodies and keycaps are larger than the footprint courtyards.
- **Tried (after Dan chose "Move them to the back band"):**
  - (38,−15)/(38,−25): C_OUT↔SW_RST courtyard overlap.
  - (39,−18)/(39,−28): **10 shorts**; the RUN/BOOT_BTN nets crossed the board.
  - (38,−15)/(38,−21): SW_RST↔SW_BOOT overlap (about 8 mm parts at 6 mm spacing).
  - Dan's suggestion, slide the LDO cluster left (U3 x=14, C_IN 10, C_OUT 18) and stack the tacts at (36,−17)/(36,−27): CLEAN route, 4 unconnected.
- **Where:** No automated 3D clearance gate came out of this. A GLB bbox check was run ad hoc at 07:12. The pcb-enclosure-fit skill covers this class of problem.

### 27. Stale GLB
- **Symptom:** Dan: "it was out dated, the switches were still in the old plce".
- **Root cause:** The GLB on disk was from 21:37 PDT (04:37 UTC), before the 04:43 UTC tact move. Claude first claimed the re-route had not touched it. The regenerate command `npx --prefix pcb tsci export pcb/index.circuit.tsx … -o pcb/renders/…` doubled the path (`ENOENT … pcb/pcb/renders`).
- **Resolution:** `make glb`. A GLB bbox check confirmed about 5 mm clearance between the tacts and SW4/SW8.

### 28. JLC DFM: GND via 0.041 mm from J1's mount hole (KiCad DRC passed it)
- **Symptom:** The DFM report flagged "Plated through-hole spacing — Danger ×1". A via at (103.70, 126.83) sat 0.041 mm, edge to edge, from J1's 1.6 mm hole; JLC's minimum is 0.5 mm. Also flagged: J1's own 0.335 mm post-to-pad spacing, about 128 silkscreen items, and 0.15 mm spacing.
- **Tried:**
  - The parser crashed on oval drills (`ValueError: could not convert string to float: 'oval'`).
  - `fix_hole_spacing.py` found **0** vias twice: first because kipy's padstack drill API returned nothing (switched to parsing holes from the file), then because `get_tracks()` returned 0 vias (`get_vias()` returns 49).
  - Removing the via left J1.14 unconnected; it was J1's SMD GND pad's only path to the plane, not a redundant via.
  - `reconnect_j14.py` v1: a via at (102.60, 126.83) shorted the VBUS track (only hole clearance had been checked).
  - v2 (copper clearance 0.2 mm + cleanup): "no clear via spot found". The script exited before saving its removal, so the shorting via stayed.
  - v3: copper clearance relaxed to 0.13 mm, with a fallback trace to J1.1 PTH. Via at (103.41, 126.26): 0 shorts / 0 unconnected, closest hole spacing 0.669 mm.
- **Resolution:** Commit `c29fd89`. J1's internal 0.335 mm spacing is part-inherent and was left. Silkscreen items were judged cosmetic (JLC clips silk at openings).
- **Where:** `fix_hole_spacing.py` (skill); `reconnect_j14.py` (einhander only, hardcoded to J1.14).

### 29. No DFM gate in the pipeline
- **Resolution:** `dfm_check.py` checks inter-part plated hole-to-hole ≥ 0.5 mm, via drill ≥ 0.3 mm and annular ring ≥ 0.13 mm. It reports intra-footprint pairs as informational and skips silkscreen. It runs as `make_fab.sh` step [0]. The first wiring piped its output through `sed`, which hid its exit code; fixed with `PIPESTATUS`. Commit `8522e8a`; SKILL.md "Verify every board → Final DFM gate" (currently around line 746).

### 30. The skill edits never reached the circuit-skills repo
- **Symptom (Dan, 20:03):** "the last change to pcb-layout is 3 days ago". `git status` in circuit-skills was clean, but `~/.claude/skills/pcb-layout` was a **copy, not a symlink**. Its SKILL.md was 65,239 bytes against the repo's 50,264. Five scripts existed only in the live copy (`route4.sh`, `make_fab.sh`, `gen_bom.py`, `dsn_4layer_planes.py`, `dsn_drop_nets.py`). Ten new scripts lived only in einhander, so SKILL.md referenced `check_floating.py` / `dfm_check.py` that did not exist in either skill copy.
- **Resolution:**
  - Copied the live SKILL.md and the 5 scripts into the repo.
  - Promoted `check_floating`, `dfm_check`, `add_npth_keepouts`, `fanout_planes`, `inspect_pads`, `add_local_zone`, `apply_fix.sh` and `fix_hole_spacing` to both copies.
  - Committed **`8e75d2a`**, replaced the live copy with a symlink into the repo (backup verified identical, then removed), and pushed.
  - Left out at the time: `reconnect_j14.py` and `patch_stragglers.py` (hardcoded), plus `finish_*`, `stitch_planes`, `add_dsn_planes` and `diag_ipc` (not promoted; synced on 2026-10-01 in `d064432`).
  - The skill's `route4.sh` copy later turned out to be older than einhander's (noted in the rerun doc).

### 31. Loose ends never closed in this session
- The enclosure was not re-rendered or fit-checked against the enlarged 91 × 68 board. Only `MARGIN_B` was edited in `cad/machine_params.py`.
- Thumb-cluster daughterboard (EC11 + SHIFT → `J_THUMB`): not designed.
- RP2040 TinyUSB-MIDI firmware: not written.
- JLC part-rotation check: not done.
- Silkscreen cleanup: not done (about 340 cosmetic items earlier; 5 `silk_over_copper` at the end).
- `fix_ldo_planes.py` / `patch_stragglers.py` remain coordinate-specific; superseded in principle by `dsn_split_sides.py`.

## Decisions and reversals
- **Architecture:** pure USB-MIDI, wired USB-C, RP2040 (Dan). Encoder + SHIFT on a daughterboard header (Claude's call, flagged to Dan; never revisited).
- **Modular subcircuits → flat global nets** (20:33). Reason: the DSN fragmentation in Problem 3. Inter-block connectors rejected (Dan agreed).
- **2-layer → 4-layer** (Dan, 22:12). Cost was framed as roughly $5 vs $2 at JLC prototype quantities.
- **Freerouting v2.1.0 → v2.2.4 + user-local JDK 25** (Dan: "Update java"). Reversed the skill's earlier "don't upgrade to v2.2.x" stance.
- **`(type power)` relabel = auto plane fanout** (23:27) **→ reversed** (06:55). Keep power routed, pour planes, finish corners. Memory and SKILL.md both corrected.
- **"Freerouting is non-deterministic" → reversed** (00:51): it is deterministic for a fixed source.
- **Board grown 13 mm-band → 91 × 68 mm** (enclosure `MARGIN_B` 12 → 24) to give the RP2040 room. In July this was credited with shrinking the tail. **(inferred)** Part of the remaining LDO-corner tail was the mirroring bug, not density.
- **0402 → 0805 for C_IN/C_OUT/C_LED** (00:52). Kept, though it did not help. Per the later finding, it moved these caps onto C11's mirrored image.
- **0 Ω jumper R_VBUS** tried and reverted (05:12–05:16). The local VBUS pour from Dan's jumper/pour idea worked in the first finish and became a SKILL.md heuristic.
- **BOOT/RESET** front edge → back band (Dan's choice); final position set by Dan's "slide the LDO cluster left" suggestion.
- **Hand-patch vs systemic re-route** (06:24): Dan chose systemic re-route.
- **Drop GND from routing** (Dan's push: "Can we exclude the whole gnd net…") → tried, failed on the QFN → reverted to routed power + planes + RP2040 local GND pour (Dan's idea).
- **LoRA post-training for placement/routing** (Dan, 15:50): Claude advised against it. Weight fine-tuning of Claude is not available to users, and placement/routing are deterministic optimisation problems better served by gate scripts and skill rules.
- **Skill deployment:** copy → **symlink** into circuit-skills (Dan: "yeah sync and symlink").

## Outcome
- **Shipped board** (`audiodestrukt/einhander` `pcb/`, final commit `8522e8a`): 4-layer RP2040 USB-MIDI controller, 91 × 68 mm, signals on F.Cu/B.Cu, GND In1 / V3V3 In2 zones, RP2040 local F.Cu GND pour, NPTH keepouts.
  - Final checks: `drc_check` 0 placement / 0 shorts / 0 crossings / 0 unconnected (2 dangling, 7 cosmetic incl. 2 J1-inherent hole_clearance); `check_floating` OK; `dfm_check` OK.
  - Fab bundle: Gerbers + drill + JLC BOM/CPL (27 assembled parts) + PCBWay MPN BOM + hand-solder list.
  - Also: PCBA GLB with Cherry MX models, Blender preview, Makefile (`cad/glb/render/fab/route`).
  - Whether Dan placed an order is not recorded in the session.
- **Not fully reproducible:** the board depends on coordinate-specific hand patches. The 2026-10-01 unattended rerun of the same circuit reached 0 shorts + 2 unconnected after the mirror fix. It is not fabbable; `pcb/` remains the fab board.
- **Skill output (circuit-skills `8e75d2a`):**
  - The 4-layer recipe (`route4.sh`, `dsn_4layer_planes.py`, `dsn_drop_nets.py`, v2.2.4/JDK 25).
  - NPTH keepouts, the floating-pad check (`check_floating.py`, `inspect_pads.py`), collision-aware `fanout_planes.py`, `add_local_zone.py`.
  - The DFM gate (`dfm_check.py`, `fix_hole_spacing.py`), the fab bundle (`make_fab.sh`, `gen_bom.py` JLC + PCBWay), `apply_fix.sh`.
  - SKILL.md: corrected 4-layer section, dense-placement heuristics, freeze-baseline rule, jumper/local-pour heuristic, kipy gotchas.
- **Not delivered:** enclosure re-sync, daughterboard, firmware.

## Pointers
- Transcript (condensed): `scratchpad/condensed/2026-06-30_dnewcome-einhander_40fca752.md`.
- einhander repo: `pcb/scripts/route4.sh` (pipeline, steps [1]–[9]); `pcb/scripts/{fix_ldo_planes,patch_stragglers,reconnect_j14}.py` (coordinate-specific hand patches); `pcb/scripts/{finish_tail,finish_iter,finish_converge,stitch_planes,add_dsn_planes}.py` (finisher experiments); `pcb/renders/INDEX.md` (0001 placement → 0004 routed-clean-planes); `Makefile`; `pcb/fab/`.
- circuit-skills `pcb-layout/SKILL.md` (line numbers as of `d064432`):
  - "Finishing the routing tail" (v2.1.0 vs v2.2.4, ~L311–349)
  - "Layer stackup strategy" incl. CORRECTED step 3 (~L459–520)
  - "Dense high-pin-count placement heuristics" + kipy gotchas + jumper (~L526–560)
  - "Mixed-side footprints" (~L562, added 2026-10-01)
  - "Two traps that pass a shorts-only check" (~L597)
  - "Fanning GND/PWR pads to the plane WITHOUT shorting" (~L620)
  - "Verify every board → Final DFM gate" (~L746)
  - "Fabrication bundle" (~L759)
- Commits: einhander `a3c4d01` … `8522e8a` (this session), `7ddbb42` (rerun); circuit-skills `8e75d2a` (this session's skill sync), `d064432` (mirror fix + drc_check unconnected-blocking).
- Project memory (local only): `~/.claude/projects/-home-dan-sandbox-dnewcome-einhander/memory/{einhander-pcb-architecture,freerouting-4layer-plane-labeling}.md`. The latter was rewritten "CORRECTED" on 07-01.
- Follow-up: [2026-10-01-einhander-rerun.md](2026-10-01-einhander-rerun.md).
