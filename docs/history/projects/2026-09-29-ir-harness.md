# ir-harness — round-trip audio measurement harness (sweeps, Hammerstein residuals, knob ramps) for checking circuit models against reality

- **Dates:** 2026-09-29 19:39 → 22:37 (UTC, transcript clock; git commits show local time, UTC−7) · **Sessions:** `99480b70` (dir `~/sandbox/audiodestrukt/ir-harness`) · **Repo:** [audiodestrukt/ir-harness](https://github.com/audiodestrukt/ir-harness) (public; commits `1d22552`, `9a95ead`, `3cefaac`). Also touched: `audiodestrukt/circuit-decimator` (commit `f6ffcbc`, local only) and `dnewcome/audiodestrukt.com` (commit `0ddee2b`) · **Skills used:** kickoff, dataviz. **No circuit-skills skill (circuit-sim, pcb-layout, pcb-enclosure-fit, pcb-3d-render) was loaded.**

> **Scope note.** This project sits next to circuit-skills but is not circuit-skills work. It is an audio *measurement* harness. Its device under test (DUT) in this session was circuit-decimator's realtime circuit simulator (a Fuzz Face solved with the DK method). Its future DUT is a vintage Marshall JMP. It shares the circuit-sim idea of validating a model against a reference, but it was built from scratch in Python with no skill. It is recorded here because it closes the loop circuit-sim leaves open, **sim against measured reality**, and because it found a solver artifact in a circuit simulator.

## Goal

Dan wants to characterize real audio hardware (first a Marshall JMP, through a load box) by pushing chirps and sweeps, stepped tones and arbitrary waveforms through it while changing knobs. He wants to compare white-box circuit models, sweep-derived models and Neural Amp Modeler, and later study why gear sounds the way it does in a mix. Constraints at kickoff: no hardware on the bench, non-USB Rigol gear, and a 192 kHz interface. The underlying problem is that **circuit-decimator had only ever been validated sim-against-sim (DK solver vs ngspice), never against a measured signal.** Chosen v1: a software harness with the sim as a stand-in DUT. Hardware becomes another adapter later.

## Timeline

- **2026-09-29 19:44** Idea stated. Kickoff split it into three threads: harness, modelling/NAM, and psychoacoustics. Dan picked "software harness, sim as stand-in DUT"; the first real DUT will be the JMP with a load box. Parked: Rigol/SCPI control, motorized knobs, NAM, a JMP model, mic'd cabs, psychoacoustics.
- **20:24** "Save the brief and go." circuit-decimator's renderers were inspected (`ff_render`, `circuit_render`, `plugin_render`, …). The dataviz skill supplied the palette. Package `irharness/` written: `stimulus.py` (synchronized exponential sweep, stepped tones, DI clip, a segment table travelling with the signal), `dut/` adapters (`sim:ff`, netlist, VST3 host, `audio:` play/record, closed-form fixtures), `align.py`, `analysis.py`, `report.py`, `session.py`, `cli.py` (`irh gen/run/compare/devices`), and pytest tests.
- **~20:29–20:37** Test failures and fixes (problems 1–3). First results at 192 kHz: **DK vs reference MNA solver null to −92 dB** on the DI clip. **The DK solver emits single-sample spikes at clipping edges** (problem 4). Starving the supply to 4.5 V costs 9 dB of level and 40 dB at 20 kHz, and raises H2 at 1 kHz from −35 to −2 dB.
- **20:42** "Push this to a public audiodestrukt repo." Commit `1d22552`, then a comprehensive README with figures in `docs/figures/` as `9a95ead`.
- **20:52** Dan: "Is this method going to be able to capture nonlinearity?" Answer: partly. Sweep harmonic IRs equal a generalized Hammerstein model, which is exact at one drive level for memoryless nonlinearity. It misses level dependence, memory (sag, bias shift), deviations in intermodulation, and non-harmonic content. The proposed test: fit the model, null it against the DI response, and treat the residual as what the method misses.
- **20:56** Dan: bake in input-level sweeps and realtime knob control, and use the residuals to decide where to focus. Built: `irharness/model.py` (Novak generalized Hammerstein from harmonic IRs, level-indexed blending), residual localization (by ⅓-octave band, input level, signal history, tone and burst, with a `focus()` ranking), multi-level sweeps, tone bursts with probes (sag, DC shift, recovery), knob ramps, `irh grid` knob-plane heatmaps, and `controls.py` with native, stepwise and prompt modes. A `--automation` option was added to circuit-decimator's `ff_render.cpp` (problem 8). Ten tests pass.
- **~21:12–21:16** Finding: the polynomial model has a ceiling of about −14 dB on a hard clipper (problem 7). Commit `3cefaac` pushed. The circuit-decimator change was committed as `f6ffcbc` but **not pushed**.
- **22:18** "Create a blog post and publish on audiodestrukt.com." The site repo (`~/sandbox/dnewcome/audiodestrukt`, static `build.py`, deployed by DigitalOcean on push) was located. A post with 8 figures was written, list rendering was fixed in `build.py` (problem 10), and commit `0ddee2b` was pushed. The post went live after about 40 s. **22:37** `/compact`.

## Problems and fixes

1. **Analysis tests failed on known-answer fixtures**
   - *Symptom:* `test_identity_ir_is_flat_unit_gain` failed. `test_lowpass_magnitude` failed with `assert 0.6126888564010731 < 0.5`, then `0.3149…`, then at 10 kHz `assert 2.6214984671325965 < 1.5`: measured −42.64 dB against an expected −40.
   - *Root causes:* (a) The sweep inverse filter was normalized to the reference peak instead of the passband spectral level and sweep level. (b) Band-limiting at 20 Hz rings symmetrically, which disturbs the 50 Hz reference point. (c) The analytic −40 dB/decade expectation was wrong for the actual discrete filter (inferred; the fix compares against scipy).
   - *Resolution:* `ess_inverse` was normalized to 0 dB passband spectral level and divided by sweep level, so the IR is output per full-scale input. A shared pre-window of up to 50 ms was added. The test now references 300/100 Hz and compares against `scipy.signal.butter`/`sosfreqz` within 0.1 dB. 7/7 tests passed. Landed in `irharness/stimulus.py`, `irharness/analysis.py` and `tests/test_harness.py`.

2. **Python 3.11 venv: `TemporaryDirectory(delete=…)`**
   - *Symptom:* `TypeError: TemporaryDirectory.__init__() got an unexpected keyword argument 'delete'` in `dut/sim.py`.
   - *Root cause:* The `delete=` parameter only exists from Python 3.12, and the venv was 3.11.14.
   - *Resolution:* The temp-dir handling in `irharness/dut/sim.py` was rewritten without that parameter.

3. **Harmonic IR windows needed bounding**
   - *Symptom/cause:* Harmonic IRs arrive L·ln(k) *before* the linear IR, and successive orders pack closer together. Without bounding, alignment could lock onto a harmonic peak, and windows could overlap.
   - *Resolution:* The alignment search is bounded at ≥ −10 ms, and each order's window stops before the next (`extract_harmonics`, spacing L·ln((k+1)/k)). Landed in `irharness/align.py` and `irharness/analysis.py`.

4. **circuit-decimator DK solver emits single-sample spikes at clipping edges**
   - *Symptom:* At 48 kHz with no oversampling, spikes reached **27 V on a 9 V circuit**. At 192 kHz there were 16 spikes in the 0 dBFS 440 Hz tone, up to 2.8× the segment's 99.9th percentile. Visible in raw samples as `… 1.69 -8.19 -1.63 …`.
   - *Root cause:* A step artifact in the solver at hard clipping edges in circuit-decimator, not a modelling error (as diagnosed in the session; the exact solver cause was not investigated).
   - *Resolution:* Not fixed. A `spikes` metric now flags isolated outliers above 2× the 99.9th percentile per segment, so it shows up in every report. "Fix DK spikes" is first on the roadmap because they would pollute any sim-vs-hardware residual. Recorded in memory (`circuit-decimator-dk-spikes.md`) and the README.

5. **"Linear IR" of the fuzz is really a describing function**
   - *Symptom/cause:* At −12 dBFS with 0.25 V per full scale, the Fuzz Face is already hard-clipped.
   - *Resolution:* Documented. Small-signal measurements need the sweep 20–30 dB lower, which the multi-level sweeps (`--sweep-dbs=-36,-24,0`) now provide.

6. **Hammerstein fit problems: wrong branch gains, blow-up above the fitted level, ill-conditioning**
   - *Symptom:* tanh branch gains came out as `[0.0214, 0, -0.0026, 0, -0.0333]` against an expected `[1, 0, -1.333, 0, 2.133]`. Order-13 fits had condition number 6.6e10 and tone RSR rose to +3–5 dB at high level. Applying the model above its fitted amplitude exploded through the high powers.
   - *Resolution:* A sine-power expansion matrix (real for odd n, j-weighted for even n, with A^(n−1) scaling). Order is chosen from the data, up to 9, with a −45 dB floor. Input is clamped to 1.05·A. `LevelIndexedModel` blends kernels from different levels by a 10 ms envelope. A test confirms tanh is explained to −40 dB at its level and fails at 0 dBFS, as it should. Landed in `irharness/model.py`.

7. **Polynomial (Hammerstein) model ceiling on a hard clipper**
   - *Symptom:* The order-9 model explains only about 3 dB of the DI clip (4 dB with four sweep levels). Order 3–9 makes no difference, and all 30 tones have RSR above −10 dB.
   - *Root cause:* The model class, not the measurement. A square wave keeps about 96% of its energy in harmonics up to the 9th, so a polynomial of order 9 cannot null a hard clipper below about −14 dB. The knob grid shows where polynomials do work: at low fuzz on a fresh 9 V supply, clip RSR is −12.6 dB and H3 is −84 dB.
   - *Status:* Open. The next model is a saturating Wiener-Hammerstein fitted from the multi-level describing functions (roadmap item 1). Recorded in memory (`polynomial-model-ceiling-on-clippers.md`) and the README.

8. **Knob automation in `ff_render` had no effect**
   - *Symptom:* With `--automation`, the output RMS stayed at 1.102 for the whole ramp.
   - *Root cause:* `render()` took `cd::FuzzFaceParams p` **by value**, so automation updates to the caller's params never reached the solver (inferred from the one-character fix).
   - *Resolution:* Changed to `cd::FuzzFaceParams& p`. RMS then rose from 1.150 to 1.606 across the ramp. Parameters are re-applied every 32 samples with `setParams`, which keeps circuit state the way a plugin knob turn does, and values hold outside the breakpoints. circuit-decimator `tools/ff_render.cpp`, commit `f6ffcbc` (**local, not pushed**).

9. **Burst metrics failed on the identity fixture**
   - *Symptom:* `assert (0.2493 < 0.05)` for sag, then `0.1495 < 0.05` for the probe deficit.
   - *Root cause:* A 10 ms RMS window that wasn't a whole number of tone cycles read a steady tone as fluctuating. The fade-in and fade-out windows were also included in the start and end estimates.
   - *Resolution:* The envelope window is now a whole number of cycles near 10 ms when the frequency is known. The end level is the median of the last ~300 ms excluding the fade-out window. 10/10 tests passed. Landed in `irharness/analysis.py` (`_env_db`, `burst_metrics`).

10. **Blog generator had no list support, and the DigitalOcean app ID lookup failed**
    - *Symptom:* Markdown bullets rendered as `<p>- …` paragraphs, including on the existing speaker-cab post. `doctl apps get 8baab499-…` returned 404.
    - *Resolution:* List rendering for `-`, `*` and `1.` was added to `audiodestrukt.com/build.py`, which fixed both posts. The guessed app ID was dropped. Deploy was verified instead by polling the live URL in the background until it returned 200 (about 40 s), and all 8 image URLs were checked for 200. Commit `0ddee2b`.

11. **Hardware path untested**
    - The `audio:` play/record adapter and the `--knob-mode prompt`/`--prompt` grid flow exist but have never run, because no interface was connected. This is stated in the README. A loopback run to establish the measurement floor is the first hardware step. The JMP still needs a reactive load box and a reamp box.

## Decisions and reversals

- **The DUT adapter is the seam.** Sim, VST3, audio interface and fixtures all share one stimulus with a segment table, so sim runs and hardware runs are cut at identical offsets.
- **Alignment from the deconvolved IR peak, not raw cross-correlation.** The IR peak is a sharper landmark and survives heavy distortion.
- **The residual is the organizing principle** (Dan's suggestion): every run fits a model to its own sweep, predicts the whole stimulus and localizes where the prediction fails. Levels, bursts and knob ramps were added as answers to what the residual points at.
- **Knob schedules are attached at run time, not baked into the stimulus,** so one stimulus serves every device. Three execution modes: native, stepwise, and prompt (a human turns the knob).
- Generated audio in `runs/` (178 MB of float WAVs) is gitignored. Figures are copied into `docs/figures/`.

## Outcome

A public, tested harness (10 tests) with a CLI, multi-level sweep, tone and burst stimulus, a sweep-derived Hammerstein model, residual localization, knob ramps and grids, and a published blog post ("A bench that says where the model is wrong", audiodestrukt.com/blog/posts/ir-harness.html). Findings about circuit-decimator: DK matches MNA to −92 dB, but DK has spike artifacts at clipping edges. Polynomial models hit a structural ceiling on hard clippers. Nothing has been round-tripped against real hardware yet. For circuit-skills, the takeaways are indirect. "Validate against reality" needs a measurement harness that circuit-sim does not provide. And a sim-vs-sim null (DK vs MNA) can hide solver artifacts that only a spike metric reveals (inferred relevance).

## Pointers

- ir-harness: `irharness/stimulus.py`, `align.py`, `analysis.py`, `model.py`, `residual.py`, `controls.py`, `session.py`, `report.py`, `cli.py`, `dut/`; `tests/test_harness.py`; `README.md`; `docs/figures/`, `docs/example_report.md`
- circuit-decimator: `tools/ff_render.cpp` (`--automation`), commit `f6ffcbc` (unpushed at session end)
- audiodestrukt.com: `posts/2026-09-29_ir-harness.md`, `build.py` (list rendering), commit `0ddee2b`
- Session memory (local): `circuit-decimator-dk-spikes.md`, `polynomial-model-ceiling-on-clippers.md`
