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
