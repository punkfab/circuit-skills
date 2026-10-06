# PCBWorld D3C · d3c-v3

10 boards · backends `freerouting,freerouting:2.1.0,tracemaker,srj:outer,srj:all` · 300 s per backend · {'circuit_skills': '20d783e', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 0.90 | 0.94 | 0.0 | 1391 | 44.0 | – | 10/10 |
| freerouting | 0.30 | 0.98 | 0.0 | 1422 | 30.6 | 13.8 | 10/10 |
| freerouting:2.1.0 | 0.30 | 0.69 | 0.1 | 1297 | 23.1 | 10.1 | 7/10 |
| srj:all | 0.00 | 1.00 | 177.1 | 1383 | 77.1 | 36.7 | 10/10 |
| srj:outer | 0.00 | 1.00 | 177.1 | 1383 | 77.1 | 36.1 | 10/10 |
| tracemaker | 0.90 | 0.90 | 0.0 | 1358 | 47.6 | 181.9 | 9/10 |
| **circuit-skills (best of all backends)** | 0.90 | 1.00 | 46.5 | 1391 | 45.9 | 380.7 | 10/10 |

Clean boards by the backend that produced the kept candidate: tracemaker 5, freerouting:2.1.0 3, freerouting 1

## Does the placement score predict it?

9 boards came back clean and 1 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 1.00 | 1.26 | 2.54 |
| congestion_p95 | 1.00 | 0.43 | 1.02 |
| over_capacity_pct | 1.00 | 0.40 | 5.30 |
| crossings | 0.67 | 127.56 | 161.00 |
| escape_ratio | 1.00 | 0.04 | 0.35 |
| signal_nets | 0.83 | 43.56 | 52.00 |
| mst_mm | 0.00 | 1218.67 | 451.90 |

route_eval diagnosis vs outcome: hand-finish: 4 clean / 1 not, order-ready: 5 clean / 0 not

## Boards

| board | u0 | freerouting | freerouting:2.1.0 | srj:all | srj:outer | tracemaker | circuit-skills |
|---|---|---|---|---|---|---|---|
| 0400_laptimer58_Chickadee | 79 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 24 drv | 1.00 · 24 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0423_induction-hob_temperature-sender | 86 | 0.98 · 0 drv | 0.94 · 0 drv | 1.00 · 21 drv | 1.00 · 21 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0448_uedaino_uedaino | 96 | 0.99 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 176 drv | 1.00 · 177 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0473_data-manager_data-manager | 92 | 0.99 · 0 drv | 0.97 · 0 drv | 1.00 · 31 drv | 1.00 · 31 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0496_kitspace_f-91w | 83 | 0.94 · 0 drv | failed | 1.00 · 465 drv | 1.00 · 469 drv | failed | 1.00 · 465 drv (srj:all) |
| 0520_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD_negative | 85 | 0.98 · 0 drv | 0.99 · 0 drv | 1.00 · 124 drv | 1.00 · 124 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0546_ozinverter_ozinverterkicad | 144 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | 1.00 · 120 drv | 1.00 · 121 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting:2.1.0) |
| 0571_Brushless_ESC_Brushless_ESC | 162 | 0.97 · 0 drv | 0.98 · 1 drv | 0.97 · 248 drv | 0.97 · 246 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0599_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD | 141 | 0.99 · 0 drv | failed | 1.00 · 327 drv | 1.00 · 326 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (tracemaker) |
| 0626_TOBS_HybridChargeController | 210 | ✓ 1.00 · 0 drv | failed | 1.00 · 235 drv | 1.00 · 232 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
