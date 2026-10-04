// A small reader for .kicad_pcb files: enough to measure routing, list nets and
// layers, and size the board, without KiCad's Python module (which only the
// system Python has).

export type SExpr = string | SExpr[];

/** Parses KiCad's s-expression format. Strings come back unquoted. */
export function parseSExpr(text: string): SExpr {
  const stack: SExpr[][] = [[]];
  let i = 0;
  const n = text.length;
  while (i < n) {
    const c = text[i];
    if (c === "(") {
      const list: SExpr[] = [];
      stack[stack.length - 1].push(list);
      stack.push(list);
      i++;
    } else if (c === ")") {
      stack.pop();
      if (!stack.length) throw new Error("unbalanced ')' in board file");
      i++;
    } else if (c === '"') {
      let j = i + 1;
      let s = "";
      while (j < n && text[j] !== '"') {
        if (text[j] === "\\" && j + 1 < n) {
          s += text[j + 1];
          j += 2;
        } else s += text[j++];
      }
      stack[stack.length - 1].push(s);
      i = j + 1;
    } else if (c === " " || c === "\n" || c === "\t" || c === "\r") {
      i++;
    } else {
      let j = i;
      while (j < n && !" \n\t\r()".includes(text[j])) j++;
      stack[stack.length - 1].push(text.slice(i, j));
      i = j;
    }
  }
  const top = stack[0];
  return top.length === 1 ? top[0] : top;
}

const isList = (e: SExpr | undefined): e is SExpr[] => Array.isArray(e);
const head = (e: SExpr) => (isList(e) && typeof e[0] === "string" ? e[0] : "");
/** Child lists of `e` whose first atom is `name`. */
export const children = (e: SExpr, name: string): SExpr[][] => (isList(e) ? (e.filter((c) => isList(c) && c[0] === name) as SExpr[][]) : []);
export const child = (e: SExpr, name: string): SExpr[] | undefined => children(e, name)[0];
const num = (e: SExpr | undefined, at = 1) => (isList(e) ? Number(e[at]) : NaN);
const str = (e: SExpr | undefined, at = 1) => (isList(e) && typeof e[at] === "string" ? (e[at] as string) : undefined);

export interface BoardInfo {
  copperLayers: string[];
  /** Board outline extent in KiCad board coordinates (mm, Y down). */
  bbox: { x: number; y: number; w: number; h: number } | null;
  footprints: number;
  nets: { name: string; pads: string[] }[];
  /** Nets that own a copper zone (planes and pours). */
  zoneNets: string[];
  zones: { net: string; layers: string[] }[];
  metrics: Metrics;
}

export interface Metrics {
  track_mm_total: number;
  track_mm_by_layer: Record<string, number>;
  segments_by_layer: Record<string, number>;
  segments_total: number;
  vias: number;
  /** Track length on nets that also have a zone: plane nets carried as traces instead. */
  zone_net_track_mm: number;
  nets_with_tracks: number;
}

const round1 = (v: number) => Math.round(v * 10) / 10;

/** Length of a three-point arc (start, mid, end). Falls back to the chord. */
function arcLength(s: number[], m: number[], e: number[]): number {
  const [ax, ay, bx, by, cx, cy] = [s[0], s[1], m[0], m[1], e[0], e[1]];
  const d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
  if (Math.abs(d) < 1e-12) return Math.hypot(cx - ax, cy - ay);
  const ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d;
  const uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d;
  const r = Math.hypot(ax - ux, ay - uy);
  const ang = (x: number, y: number) => Math.atan2(y - uy, x - ux);
  const a0 = ang(ax, ay), a1 = ang(bx, by), a2 = ang(cx, cy);
  const norm = (a: number) => ((a % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
  // Sweep from start to end through mid.
  const ccw = norm(a1 - a0) < norm(a2 - a0);
  const sweep = ccw ? norm(a2 - a0) : norm(a0 - a2);
  return r * sweep;
}

export function readBoard(text: string): BoardInfo {
  const root = parseSExpr(text);
  if (head(root) !== "kicad_pcb") throw new Error("not a KiCad board file");

  const copperLayers = (child(root, "layers") ?? [])
    .filter(isList)
    .map((l) => str(l as SExpr[], 1))
    .filter((n): n is string => !!n && n.endsWith(".Cu"));

  // Net numbers -> names (KiCad <= 9 numbers nets; newer files may name them inline).
  const netNames = new Map<string, string>();
  for (const n of children(root, "net")) netNames.set(String(n[1]), str(n, 2) ?? "");
  const netOf = (e: SExpr[]): string => {
    const n = child(e, "net");
    if (!n) return "";
    const named = str(n, 2);
    if (named !== undefined) return named;
    return netNames.get(String(n[1])) ?? String(n[1]);
  };

  // Zones (keepouts have no net) and their nets.
  const zones: { net: string; layers: string[] }[] = [];
  for (const z of children(root, "zone")) {
    if (child(z, "keepout")) continue;
    const net = str(child(z, "net_name")) ?? netOf(z);
    if (!net) continue;
    const layers = [...(child(z, "layers") ?? []).slice(1), ...(child(z, "layer") ?? []).slice(1)].filter((l): l is string => typeof l === "string");
    zones.push({ net, layers });
  }
  const zoneNets = [...new Set(zones.map((z) => z.net))].sort();

  // Routing.
  const byLayer: Record<string, number> = {};
  const segs: Record<string, number> = {};
  const byNet = new Map<string, number>();
  let vias = 0;
  for (const e of root as SExpr[]) {
    if (!isList(e)) continue;
    const kind = head(e);
    if (kind === "via") {
      vias++;
      continue;
    }
    if (kind !== "segment" && kind !== "arc") continue;
    const s = child(e, "start"), en = child(e, "end");
    if (!s || !en) continue;
    const p0 = [num(s, 1), num(s, 2)], p1 = [num(en, 1), num(en, 2)];
    const mid = child(e, "mid");
    const len = kind === "arc" && mid ? arcLength(p0, [num(mid, 1), num(mid, 2)], p1) : Math.hypot(p1[0] - p0[0], p1[1] - p0[1]);
    const layer = str(child(e, "layer")) ?? "?";
    byLayer[layer] = (byLayer[layer] ?? 0) + len;
    segs[layer] = (segs[layer] ?? 0) + 1;
    const net = netOf(e);
    byNet.set(net, (byNet.get(net) ?? 0) + len);
  }
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
  const zoneSet = new Set(zoneNets);
  const metrics: Metrics = {
    track_mm_total: round1(sum(byLayer)),
    track_mm_by_layer: Object.fromEntries(Object.entries(byLayer).sort().map(([k, v]) => [k, round1(v)])),
    segments_by_layer: Object.fromEntries(Object.entries(segs).sort()),
    segments_total: sum(segs),
    vias,
    zone_net_track_mm: round1([...byNet].filter(([n]) => zoneSet.has(n)).reduce((a, [, v]) => a + v, 0)),
    nets_with_tracks: [...byNet.keys()].filter((n) => n).length,
  };

  // Footprints and pad nets.
  const pads = new Map<string, string[]>();
  const fps = children(root, "footprint");
  for (const fp of fps) {
    const refProp = children(fp, "property").find((p) => p[1] === "Reference");
    const ref = str(refProp, 2) ?? str(children(fp, "fp_text").find((t) => t[1] === "reference"), 2) ?? "?";
    for (const pad of children(fp, "pad")) {
      const net = netOf(pad);
      if (!net) continue;
      const list = pads.get(net) ?? [];
      list.push(`${ref}.${str(pad, 1) ?? "?"}`);
      pads.set(net, list);
    }
  }
  const nets = [...pads]
    .filter(([name]) => !name.startsWith("unconnected-"))
    .map(([name, p]) => ({ name, pads: [...new Set(p)].sort() }))
    .sort((a, b) => a.name.localeCompare(b.name));

  // Outline extent from Edge.Cuts graphics.
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const grow = (x: number, y: number) => {
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
  };
  for (const e of root as SExpr[]) {
    if (!isList(e) || !head(e).startsWith("gr_") || str(child(e, "layer")) !== "Edge.Cuts") continue;
    if (head(e) === "gr_circle") {
      const c = child(e, "center"), en = child(e, "end");
      const r = Math.hypot(num(en, 1) - num(c, 1), num(en, 2) - num(c, 2));
      grow(num(c, 1) - r, num(c, 2) - r);
      grow(num(c, 1) + r, num(c, 2) + r);
      continue;
    }
    for (const key of ["start", "end", "mid", "center"]) {
      const p = child(e, key);
      if (p) grow(num(p, 1), num(p, 2));
    }
    for (const xy of children(child(e, "pts") ?? [], "xy")) grow(num(xy, 1), num(xy, 2));
  }
  const bbox = Number.isFinite(x0) ? { x: x0, y: y0, w: x1 - x0, h: y1 - y0 } : null;

  return { copperLayers, bbox, footprints: fps.length, nets, zoneNets, zones, metrics };
}

/** Plain-text netlist from a board, for projects without a tscircuit source. */
export function boardNetlist(info: BoardInfo): string {
  return ["NETS (from the KiCad board):", ...info.nets.map((n) => ` - ${n.name}: ${n.pads.join(", ")}`)].join("\n");
}

// ---- Geometry for drawing ------------------------------------------------------

/** A copper shape in board millimetres (KiCad coordinates, Y down). */
export type Prim =
  | { k: "t"; l: string; x1: number; y1: number; x2: number; y2: number; w: number } // track (capsule)
  | { k: "p"; l: string; x: number; y: number; w: number; h: number; a: number; r: number } // pad: centre, size, angle (deg), corner radius
  | { k: "v"; x: number; y: number; d: number; h: number } // via: diameter, hole
  | { k: "h"; x: number; y: number; d: number } // bare drilled hole
  | { k: "z"; l: string; pts: number[] }; // filled pour on an outer layer, flat x,y list

export interface BoardGeometry {
  bbox: { x: number; y: number; w: number; h: number } | null;
  prims: Prim[];
  /** Board outline as line segments, flat x1,y1,x2,y2 quads. */
  edges: number[];
}

const r3 = (v: number) => Math.round(v * 1000) / 1000;

/**
 * Everything a picture of the routed board needs: tracks, pads, vias, holes
 * and outer-layer pours by layer, plus the outline. Pad positions rotate with
 * their footprint; pad angles in the file are already absolute.
 */
export function boardGeometry(text: string): BoardGeometry {
  const root = parseSExpr(text);
  if (head(root) !== "kicad_pcb") throw new Error("not a KiCad board file");
  const prims: Prim[] = [];
  const edges: number[] = [];
  const outer = (l?: string) => l === "F.Cu" || l === "B.Cu";

  for (const e of root as SExpr[]) {
    if (!isList(e)) continue;
    const kind = head(e);
    if (kind === "segment" || kind === "arc") {
      const s = child(e, "start"), en = child(e, "end"), l = str(child(e, "layer"));
      if (!s || !en || !outer(l)) continue;
      const w = num(child(e, "width"));
      const mid = child(e, "mid");
      if (kind === "arc" && mid) {
        // Draw an arc as two chords through its midpoint: fine at picture scale.
        prims.push({ k: "t", l: l!, x1: r3(num(s, 1)), y1: r3(num(s, 2)), x2: r3(num(mid, 1)), y2: r3(num(mid, 2)), w });
        prims.push({ k: "t", l: l!, x1: r3(num(mid, 1)), y1: r3(num(mid, 2)), x2: r3(num(en, 1)), y2: r3(num(en, 2)), w });
      } else prims.push({ k: "t", l: l!, x1: r3(num(s, 1)), y1: r3(num(s, 2)), x2: r3(num(en, 1)), y2: r3(num(en, 2)), w });
    } else if (kind === "via") {
      const at = child(e, "at");
      prims.push({ k: "v", x: r3(num(at, 1)), y: r3(num(at, 2)), d: num(child(e, "size")), h: num(child(e, "drill")) });
    } else if (kind === "zone") {
      if (child(e, "keepout")) continue;
      for (const fp of children(e, "filled_polygon")) {
        const l = str(child(fp, "layer"));
        if (!outer(l)) continue;
        const pts = children(child(fp, "pts") ?? [], "xy").flatMap((xy) => [r3(num(xy, 1)), r3(num(xy, 2))]);
        if (pts.length >= 6) prims.push({ k: "z", l: l!, pts });
      }
    } else if (kind.startsWith("gr_") && str(child(e, "layer")) === "Edge.Cuts") {
      pushOutline(e, edges);
    } else if (kind === "footprint") {
      const at = child(e, "at");
      const fx = num(at, 1), fy = num(at, 2), frot = num(at, 3) || 0;
      const c = Math.cos((-frot * Math.PI) / 180), s = Math.sin((-frot * Math.PI) / 180);
      for (const pad of children(e, "pad")) {
        const pat = child(pad, "at");
        const lx = num(pat, 1), ly = num(pat, 2);
        const x = r3(fx + lx * c - ly * s), y = r3(fy + lx * s + ly * c);
        const size = child(pad, "size");
        const w = num(size, 1), hgt = num(size, 2);
        const a = num(pat, 3) || 0;
        const shape = str(pad, 3) ?? "rect";
        const type = str(pad, 2) ?? "smd";
        const drill = child(pad, "drill");
        const dr = drill ? Number(drill.find((v) => typeof v === "string" && /^[\d.]+$/.test(v)) ?? NaN) : NaN;
        const layers = (child(pad, "layers") ?? []).slice(1).filter((v): v is string => typeof v === "string");
        const radius = shape === "circle" || shape === "oval" ? Math.min(w, hgt) / 2 : shape === "roundrect" ? Math.min(w, hgt) * (num(child(pad, "roundrect_rratio")) || 0.25) : 0;
        if (type === "np_thru_hole") {
          prims.push({ k: "h", x, y, d: Number.isFinite(dr) ? dr : Math.min(w, hgt) });
          continue;
        }
        const onF = layers.some((l) => l === "F.Cu" || l === "*.Cu");
        const onB = layers.some((l) => l === "B.Cu" || l === "*.Cu");
        if (onB) prims.push({ k: "p", l: "B.Cu", x, y, w, h: hgt, a, r: r3(radius) });
        if (onF) prims.push({ k: "p", l: "F.Cu", x, y, w, h: hgt, a, r: r3(radius) });
        if (type === "thru_hole" && Number.isFinite(dr)) prims.push({ k: "h", x, y, d: dr });
      }
      for (const g of [...children(e, "fp_line"), ...children(e, "fp_arc"), ...children(e, "fp_rect"), ...children(e, "fp_circle")]) {
        if (str(child(g, "layer")) !== "Edge.Cuts") continue;
        // Footprint-local outline pieces (cutouts drawn in a footprint): rotate into place.
        const moved = g.map((part) =>
          isList(part) && ["start", "end", "mid", "center"].includes(head(part))
            ? [part[0], String(fx + num(part, 1) * c - num(part, 2) * s), String(fy + num(part, 1) * s + num(part, 2) * c)]
            : part,
        ) as SExpr[];
        pushOutline(["gr_" + head(g).slice(3), ...moved.slice(1)], edges);
      }
    }
  }
  const info = readBoard(text);
  return { bbox: info.bbox, prims, edges: edges.map(r3) };
}

/** Appends one Edge.Cuts graphic to `edges` as straight segments. */
function pushOutline(e: SExpr[], edges: number[]) {
  const kind = head(e);
  const p = (name: string) => {
    const q = child(e, name);
    return q ? [num(q, 1), num(q, 2)] : null;
  };
  if (kind === "gr_line") {
    const a = p("start"), b = p("end");
    if (a && b) edges.push(a[0], a[1], b[0], b[1]);
  } else if (kind === "gr_rect") {
    const a = p("start"), b = p("end");
    if (a && b) edges.push(a[0], a[1], b[0], a[1], b[0], a[1], b[0], b[1], b[0], b[1], a[0], b[1], a[0], b[1], a[0], a[1]);
  } else if (kind === "gr_circle") {
    const c = p("center"), en = p("end");
    if (!c || !en) return;
    const r = Math.hypot(en[0] - c[0], en[1] - c[1]);
    for (let i = 0; i < 32; i++) {
      const t0 = (i / 32) * 2 * Math.PI, t1 = ((i + 1) / 32) * 2 * Math.PI;
      edges.push(c[0] + r * Math.cos(t0), c[1] + r * Math.sin(t0), c[0] + r * Math.cos(t1), c[1] + r * Math.sin(t1));
    }
  } else if (kind === "gr_arc") {
    const a = p("start"), m = p("mid"), b = p("end");
    if (a && m && b) edges.push(a[0], a[1], m[0], m[1], m[0], m[1], b[0], b[1]);
  } else if (kind === "gr_poly") {
    const pts = children(child(e, "pts") ?? [], "xy").map((xy) => [num(xy, 1), num(xy, 2)]);
    for (let i = 0; i < pts.length; i++) {
      const a = pts[i], b = pts[(i + 1) % pts.length];
      edges.push(a[0], a[1], b[0], b[1]);
    }
  }
}
