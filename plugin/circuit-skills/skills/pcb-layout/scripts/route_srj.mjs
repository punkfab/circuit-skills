#!/usr/bin/env node
// route_srj.mjs — route ANY KiCad board with tscircuit's capacity autorouter, run locally.
//
// The fourth backend. Unlike route_tscircuit.mjs (which needs the tscircuit design and its
// project's router version), this converts the .kicad_pcb itself into the router's
// SimpleRouteJson: every pad as an obstacle at its real copper extent (custom pad primitives
// included) tagged with its net, drilled holes, the board bounds, and the fab's via sizes and
// clearances. It routes from scratch (existing tracks and vias are dropped), writes the routes back
// as KiCad segments and vias into a fresh candidate board, removes duplicate stacked vias, and
// refills the zones so plane antipads match the new vias.
//
//   node route_srj.mjs board.kicad_pcb -o build/srj.kicad_pcb [--layers auto|all|outer] [--time 300]
//        [--trace 0.2] [--min-trace 0.15] [--clearance 0.15] [--via 0.6] [--drill 0.3]
//        [--board live.kicad_pcb] [--srj-only out.srj.json] [--no-refill]
//
//   --layers   all: route on every copper layer. outer: F.Cu/B.Cu only (inner layers are planes).
//              auto (default): outer when the board has zones on inner layers, else all.
//   rules      the .kicad_pro's Default netclass (track, clearance, via) when present, else JLCPCB
//              minimums; the flags override. Never below 0.127 clearance / 0.3 drill / 0.6 via.
//   --board    write live status to <board>.routing.json for the viewer (backend "srj").
//   --srj-only write the router input and stop (for inspecting or filing router bug reports).
//
// Needs Node 18+ and the router package: npm install --prefix <this folder>/srj (or set
// CAPACITY_AUTOROUTER to a folder containing @tscircuit/capacity-autorouter). Zone refill uses
// KiCad's pcbnew module (CIRCUIT_SKILLS_KICAD_PYTHON, default /usr/bin/python3); without it the
// candidate is written unfilled and says so. The output must not exist yet.
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const home = (p) => p.replace(/^~(?=$|\/)/, os.homedir());

// ---- s-expressions ------------------------------------------------------------------------
export function parseSExpr(text) {
  const stack = [[]];
  for (let i = 0; i < text.length; ) {
    const c = text[i];
    if (c === "(") { const l = []; stack.at(-1).push(l); stack.push(l); i++; }
    else if (c === ")") { stack.pop(); i++; }
    else if (c === '"') {
      let j = i + 1, s = "";
      while (j < text.length && text[j] !== '"') { if (text[j] === "\\") { s += text[j + 1]; j += 2; } else s += text[j++]; }
      stack.at(-1).push(s); i = j + 1;
    } else if (" \n\t\r".includes(c)) i++;
    else { let j = i; while (j < text.length && !" \n\t\r()".includes(text[j])) j++; stack.at(-1).push(text.slice(i, j)); i = j; }
  }
  return stack[0][0];
}
const kids = (e, name) => (Array.isArray(e) ? e.filter((c) => Array.isArray(c) && c[0] === name) : []);
const kid = (e, name) => kids(e, name)[0];
const num = (e, i = 1) => (e ? Number(e[i]) : NaN);
const str = (e, i = 1) => (e && typeof e[i] === "string" ? e[i] : undefined);

// ---- KiCad -> SimpleRouteJson ----------------------------------------------------------------
const rot = (x, y, deg) => { const t = (deg * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t); return [x * c + y * s, -x * s + y * c]; }; // KiCad: +deg is CCW on screen, Y down

/** Rules: Default netclass of the .kicad_pro beside the board, floored at JLCPCB minimums, then flags. */
export function readRules(boardPath, flags = {}) {
  const r = { trace: 0.2, minTrace: 0.15, clearance: 0.15, via: 0.6, drill: 0.3 };
  const pro = boardPath.replace(/\.kicad_pcb$/, ".kicad_pro");
  try {
    const cls = JSON.parse(readFileSync(pro, "utf8")).net_settings?.classes?.find((c) => c.name === "Default");
    if (cls) {
      if (cls.track_width) r.trace = cls.track_width;
      if (cls.clearance) r.clearance = cls.clearance;
      if (cls.via_diameter) r.via = cls.via_diameter;
      if (cls.via_drill) r.drill = cls.via_drill;
    }
  } catch { /* no project file: JLCPCB defaults */ }
  for (const k of Object.keys(r)) if (flags[k] !== undefined) r[k] = flags[k];
  r.clearance = Math.max(r.clearance, 0.127);
  r.drill = Math.max(r.drill, 0.3);
  r.via = Math.max(r.via, 0.6, r.drill + 0.26);
  r.minTrace = Math.min(r.minTrace, r.trace);
  return r;
}

export function boardToSrj(text, opts = {}) {
  const root = parseSExpr(text);
  const copper = (kid(root, "layers") ?? []).filter((l) => Array.isArray(l) && /\.Cu$/.test(l[1] ?? "")).map((l) => l[1]);
  const inner = copper.filter((l) => /^In\d+\.Cu$/.test(l)).sort((a, b) => parseInt(a.slice(2)) - parseInt(b.slice(2)));
  const all = ["top", ...inner.map((l) => `inner${parseInt(l.slice(2))}`), "bottom"];
  const zones = kids(root, "zone").filter((z) => !kid(z, "keepout"));
  const zoneLayers = zones.flatMap((z) => [...(kid(z, "layers") ?? []).slice(1), ...(kid(z, "layer") ?? []).slice(1)]);
  const mode = opts.layers && opts.layers !== "auto" ? opts.layers : zoneLayers.some((l) => /^In\d+\.Cu$/.test(l)) ? "outer" : "all";
  const routable = mode === "outer" || all.length === 2 ? ["top", "bottom"] : all;
  const toSrj = (l) => (l === "F.Cu" ? "top" : l === "B.Cu" ? "bottom" : `inner${parseInt(l.slice(2))}`);
  const r = opts.rules ?? { trace: 0.2, minTrace: 0.15, clearance: 0.15, via: 0.6, drill: 0.3 };

  const obstacles = [];
  const byNet = new Map();
  for (const fp of kids(root, "footprint")) {
    const at = kid(fp, "at");
    const fx = num(at, 1), fy = num(at, 2), fr = num(at, 3) || 0;
    const ref = str(kids(fp, "property").find((p) => p[1] === "Reference"), 2) ?? "?";
    for (const pad of kids(fp, "pad")) {
      const [ox, oy] = rot(num(kid(pad, "at"), 1), num(kid(pad, "at"), 2), fr);
      const x = fx + ox, y = fy + oy;
      const a = num(kid(pad, "at"), 3) || 0; // absolute in the file
      const size = kid(pad, "size");
      let w = num(size, 1), h = num(size, 2), cx = x, cy = y, ccw = a;
      const prims = kid(pad, "primitives");
      if (prims) {
        // Custom pad: the copper is the anchor plus its primitives. Use their extent, axis-aligned.
        const pts = [[-w / 2, -h / 2], [w / 2, h / 2]];
        for (const g of prims.slice(1)) {
          const pw = (num(kid(g, "width")) || 0) / 2;
          const add = (px, py) => pts.push([px - pw, py - pw], [px + pw, py + pw]);
          for (const xy of kids(kid(g, "pts") ?? [], "xy")) add(num(xy, 1), num(xy, 2));
          for (const k of ["start", "end", "mid"]) { const p = kid(g, k); if (p) add(num(p, 1), num(p, 2)); }
          if (g[0] === "gr_circle") { const c = kid(g, "center"), e = kid(g, "end"); const rr = Math.hypot(num(e, 1) - num(c, 1), num(e, 2) - num(c, 2)); add(num(c, 1) - rr, num(c, 2) - rr); add(num(c, 1) + rr, num(c, 2) + rr); }
        }
        // The local box of anchor + primitives, its four corners rotated into the board: axis-aligned.
        const lx = pts.map((p) => p[0]), ly = pts.map((p) => p[1]);
        const corners = [[Math.min(...lx), Math.min(...ly)], [Math.max(...lx), Math.min(...ly)], [Math.min(...lx), Math.max(...ly)], [Math.max(...lx), Math.max(...ly)]].map(([px, py]) => rot(px, py, a));
        const X = corners.map((p) => p[0]), Y = corners.map((p) => p[1]);
        w = Math.max(...X) - Math.min(...X); h = Math.max(...Y) - Math.min(...Y);
        cx = x + (Math.max(...X) + Math.min(...X)) / 2; cy = y + (Math.max(...Y) + Math.min(...Y)) / 2; ccw = 0;
      }
      const type = str(pad, 2);
      const layers = (kid(pad, "layers") ?? []).slice(1);
      const through = type === "thru_hole" || type === "np_thru_hole" || layers.includes("*.Cu");
      const padLayers = through ? all : layers.filter((l) => /\.Cu$/.test(l)).map(toSrj);
      const net = str(kid(pad, "net"), 2) ?? "";
      const named = net && !net.startsWith("unconnected-") ? net : "";
      if (type === "np_thru_hole") {
        const d = num(kid(pad, "drill"), 1) || Math.min(w, h);
        obstacles.push({ type: "rect", layers: all, center: { x, y: -y }, width: d, height: d, connectedTo: [], isNonPlatedHole: true, obstacleId: `${ref}.npth` });
        continue;
      }
      if (!padLayers.length) continue;
      obstacles.push({ type: "rect", layers: padLayers, center: { x: cx, y: -cy }, width: w, height: h, ccwRotationDegrees: ccw, connectedTo: named ? [named] : [], obstacleId: `${ref}.${str(pad, 1) ?? ""}` });
      if (!named) continue;
      const list = byNet.get(named) ?? [];
      list.push(through ? { x, y: -y, layers: routable } : { x, y: -y, layer: padLayers[0] });
      byNet.set(named, list);
    }
  }
  // Board-level drilled holes (mounting holes drawn as gr_circle on Edge.Cuts are outline, not obstacles).
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const g of root.filter((e) => Array.isArray(e) && String(e[0]).startsWith("gr_") && str(kid(e, "layer")) === "Edge.Cuts")) {
    for (const k of ["start", "end", "mid", "center"]) { const p = kid(g, k); if (p) { x0 = Math.min(x0, num(p, 1)); x1 = Math.max(x1, num(p, 1)); y0 = Math.min(y0, num(p, 2)); y1 = Math.max(y1, num(p, 2)); } }
    for (const xy of kids(kid(g, "pts") ?? [], "xy")) { x0 = Math.min(x0, num(xy, 1)); x1 = Math.max(x1, num(xy, 1)); y0 = Math.min(y0, num(xy, 2)); y1 = Math.max(y1, num(xy, 2)); }
  }
  if (!Number.isFinite(x0)) throw new Error("no Edge.Cuts outline");
  const connections = [...byNet].filter(([, p]) => p.length >= 2).map(([name, pointsToConnect]) => ({ name, pointsToConnect }));
  const used = mode === "outer" ? obstacles.map((o) => ({ ...o, layers: o.layers.filter((l) => routable.includes(l)) })).filter((o) => o.layers.length) : obstacles;
  return {
    mode,
    srj: {
      layerCount: routable.length,
      minTraceWidth: r.minTrace, nominalTraceWidth: r.trace,
      minViaHoleDiameter: r.drill, minViaPadDiameter: r.via, minViaDiameter: r.via,
      defaultObstacleMargin: r.clearance, minTraceToPadEdgeClearance: r.clearance, minTraceToHoleEdgeClearance: Math.max(r.clearance, 0.25),
      minBoardEdgeClearance: 0.3, minViaEdgeToPadEdgeClearance: r.clearance,
      minViaHoleEdgeToViaHoleEdgeClearance: 0.5, minPlatedHoleDrillEdgeToDrillEdgeClearance: 0.5,
      obstacles: used, connections,
      bounds: { minX: x0, maxX: x1, minY: 0 - y1, maxY: 0 - y0 }, // 0 - v: no -0 at the origin
    },
  };
}

// ---- routes -> KiCad -----------------------------------------------------------------------------
/** The board text without its top-level segments, arcs and vias. */
export function stripRouting(src) {
  let depth = 0, res = "", skipping = false;
  for (let i = 0; i < src.length; ) {
    const ch = src[i];
    if (ch === '"') {
      let j = i + 1;
      while (j < src.length && src[j] !== '"') j += src[j] === "\\" ? 2 : 1;
      if (!skipping) res += src.slice(i, j + 1);
      i = j + 1; continue;
    }
    if (ch === "(" && depth === 1 && /^\((segment|arc|via)\b/.test(src.slice(i, i + 9))) skipping = true;
    if (ch === "(") depth++;
    if (!skipping) res += ch;
    if (ch === ")") { depth--; if (depth === 1 && skipping) skipping = false; }
    i++;
  }
  return res.replace(/\n\s*\n\s*\n/g, "\n\n");
}

export function routesToKicad(traces, netNumbers, rules) {
  const toKicad = (l) => (l === "top" ? "F.Cu" : l === "bottom" ? "B.Cu" : `In${l.replace("inner", "")}.Cu`);
  const items = [];
  const vias = new Map(); // "x,y" -> net : duplicates of one net at one spot are one via
  let segments = 0, duplicates = 0;
  for (const t of traces) {
    const name = t.connection_name ?? "";
    const net = netNumbers.get(name) ?? netNumbers.get(name.replace(/__.*$/, "")) ?? 0;
    const r = t.route ?? [];
    for (let i = 0; i < r.length; i++) {
      const p = r[i];
      if (p.route_type === "via") {
        const key = `${p.x.toFixed(3)},${p.y.toFixed(3)}`;
        if (vias.get(key) === net) { duplicates++; continue; }
        vias.set(key, net);
        items.push(`\t(via (at ${p.x.toFixed(4)} ${(-p.y).toFixed(4)}) (size ${rules.via}) (drill ${rules.drill}) (layers "F.Cu" "B.Cu") (net ${net}) (uuid "${randomUUID()}"))`);
      } else if (p.route_type === "wire" && i > 0 && r[i - 1].route_type === "wire" && r[i - 1].layer === p.layer) {
        const q = r[i - 1];
        if (Math.abs(q.x - p.x) < 1e-6 && Math.abs(q.y - p.y) < 1e-6) continue;
        items.push(`\t(segment (start ${q.x.toFixed(4)} ${(-q.y).toFixed(4)}) (end ${p.x.toFixed(4)} ${(-p.y).toFixed(4)}) (width ${(p.width ?? rules.trace).toFixed(4)}) (layer "${toKicad(p.layer)}") (net ${net}) (uuid "${randomUUID()}"))`);
        segments++;
      }
    }
  }
  return { items, segments, vias: vias.size, duplicates };
}

// ---- main --------------------------------------------------------------------------------------
async function main() {
  const args = process.argv.slice(2);
  const o = { layers: "auto", time: Number(process.env.MAXT || 300), refill: true, flags: {} };
  let input;
  const usage = (m) => { if (m) console.error(`route_srj: ${m}`); console.error("usage: route_srj.mjs <board.kicad_pcb> -o <out.kicad_pcb> [--layers auto|all|outer] [--time S] [--trace W] [--min-trace W] [--clearance C] [--via D] [--drill D] [--board PATH] [--srj-only OUT] [--no-refill]"); process.exit(2); };
  for (let i = 0; i < args.length; i++) {
    const a = args[i], v = () => args[++i] ?? usage(`${a} needs a value`);
    if (a === "-o" || a === "--output") o.output = v();
    else if (a === "--layers") o.layers = v();
    else if (a === "--time") o.time = Number(v());
    else if (a === "--board") o.board = v();
    else if (a === "--srj-only") o.srjOnly = v();
    else if (a === "--no-refill") o.refill = false;
    else if (["--trace", "--min-trace", "--clearance", "--via", "--drill"].includes(a)) o.flags[a.slice(2).replace("-t", "T")] = Number(v());
    else if (a === "-h" || a === "--help") usage();
    else if (!input) input = a;
    else usage(`unexpected ${a}`);
  }
  if (!input || (!o.output && !o.srjOnly)) usage();
  if (!["auto", "all", "outer"].includes(o.layers)) usage("--layers is auto, all or outer");
  input = path.resolve(home(input));
  const text = readFileSync(input, "utf8");
  const rules = readRules(input, o.flags);
  const { srj, mode } = boardToSrj(text, { layers: o.layers, rules });
  const tag = `${srj.connections.length} connections, ${srj.obstacles.length} obstacles, ${srj.layerCount} layers (${mode}); trace ${rules.trace}, clearance ${rules.clearance}, via ${rules.via}/${rules.drill}`;
  if (o.srjOnly) { writeFileSync(path.resolve(home(o.srjOnly)), JSON.stringify(srj, null, 1)); console.log(`srj: wrote router input: ${tag}`); return 0; }

  const output = path.resolve(home(o.output));
  if (existsSync(output)) usage(`output exists; choose a fresh candidate: ${output}`);
  mkdirSync(path.dirname(output), { recursive: true });
  const started = Date.now();
  const status = o.board ? path.resolve(home(o.board)) + ".routing.json" : null;
  const publish = (state, message) => {
    if (status) { writeFileSync(status + ".tmp", JSON.stringify({ backend: "srj", state, message, elapsed_s: Math.round((Date.now() - started) / 100) / 10, output }) + "\n"); renameSync(status + ".tmp", status); }
    console.log(`srj: ${state} · ${message}`);
  };

  let mod;
  const base = process.env.CAPACITY_AUTOROUTER ? path.resolve(home(process.env.CAPACITY_AUTOROUTER)) : path.join(HERE, "srj");
  try { mod = await import(pathToFileURL(createRequire(path.join(base, "package.json")).resolve("@tscircuit/capacity-autorouter")).href); }
  catch { usage(`the router is not installed: npm install --prefix ${path.join(HERE, "srj")}  (or set CAPACITY_AUTOROUTER)`); }

  publish("running", `routing ${tag}; KiCad verification pending`);
  const solver = new mod.AutoroutingPipelineSolver(srj);
  let lastTick = Date.now();
  while (!solver.solved && !solver.failed && Date.now() - started < o.time * 1000) {
    solver.step();
    if (Date.now() - lastTick > 2000) { lastTick = Date.now(); publish("running", `${Math.round((Date.now() - started) / 1000)}s elapsed${solver.getCurrentPhase ? ` · ${solver.getCurrentPhase()}` : ""}; KiCad verification pending`); }
  }
  if (!solver.solved) {
    publish("failed", solver.failed ? `router failed: ${String(solver.error).slice(0, 300)}` : `no solution within ${o.time}s`);
    return 1;
  }
  const traces = solver.getOutputSimpleRouteJson().traces ?? [];
  // The router's own output beside the candidate: for debugging and for router bug reports.
  writeFileSync(output + ".routes.json", JSON.stringify(traces));
  const netNumbers = new Map(kids(parseSExpr(text), "net").map((n) => [str(n, 2) ?? "", Number(n[1])]));
  const { items, segments, vias, duplicates } = routesToKicad(traces, netNumbers, rules);
  const stripped = stripRouting(text);
  const end = stripped.lastIndexOf(")");
  writeFileSync(output, stripped.slice(0, end) + items.join("\n") + "\n)\n");

  let refill = "zones not refilled (--no-refill)";
  if (o.refill) {
    const py = process.env.CIRCUIT_SKILLS_KICAD_PYTHON ?? (existsSync("/usr/bin/python3") ? "/usr/bin/python3" : "python3");
    try {
      execFileSync(py, ["-c", "import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1], b); print(len(b.Zones()))", output], { stdio: ["ignore", "pipe", "pipe"], timeout: 300_000 });
      refill = "zones refilled";
    } catch (e) {
      refill = `zones NOT refilled (${py} has no pcbnew?): refill before DRC`;
    }
  }
  publish("candidate", `${segments} segments, ${vias} vias${duplicates ? ` (${duplicates} duplicate vias merged)` : ""} for ${new Set(traces.map((t) => t.connection_name)).size} connections in ${Math.round((Date.now() - started) / 1000)}s; ${refill}; run the gates`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().then((c) => process.exit(c), (e) => { console.error(`route_srj: ${e.stack ?? e}`); process.exit(1); });
