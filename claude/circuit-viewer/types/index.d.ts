// The circuit viewer mod's state: what the pane draws from. Values the CLI
// (mcp/src/cli.ts) returns, stored per session.

export type Box = { x: number; y: number; w: number; h: number }

/** A copper shape in board millimetres (KiCad coordinates, Y down); see mcp/src/kicad.ts. */
export type Prim =
  | { k: 't'; l: string; x1: number; y1: number; x2: number; y2: number; w: number }
  | { k: 'p'; l: string; x: number; y: number; w: number; h: number; a: number; r: number }
  | { k: 'v'; x: number; y: number; d: number; h: number }
  | { k: 'h'; x: number; y: number; d: number }
  | { k: 'z'; l: string; pts: number[] }

export type Geometry = { bbox: Box | null; prims: Prim[]; edges: number[] }

export type Marker = {
  kind: 'violation' | 'unconnected'
  type: string
  severity: string
  description: string
  items: { description: string; x: number; y: number }[]
}

export type Metrics = {
  track_mm_total: number
  segments_total: number
  vias: number
  zone_net_track_mm: number
}

export type Snapshot = {
  project: { name: string; root: string; board?: string; source?: string }
  revision: string
  routing: { backend?: string; state?: string; message?: string; [k: string]: unknown } | null
  board: null | {
    copperLayers: string[]
    bbox: Box | null
    footprints: number
    nets: number
    zoneNets: string[]
    metrics: Metrics
  }
  geometry: Geometry | null
  drc: null | { markers: Marker[]; counts: Record<string, number>; unconnected: number }
}

export type Gate = { name: string; ok: boolean; exitCode: number; output: string }

export type Checks = { ok: boolean; summary: string; gates: Gate[]; revision: string }

export type Side = 'both' | 'front' | 'back'

declare module 'claude-code' {
  interface PluginState {
    'circuit-viewer': {
      /** The path the pane follows (board, design or folder), as given. */
      target: string | null
      snapshot: Snapshot | null
      checks: Checks | null
      /** What the pane is doing right now, or the last error. */
      status: string
      side: Side
      /** Index into the blocking markers, -1 for none selected. */
      focus: number
      /** Zoom the picture to the selected marker. */
      zoom: boolean
    }
  }
}
