# PCB-Bench Task 1 (multiple choice) · task1-v1-baseline2

Model `claude-opus-5-5` via `claude -p --safe-mode`, 25 questions per call. Questions: 1848 per condition.

| condition | placement-macro | placement-micro | routing-macro | routing-micro | all |
|---|---|---|---|---|---|
| baseline | 92.18 (179) | 96.91 (1133) | 99.16 (119) | 95.92 (417) | **96.37** |

PCB-Bench paper, Table 2 (CQ accuracy %, one question per call):

| model | placement-macro | placement-micro | routing-macro | routing-micro |
|---|---|---|---|---|
| GPT-4o | 92.74 | 93.82 | 98.32 | 91.13 |
| GPT-5 | 88.27 | 91.79 | 99.16 | 90.17 |
| Claude-Opus-4.1 | 93.30 | 94.35 | 99.16 | 92.32 |
| Gemini-2.5-Pro | 86.03 | 90.82 | 98.31 | 88.73 |
| DeepSeek-V3.1-671B | 92.74 | 93.64 | 97.48 | 88.49 |
| Qwen2.5-7B-Instruct | 84.36 | 86.85 | 94.12 | 82.50 |

Reported cost: baseline $0.39

Easy files are counted as macro-level and Hard as micro-level (the repo does not state the mapping).
