import { readdir, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

// A circuit-skills project is a tscircuit source (*.circuit.tsx, the design) and
// the KiCad board exported from it and routed (*.kicad_pcb, what gets fabbed).
// Either can be missing: a hand-made KiCad board has no source, and a design
// that was never exported has no board.

export interface Project {
  /** Display name: the folder, plus the board file when it isn't the default. */
  name: string;
  /** The folder holding the source and the board. */
  root: string;
  /** The routed KiCad board, if there is one. */
  board?: string;
  /** The tscircuit entry file, if there is one. */
  source?: string;
}

const isFile = async (p: string) => (await stat(p).catch(() => null))?.isFile() ?? false;
const isDir = async (p: string) => (await stat(p).catch(() => null))?.isDirectory() ?? false;

/** Files directly in `dir` matching `test`, sorted, skipping KiCad autosaves and backups. */
async function filesIn(dir: string, test: (name: string) => boolean): Promise<string[]> {
  const names = await readdir(dir).catch(() => [] as string[]);
  return names
    .filter((n) => test(n) && !n.startsWith("~") && !n.startsWith("_autosave") && !n.includes("-backup"))
    .sort()
    .map((n) => path.join(dir, n));
}

async function boardIn(dir: string, preferred?: string): Promise<string | undefined> {
  if (preferred && (await isFile(path.join(dir, preferred)))) return path.join(dir, preferred);
  if (await isFile(path.join(dir, "index.circuit.kicad_pcb"))) return path.join(dir, "index.circuit.kicad_pcb");
  return (await filesIn(dir, (n) => n.endsWith(".kicad_pcb")))[0];
}

async function sourceIn(dir: string, preferred?: string): Promise<string | undefined> {
  if (preferred && (await isFile(path.join(dir, preferred)))) return path.join(dir, preferred);
  if (await isFile(path.join(dir, "index.circuit.tsx"))) return path.join(dir, "index.circuit.tsx");
  return (await filesIn(dir, (n) => n.endsWith(".circuit.tsx")))[0];
}

function named(root: string, board?: string): string {
  const folder = path.basename(root);
  const parent = path.basename(path.dirname(root));
  // "einhander/pcb" and "einhander/pcb-rerun" read better than "pcb".
  const base = /^(pcb|board|hardware|kicad)([-_.].*)?$/i.test(folder) ? `${parent}/${folder}` : folder;
  return board && path.basename(board) !== "index.circuit.kicad_pcb" ? `${base} · ${path.basename(board)}` : base;
}

/**
 * Resolves what the user or the model pointed at: a .kicad_pcb, a .circuit.tsx,
 * or a folder (the project folder, or one that has a pcb/ folder in it).
 */
export async function resolveProject(input: string): Promise<Project> {
  // "~/x" as a person types it in /board or a tool call; Node does not expand it.
  const target = path.resolve(input.replace(/^~(?=$|\/)/, os.homedir()));
  if (await isFile(target)) {
    const root = path.dirname(target);
    if (target.endsWith(".kicad_pcb")) {
      return { name: named(root, target), root, board: target, source: await sourceIn(root) };
    }
    if (target.endsWith(".tsx")) {
      // tscircuit names the export after the entry file: index.circuit.tsx -> index.circuit.kicad_pcb
      const board = await boardIn(root, path.basename(target).replace(/\.tsx$/, ".kicad_pcb"));
      return { name: named(root, board), root, board, source: target };
    }
    throw new Error(`${path.basename(target)} is not a board (.kicad_pcb) or a tscircuit design (.circuit.tsx).`);
  }
  if (await isDir(target)) {
    for (const root of [target, path.join(target, "pcb")]) {
      const [board, source] = await Promise.all([boardIn(root), sourceIn(root)]);
      if (board || source) return { name: named(root, board), root, board, source };
    }
    throw new Error(`No .kicad_pcb or .circuit.tsx found in ${target} (or its pcb/ folder).`);
  }
  throw new Error(`${target} does not exist.`);
}
