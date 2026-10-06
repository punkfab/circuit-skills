# PCBWorld D3C · d3c-v2+tracemaker

10 boards · backends `freerouting,srj:outer,srj:all` · 300 s per backend · {'circuit_skills': '8c6d487', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 0.90 | 0.94 | 0.0 | 1391 | 44.0 | – | 10/10 |
| freerouting | 0.20 | 0.98 | 0.0 | 1394 | 23.5 | 10.0 | 10/10 |
| srj:all | 0.00 | 0.90 | 168.9 | 1344 | 74.1 | 19.2 | 9/10 |
| srj:outer | 0.00 | 1.00 | 185.8 | 1388 | 76.0 | 19.6 | 10/10 |
| tracemaker | 0.90 | 0.99 | 0.0 | 1271 | 49.9 | 58.1 | 10/10 |
| **circuit-skills (best of all backends)** | 0.20 | 1.00 | 135.6 | 1394 | 62.0 | 47.0 | 10/10 |

Clean boards by the backend that produced the kept candidate: freerouting 2

## Does the placement score predict it?

2 boards came back clean and 8 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 0.69 | 1.02 | 1.48 |
| congestion_p95 | 0.75 | 0.29 | 0.54 |
| over_capacity_pct | 0.66 | 0.10 | 1.09 |
| crossings | 0.75 | 91.00 | 140.88 |
| escape_ratio | 0.69 | 0.00 | 0.09 |
| signal_nets | 0.50 | 43.00 | 44.75 |
| mst_mm | 0.25 | 1478.55 | 1057.85 |

route_eval diagnosis vs outcome: hand-finish: 0 clean / 8 not, order-ready: 2 clean / 0 not

## Boards

| board | u0 | freerouting | srj:all | srj:outer | tracemaker | circuit-skills |
|---|---|---|---|---|---|---|
| 0423_induction-hob_temperature-sender | 86 | 0.98 · 0 drv | 1.00 · 21 drv | 1.00 · 21 drv | ✓ 1.00 · 0 drv | 1.00 · 21 drv (srj:outer) |
| 0400_laptimer58_Chickadee | 79 | 0.99 · 0 drv | 1.00 · 56 drv | 1.00 · 56 drv | ✓ 1.00 · 0 drv | 1.00 · 56 drv (srj:outer) |
| 0448_uedaino_uedaino | 96 | 0.96 · 0 drv | 1.00 · 189 drv | 1.00 · 188 drv | ✓ 1.00 · 0 drv | 1.00 · 188 drv (srj:outer) |
| 0473_data-manager_data-manager | 92 | 0.98 · 0 drv | 1.00 · 30 drv | 1.00 · 30 drv | ✓ 1.00 · 0 drv | 1.00 · 30 drv (srj:outer) |
| 0520_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD_negative | 85 | ✓ 1.00 · 0 drv | 1.00 · 122 drv | 1.00 · 123 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0546_ozinverter_ozinverterkicad | 144 | ✓ 1.00 · 0 drv | 1.00 · 120 drv | 1.00 · 121 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0496_kitspace_f-91w | 83 | 0.94 · 0 drv | 1.00 · 507 drv | 1.00 · 510 drv | 0.88 · 0 drv | 1.00 · 507 drv (srj:all) |
| 0599_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD | 141 | 0.99 · 0 drv | failed | 1.00 · 326 drv | ✓ 1.00 · 0 drv | 1.00 · 326 drv (srj:outer) |
| 0571_Brushless_ESC_Brushless_ESC | 162 | 0.97 · 0 drv | 0.97 · 247 drv | 0.97 · 254 drv | ✓ 1.00 · 0 drv | 0.97 · 0 drv (freerouting) |
| 0626_TOBS_HybridChargeController | 210 | 0.99 · 0 drv | 1.00 · 228 drv | 1.00 · 229 drv | ✓ 1.00 · 0 drv | 1.00 · 228 drv (srj:all) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
