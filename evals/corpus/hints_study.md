# What do placement hints buy?

52 corpus boards. Hints are derived from each designer's placement at three levels of detail (place_hints.py derive), every part is then placed from scratch by place_kicad.py, routed by TraceMaker (20 s) and judged by KiCad DRC.

| placement | clean | connections routed | DRC errors before routing | hints per board (met) | big parts: distance from the designer | wire vs designer | crossings vs designer | compare score beats no-hints |
|---|---|---|---|---|---|---|---|---|
| designer's placement | 0.63 | 0.959 | 0.0 | – | 0% of the board diagonal | 1.00x | 1.00x | 35/52 |
| no hints | 0.15 | 0.915 | 30.0 | – | 26% of the board diagonal | 0.76x | 0.87x | – |
| level 1: anchors (edges and regions) | 0.19 | 0.928 | 24.9 | 12 (85%) | 12% of the board diagonal | 0.86x | 0.94x | 22/52 |
| level 2: + relations between big parts | 0.21 | 0.929 | 25.7 | 16 (80%) | 11% of the board diagonal | 0.90x | 0.97x | 21/52 |
| level 3: + small parts near their big part | 0.19 | 0.915 | 30.2 | 34 (83%) | 12% of the board diagonal | 0.93x | 1.12x | 21/52 |

"Distance from the designer": how far each part with 8 or more pads ends up from where the designer put it, as a share of the board diagonal. "Wire" and "crossings": ratsnest length and crossings relative to the designer's placement (median over boards; below 1 is shorter or fewer). "Compare score": placement_score.py's fitted score; the count is boards where the hinted placement scores better than the unhinted one.
