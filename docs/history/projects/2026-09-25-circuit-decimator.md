# circuit-decimator — realtime component-level circuit and speaker simulation as VST plugins, each verified against ngspice

- **Dates:** 2026-09-25 08:22 → 2026-09-28 21:45 (UTC, transcript clock; git commits show local time, UTC−7) · **Sessions:** `40ef0305` (main session; context ran out and was auto-continued twice, at 2026-09-26 06:29 and 2026-09-27 23:51) and `9eb0d8c4` (a parallel session on 2026-09-26 15:38 → 18:09 that added the Shin-Ei FY-2 circuit and handled the website). Both ran in **`~/sandbox/punkfab/circuit-decimator`**, which was moved to **`~/sandbox/audiodestrukt/circuit-decimator`** on 2026-09-28 03:15 at Dan's request. The move script rewrote the paths inside the transcripts, so the condensed transcripts show `audiodestrukt/…` throughout. `~/sandbox/punkfab/circuit-decimator` is still a symlink to the new location, because the move's `--final` cleanup step was never run. · **Repo:** [audiodestrukt/circuit-decimator](https://github.com/audiodestrukt/circuit-decimator). It was private at first and made public 2026-09-26 17:01. Commits from these sessions run from `f7632f9` to `1a711be`. `f6ffcbc` came from the separate ir-harness session. Also touched: `dnewcome/audiodestrukt.com` (site commits `f57ea51`, `50c692e`, `2b6f164`, `03073b6`, `1f2842c`) · **Skills used:** **circuit-sim** (loaded once, at 2026-09-25 08:25, for the first Fuzz Face ngspice deck), kickoff (twice: LA-2A, speaker cab), frontend-design (Phys Fuzz UI). **pcb-layout, pcb-enclosure-fit and pcb-3d-render were not used.** There is no PCB, no tscircuit, no KiCad and no Freerouting in this project.

> **Scope note.** This is a *software* project: JUCE 9.0.2 VST3/AU plugins and a test-bench app. It uses circuit-sim's core idea, **"one parametric ngspice deck is the source of truth"**, and pushes it much further than the skill does. Every realtime C++ solver is checked against an ngspice deck of the same circuit, or against an exact analytic formula. The circuit-sim skill was only loaded at the start. Everything after that (DK solver, general netlist engine, Jiles–Atherton transformer cores, Koren tubes, a T4 opto cell, a loudspeaker FE/acoustics model, CPU regression tests) was built without a skill. The ngspice traps it hit, listed below, apply directly to circuit-sim, and **none of them have been fed back into the skill**.

## Goal

Dan wanted "a VST plugin that does realtime circuit emulation via ngspice or similar", where the electrical parameters can be automated to "change or destroy the performance of the circuit". He also wanted the static parts of a circuit "baked" (lumped models or convolution). In the first exchange this was reframed: ngspice would be the *reference*, not the engine, because it uses variable timesteps, fails to converge exactly in "destroyed" states, and keeps global state. The plugin would get its own fixed-step solver, validated against ngspice. Over the next four days the goal grew into a "workshop for effects": a general workbench (Circuit Decimator plugin plus the Circuit Bench app) and focused products sold at $4.99. Those products became **Phys Fuzz** (Fuzz Face, then also Shin-Ei FY-2), **Iron** (tube stage into a gapped single-ended output transformer), **Opto** (an LA-2A-style optical leveler) and **Cone** (a physically modelled guitar speaker and cabinet).

## Timeline

- **2026-09-25 08:22** Idea stated. The assistant advised using ngspice as the ground truth and not the engine, pointed to nodal DK, WDF and LiveSPICE, and suggested IIR filters (not convolution) for static linear blocks.
- **08:25** "let's do a fuzz face". The **circuit-sim skill was loaded**. `sim/fuzzface.cir` (silicon NPN, 9 V, a guitar-pickup source, every "destroy" value as a `.param`) and `sim/render.py` were written: 15 presets rendered to WAV through ngspice 45.2. Bias was retuned (problem 1), dead presets were moved to the "edge of death" (problem 2), and 4× oversampling was added after aliasing was heard (problem 3). ngspice measured at only 0.8–1.6× realtime at 4× OS, which was saved to memory as the reason for a custom solver.
- **08:31** "JUCE because I want this to be a vst". JUCE 9.0.2 was cloned. `dsp/FuzzFace.h` (11-node dense MNA, trapezoidal companions, Gummel-Poon subset, SPICE `pnjlim`, capped Newton) and `tools/ff_render.cpp` were written. `sim/compare.py` matched bias to the mV, with waveform correlation 0.997. The plugin was built, and so was `tools/plugin_render.cpp`, a headless VST3 host with `--ramp` automation. Several build problems along the way (problems 5–8).
- **16:27** Circuit Bench app (loops a WAV, scope, solver stats, "power cycle" button).
- **16:36** MAP-Elites sound search (`search/explore.py`): Sobol scatter plus mutation over the destroy knobs. The knob table moved to the shared header `dsp/Knobs.h`, and `libfuzzface.so` exposed it to Python through ctypes. 77–80 distinct sounds were found in about 4 minutes on 28 cores.
- **17:26** Live schematic view (`CircuitView`). **17:39** Restructured as a monorepo: `core/` plus `products/workbench` and `products/phys-fuzz`. Renders were bit-identical before and after. **17:48** Pushed to a private repo as `f7632f9`.
- **18:12–18:28** Teensy and Daisy feasibility. **Nodal DK solver** `FuzzFaceDK.h` (double and float): 26× realtime against 7.5× for MNA, matching MNA to 0.005 % RMS. A float build for Cortex-M7 with an xPack ARM GCC came to 16 KB with no f64 ops in the per-sample path. It was never run on hardware.
- **23:23** "make builds … charge 4.99". A GitHub Actions release workflow (macOS VST3+AU universal, Windows, Linux, pluginval, auval) was added. A discussion followed of selling through Curiate (its Terms forbid digital goods, and an App Store guideline 3.1.1 history applies). Decision: US-only, Stripe, Dan/Curiate as merchant of record. That work was never started.
- **23:44** Phys Fuzz "lid off" product UI, using the frontend-design skill.
- **2026-09-26 02:45–02:53** macOS Developer ID certificate created from Linux (CSR, `.p12` with `-legacy`, repo secrets). Signed and notarized builds were made, and tag `phys-fuzz-v0.1.0` produced a draft release.
- **03:29** Dan: make the engine more comprehensive; tubes via simple curves, transformers in depth, power supplies later as a separate module. **Transformer first**: `sim/transformer/` (linear deck in two equivalent forms, then a Jiles–Atherton core built from B-sources) and `core/circuit/Transformer.h`. The C++ model matched the ngspice THD to 0.1 % median.
- **04:36** **General netlist engine** `core/circuit/Circuit.h` (it derives the DK solver from a netlist) plus `Devices.h` (Bjt, Koren triode, JACore). `net_selftest` reproduces the hand-built solvers to 1e-9 / 2e-5. Tube mic pre (`sim/tubepre/`) and single-ended output stage (`sim/tubeout/`). ngspice nondeterminism found here (problem 12).
- **05:14** **Iron** plugin (first product on the netlist engine, with a live B-H loop view). pluginval editor hang (problem 16). **05:36** Circuit Bench gets a circuit selector. **05:49** Commits `16eb8de` and `bfd4a0c`, tag `iron-v0.1.0`.
- **06:20** **LA-2A** built from UA's published manual (figs. 5–7): T4 opto cell, Koren pentode for the 6AQ5, audio path and sidechain split into two circuits. The engine version matched `sim/la2a/la2a.cir` within 0.1 dB. **07:10** `6f66425`. **07:11** "cut a build" produced the **Opto** product, `64ff22b`, tag `opto-v0.1.0`.
- **15:38 (session `9eb0d8c4`, in parallel)** Shin-Ei FY-2 added to Phys Fuzz: `sim/shinei/`, `ShinEi.h`, and a circuit switch in the engine. Trademark-free names were chosen ("London '66" / "Tokyo '68"). `e42feb0`, tag `phys-fuzz-v0.2.0`. Blog post on audiodestrukt.com. **The repo was made public** (17:01). The site was switched to absolute links, and the Cloudflare Web Analytics beacon was added.
- **15:27–18:14 (session `40ef0305`)** **Speaker cab** kickoff. Brief `docs/briefs/2026-09-26-speaker-cab.md`, approach "hybrid physics → IR". Built: driver plus closed box in the mobility analogy (Bl and Sd as ideal transformers), a Rayleigh near-field radiation model, an axisymmetric shell FE model of the cone, and calibration against a published Eminence Legend 1258 datasheet (problem 25), then into Circuit Bench and a live cross-section view. Commits `7797962` and `09d3839`.
- **2026-09-27 02:17** Blog post on the cab (`03073b6`). **05:39** 10" size knob and back opening. **05:58–06:14** Bench live-input, sample-rate and bypass issues (problem 31). **06:26** Dan: mic moves don't "phase" like a real mic. A measured SM57 model and a mic-face reflection were added; the real cause turned out to be the axisymmetric cone (problem 32). **16:35** Dan: volume and back opening should change the low end more. Two real bugs were found (problem 33), commit `9c164fd`. Dan had committed the mic work himself as `4189ba9`.
- **17:43** CPU regression tests (`perf_bench`, `tests/perf_check.py`, ctest, `tests.yml` CI). **22:40** **Cone** plugin, `f241cf7`. macOS and Windows CI failures were fixed in `bae2b07`, then `cone-v0.1.0` was released.
- **22:56** Roadmap brief `docs/briefs/2026-09-27-simulation-roadmap.md`: a "fidelity budget", amp sim, multi-driver and multi-mic cabs, preamps. **22:58** Dan reported 25 % CPU in the Bench (problem 37). **23:32** "is the cone really linear?" led to the speaker large-signal model (Bl(x), suspension, coil heating) and the learnings log `docs/realtime-simulation-notes.md`.
- **2026-09-28 03:13** "move this folder to audiodestrukt and keep the chat history correct". `~/.claude/move-project.py` was written and run (problem 40). **21:20** `1a711be` pushed. **21:21** All four plugins added to the audiodestrukt.com homepage. Iron, Opto and Cone releases published (`1f2842c`).

## Problems and fixes

### ngspice / circuit-sim (the part most relevant to the skill)

1. **First silicon Fuzz Face bias had Q2 saturated**
   - *Symptom:* With bf1=100/bf2=130 and rc2b=8.2k, Vc2 was ~1.5 V (Q2 saturated), so the circuit was nearly silent.
   - *Root cause:* Silicon Fuzz Faces need high-hFE transistors and a lower Q2 collector (bias-trim) resistor.
   - *Tried:* Swept bf ∈ {250, 300} × rc2b ∈ {8.2k, 6.8k, 5.6k}. Vc2 came out at 2.59 / 3.63 / 4.51 V.
   - *Resolution:* Defaults changed to bf1=bf2=250 and rc2b=5.6k, giving Vc2 = 4.49 V. **Where:** `sim/fuzzface.cir`.

2. **"Destroy" presets that produced silence**
   - *Symptom:* `starve_3v` came out at −85 dBFS RMS. `leaky_input_cap` (rleak 20 k) was also dead.
   - *Root cause:* This is physically correct. Q2 stops working below about 5 V at that bias, and a 20 k leak pulls Q1's base.
   - *Resolution:* Presets moved to the "edge of death" (3.6 V; rleak 100 k; dying battery rbat 3 k, cbulk 4.7 µF), so they sputter instead of going silent. **Where:** `sim/render.py`. The same lesson came back for Phys Fuzz's Battery macro (0 % was retuned from silence to 4.4 V) and for the low-Battery + high-Age dead corner, which was left in as "physically honest".

3. **Aliasing in ngspice renders sampled at 48 kHz**
   - *Symptom:* Fuzz square waves alias audibly (`baseline_no_oversampling.wav` was kept for comparison).
   - *Resolution:* `render.py` steps ngspice at FS×4, band-limits and decimates. Cost: ngspice dropped from 1.5–4× realtime to **0.8–1.6× realtime** on a 2-transistor circuit. This number justified writing the custom solver, and it was saved to project memory (`ngspice-realtime-budget`).

4. **Fixed-step C++ solver vs adaptive-step ngspice: waveform error on edges**
   - *Symptom:* Bias matched to the mV, but `err/rms` was 5.9 % (baseline), 35 % (starve_3v6) and 53 % (wrecked). Correlation 0.997.
   - *Tried:* Raising the Newton cap from 8 to 50: **no change**.
   - *Root cause (stated, not proven):* ngspice shrinks its timestep at sharp edges and the realtime solver doesn't, so edges land a fraction of a sample apart.
   - *Status:* Accepted as the expected difference. The FY-2 later showed 2.5–3.6 %. The ir-harness project later found DK spikes at clipping edges (see its history file).

12. **ngspice is nondeterministic when many copies run in parallel (hysteresis decks)**
    - *Symptom:* Identical runs of `sim/tubepre` gave different results: −60 dBu at 50 Hz gave THD **4.81 %** in one run and 0.062 % in another; −10 dBu gave 21.26 % vs 22.32 %. Row counts differed (46109 vs 46092).
    - *Tried:* Finer `tran` steps (50 µs, 20.8 µs, 5.2 µs): all gave the same THD. `OMP_NUM_THREADS=1`: fewer distinct results across 24 parallel runs, but still not deterministic. Running twice and taking the median of three: one outlier (3.08 %) remained. `method=gear` and `trtol=1` run sequentially: deterministic.
    - *Root cause:* Many concurrent ngspice processes, plus ngspice's OpenMP threading, on decks whose transformer hysteresis is built from behavioural B-sources. These occasionally take a different timestep sequence or a wrong trajectory. The exact mechanism was never found.
    - *Resolution:* **Run ngspice sequentially in the harnesses and parallelize only the project's own engine**, with `OMP_NUM_THREADS=1` set in `sim/render.py`, `sim/transformer/core_sweep.py` and `sim/tubepre/compare.py`. Run that way, it is deterministic and matches the engine. The assistant suggested Xyce (which has a built-in hysteresis core) as an independent check later; not done. **Where:** the compare scripts and `sim/tubepre/README.md`. **NOT in the circuit-sim skill.**

13. **`.tran` with brace expressions in `.control` rejected**
    - *Symptom:* `Error: TSTOP is invalid, must be greater than zero.` / `unknown parameter on .tran - ignored` / `no such vector out`.
    - *Resolution:* Literal `tran 1e-4 0.1 0 1e-4` in the deck, rewritten by the Python harness. **Where:** `sim/transformer/xfmr_core.cir`.

14. **Core remanence from switching the sine on abruptly (inrush)**
    - *Symptom:* B-H loops were skewed, and the 1 kHz THD floor read 0.003 %, which was switch-on residue.
    - *Tried:* Starting at the cosine peak (`SIN(... 0 0 90)`) made it **worse**: 4 V gave ~43 % THD at every frequency.
    - *Resolution:* Fade the sine in over 4 cycles (a B-source, `min(1, time*freq/4)`). The loops came out centred and the floor went to 0.000 %. **Where:** `xfmr_core.cir`.

15. **A/B "what the iron adds" measurement traps**
    - (a) The guitar appeared to change *more* than the bass. Cause: subsonic drift in the synthetic plucked-string riff, which the two cores roll off differently. Fixed with a 20 Hz high-pass on the sources.
    - (b) In the SE output stage, the ideal-core reference had the wrong inductance (22 H), which put a *response* difference into the comparison: −4.7 dB "added" on bass. Fixed by fitting lm to the core's small-signal inductance at its DC bias (70 H), which gave −32 dB. **Where:** `sim/transformer/listen.py`, `SEOutput.h`.

17. **Power-on history changes the tone (a finding, then a feature)**
    - A fast B+ ramp overshoots the plate current (70 mA peak vs 9.7 mA settled) and leaves more flux in the core (−0.370 T at 20 ms vs −0.284 T at 1 s). The ngspice deck uses `uic` plus a `tramp` param, defaulting to 3 s so it matches the engine's monotonic `initDC`. This became Iron's "Cold start" button.

18. **First output-transformer core values were implausible**
    - Bass −8.7 dB at 30 Hz and 12 % THD. Retuned to np 4000, Ac 6 cm², k 20, c 0.3, giving −0.9 dB and 1.5 %. These are "plausible generic" values, **not calibrated to a product**.

20. **LA-2A deck: `.func` not found**
    - *Symptom:* `Error: no such function 'amp' at line 77`. Renaming it `dbupk` gave the same error.
    - *Resolution:* Replaced the `.func` with precomputed `.param a1/a2`. **Where:** `sim/la2a/la2a.cir`.

21. **LA-2A transient: "Timestep too small … trouble with node j"**
    - *Root cause:* The ideal transformer was written as E/F sources with the **F-source node order reversed**, which made it positive feedback.
    - *Resolution:* `Fxi 0 mi …` / `Fxo 0 mo …`. After that, the engine and ngspice agreed to 0.03 % at −30 dBu, and step responses agreed within 0.1 dB, attack/release to 1 ms / 10 ms, and waveform error 3–5e-4.

26. **Speaker deck: singular matrix**
    - *Symptom:* `singular matrix: check node lcms#branch`, gmin and source stepping failed, `vector re is not available`.
    - *Root cause:* Shunt inductors formed a DC loop with the E-source of an ideal transformer.
    - *Resolution:* 1e-12 Ω in series with each shunt inductor (Lcms, Lcab); impedance taken as `-v(src)/i(Vin)`. ngspice then matched the analytic network to 8e-8 dB, and closed-box theory (fc 124.74 Hz, Qtc 0.708) exactly. **Where:** `sim/speaker/speaker.cir`.

### Realtime solver, C++ and JUCE build

5. **`std::string(argv[i], eq)` compile error (GCC 15).** Fixed with a `size_t` length cast. `tools/ff_render.cpp`.
6. **JUCE's strict warnings on the solver header** (`-Wsign-conversion`, `-Wfloat-equal`, `-Wshadow`). These recurred for `FuzzFace.h`, `Circuit.h` (52 warnings in one build), `IronViews.h`, `BHLoopView.h`, `CabModel.h` and `Coupling.h`. Each was fixed with a typed `Vec<>`, casts, renamed locals or `!(x > 0)`. The project kept a zero-warning policy.
7. **GCC 15 LTO internal compiler error.** `lto1: internal compiler error: Segmentation fault` while linking `plugin_render`. Fixed by removing `juce_recommended_lto_flags`; **LTO stayed off**. Root cause never found (GCC bug).
8. **JUCE 9 API changes.** `WavAudioFormat::createWriterFor` needs `unique_ptr<OutputStream>`. `AudioPluginFormatManager::addDefaultFormats()` is deleted (use `addDefaultFormatsToManager`). `MessageManager::runDispatchLoopUntil` needs `JUCE_MODAL_LOOPS_PERMITTED=1`. `juce::jmin<int64>` dragged in `SIMDNativeOps<long long>` (incomplete type), so `std::min` was used instead. `juce::Line` has no `*`/`+` operators. `drawRect(float,float,int,int,int)` and `String + CharPointer_UTF8` were ambiguous. `std::initializer_list` couldn't deduce `{0.0f, 1, 2…}`.
9. **The headless VST3 host couldn't find parameters, and crashed on oversized blocks.** `unknown param input=1`: VST3 exposes numeric IDs, so the host matches on display name (case and spaces ignored). `--block 1024 --prepare 256` gave `double free or corruption (out)`: the host gave a block larger than the prepared size. Fixed with internal block splitting in `processBlock` (inferred from the follow-up edit). Afterwards, 37-sample and 256-sample blocks matched to −62 dB.
10. **Float DK solver drifts Q2 bias while playing.** 1.67 % RMS against double, 17.8 mV bias offset. Tried: a different capacitor-state formulation (1.54 %), and reltol 1e-3/1e-4/1e-5 (no change). At rest the error was 0.14 mV. Attributed to the fuzz's abrupt switching plus long time constants. Accepted, since envelope and spectrum stayed within 0.004 / 0.02 dB.
11. **ARM cross-build.** `-fsingle-precision-constant` gave "floating constant truncated to zero", so the flag was dropped. A `sed` whose pattern contained `|` failed with `unknown option to 's'`, and **the checks after it ran on unchanged files**. Redone as a Python edit. A later `sed` with path slashes failed the same way, and the ngspice ramp time was made a deck `.param` instead. Note: `expf` in newlib computes in double.
16. **pluginval "Editor Automation: Timeout after 5 mins" on Iron.** Cause: pluginval opens the editor before `prepare()`. The schematic took the log of the gap value (still 0), and a float `for (v += step)` drawing loop never ended. Fix: the engine initializes its knobs to defaults in its constructor, views clamp to knob ranges, and every drawing loop has a fixed iteration count. After that it passed 19 test groups at strictness 5. Side traps: `pkill -f "pluginval …"` matched its own shell (exit 144, twice in the project), and the pluginval binary vanished when the scratchpad was cleared (exit 127, twice).
19. **LA-2A cost and stability.** First netlist: 0.7× realtime mono, 4.37 Newton iterations per sample, 19 ports. Fixes: a block-diagonal Jacobian; **splitting audio path and sidechain into two circuits solved in turn** (they meet only at node j and the T4), about 3×; an extrapolated Newton starting guess with the device `limit()` applied (2.72 → 2.21 iterations audio, 2.0 → 1.24 sidechain); softplus refactors in Koren. Feedback taken from the output-transformer primary drifted, and moving it to the V2A cathode follower plus a coupling block made it stable. Gain=1.0 gave −inf dB because a pot leg became 0 Ω; pots are now built full-value and set later (inferred). `rfb` was tuned to 470 k for UA's 40 dB maximum gain. `perf` was blocked (`perf_event_paranoid=4`), so the stages were timed manually. Result: 2.5–2.9× realtime mono at 4× OS, and 4.8×/channel at 2× OS in the Opto plugin (about 40 % of a core for a stereo instance). **Status:** CPU is the open issue for Opto.
22. **Koren pentode miscalibrated.** The 6AQ5 at 250/250/−12.5 V gave 72.6 mA plate and 10.4 mA screen (datasheet: 45 and 4.5). kg1 and kg2 were rescaled to 2436 and 7488, which gives an exact match. The Koren 12AX7 gives 0.95 mA vs 1.2 mA from the datasheet; this was left as is.
23. **Small engine-vs-ngspice THD gap in the SE stage at low level** (0.236 vs 0.258 % at 0.3 V, 100 Hz). Checked: identical to 8 digits with the predictor on or off. A grep of the old transcript showed it predated that day. **Never explained.**
24. **The T4 fit and the T4 CSV.** First fit: attack 58–225 ms and 50 % release 209–3045 ms, too slow against UA's "very fast attack, 40–80 ms to 50 %". Refitted to fastShare 0.85 and τ_fast,off 30 ms, giving 6–10 ms attack and 55–493 ms release. The CSV broke on case names containing commas, so names are now quoted.

### Speaker / cab model

25. **Cone breakup looked nothing like a real guitar speaker, then calibration needed impossible paper**
    - *Symptom:* A big resonance near 1.2 kHz and a steep fall from 1.5 kHz; "breakup ripple" 51.8 dB peak-to-peak (500 Hz–5 kHz). The mesh did not converge: 24 elements were 16 dB off on the flat-plate test, and 48 elements were 47 dB off at the edge.
    - *Fixes along the way:* Two graded mesh segments with a node exactly at the dust-cap glue line, giving 96 elements within 0.04 dB of 384. Dust-cap radial and rotational stiffness added. Membrane check: 5584 Hz in both model and exact solution. Provisional paper values (h 0.6 mm, E 4 GPa, η 0.1) brought the ripple to 34 dB. The assistant **stopped and asked for data instead of tuning blind**; Dan said to use published data now and an IR loop later.
    - *Data:* Celestion doesn't publish T/S parameters, so the Eminence Legend 1258 was used. Its datasheet response chart was a **vector PDF**: `pdftocairo -svg`, axis frame and grid ticks, and the SPL and impedance paths were extracted exactly to CSV. T/S values came from eminence.com.
    - *Calibration:* Defaults gave 12.47 dB RMS error. The first fit gave 4.01 dB **but needed E = 7.9 GPa**, about 5× too stiff for real paper. With realistic bounds it gave 4.46 dB, with most parameters pinned at their bounds. *Root cause:* the circuit drove a fixed 32 g mass, but above breakup the outer cone decouples and the air load fades. *Fix:* `core/acoustic/Coupling.h`, where the cone's true neck impedance and air load feed back into the motor (the "force cut"). Along the way the Aarts–Janssen Struve H1 approximation was replaced by the exact series up to x=8, and a surround spring that wrongly carried paper loss was fixed. Rigid-cone check against an independent scipy calculation: 0.245 → 0.19 → **0.009 dB** (the remaining difference was the box; it vanished with an infinite baffle). The refit reached 1.12 dB with realistic paper. With the coil's lossy inductance fitted to the impedance curve: **SPL 2.16 dB RMS (80 Hz–6 kHz), impedance 0.67 dB**. The impedance bumps between 1.5 and 3.5 kHz were not fitted, but they land where the datasheet has them.
    - *Status:* The 1 kHz bump is about 4 dB low, and several fitted values sit at their bounds, so physics is still missing. **Where:** `sim/speaker/calibrate.py`, `sim/speaker/reference/`, `sim/speaker/README.md`.

27. **Name clash and include-order compile errors in the acoustics code.** `zc` redeclared in `Coupling.h`. The `minimumPhase` helper was placed above the `fft` it used. `Catalog.h` was missing its `Knobs.h` include.

28. **A concurrent session's edit was clobbered.** Replacing the whole `names()` line in `Catalog.h` dropped the other session's "Tokyo '68 fuzz (FY-2)" entry and left a duplicate `case 4`. It was caught by diffing the file before committing, and restored with the cab at index 5.

29. **Measured-mic response applied with zero phase put IR energy before t=0.** `cab_check` worst error jumped to **4.88 dB at 100 Hz**. Fix: minimum phase via the real cepstrum, giving 0.33 dB. `Radiation.h`.

30. **Screenshot for the public blog showed a private temp path.** The Bench's file label showed the scratchpad path with the session ID. It was painted over before publishing. Brand names were also removed from the post ("a popular American 12-inch guitar speaker").

31. **Circuit Bench live input "not working", pitch shift, odd 64 kHz rate, glitchy bypass**
    - "Not working": Dan simply hadn't seen the "File (loop)" source dropdown. Even so, a real bug was found: a guitar in input 2 never reached the circuit, which runs on channel 0.
    - Pitch shift and 64 kHz: the cause was not reproducible (no audio hardware on the box). Inferred cause: the PipeWire ALSA "default" device advertising odd rates, or a clock mismatch between devices. Fix: pin 48 kHz (or 44.1 kHz), and show the rate and devices in the stats line.
    - Glitchy bypass: summing duplicated stereo inputs doubled the level or comb-filtered. Fix: pick the single loudest channel, with hysteresis. A dropout counter was added, and `JUCE_JACK` enabled per target via a `CD_JACK` target property and generator expression (for `pw-jack`).
    - *Status:* **Not confirmed by Dan in the transcript.**

32. **Mic position and angle too tame**
    - *Symptom:* A 1 cm move changed 4–8 kHz by 0.6 dB, and a 30° tilt by 0.7 dB. Dan expected several dB.
    - *Tried:* The room was ruled out (reflections are about 30 dB down at 2.5 cm). A measured SM57 model was added: polar plots at six frequencies and the on-axis response extracted from the user guide's **vector PDF**, where all six curves sat in one SVG path that also contained the legend swatches, so points were filtered by ring radius. The model fits the datasheet to 0.76 dB RMS (polar) and 0.35 dB (response). A mic-face reflection was also added.
    - *Finding:* Real data says the mic's directivity and its face reflection are both small. Large moves already matched a published measurement (centre vs 10 cm: model −7.6 / −7.9 dB, measured −8 / −6 dB). Small moves stayed at 0.5 dB RMS.
    - *Root cause:* The **axisymmetric (perfectly round) cone**.
    - *Status:* **Open.** A non-axisymmetric cone with lobed modes is on the roadmap. The Sweetwater source returned 403 to both WebFetch and curl.

33. **Box volume and back opening hardly changed the low end (Dan's suspicion was right)**
    - *Bug 1:* `applyCircuit()` never updated the back-opening elements after build, so **the audio kept a closed box while the IR and the drawing assumed the new opening**. Fixed with `SpeakerBox::retune()`, a single path used by both build and live changes.
    - *Bug 2:* The open back's rear wave skipped the mic's own response (its rolloff and phase), so it reinforced the front instead of cancelling it. It now goes through the same mic model.
    - *Missing physics:* Baffle step (edge diffraction on a finite baffle) added.
    - Box volume itself was already correct: 20 → 150 l moves fc from 152 to 104 Hz and Q from 1.61 to 1.10, matching textbook values.
    - *Result:* Realtime output now matches the model's curve within about 1 dB. Commit `9c164fd`.

34. **CI: macOS and Windows failed on Cone.** Apple's libc++ has no `std::cyl_bessel_j`, so the project now has its own `core/acoustic/Bessel.h` (power series below 12, Hankel asymptotic above; within 3e-9 of scipy). MSVC has no `M_PI` without `_USE_MATH_DEFINES`, which is now defined for the whole core. `MicModels.h` was missing `<iterator>`. The tag was re-cut, giving `bae2b07`.

35. **Speaker large signal.** A 3-port `SpeakerMotor` device adds *corrections* to the linear circuit: Bl(x) from the overlap of an overhung coil with a tanh-fringed gap field (gap 7.9 mm, Xmax 0.48 mm from the datasheet), suspension k0(1+(x/Xs)²) with Xs = 2.5 mm (uncalibrated), and two-stage coil heating. The same corrections went into `speaker.cir` as B-sources (`nl=1`). Engine vs ngspice: THD within 0.2 % from 2 to 40 V (e.g. 23.08 vs 23.03 % at 20 V, 50 Hz). Heating: steady-state rise 55.58 K vs a calculated 55.56 K; current drop 0.90 dB vs 0.96 dB from an independent calculation. A debugging detour (a "no device" comparison build that segfaulted and had bad arguments) ended once the compare showed the linear results unchanged. Cost went from 91 to 295 ns per sample. A tabulated Bl and a new `Device::linearWithinSample()` (one Newton step when every device is linear in the sample's unknowns) brought it to 201 ns, and the baseline was updated deliberately.

### Performance and CPU

36. **CPU regression tests.** `tools/perf_bench.cpp` measures thread CPU time, best of 5 runs, normalized by a reference FFT workload, and also counts Newton iterations, which are deterministic. `tests/perf_check.py` fails at +25 % CPU or +2 % iterations, with per-machine baselines in `tests/perf_baseline.json`. These run as ctest tests `cab_accuracy` (1 dB limit) and `cpu_regression`, and in CI via `.github/workflows/tests.yml`. Proven by injecting regressions (cone mesh 160, reltol 1e-5), which were caught at +56 % and +48 %. **A CI baseline was never recorded**, so in CI the test only reports numbers.

37. **25 % CPU in Circuit Bench with the speaker cab**
    - Dan's figure was real. `bench_cpu` reproduced 18–22 % at 96 kHz and 73 % (worst callback 130 %) at 192 kHz.
    - *Root causes:* (a) the Bench oversampled the *linear* cab 4×; (b) convolution cost grew with the square of the rate, because the IR length was rounded up to a power of two and the block size was fixed.
    - *Fix:* Each circuit declares its own oversampling (`oversamplingLog2()`). The IR is trimmed to 45 ms with a fade. The convolver block scales with the rate (constant 1.33 ms latency). Result: 0.4 / 0.8 / 1.5 % at 48 / 96 / 192 kHz, with accuracy unchanged (0.24 dB).

38. **Bench and plugin output checks reported ~160–185 dBFS (both sessions).** int32 WAVs were analysed without normalization. This was an analysis-script bug, not a plugin bug.

39. **Click when switching circuits (FY-2 session)**
    - *Symptom:* Automating Fuzz Face → FY-2 produced a burst of samples at ±1.0 (peak +6 dBFS).
    - *Tried:* Tested the warm start in isolation and it was clean (it moves from 3.755/4.892 V to the DC point 3.595/1.021 V).
    - *Root cause:* Each circuit's output scale was applied *after* the downsampler, so the jump in level rang the oversampling filters.
    - *Fix:* Apply the scale inside the oversampled loop. Switching is now click-free (largest step 0.73 vs 0.87 elsewhere) and can be automated. `core/engine/FuzzEngine.cpp`.

### Process, tooling and release

40. **Moving the project folder and keeping Claude Code history.** `~/.claude/move-project.py` moves the folder, moves the `~/.claude/projects/<munged>` directories, rewrites the old path in 88 transcript files and in `history.jsonl`, copies the `~/.claude.json` entry, and leaves symlinks behind so the running session keeps working. A clean rebuild was needed because CMake had baked in the old absolute paths. The first `-j24` build stopped with "subcommand failed" and no error shown; a `-j8` rebuild succeeded (inferred: a transient or memory problem). **The `--final` cleanup was never run**, so symlinks remain at `~/sandbox/punkfab/circuit-decimator` and the old projects directories. This script is the likely origin of the later `move-project` skill (inferred).

41. **Schematic hunting while the PDF was already in the repo (FY-2 session).** About 9 minutes went into web searching: aionfx PDF unreadable by WebFetch, freestompboxes 403, GGG only links to PDFs, elektrotanya behind a form. Dan: "I put the schematic under reference/ … I don't know why it was taking you so long." It was at `products/phys-fuzz/reference/shin-ei_fy2_fuzzmaster.pdf` (the 2002 Castledine tracing). Saved as feedback memory `reference-schematics.md`: check `products/<product>/reference/` first. The Fuzz Face deck itself has **no recorded schematic source**.

42. **The snapshot tool parsed `circuit=Tokyo '68` as 0**, so the committed screenshot showed "London '66". It was regenerated with `circuit=1` and the commit amended (`e42feb0`).

43. **CI: Linux was missing JUCE 9 dependencies.** `fatal error: X11/extensions/XInput2.h`. Fixed by adding `libxi-dev libegl-dev`, per JUCE's `docs/Linux Dependencies.md`. A `platforms` input was added for manual runs, because macOS minutes cost 10× on a private repo. "release job skipped" is expected without a tag. Node 20 deprecation warnings were noted.

44. **macOS signing from Linux.** The "Developer ID Application" certificate is required; Apple Distribution certificates only work for the App Store. Steps: openssl CSR into `~/.secrets/apple/`, then `pkcs12 -export -legacy` (the macOS keychain rejects the newer default format), then five repo secrets. The run log printing "UNSIGNED" was the echoed script source, not a warning. Notarization returned Accepted and stapling succeeded.

45. **`gh repo edit --visibility public --accept-visibility-change-consequences`** was an unknown flag on the installed `gh`, and the first attempt failed silently in a pipeline. Fixed with `gh api -X PATCH repos/… -f visibility=public`. A secret scan of the tree and history ran first.

46. **Blog 404s on audiodestrukt.com.** `/blog` is served without a trailing slash and without a redirect, so the index's relative `posts/…` links resolved to `/posts/…`. The same thing had happened earlier with `/opendeck`. The generator now emits absolute links (`50c692e`). The assistant first said the CDN in front was only DigitalOcean's. Dan uses his own Cloudflare zone, which caches HTML with the origin's `s-maxage=86400`, including 404s. Recommended: purge, plus a cache rule bypassing HTML. Analytics: the Cloudflare beacon was added to the generator and the homepage, but not to the OpenDeck pages, whose privacy text promises no analytics.

47. **Trademarks.** Player-facing names avoid marks: London '66 (Fuzz Face), Tokyo '68 (FY-2), Opto (not LA-2A), and Cone (the calibrated speaker isn't named). Saved as memory `circuit-naming`. Iron and Opto signing could not be re-verified on 2026-09-28 because their CI logs had expired.

## Decisions and reversals

- **ngspice as the reference, never the engine** (2026-09-25 08:23). It held for the whole project, and it was extended: every model gets an exact reference (an ngspice deck, a closed-form formula, scipy, or a published datasheet).
- **Dense MNA solver → nodal DK** (18:16). MNA was kept as the readable reference and DC solver. **Hand-built solvers → general netlist engine** (2026-09-26 04:36). The hand-built solvers became its regression tests.
- **Bake presets into the plugin, then reversed.** `search/bake_presets.py` was written and then deleted right away; the assistant said to wait until Dan picked favourites. Instead, the Bench auto-loads the newest search run.
- **Transformer before the general engine, and before tubes** (Dan's pick through AskUserQuestion). Tubes as Koren curve models, "not deep physics". Power supplies deferred to a separate reusable module. Daisy/Teensy dropped ("I don't have those boards").
- **New circuits in Circuit Bench, not in the Circuit Decimator plugin** (AskUserQuestion), because a plugin's parameter list has to stay fixed.
- **Cab architecture: hybrid physics → IR** (AskUserQuestion), split at the cone's piston velocity, and changed to the "force cut" once calibration showed the motor has to see the cone's true impedance. The cab started linear, so it runs with no oversampling; it went nonlinear later, and **still runs without oversampling** (a per-circuit hook allows 2× if needed).
- **Stop and ask for data instead of tuning the cone blind** (2026-09-26 16:31). Published datasheet now, real-IR tuning loop later. The IR loop never happened in these sessions.
- **The speaker's 10" option is a size knob on the calibrated 12"**, not a separately calibrated 10" speaker.
- **Repo private → public** (2026-09-26 17:01) so the blog download links work. There is no license, so the code is all rights reserved, and the site says "Free Download", not open source. The FY-2 reference PDF (someone else's drawing) is in public history; removing it was offered and not done.
- **Selling via Curiate, US-only, Stripe, Dan or Curiate as merchant of record**: decided, never implemented.

## Outcome

- Four plugins released with signed and notarized macOS, Windows and Linux builds: **Phys Fuzz 0.2.0, Iron 0.1.0, Opto 0.1.0, Cone 0.1.0**. They are public on the audiodestrukt.com "Physical Models" section. Cone 0.1.0 predates the nonlinear speaker; a `cone-v0.2.0` tag was suggested.
- Engine and verification: DK and netlist engine, Jiles–Atherton cores, Koren triode and pentode, T4 cell, and a loudspeaker FE/acoustics model, each with a `sim/*/compare.py` or check tool and a README of verified numbers. There is also a living log of learnings and traps, `docs/realtime-simulation-notes.md`, plus CPU regression tests in ctest and CI.
- Open: the CI CPU baseline; the non-axisymmetric cone (needed for mic sensitivity and speaker damage); the real-IR tuning loop; Opto's CPU cost; the Curiate storefront; the move script's `--final` step.
- **Feedback to circuit-skills: none.** The last skill commit before 2026-10-01 is `8e75d2a` (2026-07-01), and nothing in circuit-skills mentions this project's techniques. **The ngspice lessons here are NOT in the circuit-sim skill:**
  - concurrent ngspice runs and OpenMP nondeterminism (run sequentially, `OMP_NUM_THREADS=1`);
  - fading in the stimulus for hysteretic cores;
  - the F-source polarity of an E/F ideal transformer;
  - series R for shunt inductors against an E-source loop;
  - `.func` and brace-expression `.tran` failures;
  - extracting reference curves from vector datasheet PDFs;
  - matched linear references in A/B comparisons;
  - "deck is the spec, realtime model checked against it".

## Pointers

- Repo: `/home/dan/sandbox/audiodestrukt/circuit-decimator` (`~/sandbox/punkfab/circuit-decimator` is a symlink to it). [github.com/audiodestrukt/circuit-decimator](https://github.com/audiodestrukt/circuit-decimator).
- Briefs: `docs/briefs/2026-09-26-transformer.md`, `2026-09-26-speaker-cab.md`, `2026-09-27-simulation-roadmap.md`. Learnings log: `docs/realtime-simulation-notes.md`.
- Verification: `sim/fuzzface.cir` + `sim/compare.py`; `sim/transformer/`; `sim/tubepre/`; `sim/tubeout/`; `sim/la2a/`; `sim/shinei/`; `sim/speaker/` (`compare.py`, `radiation.py`, `cone.py`, `breakup.py`, `calibrate.py`, `nonlinear.py`, `reference/`); `tools/net_selftest.cpp`, `cab_check.cpp`, `perf_bench.cpp`; `tests/`.
- Engine: `core/circuit/{FuzzFace,FuzzFaceDK,Circuit,Devices,Transformer}.h`, `core/circuit/circuits/*.h`, `core/acoustic/*.h`.
- Project memory (Claude Code): `~/.claude/projects/-home-dan-sandbox-audiodestrukt-circuit-decimator/memory/` (`ngspice-realtime-budget`, `reference-schematics`, `circuit-naming`, `realtime-learnings-log`, `audiodestrukt-site`, `product-direction`).
- Related history: `docs/history/projects/2026-09-29-ir-harness.md` (it measured this project's DK solver and added `ff_render --automation`, `f6ffcbc`).
