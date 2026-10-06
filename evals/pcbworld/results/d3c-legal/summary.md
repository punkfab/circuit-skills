# PCBWorld D3C · d3c-legal

10 boards · backends `srj-legal:all` · 300 s per backend · {'circuit_skills': 'a0cdac3', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 0.90 | 0.94 | 0.0 | 1391 | 44.0 | – | 10/10 |
| srj-legal:all | 0.20 | 0.97 | 0.0 | 1654 | 70.4 | 490.8 | 10/10 |
| **circuit-skills (best of all backends)** | 0.20 | 0.97 | 0.0 | 1654 | 70.4 | 490.8 | 10/10 |

Clean boards by the backend that produced the kept candidate: srj-legal:all 2

## Does the placement score predict it?

2 boards came back clean and 8 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 0.94 | 0.94 | 1.50 |
| congestion_p95 | 0.97 | 0.26 | 0.54 |
| over_capacity_pct | 0.88 | 0.00 | 1.11 |
| crossings | 0.81 | 89.50 | 141.25 |
| escape_ratio | 0.69 | 0.00 | 0.09 |
| signal_nets | 0.75 | 36.00 | 46.50 |
| mst_mm | 0.44 | 1295.45 | 1103.62 |

route_eval diagnosis vs outcome: hand-finish: 1 clean / 4 not, order-ready: 1 clean / 0 not, re-place: 0 clean / 4 not

## Boards

| board | u0 | srj-legal:all | circuit-skills |
|---|---|---|---|
| 0400_laptimer58_Chickadee | 79 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0423_induction-hob_temperature-sender | 86 | 0.99 · 0 drv | 0.99 · 0 drv (srj-legal:all) |
| 0448_uedaino_uedaino | 96 | 0.97 · 0 drv | 0.97 · 0 drv (srj-legal:all) |
| 0473_data-manager_data-manager | 92 | 0.85 · 0 drv | 0.85 · 0 drv (srj-legal:all) |
| 0496_kitspace_f-91w | 83 | 0.93 · 0 drv | 0.93 · 0 drv (srj-legal:all) |
| 0520_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD_negative | 85 | 0.98 · 0 drv | 0.98 · 0 drv (srj-legal:all) |
| 0546_ozinverter_ozinverterkicad | 144 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0571_Brushless_ESC_Brushless_ESC | 162 | 0.98 · 0 drv | 0.98 · 0 drv (srj-legal:all) |
| 0599_RGBMatrixPanelCPLD-PhotonBackpack_RGBMatrixPanel_CPLD | 141 | 0.99 · 0 drv | 0.99 · 0 drv (srj-legal:all) |
| 0626_TOBS_HybridChargeController | 210 | 0.99 · 0 drv | 0.99 · 0 drv (srj-legal:all) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
