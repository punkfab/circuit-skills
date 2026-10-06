# Which placement measures predict a clean route?

64 corpus boards, 320 placements, each routed by TraceMaker and judged by KiCad DRC.

| placement | n | clean | connections routed | DRC errors before routing |
|---|---|---|---|---|
| designer | 64 | 0.56 | 0.96 | 0.0 |
| swap25 | 64 | 0.39 | 0.94 | 0.9 |
| swap100 | 64 | 0.31 | 0.90 | 3.5 |
| pk | 64 | 0.12 | 0.92 | 36.9 |
| tm | 64 | 0.16 | 0.78 | 200.3 |

Lower is better for every measure. **Pairwise**: of 440 pairs of placements of the same board with different outcomes, how often the measure ranks the better one lower (0.50 = a coin). **AUC**: across all placements, the chance a placement that did not route clean scores worse than one that did.

| measure | pairwise | AUC | pairwise, legal placements only |
|---|---|---|---|
| **combined (fit on all)** | 0.79 | 0.78 | 0.84 |
| congestion_max | 0.72 | 0.73 | 0.62 |
| placement_drv | 0.70 | 0.73 | 0.50 |
| over_capacity_pct | 0.70 | 0.70 | 0.63 |
| congestion_p95 | 0.66 | 0.65 | 0.72 |
| decap_mm | 0.60 | 0.65 | 0.75 |
| crossings | 0.60 | 0.70 | 0.85 |
| crossings_per_net | 0.60 | 0.69 | 0.85 |
| off_board_pads | 0.57 | 0.55 | 0.52 |
| overlaps | 0.56 | 0.59 | 0.50 |
| escape_ratio | 0.52 | 0.60 | 0.50 |
| mst_mm | 0.51 | 0.62 | 0.84 |
| mst_norm | 0.51 | 0.50 | 0.84 |

Combined score: logistic regression on log(1 + measure) differences between two placements of a board. Held-out pairwise accuracy, 5 folds split by board: **0.79** (folds 0.80, 0.77, 0.82, 0.73, 0.82).

Dropped because the fit gave them a negative weight (it would reward a worse value): mst_norm, overlaps. Weights (per unit of log(1 + measure); positive = worse): over_capacity_pct +2.41, crossings_per_net +1.29, decap_mm +1.24, congestion_max +0.73, off_board_pads +0.23

116 of the pairs are between two placements with no DRC errors before routing.
