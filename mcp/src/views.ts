import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdir, readdir, readFile, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { boardNetlist, readBoard, type BoardInfo } from "./kicad.js";
import type { Project } from "./project.js";

// Every view is made by the same tools the skills use, headless:
//   board layers  kicad-cli pcb export svg   (one layer per file, board coordinates)
//   3D            kicad-cli pcb export glb
//   DRC markers   kicad-cli pcb drc --format json
//   schematic     tsci export -f schematic-svg
//   netlist       tsci export -f readable-netlist (or the board's own nets)
// Results are cached per input file and modification time, so switching tabs and
// reopening a board is instant until the files change.

const run = promisify(execFile);
const CACHE = path.join(os.tmpdir(), "circuit-skills-viewer");
const KICAD_CLI = process.env.KICAD_CLI ?? "kicad-cli";

/** Layers drawn on the board view besides copper, in stacking order (bottom first). */
const EXTRA_LAYERS = ["B.Silkscreen", "F.Silkscreen", "Edge.Cuts"];

const inflight = new Map<string, Promise<unknown>>();
/** Runs `make` once per key at a time; concurrent callers share the result. */
function once<T>(key: string, make: () => Promise<T>): Promise<T> {
  const existing = inflight.get(key);
  if (existing) return existing as Promise<T>;
  const p = make().finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

async function cacheDir(input: string, stamp: number): Promise<string> {
  const id = createHash("sha1").update(path.resolve(input)).digest("hex").slice(0, 16);
  const dir = path.join(CACHE, id, String(Math.round(stamp)));
  await mkdir(dir, { recursive: true });
  return dir;
}

const mtime = async (p: string) => (await stat(p)).mtimeMs;

function toolError(what: string, e: unknown): Error {
  const err = e as { code?: string; stderr?: string; message?: string };
  if (err.code === "ENOENT") return new Error(`${what}: the command was not found. Is it installed and on PATH?`);
  const detail = (err.stderr || err.message || String(e)).trim().split("\n").slice(-6).join("\n");
  return new Error(`${what} failed:\n${detail}`);
}

// ---- KiCad -------------------------------------------------------------------

const boards = new Map<string, { stamp: number; info: BoardInfo }>();

export async function boardInfo(board: string): Promise<BoardInfo> {
  const stamp = await mtime(board);
  const hit = boards.get(board);
  if (hit && hit.stamp === stamp) return hit.info;
  const info = readBoard(await readFile(board, "utf8"));
  boards.set(board, { stamp, info });
  return info;
}

export async function boardLayerNames(board: string): Promise<string[]> {
  const info = await boardInfo(board);
  // Bottom to top, so the front layer draws last.
  const copper = [...info.copperLayers].reverse();
  return [EXTRA_LAYERS[0], ...copper, ...EXTRA_LAYERS.slice(1)];
}

/**
 * One layer as SVG, black on transparent so the viewer can colour it. Exported
 * WITHOUT fit-to-board: the page origin is the board origin, so SVG units are
 * board millimetres and DRC positions land exactly.
 */
export async function layerSvg(board: string, layer: string): Promise<string> {
  if (!/^[A-Za-z0-9.]+$/.test(layer)) throw new Error(`bad layer name ${layer}`);
  const dir = await cacheDir(board, await mtime(board));
  const out = path.join(dir, `${layer}.svg`);
  if (!existsSync(out)) {
    await once(out, async () => {
      try {
        await run(KICAD_CLI, ["pcb", "export", "svg", "--mode-single", "--black-and-white", "--exclude-drawing-sheet", "--layers", layer, "-o", out, board], { maxBuffer: 1 << 24 });
      } catch (e) {
        throw toolError(`kicad-cli svg export of ${layer}`, e);
      }
    });
  }
  return readFile(out, "utf8");
}

export async function boardGlb(board: string): Promise<Buffer> {
  const dir = await cacheDir(board, await mtime(board));
  const out = path.join(dir, "board.glb");
  if (!existsSync(out)) {
    await once(out, async () => {
      try {
        await run(KICAD_CLI, ["pcb", "export", "glb", "--subst-models", "--include-tracks", "--include-pads", "--include-zones", "--include-silkscreen", "--include-soldermask", "-f", "-o", out, board], {
          maxBuffer: 1 << 24,
          timeout: 180_000,
        });
      } catch (e) {
        throw toolError("kicad-cli glb export", e);
      }
    });
  }
  return readFile(out);
}

export interface DrcMarker {
  kind: "violation" | "unconnected";
  type: string;
  severity: string;
  description: string;
  items: { description: string; x: number; y: number }[];
}

export interface DrcReport {
  markers: DrcMarker[];
  counts: Record<string, number>;
  unconnected: number;
}

export async function boardDrc(board: string): Promise<DrcReport> {
  const stamps = await Promise.all([board, board.replace(/\.kicad_pcb$/, ".kicad_pro"), board.replace(/\.kicad_pcb$/, ".kicad_dru")].map(p => mtime(p).catch(() => 0)));
  const dir = await cacheDir(board + JSON.stringify(stamps), Math.max(...stamps));
  const out = path.join(dir, "drc.json");
  if (!existsSync(out)) {
    await once(out, async () => {
      try {
        await run(KICAD_CLI, ["pcb", "drc", "--format", "json", "--severity-all", "--units", "mm", "-o", out, board], { maxBuffer: 1 << 24, timeout: 180_000 });
      } catch (e) {
        // kicad-cli exits non-zero only on real failure here (no --exit-code-violations).
        if (!existsSync(out)) throw toolError("kicad-cli drc", e);
      }
    });
  }
  type RawItem = { description?: string; pos?: { x: number; y: number } };
  type Raw = { type?: string; severity?: string; description?: string; items?: RawItem[] };
  const json = JSON.parse(await readFile(out, "utf8")) as { violations?: Raw[]; unconnected_items?: Raw[] };
  const toMarker = (kind: DrcMarker["kind"]) => (v: Raw): DrcMarker => ({
    kind,
    type: v.type ?? kind,
    severity: v.severity ?? "error",
    description: v.description ?? "",
    items: (v.items ?? []).filter((i) => i.pos).map((i) => ({ description: i.description ?? "", x: i.pos!.x, y: i.pos!.y })),
  });
  const markers = [...(json.violations ?? []).map(toMarker("violation")), ...(json.unconnected_items ?? []).map(toMarker("unconnected"))];
  const counts: Record<string, number> = {};
  for (const m of markers) counts[m.type] = (counts[m.type] ?? 0) + 1;
  return { markers, counts, unconnected: json.unconnected_items?.length ?? 0 };
}

// ---- tscircuit ---------------------------------------------------------------

/** The newest modification time of the design's .tsx files (modules, lib, imports included). */
async function sourceStamp(root: string): Promise<number> {
  let newest = 0;
  const walk = async (dir: string, depth: number) => {
    for (const e of await readdir(dir, { withFileTypes: true }).catch(() => [])) {
      if (e.name.startsWith(".") || ["node_modules", "dist", "build", "fab", "renders"].includes(e.name)) continue;
      const p = path.join(dir, e.name);
      if (e.isDirectory() && depth < 3) await walk(p, depth + 1);
      else if (e.isFile() && /\.(tsx|ts|json)$/.test(e.name)) newest = Math.max(newest, (await stat(p)).mtimeMs);
    }
  };
  await walk(root, 0);
  return newest;
}

/** The project's own tscircuit CLI (node_modules/.bin/tsci), searching upward. */
function findTsci(root: string): string | null {
  for (let dir = root; ; dir = path.dirname(dir)) {
    const bin = path.join(dir, "node_modules", ".bin", "tsci");
    if (existsSync(bin)) return bin;
    if (path.dirname(dir) === dir) return null;
  }
}

async function tsciExport(project: Project, format: string, fileName: string): Promise<string> {
  if (!project.source) throw new Error(`${project.name} has no tscircuit source (*.circuit.tsx).`);
  const source = project.source;
  const dir = await cacheDir(source, await sourceStamp(project.root));
  const out = path.join(dir, fileName);
  if (!existsSync(out)) {
    await once(out, async () => {
      const tsci = findTsci(project.root);
      if (!tsci) throw new Error(`tscircuit is not installed for ${project.name}: run \`npm install\` in ${project.root}.`);
      // tsci resolves -o against the project folder and mangles absolute paths,
      // so hand it a path relative to the project that lands in the cache.
      const rel = path.relative(path.dirname(source), out);
      const env = { ...process.env, PATH: [path.join(os.homedir(), ".bun", "bin"), process.env.PATH ?? ""].join(path.delimiter) };
      try {
        await run(tsci, ["export", "-f", format, path.basename(source), "-o", rel], { cwd: path.dirname(source), env, maxBuffer: 1 << 24, timeout: 240_000 });
      } catch (e) {
        throw toolError(`tsci export -f ${format}`, e);
      }
      if (!existsSync(out)) throw new Error(`tsci export -f ${format} did not write ${fileName}.`);
    });
  }
  return readFile(out, "utf8");
}

export const schematicSvg = (project: Project) => tsciExport(project, "schematic-svg", "schematic.svg");

export async function netlistText(project: Project): Promise<{ text: string; from: "tscircuit" | "board" }> {
  if (project.source) return { text: await tsciExport(project, "readable-netlist", "netlist.txt"), from: "tscircuit" };
  if (project.board) return { text: boardNetlist(await boardInfo(project.board)), from: "board" };
  throw new Error(`${project.name} has neither a source nor a board.`);
}
