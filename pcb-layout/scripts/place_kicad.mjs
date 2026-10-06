#!/usr/bin/env node
// place_kicad.mjs — the placer core behind place_kicad.py: simulated annealing over single parts
// (position and 0/90/180/270 rotation), then a push-apart pass that makes the result legal.
//
//   node place_kicad.mjs problem.json solution.json [--restarts 4] [--seed 1] [--hint-weight 4]
//
// problem  { bbox:[x0,y0,x1,y1], poly:[[x,y],...], cuts:[[x0,y0,x1,y1],...],
//            parts:[{ref,w,h,cx,cy,locked,side,through,pads:[{net,num,off:[dx,dy]}]}], hints:[...] }
//          mm, Y up; pad offsets from the body centre at rotation 0.
// solution { parts:{ref:{cx,cy,rot}}, hpwl, overlap, outside, hints:[{text,miss}] }
//
// Cost = signal-net wirelength at pad level (half-perimeter, so rotation counts)
//      + a hard penalty for bodies that overlap (same side, or either one through-hole) or leave the board
//      + the hints: soft penalties in mm, each multiplied by --hint-weight (see place_hints.py).
// It grew out of autoplace.mjs (blocks of a tscircuit design) and untangle.mjs (rotation): the same two
// ideas, in one cost, on the parts of any KiCad board.
import { readFileSync, writeFileSync } from "node:fs";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? Number(args[i + 1]) : d; };
const prob = JSON.parse(readFileSync(args[0], "utf8"));
const FANOUT = 8, MARGIN = 0.25, PEN = 200, HW = opt("--hint-weight", 12);
const EDGE = 0.5;  // copper keeps this far inside the outline
const P = prob.parts, n = P.length, [X0, Y0, X1, Y1] = [prob.bbox[0] + EDGE, prob.bbox[1] + EDGE, prob.bbox[2] - EDGE, prob.bbox[3] - EDGE], BW = X1 - X0, BH = Y1 - Y0;
const poly = prob.poly?.length >= 3 ? prob.poly : null, cuts = prob.cuts ?? [], hints = prob.hints ?? [];

function rng32(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), a | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const rot = (dx, dy, deg) => (deg === 0 ? [dx, dy] : deg === 90 ? [-dy, dx] : deg === 180 ? [-dx, -dy] : [dy, -dx]);
const inPoly = (x, y) => {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};

// Signal nets only: a high-fanout net is a pour or a rail and would pull everything into one heap.
const netPads = new Map();
P.forEach((p, i) => p.pads.forEach((pad) => { if (pad.net) (netPads.get(pad.net) ?? netPads.set(pad.net, []).get(pad.net)).push([i, pad.off]); }));
const nets = [...netPads.values()].filter((m) => { const k = new Set(m.map((x) => x[0])).size; return k >= 2 && k <= FANOUT; });
const netsOf = P.map(() => []);
nets.forEach((m, k) => new Set(m.map((x) => x[0])).forEach((i) => netsOf[i].push(k)));
const collide = (i, j) => !P[i].hollow && !P[j].hollow && (P[i].side === P[j].side || P[i].through || P[j].through);

function makeState(rng, seedPos) {
  return P.map((p, i) => p.locked ? { cx: p.cx, cy: p.cy, rot: 0 } : seedPos?.[i] ?? { cx: X0 + rng() * BW, cy: Y0 + rng() * BH, rot: 0 });
}
const box = (S, i, m = 0) => { const s = S[i], w = (s.rot % 180 ? P[i].h : P[i].w) / 2 + m, h = (s.rot % 180 ? P[i].w : P[i].h) / 2 + m; return [s.cx - w, s.cy - h, s.cx + w, s.cy + h]; };
const netLen = (S, k) => {
  let ax = 1e9, bx = -1e9, ay = 1e9, by = -1e9;
  for (const [i, off] of nets[k]) { const [dx, dy] = rot(off[0], off[1], S[i].rot), x = S[i].cx + dx, y = S[i].cy + dy; if (x < ax) ax = x; if (x > bx) bx = x; if (y < ay) ay = y; if (y > by) by = y; }
  return bx - ax + by - ay;
};
const overlapOf = (S, i) => {
  let a = 0; const b = box(S, i, MARGIN);
  for (let j = 0; j < n; j++) {
    if (j === i || !collide(i, j)) continue;
    const c = box(S, j, MARGIN), w = Math.min(b[2], c[2]) - Math.max(b[0], c[0]), h = Math.min(b[3], c[3]) - Math.max(b[1], c[1]);
    if (w > 0 && h > 0) a += w * h;
  }
  for (const c of cuts) { const w = Math.min(b[2], c[2]) - Math.max(b[0], c[0]), h = Math.min(b[3], c[3]) - Math.max(b[1], c[1]); if (w > 0 && h > 0) a += w * h; }
  return a;
};
const outsideOf = (S, i) => {  // mm the body reaches past the outline
  const b = box(S, i);
  let d = Math.max(0, X0 - b[0]) + Math.max(0, b[2] - X1) + Math.max(0, Y0 - b[1]) + Math.max(0, b[3] - Y1);
  if (poly) for (const [x, y] of [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]) if (!inPoly(x, y)) d += 1 + Math.hypot(x - (X0 + X1) / 2, y - (Y0 + Y1) / 2) * 0.05;
  return d;
};

// ---- hints -----------------------------------------------------------------------------------------
const FRAC = { left: 0.18, center: 0.5, right: 0.82, bottom: 0.18, middle: 0.5, top: 0.82 };
const REGION = { center: ["center", "middle"], top: ["center", "top"], bottom: ["center", "bottom"], left: ["left", "middle"], right: ["right", "middle"],
  "top-left": ["left", "top"], "top-right": ["right", "top"], "bottom-left": ["left", "bottom"], "bottom-right": ["right", "bottom"] };
function target(S, t) {  // -> [x0,y0,x1,y1] of what a hint points at
  if (t.pad) { const [i, off] = t.pad, [dx, dy] = rot(off[0], off[1], S[i].rot), x = S[i].cx + dx, y = S[i].cy + dy; return [x, y, x, y]; }
  const b = t.parts.map((i) => box(S, i));
  return [Math.min(...b.map((v) => v[0])), Math.min(...b.map((v) => v[1])), Math.max(...b.map((v) => v[2])), Math.max(...b.map((v) => v[3]))];
}
const GAP = { none: 0, tight: 0.5, normal: 1.5, wide: 4 };
function hintMiss(S, h) {  // mm by which the hint is not met (0 = met)
  let miss = 0;
  const subj = h.parts;
  if (h.kind === "group") {  // members within a circle sized to hold them
    const cx = subj.reduce((a, i) => a + S[i].cx, 0) / subj.length, cy = subj.reduce((a, i) => a + S[i].cy, 0) / subj.length;
    const r = Math.sqrt(subj.reduce((a, i) => a + (P[i].w + 1) * (P[i].h + 1), 0)) * 0.75;
    for (const i of subj) miss += Math.max(0, Math.hypot(S[i].cx - cx, S[i].cy - cy) - r);
    return miss;
  }
  const t = h.target ? target(S, h.target) : null;
  for (const i of subj) {
    const b = box(S, i), s = S[i];
    if (h.kind === "region") {
      const [fx, fy] = REGION[h.arg], tx = X0 + FRAC[fx] * BW, ty = Y0 + FRAC[fy] * BH;
      miss += Math.max(0, Math.abs(s.cx - tx) - 0.16 * BW) + Math.max(0, Math.abs(s.cy - ty) - 0.16 * BH);
    } else if (h.kind === "edge") {
      miss += h.arg === "left" ? Math.abs(b[0] - X0) : h.arg === "right" ? Math.abs(X1 - b[2]) : h.arg === "bottom" ? Math.abs(b[1] - Y0) : Math.abs(Y1 - b[3]);
    } else if (h.kind === "dir") {
      const g = h.gap ?? GAP.normal;
      // The stated side is a minimum distance; with nothing else said, stay roughly on the target's centre line.
      if (h.arg === "right") miss += Math.max(0, t[2] + g - b[0]) + 0.3 * Math.max(0, Math.abs(s.cy - (t[1] + t[3]) / 2) - (t[3] - t[1]) / 2);
      if (h.arg === "left") miss += Math.max(0, b[2] + g - t[0]) + 0.3 * Math.max(0, Math.abs(s.cy - (t[1] + t[3]) / 2) - (t[3] - t[1]) / 2);
      if (h.arg === "above") miss += Math.max(0, t[3] + g - b[1]) + 0.3 * Math.max(0, Math.abs(s.cx - (t[0] + t[2]) / 2) - (t[2] - t[0]) / 2);
      if (h.arg === "below") miss += Math.max(0, b[3] + g - t[1]) + 0.3 * Math.max(0, Math.abs(s.cx - (t[0] + t[2]) / 2) - (t[2] - t[0]) / 2);
    } else if (h.kind === "level") {
      miss += h.arg === "x" ? Math.abs(s.cx - (t[0] + t[2]) / 2) : Math.abs(s.cy - (t[1] + t[3]) / 2);
    } else if (h.kind === "near") {  // edge-to-edge distance within `gap`
      const dx = Math.max(0, t[0] - b[2], b[0] - t[2]), dy = Math.max(0, t[1] - b[3], b[1] - t[3]);
      miss += Math.max(0, Math.hypot(dx, dy) - (h.gap ?? 2));
    }
  }
  return miss;
}
const hintsOf = P.map(() => []);
hints.forEach((h, k) => new Set([...h.parts, ...(h.target?.parts ?? []), ...(h.target?.pad ? [h.target.pad[0]] : [])]).forEach((i) => hintsOf[i].push(k)));
const fixedRot = new Map(hints.filter((h) => h.kind === "rotate").flatMap((h) => h.parts.map((i) => [i, h.arg])));

// ---- anneal ------------------------------------------------------------------------------------------
let pen = PEN;  // ramps up through the main anneal: parts may pass through each other early, not late
const local = (S, i) => {
  let c = pen * (overlapOf(S, i) + outsideOf(S, i));
  for (const k of netsOf[i]) c += netLen(S, k);
  for (const k of hintsOf[i]) c += HW * (hints[k].weight ?? 1) * hintMiss(S, hints[k]);
  return c;
};
function anneal(S, rng, iters, T0, ramp = false) {
  const mov = P.map((p, i) => i).filter((i) => !P[i].locked);
  if (!mov.length) return;
  for (const [i, deg] of fixedRot) if (!P[i].locked) S[i].rot = deg;
  for (let it = 0; it < iters; it++) {
    pen = ramp ? PEN * (0.01 + 0.99 * Math.pow(it / iters, 2)) : PEN;
    const T = T0 * Math.pow(0.002, it / iters), i = mov[(rng() * mov.length) | 0], s = S[i], save = { ...s };
    const before = local(S, i);
    const r = rng();
    if (r < 0.15 && !fixedRot.has(i)) s.rot = [0, 90, 180, 270][(rng() * 4) | 0];
    else if (r < 0.25) {  // swap with another movable part
      const j = mov[(rng() * mov.length) | 0];
      if (j !== i) {
        const sj = S[j], savej = { ...sj }, bj = local(S, j);
        [s.cx, sj.cx] = [sj.cx, s.cx]; [s.cy, sj.cy] = [sj.cy, s.cy];
        const d = local(S, i) + local(S, j) - before - bj;
        if (!(d < 0 || rng() < Math.exp(-d / T))) { Object.assign(s, save); Object.assign(sj, savej); }
        continue;
      }
    } else { const step = 0.3 + T; s.cx += (rng() - 0.5) * 2 * step; s.cy += (rng() - 0.5) * 2 * step; }
    const d = local(S, i) - before;
    if (!(d < 0 || rng() < Math.exp(-d / T))) Object.assign(s, save);
  }
}

// ---- legalise: push overlapping bodies apart along the shallow axis, pull strays back onto the board ----
function legalise(S, rounds = 400) {
  for (let r = 0; r < rounds; r++) {
    let moved = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      if (!collide(i, j) || (P[i].locked && P[j].locked)) continue;
      const a = box(S, i, MARGIN), b = box(S, j, MARGIN), w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
      if (w <= 1e-6 || h <= 1e-6) continue;
      moved++;
      const fi = P[i].locked ? 0 : P[j].locked ? 1 : 0.5, fj = 1 - fi;
      if (w < h) { const dir = S[i].cx <= S[j].cx ? -1 : 1; S[i].cx += dir * (w + 0.02) * fi; S[j].cx -= dir * (w + 0.02) * fj; }
      else { const dir = S[i].cy <= S[j].cy ? -1 : 1; S[i].cy += dir * (h + 0.02) * fi; S[j].cy -= dir * (h + 0.02) * fj; }
    }
    for (let i = 0; i < n; i++) {
      if (P[i].locked) continue;
      const b = box(S, i);
      S[i].cx += Math.max(0, X0 - b[0]) - Math.max(0, b[2] - X1);
      S[i].cy += Math.max(0, Y0 - b[1]) - Math.max(0, b[3] - Y1);
    }
    if (!moved) break;
  }
}

const total = (S) => {
  let wire = 0, over = 0, out = 0, miss = 0;
  for (let k = 0; k < nets.length; k++) wire += netLen(S, k);
  for (let i = 0; i < n; i++) { over += overlapOf(S, i) / 2; if (!P[i].locked) out += outsideOf(S, i); }
  for (const h of hints) miss += (h.weight ?? 1) * hintMiss(S, h);
  return { wire, over, out, miss };
};

const movable = P.filter((p) => !p.locked).length;
const iters = Math.max(20000, Math.min(400000, movable * 2500));
let best = null;
for (let r = 0; r < opt("--restarts", 4); r++) {
  const rng = rng32(opt("--seed", 1) * 1000 + r);
  const S = makeState(rng);
  anneal(S, rng, iters, Math.max(BW, BH) / 6, true);
  legalise(S);
  anneal(S, rng, Math.round(iters / 4), 0.4);  // settle after the push-apart, small moves only
  legalise(S);
  const t = total(S);
  const key = (t.over > 0.01 ? 1e6 : 0) + (t.out > 0.01 ? 1e5 * (1 + t.out) : 0) + t.wire + HW * t.miss;
  if (!best || key < best.key) best = { key, S: S.map((s) => ({ ...s })), t };
}
const out = { parts: Object.fromEntries(best.S.map((s, i) => [P[i].ref, s])), hpwl: +best.t.wire.toFixed(1), overlap: +best.t.over.toFixed(3), outside: +best.t.out.toFixed(2),
  hints: hints.map((h) => ({ text: h.text, miss: +hintMiss(best.S, h).toFixed(2) })), iters, nets: nets.length };
writeFileSync(args[1], JSON.stringify(out));
const unmet = out.hints.filter((h) => h.miss > 0.5).length;
console.log(`place_kicad: ${n} parts (${movable} placed), ${nets.length} signal nets, ${iters} moves x ${opt("--restarts", 4)} -> wire ${out.hpwl} mm, overlap ${out.overlap} mm2, off board ${out.outside} mm` +
  (hints.length ? `, hints ${hints.length - unmet}/${hints.length} met` : ""));
