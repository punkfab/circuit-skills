#!/usr/bin/env node
// place_kicad.mjs — the part-level core of place_kicad.py: autoplace.mjs's annealer over single parts,
// then untangle.mjs's rotation pass, with restarts. Reads and writes the JSON place_kicad.py exchanges.
//
//   node place_kicad.mjs problem.json solution.json [--restarts 6] [--seed 1]
//
// problem:  { bbox:[x0,y0,x1,y1], parts:[{ref,w,h,cx,cy,locked,pads:[{net,off:[dx,dy]}]}] }  (mm, Y up,
//           pad offsets from the body centre at rotation 0)
// solution: { parts:{ref:{cx,cy,rot}}, hpwl, overlap }
import { readFileSync, writeFileSync } from "node:fs";
import { anneal, totalCost, blockBox, rectOverlap } from "./autoplace.mjs";
import { untangle, totalHPWL } from "./untangle.mjs";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? Number(args[i + 1]) : d; };
const prob = JSON.parse(readFileSync(args[0], "utf8"));
const FANOUT = 8, MARGIN = 0.5;

function rng32(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), a | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// nets -> members; signal nets only (a high-fanout net is a pour or a rail and would pull everything together)
const nets = {};
for (const p of prob.parts) for (const pad of p.pads) (nets[pad.net] ||= []).push({ ref: p.ref, off: pad.off });
for (const [n, m] of Object.entries(nets)) if (new Set(m.map((x) => x.ref)).size < 2 || new Set(m.map((x) => x.ref)).size > FANOUT) delete nets[n];
const parts = {};
for (const p of prob.parts) parts[p.ref] = { w: p.w, h: p.h, nets: Object.keys(nets).filter((n) => nets[n].some((m) => m.ref === p.ref)) };
const ew = {};
for (const m of Object.values(nets)) {
  const refs = [...new Set(m.map((x) => x.ref))];
  for (let i = 0; i < refs.length; i++) for (let j = i + 1; j < refs.length; j++) { const k = [refs[i], refs[j]].sort().join("|"); ew[k] = (ew[k] || 0) + 1 / (refs.length - 1); }
}
const edges = Object.entries(ew).map(([k, w]) => { const [a, b] = k.split("|"); return { a, b, w }; });

const n = prob.parts.length, [x0, y0, x1, y1] = prob.bbox;
const iters = Math.max(4000, Math.min(60000, Math.round(6e7 / (n * n))));
let best = null;
for (let r = 0; r < opt("--restarts", 6); r++) {
  const rng = rng32(opt("--seed", 1) * 1000 + r);
  const blocks = prob.parts.map((p) => ({ name: p.ref, w: p.w + MARGIN, h: p.h + MARGIN, rot: 0, locked: p.locked,
    cx: p.locked ? p.cx : x0 + rng() * (x1 - x0), cy: p.locked ? p.cy : y0 + rng() * (y1 - y0) }));
  const byName = Object.fromEntries(blocks.map((b) => [b.name, b]));
  const env = { blocks, byName, edges, cuts: [], poly: [], bbox: prob.bbox };
  anneal(env, { iters, T0: Math.max(x1 - x0, y1 - y0) / 4, rng });
  const place = Object.fromEntries(blocks.map((b) => [b.name, { cx: b.cx, cy: b.cy, rot: b.rot ? 90 : 0 }]));
  const free = Object.fromEntries(Object.entries(parts).filter(([ref]) => !byName[ref].locked));
  untangle(free, nets, place, { poly: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], cuts: [] });
  let overlap = 0;
  const boxes = blocks.map((b) => blockBox({ ...b, w: b.w - MARGIN, h: b.h - MARGIN }));
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (!(blocks[i].locked && blocks[j].locked)) overlap += rectOverlap(boxes[i], boxes[j]);
  const off = totalCost(env) >= 1e4 ? 1 : 0;  // a penalty term is still active: something overlaps or is off the board
  const hpwl = totalHPWL(parts, nets, place);
  const bad = (overlap > 1e-6 ? 2 : 0) + off;  // legal first, then shortest
  if (!best || bad < best.bad || (bad === best.bad && hpwl < best.hpwl)) best = { bad, parts: place, hpwl, overlap };
}
writeFileSync(args[1], JSON.stringify({ parts: best.parts, hpwl: +best.hpwl.toFixed(1), overlap: +best.overlap.toFixed(3), iters, nets: Object.keys(nets).length }));
console.log(`place_kicad: ${n} parts, ${Object.keys(nets).length} signal nets, ${iters} iterations x ${opt("--restarts", 6)} restarts -> HPWL ${best.hpwl.toFixed(1)} mm, overlap ${best.overlap.toFixed(2)} mm2`);
