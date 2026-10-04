import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { boardDrc, boardInfo } from "./views.js";
import type { Metrics } from "./kicad.js";

// The board gates are the pcb-layout skill's own scripts, run unchanged, so the
// viewer, the agent and the pipeline all get the same verdict:
//   drc_check.py       DRC triaged into placement / shorts / unconnected / cosmetic
//   dfm_check.py       fab rules KiCad's DRC misses (hole-to-hole, via drill/annular)
//   check_floating.py  SMD pads reached only by copper on the other layer
// They need only the Python standard library and kicad-cli.

export interface GateResult {
  name: string;
  ok: boolean;
  exitCode: number;
  output: string;
}

export interface CheckReport {
  board: string;
  ok: boolean;
  summary: string;
  gates: GateResult[];
  drc: { counts: Record<string, number>; unconnected: number };
  metrics: Metrics;
  zoneNets: string[];
}

/** Where pcb-layout's scripts are: next to the bundled plugin, or in the repo when developing. */
export function scriptsDir(): string {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    process.env.CIRCUIT_SKILLS_SCRIPTS,
    path.join(here, "..", "skills", "pcb-layout", "scripts"), // plugin/circuit-skills/dist -> skills/
    path.join(here, "..", "..", "pcb-layout", "scripts"), // mcp/dist -> repo root
    path.join(here, "..", "..", "..", "pcb-layout", "scripts"), // mcp/dist/src -> repo root
  ].filter((p): p is string => !!p);
  const found = candidates.find((p) => existsSync(path.join(p, "drc_check.py")));
  if (!found) throw new Error(`Can't find pcb-layout/scripts (looked in ${candidates.join(", ")}). Set CIRCUIT_SKILLS_SCRIPTS.`);
  return found;
}

function runGate(name: string, script: string, board: string): Promise<GateResult> {
  const python = name === "critical_routing"
    ? (process.env.CIRCUIT_SKILLS_KICAD_PYTHON ?? (process.platform === "linux" && existsSync("/usr/bin/python3") ? "/usr/bin/python3" : "python3"))
    : (process.env.CIRCUIT_SKILLS_PYTHON ?? "python3");
  return new Promise((resolve) => {
    execFile(python, [script, board], { cwd: path.dirname(board), maxBuffer: 1 << 24, timeout: 300_000 }, (error, stdout, stderr) => {
      const code = error ? (typeof (error as { code?: unknown }).code === "number" ? ((error as { code: number }).code) : -1) : 0;
      const output = `${stdout}${stderr ? `\n${stderr}` : ""}`.trim();
      if (error && code === -1) {
        resolve({ name, ok: false, exitCode: -1, output: `could not run ${python} ${path.basename(script)}: ${error.message}` });
      } else {
        resolve({ name, ok: code === 0, exitCode: code, output });
      }
    });
  });
}

export async function checkBoard(board: string): Promise<CheckReport> {
  const dir = scriptsDir();
  const policy = board.replace(/\.kicad_pcb$/i, ".routing-policy.json");
  const hasCriticalPolicy = existsSync(policy);
  const [gates, drc, info] = await Promise.all([
    Promise.all([
      runGate("drc_check", path.join(dir, "drc_check.py"), board),
      runGate("dfm_check", path.join(dir, "dfm_check.py"), board),
      runGate("check_floating", path.join(dir, "check_floating.py"), board),
      ...(hasCriticalPolicy ? [runGate("critical_routing", path.join(dir, "check_critical_routing.py"), board)] : []),
    ]),
    boardDrc(board),
    boardInfo(board),
  ]);
  const ok = gates.every((g) => g.ok);
  const drcLine = gates[0].output.split("\n").find((l) => l.startsWith("SUMMARY:")) ?? "";
  const m = info.metrics;
  const summary = [
    `${path.basename(board)}: ${ok ? "all gates pass" : `FAILING: ${gates.filter((g) => !g.ok).map((g) => g.name).join(", ")}`}`,
    hasCriticalPolicy ? "Critical routing policy evaluated (screening plus current-board review evidence)." : "Critical routing NOT ASSESSED: no .routing-policy.json; passing geometry gates is not release approval.",
    drcLine && `DRC ${drcLine.replace("SUMMARY: ", "")}`,
    `Routing: ${m.track_mm_total} mm of track in ${m.segments_total} segments, ${m.vias} vias` +
      (info.zoneNets.length ? `; ${m.zone_net_track_mm} mm of it on plane/pour nets (${info.zoneNets.join(", ")})` : ""),
  ]
    .filter(Boolean)
    .join("\n");
  return { board, ok, summary, gates, drc: { counts: drc.counts, unconnected: drc.unconnected }, metrics: m, zoneNets: info.zoneNets };
}
