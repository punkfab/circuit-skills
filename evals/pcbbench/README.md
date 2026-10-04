# PCB-Bench Task 1 as a circuit-skills eval

[PCB-Bench](https://github.com/digailab/PCB-Bench) (Li et al., *PCB-Bench: Benchmarking LLMs for
Printed Circuit Board Placement and Routing*, ICLR 2026,
[OpenReview](https://openreview.net/forum?id=Q5QLu7XTWx)) measures what language models **know**
about PCB placement and routing. Nothing in it routes a board. It has three tasks:

| task | what it asks | relevant to circuit-skills? |
|---|---|---|
| 1. Text QA / choice | 1,848 five-option questions (plus free-form versions) on placement and routing practice: signal integrity, EMI/EMC, power planning, differential pairs, DFM, thermal, stack-up | **yes**: does loading the skill change the answers? |
| 2. Image + text | ~500 questions about PCB screenshots, e.g. "how many nets are routed here?" | no: circuit-skills reads the board file, not a picture of it |
| 3. Design understanding | describe 174 OSHWHub boards from an EDA screenshot | no |

`run_task1.py` runs Task 1's multiple-choice questions on the same model under two conditions:

- **baseline:** the paper's own English system prompt.
- **skill:** the same prompt plus `pcb-layout/SKILL.md`, as an agent would have it loaded.

It also reports which questions the skill fixed and which it broke. That's the useful output: a
skill that teaches workflow should not make the model worse at the fundamentals, and any question
it breaks points at a line in the skill worth re-reading.

```bash
git clone --depth 1 https://github.com/digailab/PCB-Bench /tmp/PCB-Bench
python3 evals/pcbbench/run_task1.py --data /tmp/PCB-Bench               # both conditions, ~$8 on Opus 5.5
python3 evals/pcbbench/run_task1.py --data /tmp/PCB-Bench --limit 50    # a quick check
python3 evals/pcbbench/run_task1.py --summarize task1-v1
```

How calls are made:

- Every call goes through `claude -p --safe-mode`, with no tools. No CLAUDE.md, memory, hooks, plugins or MCP servers load, so the baseline is the bare model. A plain `claude -p` call in a configured setup carries ~100k tokens of the user's own context, which would contaminate the baseline.
- Questions go 25 per call, and the model answers with a JSON object of letters. The paper sends one question per call.
- A run with the same `--run` name resumes.

## Caveats

- **The scale is nearly saturated.** In the paper, frontier models score 86–99%. Claude Opus 4.1 is best or tied best on all four choice-question columns.
- **The macro/micro split is our assumption.** The paper reports placement/routing × macro/micro. The repository's files are named Easy/Hard, and we map Easy to macro and Hard to micro. The repo doesn't state the mapping.
- **The answer key is one view of practice.** It's expert-written, but many questions have defensible alternatives. Read the "broken by the skill" list before concluding the skill is wrong.
- **Free-form QA isn't run.** The paper scores it with BERTScore and SBERT similarity to a reference answer. Those reward wording overlap, not correctness, and score small and frontier models alike (~0.80).

## Results (2026-10-04, Claude Opus 5.5)

| | placement macro | placement micro | routing macro | routing micro | all 1,848 |
|---|---|---|---|---|---|
| Opus 5.5 alone | 92.74 | 96.91 | 99.16 | 95.68 | **96.37** |
| Opus 5.5 + pcb-layout skill | 93.30 | 97.62 | 99.16 | 96.16 | **96.97** |
| paper's best (Claude Opus 4.1) | 93.30 | 94.35 | 99.16 | 92.32 | – |

- **Fixes and breaks.** The skill fixed 11 questions and broke none.
- **The baseline is stable.** A second baseline run (`results/task1-v1-baseline2`) scored 96.37% again, flipping 1 question each way. All 11 fixes are on questions it gets wrong both times, so the gain is small but real: 11 of 66 consistent misses.
- **What the skill fixes is mostly a reflex.** In 9 of the 11, the bare model rejected every option and chose "E: none of the above" on a placement question ("how to lay out PHY, magnetics and MAC?"). With the skill loaded, it committed to the practical answer the key expects. The other two are the NTC divider placement and the P/N crossover rules for differential pairs.
- **What's left is mostly disagreement with the key.** 37 of the baseline's 67 misses are "none of the above" picks where the key is a specific option; the key is never E among the misses. So the remaining ~3% is mostly the model being stricter than the answer key, not missing knowledge.
- **Cost:** baseline $3.84, skill $4.20, as reported by `claude -p`, with prompt caching.

What it means for circuit-skills: the skill doesn't degrade the model's PCB fundamentals, and it nudges answers toward committing to a practical layout. But this benchmark can't see what the skill is for, which is producing and verifying real boards. That is what `evals/pcbworld` measures.
