---
name: circuit-viewer
description: Show and check PCB projects in the circuit viewer — the schematic and netlist from a tscircuit design, the routed KiCad board layer by layer with DRC markers, a 3D view, and the pcb-layout gates (DRC triage, DFM, floating pads) with routing metrics. Use whenever the user wants to see, show, open, compare or review a board, schematic or routing result, or before calling a board done or ordering it. Works with the pcb-layout skill, which produces the boards.
---

# Circuit viewer

The circuit viewer shows a PCB project the way the pcb-layout pipeline builds it:

| Tab | What it shows | Made by |
|---|---|---|
| Board | the routed `.kicad_pcb`, one toggleable layer at a time, with every DRC marker | `kicad-cli pcb export svg` + `kicad-cli pcb drc` |
| Schematic | the tscircuit design's schematic | `tsci export -f schematic-svg` |
| Netlist | components and nets, filterable | `tsci export -f readable-netlist` (or the board's nets) |
| 3D | the routed board, orbitable | `kicad-cli pcb export glb` |
| Checks | the pcb-layout gates and routing metrics | `drc_check.py`, `dfm_check.py`, `check_floating.py` |

The routed board and 3D come from the KiCad file, not from tscircuit: they show what will be
fabbed, including Freerouting's copper and any hand finishing.

## Tools

- **`open_board(path)`** — open a project folder (or one with a `pcb/` folder), a `.kicad_pcb`, or
  a `.circuit.tsx` in the viewer. Use absolute paths. The result summarises the board.
- **`check_board(path)`** — run the gates. Read the verdict before saying a board is done:
  - `drc_check` blocks on courtyard overlaps, real shorts, crossings, copper over the edge **and
    unconnected items**.
  - `dfm_check` catches what KiCad's DRC misses (hole-to-hole spacing, via drill / annular ring).
  - `check_floating` catches SMD pads reached only by copper on the other layer.
  - The metrics include track on plane/pour nets: on a 4-layer board, a large number means power is
    travelling as traces instead of through the planes.
- **`get_netlist(path)`** — connectivity as text, for checking a design against intent.

## How to use it

- After a routing or finishing step: `check_board`, then `open_board` so the user can see the DRC
  markers you are talking about. In the Board tab they can click a marker type to step through them.
- Comparing two versions (say a hand-finished board against an unattended run): open each, and
  compare `check_board` results and metrics side by side.
- The viewer reports what is open (and the last check summary) back to you as context.
- If a view fails, the message names the tool that failed: `kicad-cli` must be on PATH (KiCad 9+),
  and the schematic/netlist need tscircuit installed in the project (`npm install`).
