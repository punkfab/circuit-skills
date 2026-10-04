# PCBWorld D3B · d3b-v2

10 boards · backends `freerouting,srj:outer,srj:all` · 120 s per backend · {'circuit_skills': '8c6d487', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 1.00 | 1.00 | 0.0 | 570 | 6.7 | – | 10/10 |
| freerouting | 0.70 | 0.97 | 0.0 | 511 | 3.8 | 4.5 | 10/10 |
| srj:all | 0.00 | 1.00 | 46.2 | 504 | 11.9 | 6.8 | 10/10 |
| srj:outer | 0.00 | 1.00 | 46.8 | 504 | 11.9 | 6.8 | 10/10 |
| **circuit-skills (best of all backends)** | 0.70 | 1.00 | 15.3 | 524 | 6.0 | 18.0 | 10/10 |

PCBWorld paper, Table 3, D3B (@5: best of five rollouts; Freerouting and PPO are 4-seed means):

| method | CP ↑ | Rout. ↑ | time s |
|---|---|---|---|
| Reference | 1.00 | 1.00 | – |
| Freerouting 2.1.0 | 0.78 | 1.00 | 9.9 |
| KiCadRoutingTools | 0.20 | 0.86 | 3.3 |
| OrthoRoute | 0.00 | 0.44 | 9.3 |
| GPT-5.4 agent | 0.00 | 0.62 | 865.8 |
| GPT-5.4-mini agent | 0.00 | 0.61 | 422.1 |
| PPO | 0.45 | 0.85 | 10.8 |
| PPO (w/o finish) | 0.42 | 0.87 | 14.4 |

Clean boards by the backend that produced the kept candidate: freerouting 7

## Does the placement score predict it?

7 boards came back clean and 3 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 1.00 | 0.90 | 4.11 |
| congestion_p95 | 0.81 | 0.31 | 0.60 |
| over_capacity_pct | 1.00 | 0.03 | 1.50 |
| crossings | 0.05 | 32.43 | 12.67 |
| escape_ratio | 0.62 | 0.04 | 0.10 |
| signal_nets | 0.29 | 18.00 | 14.67 |
| mst_mm | 0.29 | 480.96 | 378.27 |

route_eval diagnosis vs outcome: hand-finish: 1 clean / 3 not, order-ready: 6 clean / 0 not

## Boards

| board | u0 | freerouting | srj:all | srj:outer | circuit-skills |
|---|---|---|---|---|---|
| 0144_ottawa-badges-2016_ottawa-badge-tagger-2016 | 30 | ✓ 1.00 · 0 drv | 1.00 · 54 drv | 1.00 · 54 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0174_sensorboard_DiffIR | 32 | ✓ 1.00 · 0 drv | 1.00 · 18 drv | 1.00 · 18 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0113_maytal_Maytal | 20 | ✓ 1.00 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0260_NiMH-Charger_NiMH Charger | 45 | ✓ 1.00 · 0 drv | 1.00 · 111 drv | 1.00 · 116 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0203_MOD-MPU9150_mod-mpu9150 | 38 | 0.87 · 0 drv | 0.97 · 42 drv | 0.97 · 43 drv | 0.97 · 42 drv (srj:all) |
| 0232_ATtiny461Breakout_ATTiny461DevBoard | 38 | 0.95 · 0 drv | 1.00 · 33 drv | 1.00 · 33 drv | 1.00 · 33 drv (srj:outer) |
| 0316_kicad-workshop_fancyboard | 55 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0288_raspberrypi-3-usb-hub_usb_hub | 56 | 0.93 · 0 drv | 1.00 · 78 drv | 1.00 · 78 drv | 1.00 · 78 drv (srj:outer) |
| 0344_mavbridge_mavbridge | 64 | ✓ 1.00 · 0 drv | 1.00 · 73 drv | 1.00 · 73 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0376_cat-trainer_teensy_base_pcb | 67 | ✓ 1.00 · 0 drv | 1.00 · 34 drv | 1.00 · 34 drv | ✓ 1.00 · 0 drv (freerouting) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
