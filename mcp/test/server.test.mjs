// The MCP server end to end, through an in-memory client, against a real
// project: einhander (audiodestrukt/einhander) — the shipped board in pcb/ and
// the unattended re-route in pcb-rerun/. Point CIRCUIT_VIEWER_FIXTURE elsewhere,
// or the project-dependent tests skip.
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { loadAssets } from "../dist/assets.js";
import { createServer } from "../dist/server.js";
import { readBoard, parseSExpr } from "../dist/kicad.js";
import { resolveProject } from "../dist/project.js";

const FIXTURE = process.env.CIRCUIT_VIEWER_FIXTURE ?? path.join(os.homedir(), "sandbox/audiodestrukt/einhander");
const SHIPPED = path.join(FIXTURE, "pcb");
const RERUN = path.join(FIXTURE, "pcb-rerun");
const have = existsSync(path.join(SHIPPED, "index.circuit.kicad_pcb"));
const skip = have ? false : `fixture not found at ${FIXTURE}`;

async function connect() {
  const server = createServer(await loadAssets());
  const [a, b] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test", version: "0" });
  await Promise.all([server.connect(a), client.connect(b)]);
  return client;
}
const text = (r) => r.content.find((c) => c.type === "text")?.text ?? "";

test("s-expression reader: strings, escapes, nesting", () => {
  assert.deepEqual(parseSExpr('(a "b c" (d 1.5) "q\\"x")'), ["a", "b c", ["d", "1.5"], 'q"x']);
});

test("a tiny board: layers, outline, track, vias, zone nets", () => {
  const board = `(kicad_pcb (version 20241229)
    (layers (0 "F.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user))
    (net 0 "") (net 1 "GND") (net 2 "SIG")
    (gr_rect (start 0 0) (end 20 10) (layer "Edge.Cuts"))
    (segment (start 1 1) (end 4 5) (width 0.2) (layer "F.Cu") (net 2))
    (segment (start 4 5) (end 4 9) (width 0.2) (layer "B.Cu") (net 1))
    (via (at 4 5) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net 2))
    (zone (net 1) (net_name "GND") (layer "B.Cu"))
    (zone (net 0) (net_name "") (layer "F.Cu") (keepout (tracks not_allowed)))
    (footprint "R" (layer "F.Cu") (property "Reference" "R1") (pad "1" smd rect (net 2 "SIG")) (pad "2" smd rect (net 1 "GND"))))`;
  const b = readBoard(board);
  assert.deepEqual(b.copperLayers, ["F.Cu", "B.Cu"]);
  assert.deepEqual(b.bbox, { x: 0, y: 0, w: 20, h: 10 });
  assert.equal(b.metrics.track_mm_total, 9);
  assert.equal(b.metrics.vias, 1);
  assert.deepEqual(b.zoneNets, ["GND"]);
  assert.equal(b.metrics.zone_net_track_mm, 4);
  assert.deepEqual(b.nets, [{ name: "GND", pads: ["R1.2"] }, { name: "SIG", pads: ["R1.1"] }]);
});

test("tools are listed, and load_view is for the app only", async () => {
  const client = await connect();
  const { tools } = await client.listTools();
  const byName = Object.fromEntries(tools.map((t) => [t.name, t]));
  for (const n of ["open_board", "open_viewer", "open_file", "check_board", "get_netlist", "load_view"]) assert.ok(byName[n], n);
  assert.deepEqual(byName.load_view._meta.ui.visibility, ["app"]);
  assert.deepEqual(byName.open_viewer._meta["openai/ui"].entrypoints, [{ type: "global" }, { type: "thread" }]);
  assert.deepEqual(byName.open_file._meta["openai/ui"].entrypoints[0].extensions, [".kicad_pcb", ".circuit.tsx"]);
  const res = await client.readResource({ uri: byName.open_board._meta.ui.resourceUri });
  assert.match(res.contents[0].text, /<title>Circuit viewer<\/title>/);
});

test("resolving a project from a folder, a board, a design, and a parent folder", { skip }, async () => {
  const fromDir = await resolveProject(SHIPPED);
  assert.equal(path.basename(fromDir.board), "index.circuit.kicad_pcb");
  assert.equal(path.basename(fromDir.source), "index.circuit.tsx");
  assert.equal(fromDir.name, "einhander/pcb");
  assert.deepEqual(await resolveProject(fromDir.board), fromDir);
  assert.deepEqual(await resolveProject(fromDir.source), fromDir);
  assert.deepEqual(await resolveProject(FIXTURE), fromDir); // finds pcb/
  await assert.rejects(resolveProject(path.join(FIXTURE, "README.md")), /not a board/);
});

test("open_board summarises the shipped board", { skip }, async () => {
  const client = await connect();
  const r = await client.callTool({ name: "open_board", arguments: { path: SHIPPED } });
  assert.ok(!r.isError, text(r));
  const d = r.structuredContent;
  assert.deepEqual(d.board.copperLayers, ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]);
  assert.equal(d.board.metrics.track_mm_total, 1463.8); // matches pcbnew (board_metrics.py)
  assert.equal(d.board.metrics.vias, 49);
  assert.equal(d.board.metrics.zone_net_track_mm, 484.5);
  assert.deepEqual(d.layers, ["B.Silkscreen", "B.Cu", "In2.Cu", "In1.Cu", "F.Cu", "F.Silkscreen", "Edge.Cuts"]);
  assert.match(text(r), /4 copper layers, 42 footprints/);
});

test("load_view: a layer SVG in board coordinates, DRC markers, and the 3D model", { skip }, async () => {
  const client = await connect();
  const layer = await client.callTool({ name: "load_view", arguments: { path: SHIPPED, view: "layer", layer: "F.Cu" } });
  assert.ok(!layer.isError, text(layer));
  // Not fit-to-board: the page is A4 and units are board millimetres.
  assert.match(layer.structuredContent.svg, /viewBox="0\.0000 0\.0000 297\.\d+ 210\.\d+"/);
  await assert.rejects(client.callTool({ name: "load_view", arguments: { path: SHIPPED, view: "layer", layer: "../x" } }).then((r) => (r.isError ? Promise.reject(new Error(text(r))) : r)), /bad layer/);

  const drc = await client.callTool({ name: "load_view", arguments: { path: SHIPPED, view: "drc" } });
  assert.ok(!drc.isError, text(drc));
  assert.equal(drc.structuredContent.unconnected, 0);

  const rerun = await client.callTool({ name: "load_view", arguments: { path: RERUN, view: "drc" } });
  assert.equal(rerun.structuredContent.unconnected, 2); // QSPI_SCLK + one USB_DP pad
  const un = rerun.structuredContent.markers.filter((m) => m.kind === "unconnected");
  assert.ok(un.every((m) => m.items.length === 2 && m.items.every((i) => i.x > 50 && i.x < 150)));

  const glb = await client.callTool({ name: "load_view", arguments: { path: SHIPPED, view: "glb" } });
  assert.ok(!glb.isError, text(glb));
  assert.equal(Buffer.from(glb.structuredContent.glb, "base64").subarray(0, 4).toString(), "glTF");
});

test("check_board: shipped passes, the unattended re-route is blocked by 2 open nets", { skip }, async () => {
  const client = await connect();
  const shipped = await client.callTool({ name: "check_board", arguments: { path: SHIPPED, verbose: false } });
  assert.ok(!shipped.isError, text(shipped));
  assert.equal(shipped.structuredContent.ok, true, text(shipped));
  const rerun = await client.callTool({ name: "check_board", arguments: { path: RERUN } });
  assert.equal(rerun.structuredContent.ok, false);
  assert.equal(rerun.structuredContent.gates.find((g) => g.name === "drc_check").ok, false);
  assert.match(text(rerun), /unconnected=2/);
  assert.match(text(rerun), /507 mm of it on plane\/pour nets \(GND, V3V3\)/);
});

test("schematic and netlist come from the tscircuit design", { skip, timeout: 240_000 }, async () => {
  const client = await connect();
  const sch = await client.callTool({ name: "load_view", arguments: { path: SHIPPED, view: "schematic" } });
  assert.ok(!sch.isError, text(sch));
  assert.match(sch.structuredContent.svg, /^<svg[^>]*tscircuit-schematic/);
  const net = await client.callTool({ name: "get_netlist", arguments: { path: SHIPPED } });
  assert.ok(!net.isError, text(net));
  assert.match(text(net), /U1: RP2040/);
});

test("errors name the problem", async () => {
  const client = await connect();
  const r = await client.callTool({ name: "open_board", arguments: { path: "/nonexistent/board" } });
  assert.ok(r.isError);
  assert.match(text(r), /does not exist/);
});
