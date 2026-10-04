import { stat, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import type { Project } from "./project.js";

/** Cheap polling: do not parse/export a board or run DRC on every tick. */
export async function projectStatus(project: Project) {
  const files = [project.board, project.source];
  if (project.board) files.push(project.board.replace(/\.kicad_pcb$/, ".kicad_pro"), project.board.replace(/\.kicad_pcb$/, ".kicad_dru"), project.board.replace(/\.kicad_pcb$/, ".routing-policy.json"));
  const stamps = await Promise.all(files.filter((p): p is string => !!p).map(async p => {
    try { const s = await stat(p); return [p, s.mtimeMs, s.size]; }
    catch { return [p, null]; }
  }));
  let routing: Record<string, unknown> | null = null;
  if (project.board) {
    try {
      const data = JSON.parse(await readFile(project.board + ".routing.json", "utf8"));
      if (["freerouting", "fastroute"].includes(data.backend) && typeof data.state === "string") routing = data;
    } catch { /* missing/partially saved status is retried next tick */ }
  }
  return { revision: createHash("sha256").update(JSON.stringify(stamps)).digest("hex"), routing };
}
