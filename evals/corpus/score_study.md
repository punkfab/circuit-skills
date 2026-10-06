# Which placement measures predict a clean route?

64 corpus boards, 319 placements, each routed by TraceMaker and judged by KiCad DRC.

| placement | n | clean | connections routed | DRC errors before routing |
|---|---|---|---|---|
| designer | 64 | 0.56 | 0.96 | 0.0 |
| swap25 | 64 | 0.39 | 0.94 | 0.9 |
| swap100 | 64 | 0.31 | 0.90 | 3.5 |
| pk | 63 | 0.02 | 0.26 | 45.8 |
| tm | 64 | 0.16 | 0.78 | 200.3 |

Lower is better for every measure. **Pairwise**: of 494 pairs of placements of the same board with different outcomes, how often the measure ranks the better one lower (0.50 = a coin). **AUC**: across all placements, the chance a placement that did not route clean scores worse than one that did.

| measure | pairwise | AUC | pairwise, legal placements only |
|---|---|---|---|
| **combined (fit on all)** | 0.89 | 0.81 | 0.92 |
| placement_drv | 0.80 | 0.76 | 0.50 |
| congestion_max | 0.79 | 0.77 | 0.64 |
| over_capacity_pct | 0.73 | 0.72 | 0.67 |
| off_board_pads | 0.72 | 0.64 | 0.53 |
| decap_mm | 0.71 | 0.65 | 0.76 |
| crossings | 0.68 | 0.71 | 0.90 |
| crossings_per_net | 0.68 | 0.73 | 0.90 |
| mst_mm | 0.65 | 0.63 | 0.90 |
| mst_norm | 0.65 | 0.58 | 0.90 |
| congestion_p95 | 0.65 | 0.64 | 0.77 |
| overlaps | 0.52 | 0.59 | 0.50 |
| escape_ratio | 0.52 | 0.59 | 0.50 |

Combined score: logistic regression on log(1 + measure) differences between two placements of a board. Held-out pairwise accuracy, 5 folds split by board: **0.89** (folds 0.88, 0.87, 0.84, 0.91, 0.95).

Dropped because the fit gave them a negative weight (it would reward a worse value): mst_norm. Weights (per unit of log(1 + measure); positive = worse): over_capacity_pct +1.75, crossings_per_net +1.73, off_board_pads +1.41, decap_mm +1.15, congestion_max +0.77, overlaps +0.21

99 of the pairs are between two placements with no DRC errors before routing.
