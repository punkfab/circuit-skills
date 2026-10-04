# PCBWorld D3 as a circuit-skills eval

[PCBWorld](https://github.com/LGAI-Research/PCBWorld) (LG AI Research, KDD 2026 Workshop on
Evaluation and Trustworthiness of Agentic AI, [arXiv:2607.05915](https://arxiv.org/abs/2607.05915))
is a routing benchmark built on KiCad. Its D3 set is 678 real open-source boards from
[PCBench](https://github.com/PCBench/PCBench). Every part stays where the designer put it, the
routing is stripped, and a router has to put it back. Each result is scored by KiCad DRC against
the board's own design rules.

That is the job `pcb-layout/scripts/route_eval.py` does on our own boards. `run_d3.py` sends every
D3 board through `route_eval`, which runs every backend we have:

- Freerouting 2.2.4, through KiCad's own Specctra export and import (`route_kicad_dsn.py`);
- the tscircuit capacity autorouter on two layers (`srj:outer`);
- the capacity autorouter on all layers (`srj:all`).

Each result is scored the way the paper scores its baselines.

## Metrics

| metric | meaning |
|---|---|
| **CP** | Clean pass: fully connected *and* zero error-level DRC violations. The headline number, "ready to fabricate". |
| Rout. | 1 − open ratsnest edges ÷ the bare board's open edges. 0 when bare, 1 when connected. |
| DRV | Error-level DRC violations. |
| WL, vias | Routed copper in mm, and via count. |
| time | Routing seconds. |

Rows:

- **circuit-skills** is the best candidate per board: clean pass first, then routability, DRV, vias, length. The paper does the same over five rollouts.
- **reference** is the designer's own routing scored the same way. The paper's Reference row is CP 1.00; ours checks the scorer.

Each board also gets a placement score (`placement_score.py`) of its bare board, and `route_eval`'s
hand-finish-or-re-place diagnosis. The summary reports how well each placement metric separates
boards that came back clean from boards that did not (AUC). That makes D3 a calibration set for
the diagnosis, not just a leaderboard.

## Build the board set (once, ~25 min, 3.3 GB)

PCBench boards aren't redistributed, by PCBench or PCBWorld or us. You build them with PCBWorld's
own chain. A stock KiCad 9 (`kicad-cli` plus the system `pcbnew` module) is enough; their GPL
engine build isn't needed:

```bash
git clone --depth 1 https://github.com/LGAI-Research/PCBWorld
cd PCBWorld
export PCBWORLD_DATA_ROOT=$HOME/.cache/circuit-skills/pcbworld KICAD_CLI=/usr/bin/kicad-cli PCBNEW_PYTHON=/usr/bin/python3
bash tools/quickstart/prepare_pcbench.sh --workers 12
```

With KiCad 9.0.8 this gives the paper's 679 boards (678 in the split json). One difference: a stock
`kicad-cli` caps DRC reports at 199 per type. On the ~15 boards that hit the cap, the guide-board
track widths can differ from the paper's (PCBWorld's prep README explains this).

## Run

```bash
python3 evals/pcbworld/run_d3.py --split d3a                      # D3-A test: 99 small boards
python3 evals/pcbworld/run_d3.py --split d3b --time 120           # D3-B test: 10 medium boards
python3 evals/pcbworld/run_d3.py --split d3c --time 300           # D3-C test: 10 large boards
python3 evals/pcbworld/run_d3.py --boards 0018,0100 --run try     # just these boards
python3 evals/pcbworld/run_d3.py --summarize d3a-v1               # rebuild a summary
```

- `--backends` takes any `route_eval` list (default `freerouting,srj:outer,srj:all`).
- `--jobs` sets how many boards route at once (default 3). Freerouting is multi-threaded and takes about 0.5 GB per board.
- A run with the same `--run` name resumes where it stopped.
- Candidates and logs go to `~/.cache/circuit-skills/pcbworld/runs/<run>/`.
- `per_board.jsonl`, `meta.json` and `summary.md` go to `results/<run>/` here, and are committed.

## How this differs from the paper's protocol

- **Scoring.** We use stock `kicad-cli pcb drc --severity-error` with each board's own `.kicad_pro`. The paper uses its engine's DRC (KiCad 9.0.8 with uncapped reports), with the same rules and severities.
- **Runs per board.** We run each backend once per board. The paper keeps the best of five rollouts (@5) and averages Freerouting and PPO over four seeds. The best-of-backends row is our analogue of @5.
- **Freerouting version.** We use 2.2.4; the paper used 2.1.0.
- **Routability.** We compute it from KiCad's unconnected-item count (ratsnest edges = Σ(groups − 1) per net). That is the paper's definition, but we didn't use its code.
- **Not reported.** The potential gain Φ (a weighted reward) isn't computed.

`d3.json` is vendored from PCBWorld (BSD-3-Clause, `LICENSE.PCBWorld`), commit `b3d62f5`.

## Results

See `results/`. Each run's `summary.md` has the method table, the paper's Table 3 for the same
split, which backend produced each clean board, the placement-score AUCs, and a per-board table.
