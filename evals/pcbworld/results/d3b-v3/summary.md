# PCBWorld D3B · d3b-v3

10 boards · backends `freerouting,freerouting:2.1.0,tracemaker,srj:outer,srj:all` · 120 s per backend · {'circuit_skills': '20d783e', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 1.00 | 1.00 | 0.0 | 570 | 6.7 | – | 10/10 |
| freerouting | 0.60 | 0.95 | 0.0 | 487 | 4.4 | 4.7 | 10/10 |
| freerouting:2.1.0 | 0.80 | 0.99 | 0.0 | 538 | 3.8 | 14.6 | 10/10 |
| srj:all | 0.00 | 1.00 | 49.3 | 504 | 11.9 | 7.5 | 10/10 |
| srj:outer | 0.00 | 1.00 | 49.3 | 504 | 11.9 | 7.5 | 10/10 |
| tracemaker | 1.00 | 1.00 | 0.0 | 505 | 8.8 | 22.3 | 10/10 |
| **circuit-skills (best of all backends)** | 1.00 | 1.00 | 0.0 | 519 | 5.5 | 56.6 | 10/10 |

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

Clean boards by the backend that produced the kept candidate: tracemaker 5, freerouting:2.1.0 4, freerouting 1

## Does the placement score predict it?

10 boards came back clean and 0 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | – | 1.86 | – |
| congestion_p95 | – | 0.40 | – |
| over_capacity_pct | – | 0.47 | – |
| crossings | – | 26.50 | – |
| escape_ratio | – | 0.05 | – |
| signal_nets | – | 17.00 | – |
| mst_mm | – | 450.15 | – |

route_eval diagnosis vs outcome: order-ready: 10 clean / 0 not

## Boards

| board | u0 | freerouting | freerouting:2.1.0 | srj:all | srj:outer | tracemaker | circuit-skills |
|---|---|---|---|---|---|---|---|
| 0113_maytal_Maytal | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 14 drv | 1.00 · 13 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0144_ottawa-badges-2016_ottawa-badge-tagger-2016 | 30 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 53 drv | 1.00 · 53 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0174_sensorboard_DiffIR | 32 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 14 drv | 1.00 · 15 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0203_MOD-MPU9150_mod-mpu9150 | 38 | 0.89 · 0 drv | 0.95 · 0 drv | 0.97 · 53 drv | 0.97 · 54 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0232_ATtiny461Breakout_ATTiny461DevBoard | 38 | 0.92 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 33 drv | 1.00 · 33 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0260_NiMH-Charger_NiMH Charger | 45 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 116 drv | 1.00 · 115 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0288_raspberrypi-3-usb-hub_usb_hub | 56 | 0.80 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 70 drv | 1.00 · 70 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0316_kicad-workshop_fancyboard | 55 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0344_mavbridge_mavbridge | 64 | 0.91 · 0 drv | 0.97 · 0 drv | 1.00 · 79 drv | 1.00 · 80 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0376_cat-trainer_teensy_base_pcb | 67 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 55 drv | 1.00 · 54 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
