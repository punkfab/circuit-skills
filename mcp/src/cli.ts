// The circuit viewer's backend as a command line, for hosts that are not MCP
// clients: the Claude Code mod (claude/circuit-viewer) runs it with
// `node --input-type=module - <command> <path>`, the bundle on stdin, so it
// needs no install location. Every command prints one JSON line:
//   {"ok":true,"data":...}  or  {"ok":false,"error":"..."}
//
//   snapshot <path>   project summary + board geometry + DRC markers + revision
//   status <path>     the cheap revision hash and routing progress (for polling)
//   check <path>      the pcb-layout gates and routing metrics
//   netlist <path>    the netlist text
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import drcCheck from "../../pcb-layout/scripts/drc_check.py";
import dfmCheck from "../../pcb-layout/scripts/dfm_check.py";
import checkFloating from "../../pcb-layout/scripts/check_floating.py";
import { checkBoard, scriptsDir } from "./checks.js";
import { checkText, describeProject } from "./describe.js";
import { boardGeometry } from "./kicad.js";
import { resolveProject } from "./project.js";
import { projectStatus } from "./status.js";
import { boardDrc, netlistText } from "./views.js";

/** pcb-layout's gates, from a checkout when there is one, else unpacked from this bundle. */
async function ensureScripts() {
  try {
    scriptsDir();
    return;
  } catch {
    /* no checkout nearby: use the embedded copies */
  }
  const scripts = { "drc_check.py": drcCheck, "dfm_check.py": dfmCheck, "check_floating.py": checkFloating };
  const id = createHash("sha1").update(Object.values(scripts).join("\0")).digest("hex").slice(0, 12);
  const dir = path.join(os.tmpdir(), "circuit-skills-viewer", `scripts-${id}`);
  if (!existsSync(path.join(dir, "check_floating.py"))) {
    await mkdir(dir, { recursive: true });
    for (const [name, text] of Object.entries(scripts)) await writeFile(path.join(dir, name), text);
  }
  process.env.CIRCUIT_SKILLS_SCRIPTS = dir;
}

async function main(): Promise<unknown> {
  // argv: node, the script (or "-" when it came on stdin), command, path
  const [command, target] = process.argv.slice(2);
  if (!command || !target) throw new Error("usage: cli <snapshot|status|check|netlist> <path>");
  const project = await resolveProject(target);
  switch (command) {
    case "snapshot": {
      const [described, geometry, drc] = await Promise.all([
        describeProject(project),
        project.board ? readFile(project.board, "utf8").then(boardGeometry) : null,
        project.board ? boardDrc(project.board) : null,
      ]);
      return { ...described, geometry, drc };
    }
    case "status":
      return { project, ...(await projectStatus(project)) };
    case "check": {
      if (!project.board) throw new Error(`${project.name} has no .kicad_pcb to check yet.`);
      await ensureScripts();
      const report = await checkBoard(project.board);
      return { ...report, text: checkText(report, true) };
    }
    case "netlist":
      return await netlistText(project);
    default:
      throw new Error(`unknown command ${command}`);
  }
}

main().then(
  (data) => process.stdout.write(JSON.stringify({ ok: true, data }) + "\n"),
  (e) => {
    process.stdout.write(JSON.stringify({ ok: false, error: (e as Error).message ?? String(e) }) + "\n");
    process.exitCode = 1;
  },
);
