#!/usr/bin/env node
// route_tscircuit.mjs — route with tscircuit's own autorouter and export the routed KiCad board.
//
// The other backends (route_dsn.py: Freerouting, FastRoute) route a DSN into an SES that is then
// injected into KiCad. tscircuit routes while the design is evaluated, so this backend works on the
// .circuit.tsx: it writes a temporary copy of the entry file beside it with the <board> autorouter
// set to the preset asked for (the design's own source is never edited), runs
// `tsci export -f kicad_pcb` on that copy, and deletes it. The output carries tscircuit's traces and
// vias; pour planes, apply fab rules and run the gates on it like any other candidate.
//
//   node route_tscircuit.mjs index.circuit.tsx -o build/tscircuit.kicad_pcb \
//        [--preset auto_local] [--effort 2x] [--tsci path/to/tsci] [--board live.kicad_pcb] [--max-time 900]
//
//   --preset    the <board autorouter> value (default auto_local, or $TSCIRCUIT_AUTOROUTER). Which
//               presets exist depends on the project's tscircuit version; recent ones include
//               auto_local, auto_cloud, auto_jumper, tscircuit_beta, krt, laser_prefab, fanout.
//   --effort    autorouterEffortLevel on the board (recent tscircuit: 1x 1.5x 2x 5x 10x 100x).
//   --tsci      the tsci to run (default: the project's node_modules/.bin/tsci, searching upward).
//   --board     write live status to <board>.routing.json, as route_dsn.py does, for the viewer.
//
// The output must not exist yet: every run is a fresh candidate. Exit 0 when a board with traces
// was written; tscircuit's warnings are kept in <output>.log.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

function usage(msg) {
  if (msg) console.error(`route_tscircuit: ${msg}`);
  console.error("usage: route_tscircuit.mjs <entry.circuit.tsx> -o <out.kicad_pcb> [--preset P] [--effort E] [--tsci PATH] [--board PATH] [--max-time S]");
  process.exit(2);
}

const args = process.argv.slice(2);
const opt = { preset: process.env.TSCIRCUIT_AUTOROUTER || "auto_local", maxTime: Number(process.env.MAXT || 900) };
let entry;
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  const val = () => args[++i] ?? usage(`${a} needs a value`);
  if (a === "-o" || a === "--output") opt.output = val();
  else if (a === "--preset") opt.preset = val();
  else if (a === "--effort") opt.effort = val();
  else if (a === "--tsci") opt.tsci = val();
  else if (a === "--board") opt.board = val();
  else if (a === "--max-time") opt.maxTime = Number(val());
  else if (a === "-h" || a === "--help") usage();
  else if (!entry) entry = a;
  else usage(`unexpected argument ${a}`);
}
const home = (p) => p.replace(/^~(?=$|\/)/, os.homedir());
if (!entry || !opt.output) usage();
entry = path.resolve(home(entry));
const output = path.resolve(home(opt.output));
if (!existsSync(entry)) usage(`no such design: ${entry}`);
if (existsSync(output)) usage(`output exists; choose a fresh candidate: ${output}`);
if (!/^[A-Za-z0-9_.-]+$/.test(opt.preset)) usage(`bad preset ${opt.preset}`);
if (opt.effort && !/^[0-9.]+x$/.test(opt.effort)) usage(`bad effort ${opt.effort} (e.g. 2x)`);
if (!(opt.maxTime > 0)) usage("--max-time must be positive");

function findTsci(dir) {
  for (let d = dir; ; d = path.dirname(d)) {
    const bin = path.join(d, "node_modules", ".bin", "tsci");
    if (existsSync(bin)) return bin;
    if (path.dirname(d) === d) return null;
  }
}
const tsci = opt.tsci ? path.resolve(home(opt.tsci)) : findTsci(path.dirname(entry));
if (!tsci) usage(`tscircuit is not installed for ${path.dirname(entry)} (npm install there, or --tsci)`);

// ---- the routed copy of the entry file ------------------------------------------------------
const source = readFileSync(entry, "utf8");
const boardTag = source.match(/<board\b[\s\S]*?>/);
if (!boardTag) usage(`no <board> element in ${path.basename(entry)}`);
let tag = boardTag[0]
  .replace(/\sautorouter=(?:"[^"]*"|'[^']*'|\{[^}]*\})/, "")
  .replace(/\sautorouterEffortLevel=(?:"[^"]*"|'[^']*'|\{[^}]*\})/, "");
const extra = ` autorouter="${opt.preset}"` + (opt.effort ? ` autorouterEffortLevel="${opt.effort}"` : "");
tag = tag.replace(/^<board\b/, `<board${extra}`);
const routed = source.slice(0, boardTag.index) + tag + source.slice(boardTag.index + boardTag[0].length);
// Beside the original so its relative imports resolve; a name no project would use.
const temp = path.join(path.dirname(entry), `.route-tscircuit-${process.pid}.circuit.tsx`);

// ---- live status, in route_dsn.py's format --------------------------------------------------
const started = Date.now();
const statusFile = opt.board ? path.resolve(home(opt.board)) + ".routing.json" : null;
const log = output + ".log";
function publish(state, message) {
  const data = { backend: `tscircuit:${opt.preset}`, state, message, elapsed_s: Math.round((Date.now() - started) / 100) / 10, output, log };
  if (statusFile) {
    writeFileSync(statusFile + ".tmp", JSON.stringify(data) + "\n");
    renameSync(statusFile + ".tmp", statusFile);
  }
  console.log(`tscircuit:${opt.preset}: ${state} · ${message}`);
}

const cleanup = () => rmSync(temp, { force: true });
process.on("SIGINT", () => { cleanup(); process.exit(130); });
process.on("SIGTERM", () => { cleanup(); process.exit(143); });

mkdirSync(path.dirname(output), { recursive: true });
writeFileSync(temp, routed);
publish("running", "tscircuit is routing while it evaluates the design; KiCad verification pending");
// tsci resolves -o against the design's folder and mangles absolute paths: hand it a relative one.
const rel = path.relative(path.dirname(entry), output);
const env = { ...process.env, PATH: [path.join(os.homedir(), ".bun", "bin"), process.env.PATH ?? ""].join(path.delimiter) };
const child = spawn(tsci, ["export", "-f", "kicad_pcb", path.basename(temp), "-o", rel], { cwd: path.dirname(entry), env });
let out = "";
child.stdout.on("data", (d) => (out += d));
child.stderr.on("data", (d) => (out += d));
const tick = setInterval(() => publish("running", `${Math.round((Date.now() - started) / 1000)}s elapsed; KiCad verification pending`), 2000);
const killer = setTimeout(() => child.kill("SIGTERM"), opt.maxTime * 1000);
child.on("close", (code) => {
  clearInterval(tick);
  clearTimeout(killer);
  cleanup();
  writeFileSync(log, out);
  const ok = existsSync(output) && statSync(output).size > 0;
  if (!ok) {
    publish("failed", `no board written (exit ${code}${Date.now() - started > opt.maxTime * 1000 ? `, over ${opt.maxTime}s` : ""}); see ${log}`);
    process.exit(1);
  }
  const board = readFileSync(output, "utf8");
  const segments = (board.match(/\(segment\b/g) ?? []).length + (board.match(/\(arc\b/g) ?? []).length;
  const vias = (board.match(/\(via\b/g) ?? []).length;
  const unsaved = out.split("\n").filter((l) => /could not|failed|error/i.test(l)).length;
  publish(
    segments ? "candidate" : "failed",
    segments
      ? `${segments} track segments, ${vias} vias${unsaved ? `, ${unsaved} router warning(s) in the log` : ""}; pour planes, apply fab rules and run the gates`
      : "the board has no tracks: the preset did not route (see the log)",
  );
  process.exit(segments ? 0 : 1);
});
