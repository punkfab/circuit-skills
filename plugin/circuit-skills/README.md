# circuit-skills plugin for Codex

The circuit skills, plus a viewer and the board checks, inside the Codex desktop app.

| Where | What you get |
| --- | --- |
| Sidebar | **Circuit viewer**: open any project by path. |
| Thread | The viewer as a panel beside the conversation. |
| Files | `.kicad_pcb` boards and `.circuit.tsx` designs in your workspace open in the viewer. |
| Agent | `open_board`, `check_board`, `get_netlist`, and the skills: `pcb-layout`, `circuit-sim`, `pcb-enclosure-fit`, `pcb-3d-render`, `circuit-viewer`. |

The viewer's tabs:

- **Board**: the routed KiCad board, one toggleable layer at a time (inner planes start hidden), with
  every DRC marker. Click a marker type to step through its markers. Blocking types are shown; cosmetic
  ones are listed but hidden.
- **Schematic** and **Netlist**: from the tscircuit design (`tsci export`). The netlist filters by net,
  part or pin, and falls back to the board's own nets when there is no design.
- **3D**: KiCad's GLB of the routed board, orbitable.
- **Checks**: `drc_check`, `dfm_check` and `check_floating` from pcb-layout, with routing metrics
  (track, vias, and how much plane/pour-net copper travels as track).

The board and 3D views come from the KiCad file, so they show what will be fabbed: Freerouting's copper
and any hand finishing, which tscircuit's own viewers never see.

## Install

Needs Node.js 18+, KiCad 9+ (`kicad-cli` on PATH), Python 3 (for the check scripts), and a recent Codex
(tested with 0.157). The schematic and netlist also need tscircuit installed in the project
(`npm install` there). Nothing to build: `dist/` and `skills/` are committed.

```sh
# from a clone of github.com/punkfab/circuit-skills
codex plugin marketplace add /path/to/circuit-skills
codex plugin add circuit-skills@circuit-skills
```

Restart the desktop app. To update after pulling: `codex plugin marketplace upgrade`, then
`codex plugin remove circuit-skills@circuit-skills` and `codex plugin add circuit-skills@circuit-skills`.

## Try it

- Click **Circuit viewer** in the sidebar and paste a project path.
- Ask: *"Open pcb/ in the circuit viewer and check it."*
- Open a `.kicad_pcb` from the file tree.

## What is in here

- `.codex-plugin/plugin.json`: the manifest.
- `.mcp.json`: launches `dist/server.mjs` (one bundled file) over stdio.
- `dist/widget.html`: the viewer (self-contained; three.js included).
- `skills/`: copied from the repo root by the build, plus `circuit-viewer`.

Source and tests are in `../../mcp` (`npm test`, and `npm run e2e` for the browser run). `dist/` and
`skills/` are produced by `npm run build` there; edit the skills at the repo root, not here.
