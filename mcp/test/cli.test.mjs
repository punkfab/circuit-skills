// The CLI the Claude Code mod runs: `node --input-type=module -` with the
// bundle on stdin, from a folder with no checkout nearby, against einhander.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

const FIXTURE = process.env.CIRCUIT_VIEWER_FIXTURE ?? path.join(os.homedir(), "sandbox/audiodestrukt/einhander");
const skip = existsSync(path.join(FIXTURE, "pcb-rerun", "index.circuit.kicad_pcb")) ? false : `fixture not found at ${FIXTURE}`;
const bundle = readFileSync(new URL("../dist/cli.mjs", import.meta.url), "utf8");

function cli(...args) {
  let out;
  try {
    out = execFileSync("node", ["--input-type=module", "-", ...args], { input: bundle, cwd: os.tmpdir(), encoding: "utf8", maxBuffer: 1 << 26 });
  } catch (e) {
    out = e.stdout;
  }
  return JSON.parse(out.trim().split("\n").pop());
}

test("the mod's copy of the CLI is this build", () => {
  const mod = readFileSync(new URL("../../claude/circuit-viewer/hooks/cli-source.ts", import.meta.url), "utf8");
  assert.ok(mod.includes(JSON.stringify(bundle)), "run `node build.mjs` to regenerate claude/circuit-viewer/hooks/cli-source.ts");
});

test("snapshot: project, geometry, DRC and revision in one call", { skip }, () => {
  const r = cli("snapshot", path.join(FIXTURE, "pcb-rerun"));
  assert.ok(r.ok, r.error);
  const { project, geometry, drc, revision, board } = r.data;
  assert.equal(project.name, "einhander/pcb-rerun");
  assert.match(revision, /^[0-9a-f]{64}$/);
  assert.equal(board.metrics.vias, 32);
  const count = (k, l) => geometry.prims.filter((p) => p.k === k && (!l || p.l === l)).length;
  assert.equal(count("t", "F.Cu") + count("t", "B.Cu"), 497); // every segment, on outer layers
  assert.equal(count("v"), 32);
  assert.ok(count("p", "F.Cu") > 100 && count("h") > 30);
  assert.equal(drc.unconnected, 2);
});

test("a rotated footprint's pads land where KiCad puts them", { skip }, () => {
  // einhander U1 (RP2040) is at -90 degrees; KiCad (pcbnew) puts pad 1 at (78.600, 118.575).
  const r = cli("snapshot", path.join(FIXTURE, "pcb"));
  const hit = r.data.geometry.prims.find((p) => p.k === "p" && Math.abs(p.x - 78.6) < 0.01 && Math.abs(p.y - 118.575) < 0.01);
  assert.ok(hit, "no pad at U1.1's KiCad position");
  assert.deepEqual([hit.w, hit.h], [0.2, 0.850011]);
});

test("check: the gates run from the embedded scripts", { skip, timeout: 300_000 }, () => {
  const r = cli("check", path.join(FIXTURE, "pcb-rerun"));
  assert.ok(r.ok, r.error);
  assert.equal(r.data.ok, false);
  assert.match(r.data.text, /unconnected=2/);
});

test("a path starting with ~ is the home folder", { skip }, () => {
  const rel = path.relative(os.homedir(), path.join(FIXTURE, "pcb-rerun"));
  const r = cli("status", `~/${rel}`);
  assert.ok(r.ok, r.error);
  assert.equal(r.data.project.name, "einhander/pcb-rerun");
});

test("errors come back as JSON", () => {
  const r = cli("snapshot", "/nonexistent");
  assert.equal(r.ok, false);
  assert.match(r.error, /does not exist/);
});
