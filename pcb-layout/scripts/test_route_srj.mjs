// route_srj.mjs without the router: KiCad -> SimpleRouteJson conversion, and routes -> KiCad.
//   node --test pcb-layout/scripts/test_route_srj.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import { boardToSrj, readRules, routesToKicad, stripRouting } from "./route_srj.mjs";

const BOARD = `(kicad_pcb (version 20241229)
  (layers (0 "F.Cu" signal) (4 "In1.Cu" signal) (6 "In2.Cu" signal) (2 "B.Cu" signal) (25 "Edge.Cuts" user))
  (net 0 "") (net 1 "GND") (net 2 "SIG") (net 3 "unconnected-(U1-Pad9)")
  (gr_rect (start 0 0) (end 40 30) (layer "Edge.Cuts"))
  (footprint "R" (layer "F.Cu") (at 10 10 90) (property "Reference" "R1")
    (pad "1" smd rect (at 1 0) (size 0.5 0.6) (layers "F.Cu" "F.Mask") (net 2 "SIG"))
    (pad "2" smd rect (at -1 0) (size 0.5 0.6) (layers "F.Cu" "F.Mask") (net 1 "GND")))
  (footprint "J" (layer "F.Cu") (at 20 20) (property "Reference" "J1")
    (pad "1" thru_hole circle (at 0 0) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask") (net 2 "SIG"))
    (pad "13" smd custom (at 3 0) (size 0.2 0.2) (layers "F.Cu") (net 1 "GND")
      (primitives (gr_poly (pts (xy -0.3 -0.65) (xy 0.3 -0.65) (xy 0.3 0.65) (xy -0.3 0.65)) (width 0) (fill yes))))
    (pad "" np_thru_hole circle (at 5 0) (size 1 1) (drill 1) (layers "*.Cu")))
  (footprint "U" (layer "B.Cu") (at 30 10) (property "Reference" "U1")
    (pad "9" smd rect (at 0 0) (size 0.3 0.3) (layers "B.Cu") (net 3 "unconnected-(U1-Pad9)"))
    (pad "1" smd rect (at 1 0) (size 0.3 0.3) (layers "B.Cu") (net 1 "GND")))
  (segment (start 1 1) (end 2 2) (width 0.2) (layer "F.Cu") (net 2) (uuid "a"))
  (via (at 2 2) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net 2) (uuid "b"))
  (zone (net 1) (net_name "GND") (layer "In1.Cu"))
)`;

test("rules: JLCPCB defaults and floors", () => {
  const r = readRules("/nonexistent/x.kicad_pcb", { clearance: 0.1, drill: 0.2 });
  assert.equal(r.clearance, 0.127);
  assert.equal(r.drill, 0.3);
  assert.equal(r.via, 0.6);
});

test("conversion: pads, rotation, custom pads, holes, nets, layers", () => {
  const { srj, mode } = boardToSrj(BOARD, { layers: "auto" });
  assert.equal(mode, "outer"); // an inner-layer zone: the inner layers are planes
  assert.equal(srj.layerCount, 2);
  assert.deepEqual(srj.bounds, { minX: 0, maxX: 40, minY: -30, maxY: 0 });
  const ob = Object.fromEntries(srj.obstacles.map((o) => [o.obstacleId, o]));
  // R1 at 90 degrees: local (1,0) lands at (10,9) in KiCad, (10,-9) in the router's Y-up frame.
  assert.ok(Math.abs(ob["R1.1"].center.x - 10) < 1e-9 && Math.abs(ob["R1.1"].center.y + 9) < 1e-9);
  // The custom pad is its primitives' copper (0.6 x 1.3), not its 0.2 mm anchor.
  assert.ok(Math.abs(ob["J1.13"].width - 0.6) < 1e-9 && Math.abs(ob["J1.13"].height - 1.3) < 1e-9);
  assert.equal(ob["J1.npth"].isNonPlatedHole, true);
  assert.deepEqual(ob["J1.npth"].connectedTo, []);
  // Through-hole pads are on the routable layers only when the inner layers are planes.
  assert.deepEqual(ob["J1.1"].layers, ["top", "bottom"]);
  // An unconnected-* pad is an obstacle on no net, and not a connection.
  assert.deepEqual(ob["U1.9"].connectedTo, []);
  const conns = Object.fromEntries(srj.connections.map((c) => [c.name, c.pointsToConnect]));
  assert.deepEqual(Object.keys(conns).sort(), ["GND", "SIG"]);
  assert.equal(conns.GND.length, 3);
  assert.deepEqual(conns.SIG.find((p) => p.layers).layers, ["top", "bottom"]);
  assert.equal(srj.minViaHoleDiameter, 0.3);
  const all = boardToSrj(BOARD, { layers: "all" }).srj;
  assert.equal(all.layerCount, 4);
  assert.deepEqual(all.obstacles.find((o) => o.obstacleId === "J1.1").layers, ["top", "inner1", "inner2", "bottom"]);
});

test("routes back to KiCad: Y flipped, nets numbered, duplicate vias merged", () => {
  const nets = new Map([["SIG", 2], ["GND", 1]]);
  const traces = [
    { connection_name: "SIG", route: [
      { route_type: "wire", x: 1, y: -1, width: 0.2, layer: "top" },
      { route_type: "wire", x: 3, y: -1, width: 0.2, layer: "top" },
      { route_type: "via", x: 3, y: -1, from_layer: "top", to_layer: "bottom" },
      { route_type: "wire", x: 3, y: -1, width: 0.2, layer: "bottom" },
      { route_type: "wire", x: 3, y: -4, width: 0.2, layer: "bottom" },
    ] },
    { connection_name: "SIG__part2", route: [{ route_type: "via", x: 3, y: -1, from_layer: "top", to_layer: "bottom" }] },
  ];
  const { items, segments, vias, duplicates } = routesToKicad(traces, nets, { via: 0.6, drill: 0.3, trace: 0.2 });
  assert.equal(segments, 2);
  assert.equal(vias, 1);
  assert.equal(duplicates, 1);
  assert.match(items[0], /\(segment \(start 1\.0000 1\.0000\) \(end 3\.0000 1\.0000\) \(width 0\.2000\) \(layer "F\.Cu"\) \(net 2\)/);
  assert.match(items.join("\n"), /\(via \(at 3\.0000 1\.0000\) \(size 0\.6\) \(drill 0\.3\)/);
  assert.match(items.join("\n"), /\(layer "B\.Cu"\)/);
});

test("stripRouting drops top-level tracks and vias only", () => {
  const out = stripRouting(BOARD);
  assert.doesNotMatch(out, /\(segment|\(via \(at 2 2/);
  assert.match(out, /\(footprint "R"/);
  assert.match(out, /\(zone \(net 1\)/);
  assert.match(out, /\(pad "1" thru_hole/);
});

test("a round board's bounds are its circle, not the circle's center and rim point", () => {
  const round = BOARD.replace('(gr_rect (start 0 0) (end 40 30) (layer "Edge.Cuts"))', '(gr_circle (center 20 15) (end 35 15) (layer "Edge.Cuts"))');
  assert.deepEqual(boardToSrj(round, { layers: "auto" }).srj.bounds, { minX: 5, maxX: 35, minY: -30, maxY: 0 });
});

test("rules: the board's own minimum track width floors neck-down, and net classes set per-net widths", async () => {
  const { mkdtempSync, writeFileSync } = await import("node:fs");
  const dir = mkdtempSync("/tmp/route_srj_test-");
  writeFileSync(`${dir}/b.kicad_pro`, JSON.stringify({
    board: { design_settings: { rules: { min_track_width: 0.254 } } },
    net_settings: { classes: [{ name: "Default", track_width: 0.254, clearance: 0.2 }, { name: "Power", track_width: 0.8 }],
      netclass_patterns: [{ pattern: "GND", netclass: "Power" }] },
  }));
  const r = readRules(`${dir}/b.kicad_pcb`);
  assert.equal(r.minTrace, 0.254);
  assert.equal(r.netWidth("GND"), 0.8);
  assert.equal(r.netWidth("SIG"), undefined);
  const conns = Object.fromEntries(boardToSrj(BOARD, { layers: "auto", rules: r }).srj.connections.map((c) => [c.name, c]));
  assert.equal(conns.GND.nominalTraceWidth, 0.8);
  assert.equal(conns.SIG.nominalTraceWidth, undefined);
});

test("a shaped outline becomes the router's outline polygon, and interior cutouts become obstacles", () => {
  // An L-shaped board drawn as six chained lines (two of them reversed), with a round hole and a rect window.
  const edges = [[0, 0, 40, 0], [40, 0, 40, 15], [20, 15, 40, 15], [20, 15, 20, 30], [20, 30, 0, 30], [0, 30, 0, 0]]
    .map(([a, b, c, d]) => `(gr_line (start ${a} ${b}) (end ${c} ${d}) (layer "Edge.Cuts"))`).join("\n  ");
  const shaped = BOARD.replace('(gr_rect (start 0 0) (end 40 30) (layer "Edge.Cuts"))',
    `${edges}\n  (gr_circle (center 5 25) (end 7 25) (layer "Edge.Cuts"))\n  (gr_rect (start 30 3) (end 36 7) (layer "Edge.Cuts"))`);
  const { srj } = boardToSrj(shaped, { layers: "auto" });
  assert.deepEqual(srj.bounds, { minX: 0, maxX: 40, minY: -30, maxY: 0 });
  assert.equal(srj.outline.length, 6);
  assert.ok(srj.outline.some((p) => p.x === 20 && p.y === -15)); // the inside corner of the L
  const cut = srj.obstacles.filter((o) => o.obstacleId.startsWith("cutout."));
  assert.equal(cut.length, 2);
  const hole = cut.find((o) => Math.abs(o.center.x - 5) < 1e-6);
  assert.ok(Math.abs(hole.width - 4) < 1e-6 && Math.abs(hole.center.y + 25) < 1e-6);
  assert.deepEqual(cut[0].connectedTo, []);
  // A plain rectangle stays bounds-only.
  assert.equal(boardToSrj(BOARD, { layers: "auto" }).srj.outline, undefined);
});
