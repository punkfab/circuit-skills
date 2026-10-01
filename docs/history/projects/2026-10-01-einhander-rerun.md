# einhander rerun — the 4-layer board re-routed unattended, three months later

- **Dates:** 2026-09-28 → 2026-10-01 · **Sessions:** `37493db6` (dir `-home-dan-sandbox-dnewcome-circuit-skills`, moved to `-home-dan-sandbox-punkfab-circuit-skills`) · **Repos:** punkfab/circuit-skills, audiodestrukt/einhander (`pcb-rerun/`), punkfab/punkfab.com (blog) · **Skills used:** move-project, pcb-layout

## Goal

Re-run the einhander PCB pipeline with nobody touching it, side by side with the board shipped in July
(see [2026-06-30-einhander.md](2026-06-30-einhander.md)), to measure how close an unattended run gets and
how much the tooling/models have moved. Dan's framing: "I still haven't been able to get a single run of
things like einhander to fully work."

## Timeline

- **2026-09-28** — circuit-skills moved `dnewcome/circuit-skills` → `punkfab/circuit-skills` with the
  move-project skill (GitHub transfer, local folder, session dirs, `~/.claude/skills/pcb-layout` symlink).
  The pushed remote briefly answered `Repository 'punkfab/circuit-skills' is disabled` right after the
  transfer; it cleared on retry within a minute.
- **2026-10-01 08:20** — Dan pasted a "PCB Studio" announcement blurb (rules: ground planes not daisy
  chains, DRC before Gerbers, no autorouter spaghetti). All three were already pcb-layout's core rules
  (SKILL.md `:94`, `:109/:230`, `:8/:316`); nothing to adopt.
- **08:30** — baseline: the shipped `pcb/index.circuit.kicad_pcb` (commit `8522e8a`) measured with
  `drc_check.py` (0 placement / 0 shorts / 0 unconnected / 2 dangling / 5 cosmetic), `dfm_check.py` (OK),
  `check_floating.py` (OK) and a new `board_metrics.py` (1463.8 mm track, 467 segments, 49 vias, 484.5 mm
  of GND/V3V3 on signal layers).
- **08:32** — git worktree `einhander-rerun` (branch `rerun-2026-10-01`). Found the skill's `route4.sh`
  was OLDER than einhander's copy, and ~10 einhander finisher scripts had never been synced to the skill.
- **08:34** — unattended `make route` (einhander's route4.sh): **31.6 s**, Freerouting 2.2.4 107 nets →
  SES 267 wires / 35 vias. Result: **1 short (VBUS↔RUN), 6 unconnected, 3 dangling**.
- **08:35–08:37** — diagnosis (below): all 7 defects on C_IN / C_OUT / C_LED → DSN image mirroring.
- **08:37** — wrote `dsn_split_sides.py`; first version flagged U1 falsely (local-frame comparison);
  rewritten to compare in absolute board coordinates via pcbnew → flags exactly the 3 caps; idempotent.
- **08:38** — rerun with the fix: **0 shorts, 0 dangling, 2 unconnected** (QSPI_SCLK, one USB_DP pad).
  `drc_check.py` printed `RESULT: CLEAN ✓` anyway → fixed the gate.
- **08:38–08:55** — tail investigation: longer Freerouting passes, net-drop determinism test, `@`-in-name
  test, incremental frozen-wiring pass (+ bisection), Freerouting v2.4.1. All dead ends (below).
- **08:56** — metrics + KiCad SVG plots of shipped vs rerun.
- **09:05–09:40** — skill update committed (`d064432`), blog post written, fact-checked, committed
  (`af33869`), both pushed. einhander `pcb-rerun/` folder committed + pushed (`7ddbb42`); worktree removed.
- **Later 10-01** — Dan asked whether this helps Freerouting's 4-layer plane weakness; answer: no (see
  [../research/4-layer-planes.md](../research/4-layer-planes.md)).

## Problems and fixes

1. **Mixed-side footprint mirroring in tscircuit's DSN export (the root cause of einhander's tail).**
   - *Symptom:* unattended run → 1 short (`Pad 1 [VBUS] of C_IN` vs `Track [RUN]`), 6 unconnected, 3
     dangling. Every item on C_IN, C_OUT or C_LED; each net's B.Cu track ended on the part's *other* pad
     with no via.
   - *Root cause:* `tsci export -f specctra-dsn` dedupes `(image …)` by footprint name
     (`simple_capacitor:2.8500x1.4000_mm`). The image was written from **C11 (0805, `layer="bottom"`)** →
     `[B]` padstacks, pin 1 at +x. Top-side C_IN/C_OUT/C_LED (also 0805) reused it, so Freerouting routed
     them as mirrored bottom-side parts. The `.kicad_pcb` export is correct per part (C_IN pin 1 at −x on
     F.Cu), so the two files silently disagree.
   - *History:* the July session saw the same corner fail and hand-patched it at hard-coded coordinates
     (`fix_ldo_planes.py`, `patch_stragglers.py`), attributing it to Freerouting / density.
   - *Fix:* `scripts/dsn_split_sides.py <board> <dsn>` — loads pcbnew, computes every DSN pin's absolute
     position (place + rotated image pin, offset derived from the board by median), compares to the KiCad
     pad's absolute position + copper side; mismatching parts get a private image built from the KiCad
     pads plus a side-swapped padstack clone. Wired into `route4.sh` as step 2a.
   - *Sub-problem:* v1 compared in footprint-local coordinates and flagged U1 (RP2040 at −90°) — 56/57
     pins "mismatched" because KiCad and the DSN store rotated pad offsets in different frames. Fixed by
     comparing absolute coordinates.
   - *Status:* fixed → 0 shorts / 0 dangling / 2 unconnected, zero hand steps. Landed in pcb-layout
     `d064432` (SKILL.md "Mixed-side footprints: the DSN mirrors top-side parts").

2. **`drc_check.py` printed CLEAN with open nets.**
   - *Symptom:* `unconnected=2` in the SUMMARY line, `RESULT: CLEAN ✓`.
   - *Cause:* `blocking` summed courtyard + shorts + false shorts + crossings + edge-over-cut, not
     `unconnected`.
   - *Fix:* add `unconn` to `blocking`. Any "CLEAN" from before 2026-10-01 must be re-read for the
     unconnected count. Landed `d064432`.

3. **Freerouting silently drops a net (QSPI_SCLK).**
   - *Symptom:* with the side fix, QSPI_SCLK absent from the SES entirely (no wire near U1.52 or U2.6);
     Freerouting log: pass 18 "(1 unrouted)", pass 19 score 997.19 with no unrouted count, "session
     completed".
   - *Checked:* DSN net present with both pins; both pins exist in their images at correct absolute
     positions; no residual `(wiring)`; `@` in image names not the cause (renamed → same).
   - *Determinism:* pre-split DSN 3/3 runs include SCLK; split DSN 3/3 runs omit it. So it is triggered by
     the corrected geometry, not run-to-run noise.
   - *Status:* root cause never found; open. Only `drc_check` (unconnected) catches it.

4. **USB_DP one pad short** — track ends ~1 mm from J1 pad 10 (second D+ contact). Open; counted in the 2.

5. **Incremental "tail" pass with frozen wiring hangs Freerouting 2.2.4.**
   - *Attempt:* `dsn_freeze_ses.py` writes the previous SES's 261 wires + 32 vias into the DSN as
     `(wiring … (type fix))` so a second run routes only the open nets.
   - *Symptom:* run hangs right after "Job started" (300 s timeout, no pass). Bisection: vias-only →
     3 passes OK; wires-only → hang; `(type protect)` / `(type route)` → hang; first 10 wires → 2 passes
     then hang; first 60 → 1 pass then hang.
   - *Status:* abandoned; kept as `pcb-rerun/scripts/dsn_freeze_ses.py` marked DEAD END; documented in
     SKILL.md "Freerouting tail dead-ends". (Useful side-finding: **fixed vias do not stall it** — see the
     planes research note.)

6. **KiCad headless DSN export fails** — `pcbnew.ExportSpecctraDSN(board, path)` returns `False` with
   relative and absolute paths, no file written; `kicad-cli pcb export` has no specctra option. Abandoned
   (was going to be the source for an incremental pass).

7. **Freerouting v2.4.1 is worse on this board** — 1376 violations at the optimizer stage, ~88 s per
   optimizer pass, no SES within 200 s. Stayed on 2.2.4 (`freert224` honours `FREERT_JAR` to switch jars).

8. **Skill drift** — circuit-skills' `route4.sh` and `make_fab.sh` were older than einhander's, and
   `finish_tail/iter/converge`, `stitch_planes`, `add_dsn_planes`, `diag_ipc` existed only in einhander.
   Synced in `d064432`; the coordinate-hardcoded `fix_ldo_planes.py`, `patch_stragglers.py`,
   `reconnect_j14.py` deliberately left out.

9. **Environment snags** — `pcbnew` only importable from system `/usr/bin/python3` (pyenv shim lacks it;
   `dsn_split_sides.py` / `board_metrics.py` use that shebang). `rsvg-convert` missing → used ImageMagick
   `magick -density` for SVG→PNG. `pkill -f 'http.server 8765'` matched its own shell and killed the
   command (exit 144).

## Decisions and reversals

- **Reversed:** "the LDO/USB power corner is intrinsically short-prone" (July). It was the mirror bug.
  SKILL.md step 4 now says to run `dsn_split_sides.py` and re-check before hand-patching any corner.
- **Corrected:** "Freerouting is NON-DETERMINISTIC". Same DSN → same result 3/3; the tail moves when the
  *input* changes.
- **Kept:** Freerouting 2.2.4; finishing the last nets by hand or with a DRC-verified finisher, not
  another router pass.
- **Decided:** shipped `pcb/` stays the fab board; `pcb-rerun/` is a record, not fabbable (2 open nets).

## Outcome

| | Shipped (July, hand-finished) | Unattended raw | Unattended + fix |
|---|---|---|---|
| Shorts / unconnected / dangling | 0 / 0 / 2 | 1 / 6 / 3 | **0 / 2 / 0** |
| Board-specific patch scripts | 3 | — | 0 |
| Track length | 1463.8 mm | 1461.4 mm | 1421.2 mm |
| Vias | 49 | 35 | 32 |
| GND/V3V3 track on signal layers | 484.5 mm | 543.8 mm | 507.0 mm |

Unattended board uses less copper and fewer vias but routes the key matrix as long diagonals (the July
board is neater). Blog post: <https://punkfab.com/blog/einhander-reroute/>.

## Pointers

- circuit-skills `d064432` — `pcb-layout/scripts/dsn_split_sides.py`, `drc_check.py`, synced
  `route4.sh`/`make_fab.sh`, finishers; SKILL.md sections "Mixed-side footprints…" and "Freerouting tail
  dead-ends".
- audiodestrukt/einhander `7ddbb42` — `pcb-rerun/` (README, `results/stage0-*`, `results/stage1-*`,
  `shipped-metrics.json`, `scripts/board_metrics.py`, `scripts/dsn_freeze_ses.py`).
- punkfab/punkfab.com `af33869` — `blog/einhander-reroute/`.
