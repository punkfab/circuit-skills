# PCB-Bench Task 1 (multiple choice) · task1-v1

Model `claude-opus-5-5` via `claude -p --safe-mode`, 25 questions per call. Questions: 1848 per condition.

| condition | placement-macro | placement-micro | routing-macro | routing-micro | all |
|---|---|---|---|---|---|
| baseline | 92.74 (179) | 96.91 (1133) | 99.16 (119) | 95.68 (417) | **96.37** |
| skill | 93.30 (179) | 97.62 (1133) | 99.16 (119) | 96.16 (417) | **96.97** |

PCB-Bench paper, Table 2 (CQ accuracy %, one question per call):

| model | placement-macro | placement-micro | routing-macro | routing-micro |
|---|---|---|---|---|
| GPT-4o | 92.74 | 93.82 | 98.32 | 91.13 |
| GPT-5 | 88.27 | 91.79 | 99.16 | 90.17 |
| Claude-Opus-4.1 | 93.30 | 94.35 | 99.16 | 92.32 |
| Gemini-2.5-Pro | 86.03 | 90.82 | 98.31 | 88.73 |
| DeepSeek-V3.1-671B | 92.74 | 93.64 | 97.48 | 88.49 |
| Qwen2.5-7B-Instruct | 84.36 | 86.85 | 94.12 | 82.50 |

Skill vs baseline on the same 1848 questions: **11 fixed, 0 broken**.

### Fixed by the skill

- Where should voltage divider resistors for NTC thermistors be placed? (key C; baseline A, skill C) — `Text-Text_QA-CQ_Layout_Easy_DFM-Practical-Concerns_44_scq`
- In delivery robot boards, how to layout planner, sensors, and drivers? (key A; baseline E, skill A) — `Text-Text_QA-CQ_Layout_Hard_Component-Placement-Rules_Interface-and-Connector-Placement_198_scq`
- In hybrid vehicle controllers, how to layout isolators, CAN, and BMS? (key D; baseline E, skill D) — `Text-Text_QA-CQ_Layout_Hard_Component-Placement-Rules_Interface-and-Connector-Placement_198_scq`
- In Ethernet gateway boards, how to layout PHY, magnetics, and MAC? (key A; baseline E, skill A) — `Text-Text_QA-CQ_Layout_Hard_Component-Placement-Rules_Interface-and-Connector-Placement_198_scq`
- In precision ADC boards, how to layout analog ref, digital IO, and isolation? (key A; baseline E, skill A) — `Text-Text_QA-CQ_Layout_Hard_Component-Placement-Rules_Interface-and-Connector-Placement_198_scq`
- In RS485 boards, how to layout transceiver, terminator, and CMRR components? (key A; baseline E, skill A) — `Text-Text_QA-CQ_Layout_Hard_Component-Placement-Rules_Interface-and-Connector-Placement_198_scq`
- In satellite downlink modules, how to layout LNA, pre-selector, and PLL LO? (key B; baseline E, skill B) — `Text-Text_QA_Layout_Hard_Component-Placement-Rules_Critical-Component-Placement_111_scq`
- In emergency-shutdown control boards, how to layout power-fail detect, cutoff MOS, and backup caps? (key B; baseline E, skill B) — `Text-Text_QA_Layout_Hard_Component-Placement-Rules_Spacing,-Clearance-and-Orientation_120_scq`
- How to layout multi-layer flex PCBs to reduce bending impact on signal integrity? (key B; baseline E, skill B) — `Text-Text_QA_Layout_Hard_Stack-up-and-Layer-Design_26_scq`
- What are the consequences of reversing the routing order of differential pairs (i.e., P/N signal crossovers)? In what scenarios is crossover allowed? (key D; baseline B, skill D) — `Text-Text_QA_Routing_Hard_High-Speed-Differential-Pairs_40_scq`
- How to route control boards for Class B EMC compliance in home appliances? (key C; baseline E, skill C) — `Text-Text_QA_Routing_Hard_High-speed-Layout-Challenges_111_scq`

Reported cost: baseline $3.84, skill $4.20

Easy files are counted as macro-level and Hard as micro-level (the repo does not state the mapping).
