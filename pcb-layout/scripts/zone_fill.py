#!/usr/bin/env python3
"""zone_fill.py — refill (or clear) every copper zone of a KiCad board, headless.

  /usr/bin/python3 zone_fill.py <board.kicad_pcb> [--unfill]

A router that reads the board file sees a stale fill as solid copper in its way, and a board judged
with the fill from before routing shows clearance errors that are not there. Clear the fills before
such a router runs and refill after it. Needs pcbnew.
"""
import sys
sys.path.insert(0, '/usr/lib/python3/dist-packages')
import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
zones = board.Zones()
if '--unfill' in sys.argv:
    for z in zones:
        z.UnFill()
else:
    pcbnew.ZONE_FILLER(board).Fill(zones)
pcbnew.SaveBoard(sys.argv[1], board)
print(f"zone_fill: {'cleared' if '--unfill' in sys.argv else 'filled'} {len(zones)} zones in {sys.argv[1]}")
