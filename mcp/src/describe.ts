import path from "node:path";
import type { CheckReport } from "./checks.js";
import type { Project } from "./project.js";
import { projectStatus } from "./status.js";
import { boardInfo, boardLayerNames } from "./views.js";

// What a host (the Codex widget, the Claude mod) and the model are told about an
// opened project. Shared by the MCP server and the CLI.

/** What the widget and the model are told about an opened project. */
export async function describeProject(project: Project) {
  const info = project.board ? await boardInfo(project.board) : null;
  return {
    ...(await projectStatus(project)),
    project,
    layers: project.board ? await boardLayerNames(project.board) : [],
    board: info
      ? {
          copperLayers: info.copperLayers,
          bbox: info.bbox,
          footprints: info.footprints,
          nets: info.nets.length,
          zoneNets: info.zoneNets,
          metrics: info.metrics,
        }
      : null,
  };
}

export function projectText(d: Awaited<ReturnType<typeof describeProject>>): string {
  const p = d.project;
  const lines = [`Opened ${p.name} in the circuit viewer (${p.root}).`];
  lines.push(p.source ? `Design: ${path.basename(p.source)} (tscircuit)` : "Design: none (no .circuit.tsx; schematic unavailable)");
  if (d.board) {
    const b = d.board;
    const size = b.bbox ? `${b.bbox.w.toFixed(1)} x ${b.bbox.h.toFixed(1)} mm, ` : "";
    lines.push(
      `Board: ${path.basename(p.board!)}: ${size}${b.copperLayers.length} copper layers, ${b.footprints} footprints, ${b.nets} nets; ` +
        `${b.metrics.track_mm_total} mm of track, ${b.metrics.vias} vias`,
    );
  } else lines.push("Board: none exported yet (run the pcb-layout export/route step).");
  lines.push("Run check_board for the DRC / DFM / floating-pad gates.");
  return lines.join("\n");
}

export function checkText(r: CheckReport, verbose: boolean): string {
  if (!verbose) return r.summary;
  return [r.summary, ...r.gates.map((g) => `\n── ${g.name} (${g.ok ? "pass" : `exit ${g.exitCode}`}) ──\n${g.output}`)].join("\n");
}

