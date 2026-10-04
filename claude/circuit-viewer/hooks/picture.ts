// Pictures of a routed board from its geometry (board millimetres, Y down):
//   rasterCells  a terminal Raster: half-block cells, two pixels per cell
//   boardSvg     an Svg for the desktop and editor surfaces
// Both draw the same things in the same order: board, back copper, front
// copper, vias, holes, outline, then the DRC markers on top.

import type { Box, Geometry, Marker, Prim, Side } from '../types'

const BG = 0x0d1117
const BOARD = 0x14241b
const FRONT = 0xe5484d
const BACK = 0x3e8ed0
const VIA = 0xc9ced4
const EDGE = 0xf5d76e
const MARK = { unconnected: 0xffb547, short: 0xff3b3b, other: 0xff8fd0, focus: 0xffffff }

/** DRC types that make a board unbuildable or open: the ones the pane lists and draws. */
export const SERIOUS = new Set([
  'shorting_items', 'tracks_crossing', 'courtyards_overlap', 'unconnected_items', 'copper_edge_clearance',
  'clearance', 'hole_clearance', 'hole_to_hole', 'items_not_allowed', 'annular_width', 'drill_out_of_range',
  'via_diameter', 'track_width',
])

export const markerColor = (m: Marker) =>
  m.kind === 'unconnected' ? MARK.unconnected : m.type === 'shorting_items' || m.type === 'tracks_crossing' ? MARK.short : MARK.other

const hex = (c: number) => '#' + c.toString(16).padStart(6, '0')

/** The region to draw: the whole board, or a window around the focused marker. */
export function viewBox(geom: Geometry, focus: Marker | null, zoom: boolean): Box {
  const b = geom.bbox ?? { x: 0, y: 0, w: 100, h: 100 }
  if (zoom && focus && focus.items.length) {
    const xs = focus.items.map(i => i.x), ys = focus.items.map(i => i.y)
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2
    const span = Math.max(8, (Math.max(...xs) - Math.min(...xs)) * 3, (Math.max(...ys) - Math.min(...ys)) * 3)
    return { x: cx - span / 2, y: cy - (span * b.h) / b.w / 2, w: span, h: (span * b.h) / b.w }
  }
  const pad = Math.max(b.w, b.h) * 0.02
  return { x: b.x - pad, y: b.y - pad, w: b.w + 2 * pad, h: b.h + 2 * pad }
}

const shown = (side: Side, layer: string) => side === 'both' || (side === 'front' ? layer === 'F.Cu' : layer === 'B.Cu')

// ---- raster ---------------------------------------------------------------------

/** Rows of cells that keep the board's aspect at `cols` wide (two pixels per cell, square-ish). */
export function rowsFor(view: Box, cols: number, maxRows: number): number {
  return Math.max(4, Math.min(maxRows, Math.round((cols * view.h) / view.w / 2)))
}

class Canvas {
  W: number
  H: number
  px: Uint32Array
  scale: number
  ox: number
  oy: number
  constructor(W: number, H: number, view: Box) {
    this.W = W
    this.H = H
    this.px = new Uint32Array(W * H).fill(BG)
    this.scale = Math.min(W / view.w, H / view.h)
    this.ox = (W - view.w * this.scale) / 2 - view.x * this.scale
    this.oy = (H - view.h * this.scale) / 2 - view.y * this.scale
  }
  X(x: number) { return x * this.scale + this.ox }
  Y(y: number) { return y * this.scale + this.oy }
  /** Paints every pixel whose centre passes `inside`, over a box in board mm. */
  fill(x0: number, y0: number, x1: number, y1: number, color: number, inside: (x: number, y: number) => boolean) {
    const a = Math.max(0, Math.floor(this.X(x0))), b = Math.min(this.W - 1, Math.ceil(this.X(x1)))
    const c = Math.max(0, Math.floor(this.Y(y0))), d = Math.min(this.H - 1, Math.ceil(this.Y(y1)))
    for (let py = c; py <= d; py++) {
      const y = (py + 0.5 - this.oy) / this.scale
      for (let px = a; px <= b; px++) if (inside((px + 0.5 - this.ox) / this.scale, y)) this.px[py * this.W + px] = color
    }
  }
  /** A half-pixel in board mm: the least a shape is drawn, so thin copper stays visible. */
  get half() { return 0.5 / this.scale }
  line(x1: number, y1: number, x2: number, y2: number, color: number) {
    let a = Math.round(this.X(x1) - 0.5), b = Math.round(this.Y(y1) - 0.5)
    const c = Math.round(this.X(x2) - 0.5), d = Math.round(this.Y(y2) - 0.5)
    const dx = Math.abs(c - a), dy = -Math.abs(d - b), sx = a < c ? 1 : -1, sy = b < d ? 1 : -1
    let err = dx + dy
    for (let i = 0; i < 4096; i++) {
      if (a >= 0 && a < this.W && b >= 0 && b < this.H) this.px[b * this.W + a] = color
      if (a === c && b === d) break
      const e2 = 2 * err
      if (e2 >= dy) { err += dy; a += sx }
      if (e2 <= dx) { err += dx; b += sy }
    }
  }
}

function segDist(x: number, y: number, x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1, dy = y2 - y1
  const t = dx || dy ? Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy))) : 0
  return Math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
}

function paintPrim(cv: Canvas, p: Prim, color: number) {
  const h = cv.half
  if (p.k === 't') {
    const r = Math.max(p.w / 2, h)
    cv.fill(Math.min(p.x1, p.x2) - r, Math.min(p.y1, p.y2) - r, Math.max(p.x1, p.x2) + r, Math.max(p.y1, p.y2) + r, color,
      (x, y) => segDist(x, y, p.x1, p.y1, p.x2, p.y2) <= r)
  } else if (p.k === 'p') {
    const t = (p.a * Math.PI) / 180, c = Math.cos(t), s = Math.sin(t)
    const hw = Math.max(p.w / 2, h), hh = Math.max(p.h / 2, h), rr = Math.min(p.r, hw, hh)
    const R = Math.hypot(hw, hh)
    cv.fill(p.x - R, p.y - R, p.x + R, p.y + R, color, (x, y) => {
      const u = Math.abs((x - p.x) * c - (y - p.y) * s), v = Math.abs((x - p.x) * s + (y - p.y) * c)
      if (u > hw || v > hh) return false
      const du = u - (hw - rr), dv = v - (hh - rr)
      return du <= 0 || dv <= 0 || du * du + dv * dv <= rr * rr
    })
  } else if (p.k === 'z') {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity
    for (let i = 0; i < p.pts.length; i += 2) {
      x0 = Math.min(x0, p.pts[i]!); x1 = Math.max(x1, p.pts[i]!); y0 = Math.min(y0, p.pts[i + 1]!); y1 = Math.max(y1, p.pts[i + 1]!)
    }
    const n = p.pts.length / 2
    cv.fill(x0, y0, x1, y1, color, (x, y) => {
      let inside = false
      for (let i = 0, j = n - 1; i < n; j = i++) {
        const xi = p.pts[2 * i]!, yi = p.pts[2 * i + 1]!, xj = p.pts[2 * j]!, yj = p.pts[2 * j + 1]!
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
      }
      return inside
    })
  }
}

const dim = (c: number, k: number) =>
  (Math.round(((c >> 16) & 255) * k) << 16) | (Math.round(((c >> 8) & 255) * k) << 8) | Math.round((c & 255) * k)

export interface PictureArgs {
  geom: Geometry
  markers: Marker[]
  focus: number
  side: Side
  view: Box
}

/** Pixels (0xRRGGBB, W x H) of the board. */
export function paint({ geom, markers, focus, side, view }: PictureArgs, W: number, H: number): Uint32Array {
  const cv = new Canvas(W, H, view)
  if (geom.bbox) { const b = geom.bbox; cv.fill(b.x, b.y, b.x + b.w, b.y + b.h, BOARD, () => true) }
  // Back first, front over it; with both shown the back is dimmed so the front reads on top.
  for (const layer of ['B.Cu', 'F.Cu']) {
    if (!shown(side, layer)) continue
    const color = layer === 'F.Cu' ? FRONT : side === 'both' ? dim(BACK, 0.8) : BACK
    for (const p of geom.prims) if (p.k === 'z' && p.l === layer) paintPrim(cv, p, dim(color, 0.45))
    for (const p of geom.prims) if ((p.k === 't' || p.k === 'p') && p.l === layer) paintPrim(cv, p, color)
  }
  for (const p of geom.prims) {
    if (p.k === 'v') {
      const r = Math.max(p.d / 2, cv.half)
      cv.fill(p.x - r, p.y - r, p.x + r, p.y + r, VIA, (x, y) => Math.hypot(x - p.x, y - p.y) <= r)
    }
  }
  for (const p of geom.prims) {
    if (p.k === 'h' || p.k === 'v') {
      const r = p.k === 'h' ? p.d / 2 : p.h / 2
      if (r * cv.scale < 0.35) continue // a hole smaller than a pixel would erase its own ring
      cv.fill(p.x - r, p.y - r, p.x + r, p.y + r, BG, (x, y) => Math.hypot(x - p.x, y - p.y) <= r)
    }
  }
  for (let i = 0; i + 3 < geom.edges.length; i += 4) cv.line(geom.edges[i]!, geom.edges[i + 1]!, geom.edges[i + 2]!, geom.edges[i + 3]!, EDGE)
  markers.forEach((m, i) => {
    const color = i === focus ? MARK.focus : markerColor(m)
    const [a, b] = m.items
    if (a && b && m.kind === 'unconnected') cv.line(a.x, a.y, b.x, b.y, color)
    for (const it of m.items.slice(0, 2)) {
      const r = (i === focus ? 2.5 : 1.5) / cv.scale
      cv.fill(it.x - r, it.y - r, it.x + r, it.y + r, color, (x, y) => {
        const d = Math.hypot(x - it.x, y - it.y)
        return d <= r && d >= r - 1.1 / cv.scale
      })
      cv.fill(it.x, it.y, it.x, it.y, color, () => true)
    }
  })
  return cv.px
}

function base64(bytes: Uint8Array): string {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  let out = ''
  for (let i = 0; i < bytes.length; i += 3) {
    const n = (bytes[i]! << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0)
    out += A[(n >> 18) & 63]! + A[(n >> 12) & 63]! + (i + 1 < bytes.length ? A[(n >> 6) & 63]! : '=') + (i + 2 < bytes.length ? A[n & 63]! : '=')
  }
  return out
}

/** A Raster's `cells`: one upper-half block per cell, the top pixel as ink and the bottom as paper. */
export function rasterCells(args: PictureArgs, cols: number, rows: number): string {
  const px = paint(args, cols, rows * 2)
  const words = new Uint32Array(cols * rows * 3)
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const o = (r * cols + c) * 3
      words[o] = 0x2580
      words[o + 1] = px[2 * r * cols + c]!
      words[o + 2] = px[(2 * r + 1) * cols + c]!
    }
  }
  return base64(new Uint8Array(words.buffer))
}

// ---- svg ------------------------------------------------------------------------------

const f = (v: number) => (Math.round(v * 100) / 100).toString()

/** The board as SVG markup (board mm as user units), at most `limit` characters. */
export function boardSvg({ geom, markers, focus, side, view }: PictureArgs, limit = 130000): string {
  const out: string[] = []
  if (geom.bbox) { const b = geom.bbox; out.push(`<rect x="${f(b.x)}" y="${f(b.y)}" width="${f(b.w)}" height="${f(b.h)}" fill="${hex(BOARD)}"/>`) }
  for (const layer of ['B.Cu', 'F.Cu']) {
    if (!shown(side, layer)) continue
    const color = hex(layer === 'F.Cu' ? FRONT : BACK)
    const zones = geom.prims.filter((p): p is Extract<Prim, { k: 'z' }> => p.k === 'z' && p.l === layer)
    for (const z of zones) {
      const pts = z.pts.map(f).join(' ')
      if (pts.length < 20000) out.push(`<polygon points="${pts}" fill="${color}" fill-opacity="0.35"/>`)
    }
    // Tracks grouped by width: one path per width.
    const byWidth = new Map<number, string[]>()
    for (const p of geom.prims) if (p.k === 't' && p.l === layer) {
      const list = byWidth.get(p.w) ?? []
      list.push(`M${f(p.x1)} ${f(p.y1)}L${f(p.x2)} ${f(p.y2)}`)
      byWidth.set(p.w, list)
    }
    out.push(`<g stroke="${color}" stroke-linecap="round" fill="none"${layer === 'B.Cu' && side === 'both' ? ' opacity="0.85"' : ''}>`)
    for (const [w, d] of byWidth) out.push(`<path stroke-width="${f(w)}" d="${d.join('')}"/>`)
    out.push(`</g><g fill="${color}">`)
    for (const p of geom.prims) if (p.k === 'p' && p.l === layer)
      out.push(`<rect x="${f(p.x - p.w / 2)}" y="${f(p.y - p.h / 2)}" width="${f(p.w)}" height="${f(p.h)}"${p.r ? ` rx="${f(p.r)}"` : ''}${p.a ? ` transform="rotate(${f(-p.a)} ${f(p.x)} ${f(p.y)})"` : ''}/>`)
    out.push('</g>')
  }
  out.push(`<g fill="${hex(VIA)}">`)
  for (const p of geom.prims) if (p.k === 'v') out.push(`<circle cx="${f(p.x)}" cy="${f(p.y)}" r="${f(p.d / 2)}"/>`)
  out.push(`</g><g fill="${hex(BG)}">`)
  for (const p of geom.prims) if (p.k === 'v' || p.k === 'h') out.push(`<circle cx="${f(p.x)}" cy="${f(p.y)}" r="${f((p.k === 'v' ? p.h : p.d) / 2)}"/>`)
  out.push('</g>')
  const e = geom.edges
  let d = ''
  for (let i = 0; i + 3 < e.length; i += 4) d += `M${f(e[i]!)} ${f(e[i + 1]!)}L${f(e[i + 2]!)} ${f(e[i + 3]!)}`
  out.push(`<path d="${d}" stroke="${hex(EDGE)}" stroke-width="0.25" fill="none"/>`)
  const s = view.w / 120 // marker size relative to the window
  markers.forEach((m, i) => {
    const color = hex(i === focus ? MARK.focus : markerColor(m))
    const [a, b] = m.items
    if (a && b && m.kind === 'unconnected') out.push(`<line x1="${f(a.x)}" y1="${f(a.y)}" x2="${f(b.x)}" y2="${f(b.y)}" stroke="${color}" stroke-width="${f(s / 3)}" stroke-dasharray="${f(s)} ${f(s / 2)}"/>`)
    for (const it of m.items.slice(0, 2)) out.push(`<circle cx="${f(it.x)}" cy="${f(it.y)}" r="${f(i === focus ? s * 2.4 : s * 1.6)}" fill="none" stroke="${color}" stroke-width="${f(s / 2.5)}"/>`)
  })
  const head = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${f(view.x)} ${f(view.y)} ${f(view.w)} ${f(view.h)}" style="background:${hex(BG)}">`
  let body = out.join('')
  // Over the surface's limit: drop the pours first, then the pads, keeping tracks and markers.
  if (head.length + body.length + 6 > limit) body = body.replace(/<polygon [^>]*\/>/g, '')
  if (head.length + body.length + 6 > limit) body = body.replace(/<rect x[^>]*\/>/g, '')
  return `${head}${body}</svg>`
}
