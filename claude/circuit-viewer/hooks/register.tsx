// The circuit viewer inside Claude Code: a pane that shows a PCB project the way
// the circuit-skills pipeline builds it (the routed KiCad board with its DRC
// markers, the gates' verdict, the routing metrics), kept live while the board
// changes, plus the tools the model uses to open and check boards.
//
// The work is done by the circuit viewer's CLI (mcp/src/cli.ts), embedded here
// as source and run with `node --input-type=module -`: kicad-cli for DRC,
// pcb-layout's gate scripts, and a reader for .kicad_pcb geometry. Needs Node
// and KiCad 9+ (kicad-cli) on PATH, Python 3 for the gates.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Checks, Marker, Side, Snapshot } from '../types'
import { CLI_SOURCE } from './cli-source'
import { SERIOUS, boardSvg, markerColor, rasterCells, rowsFor, viewBox } from './picture'

type $ = EngineInterface

const PANE = 'circuit-viewer'
const targetA = atom({ plugin: 'circuit-viewer', key: 'target' } as const, null)
const snapshotA = atom({ plugin: 'circuit-viewer', key: 'snapshot' } as const, null)
const checksA = atom({ plugin: 'circuit-viewer', key: 'checks' } as const, null)
const statusA = atom({ plugin: 'circuit-viewer', key: 'status' } as const, '')
const sideA = atom({ plugin: 'circuit-viewer', key: 'side' } as const, 'both' as Side)
const focusA = atom({ plugin: 'circuit-viewer', key: 'focus' } as const, -1)
const zoomA = atom({ plugin: 'circuit-viewer', key: 'zoom' } as const, false)

// ---- the backend ------------------------------------------------------------------

async function cli<T>($: $, command: string, path: string, timeoutMs = 120_000): Promise<T> {
  const run = await $.process.run(['node', '--input-type=module', '-', command, path], { stdin: CLI_SOURCE, timeoutMs })
  const line = run.stdout.trim().split('\n').pop() ?? ''
  let answer: { ok: boolean; data?: T; error?: string }
  try {
    answer = JSON.parse(line)
  } catch {
    throw new Error(run.stderr.trim().split('\n').slice(-3).join(' ') || `the circuit viewer's backend gave no answer (node exit ${run.exitCode}); is Node.js on PATH?`)
  }
  if (!answer.ok) throw new Error(answer.error ?? 'failed')
  return answer.data as T
}

/** A tool's own arguments arrive on the tool.call event itself, beside `tool` and `tool_use_id`. */
const arg = (e: object, name: string): unknown => (e as Record<string, unknown>)[name]

const blocking = (s: Snapshot | null): Marker[] => (s?.drc?.markers ?? []).filter(m => SERIOUS.has(m.type))

function summary(s: Snapshot): string {
  const b = s.board
  const lines = [`${s.project.name} (${s.project.root})`]
  if (b) {
    const size = b.bbox ? `${b.bbox.w.toFixed(1)} x ${b.bbox.h.toFixed(1)} mm, ` : ''
    lines.push(`Board: ${size}${b.copperLayers.length} copper layers, ${b.footprints} footprints, ${b.nets} nets; ${b.metrics.track_mm_total} mm of track, ${b.metrics.vias} vias` +
      (b.zoneNets.length ? `; ${b.metrics.zone_net_track_mm} mm on plane/pour nets (${b.zoneNets.join(', ')})` : ''))
    const m = blocking(s)
    lines.push(m.length ? `DRC: ${m.length} blocking marker(s): ${[...new Set(m.map(x => x.type))].join(', ')}` : 'DRC: no blocking markers')
  } else lines.push('No .kicad_pcb exported yet.')
  if (s.routing?.state) lines.push(`Routing (${s.routing.backend}): ${s.routing.state}${s.routing.message ? `: ${s.routing.message}` : ''}`)
  return lines.join('\n')
}

/** Loads (or reloads) the project into the pane's state. */
async function load($: $, path: string, opts: { withChecks?: boolean } = {}): Promise<Snapshot> {
  await update($, statusA, () => 'loading…')
  try {
    const snap = await cli<Snapshot>($, 'snapshot', path)
    const prev = await read($, targetA)
    await update($, targetA, () => path)
    await update($, snapshotA, () => snap)
    if (prev !== path) {
      await update($, focusA, () => -1)
      await update($, zoomA, () => false)
      await update($, checksA, () => null)
    }
    await update($, statusA, () => '')
    if (opts.withChecks && snap.project.board) void runChecks($, path, snap.revision)
    return snap
  } catch (e) {
    await update($, statusA, () => (e as Error).message)
    throw e
  }
}

async function runChecks($: $, path: string, revision: string): Promise<Checks> {
  await update($, statusA, () => 'running drc_check, dfm_check, check_floating…')
  try {
    const r = await cli<Omit<Checks, 'revision'> & { text: string }>($, 'check', path, 300_000)
    const checks: Checks = { ok: r.ok, summary: r.summary, gates: r.gates, revision }
    if ((await read($, targetA)) === path) await update($, checksA, () => checks)
    await update($, statusA, () => '')
    $.ui.status(`${r.ok ? 'board ok' : 'board FAILING'}: ${r.summary.split('\n')[0]}`)
    return checks
  } catch (e) {
    await update($, statusA, () => (e as Error).message)
    throw e
  }
}

const open = ($: $, title = 'Circuit board') => $.ui.open({ id: PANE, title })

// ---- live refresh ---------------------------------------------------------------------

/** What a save changes: the board, its rules, the design, and the router's progress file. */
async function stamp($: $, s: Snapshot): Promise<string> {
  const files = [s.project.board, s.project.source]
  if (s.project.board) files.push(s.project.board.replace(/\.kicad_pcb$/, '.kicad_pro'), s.project.board.replace(/\.kicad_pcb$/, '.kicad_dru'), `${s.project.board}.routing.json`)
  const parts = await Promise.all(
    files.filter((f): f is string => !!f).map(f => $.fs.stat(f).then(st => `${st.mtimeMs}:${st.size}`, () => '-')),
  )
  return parts.join('|')
}

// ---- hooks ----------------------------------------------------------------------------

export const register: Register = on => {
  let lastStamp = ''
  let busy = false

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'board',
      description: 'Circuit viewer: /board <path> opens a PCB project (folder, .kicad_pcb or .circuit.tsx); /board check runs the gates; /board alone reopens the pane',
    })
    await $.tool.register({
      name: 'open_board',
      description:
        'Open a PCB project in the circuit viewer pane beside the conversation: the routed KiCad board with its DRC markers, and (after check_board) the pcb-layout gates. ' +
        'The pane follows the board live: save to the same file and it redraws. Give an absolute path to a project folder (or one with a pcb/ folder), a .kicad_pcb, or a .circuit.tsx. ' +
        'Returns a summary: size, layers, parts, nets, track, vias, blocking DRC markers.',
      inputSchema: { type: 'object', properties: { path: { type: 'string', description: 'Absolute path' } }, required: ['path'] },
    })
    await $.tool.register({
      name: 'check_board',
      description:
        'Run the pcb-layout gates on a routed KiCad board: drc_check (DRC triaged; courtyard overlaps, real shorts, crossings, copper over the edge and unconnected items block), ' +
        'dfm_check (hole-to-hole spacing, via drill and annular ring), check_floating (SMD pads reached only by copper on the other layer), plus routing metrics. ' +
        'Use after every routing or finishing step and before calling a board done. Defaults to the board open in the pane.',
      inputSchema: { type: 'object', properties: { path: { type: 'string', description: 'Absolute path; defaults to the open board' } } },
    })
    await $.tool.register({
      name: 'get_netlist',
      description: "The project's netlist as text (components and every net with its pins), from the tscircuit design, or from the KiCad board when there is no design.",
      inputSchema: { type: 'object', properties: { path: { type: 'string', description: 'Absolute path; defaults to the open project' } } },
    })

    // Follow the open board: a cheap stat every two seconds, a full reload on change.
    $.clock.every(2000, async () => {
      if (busy) return
      const snap = await read($, snapshotA)
      const path = await read($, targetA)
      if (!snap || !path) return
      const now = await stamp($, snap)
      if (!lastStamp) { lastStamp = now; return }
      if (now === lastStamp) return
      lastStamp = now
      busy = true
      try {
        const hadChecks = !!(await read($, checksA))
        const fresh = await load($, path)
        if (hadChecks && fresh.project.board) await runChecks($, path, fresh.revision)
        $.ui.toast(`circuit viewer: ${fresh.project.name} changed, redrawn`)
      } catch {
        /* status carries the error */
      } finally {
        busy = false
      }
    })

    return next(e)
  })

  on('command.run', { command: 'board' }, async ($, e) => {
    const arg = e.args.trim()
    try {
      if (arg === 'check') {
        const path = await read($, targetA)
        const snap = await read($, snapshotA)
        if (!path || !snap) return { text: 'No board open. Use /board <path> first.' }
        await open($)
        const r = await runChecks($, path, snap.revision)
        return { text: r.summary }
      }
      if (!arg) {
        const snap = await read($, snapshotA)
        await open($, snap?.project.name ?? 'Circuit board')
        return { text: snap ? `Circuit viewer: ${snap.project.name}` : 'Circuit viewer open. Use /board <path> to open a project.' }
      }
      const snap = await load($, arg, { withChecks: true })
      lastStamp = await stamp($, snap)
      await open($, snap.project.name)
      return { text: summary(snap), context: [`The circuit viewer pane now shows ${snap.project.board ?? snap.project.root}. Use the circuit-viewer tools (check_board, get_netlist) on it.`] }
    } catch (err) {
      return { text: `circuit viewer: ${(err as Error).message}` }
    }
  })

  on('tool.call', { tool: 'mcp__circuit-viewer__open_board' }, async ($, e) => {
    const path = String(arg(e, 'path') ?? '')
    try {
      const snap = await load($, path, { withChecks: true })
      lastStamp = await stamp($, snap)
      await open($, snap.project.name)
      return { result: `Opened in the circuit viewer pane.\n${summary(snap)}\nThe gates are running; call check_board for their verdict.` }
    } catch (err) {
      return { deny: (err as Error).message }
    }
  })

  on('tool.call', { tool: 'mcp__circuit-viewer__check_board' }, async ($, e) => {
    const given = arg(e, 'path')
    const open_ = await read($, targetA)
    const path = typeof given === 'string' && given ? given : open_
    if (!path) return { deny: 'No board open in the circuit viewer; give a path.' }
    try {
      if (path === open_) {
        const snap = await read($, snapshotA)
        const r = await runChecks($, path, snap?.revision ?? '')
        return { result: [r.summary, ...r.gates.map(g => `\n── ${g.name} (${g.ok ? 'pass' : `exit ${g.exitCode}`}) ──\n${g.output}`)].join('\n') }
      }
      const r = await cli<{ text: string }>($, 'check', path, 300_000)
      return { result: r.text }
    } catch (err) {
      return { deny: (err as Error).message }
    }
  })

  on('tool.call', { tool: 'mcp__circuit-viewer__get_netlist' }, async ($, e) => {
    const given = arg(e, 'path')
    const path = typeof given === 'string' && given ? given : await read($, targetA)
    if (!path) return { deny: 'No project open in the circuit viewer; give a path.' }
    try {
      const { text, from } = await cli<{ text: string; from: string }>($, 'netlist', path, 240_000)
      return { result: `Netlist (from the ${from === 'tscircuit' ? 'tscircuit design' : 'KiCad board'}):\n${text}` }
    } catch (err) {
      return { deny: (err as Error).message }
    }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const els = $.ui.resolve(e)
    const { Box, Text, Button } = els
    const [snap, checks, status, side, focus, zoom] = await Promise.all([
      read($, snapshotA), read($, checksA), read($, statusA), read($, sideA), read($, focusA), read($, zoomA),
    ])
    const cols = Math.max(20, e.props.bodyColumns)

    if (!snap) {
      return (
        <Box flexDirection="column">
          <Text bold>Circuit viewer</Text>
          <Text dimColor>{status || 'Open a project with /board <path>, or ask Claude to open one.'}</Text>
        </Box>
      )
    }

    const markers = blocking(snap)
    const sel = focus >= 0 && focus < markers.length ? markers[focus]! : null
    const b = snap.board
    const stale = checks && checks.revision !== snap.revision
    const verdict = !checks
      ? <Text dimColor>gates not run</Text>
      : checks.ok
        ? <Text color="#39d98a" bold>{stale ? 'gates passed (before this save)' : 'all gates pass'}</Text>
        : <Text color="#ff5d5d" bold>FAILING: {checks.gates.filter(g => !g.ok).map(g => g.name).join(', ')}{stale ? ' (before this save)' : ''}</Text>

    let picture = null
    if (snap.geometry) {
      const view = viewBox(snap.geometry, sel, zoom)
      const args = { geom: snap.geometry, markers, focus, side, view }
      const rows = rowsFor(view, cols, Math.max(6, (e.viewport?.rows ?? 40) - 14))
      if (e.surface === 'terminal') {
        const { Raster } = $.ui.resolve(e)
        picture = <Raster key="board" columns={Math.min(cols, 512)} rows={rows} cells={rasterCells(args, Math.min(cols, 512), rows)} />
      } else {
        const { Svg } = $.ui.resolve(e)
        picture = <Svg source={boardSvg(args)} alt={`${snap.project.name}: routed board`} />
      }
    }

    const counts = new Map<string, number>()
    for (const m of markers) counts.set(m.type, (counts.get(m.type) ?? 0) + 1)

    return (
      <Box flexDirection="column">
        <Box flexDirection="row" gap={2}>
          <Text bold>{snap.project.name}</Text>
          {verdict}
        </Box>
        {b && (
          <Text dimColor wrap="truncate-end">
            {b.metrics.track_mm_total} mm track · {b.metrics.vias} vias{b.zoneNets.length ? ` · ${b.metrics.zone_net_track_mm} mm on ${b.zoneNets.join('/')} as track` : ''} · {b.footprints} parts · {b.nets} nets
          </Text>
        )}
        {snap.routing?.state && (
          <Text color="#ffb547" wrap="truncate-end">routing ({snap.routing.backend}): {snap.routing.state}{snap.routing.message ? ` · ${snap.routing.message}` : ''}</Text>
        )}
        {picture}
        <Box flexDirection="row" gap={2}>
          <Text color="#e5484d">■ front</Text>
          <Text color="#3e8ed0">■ back</Text>
          <Text color="#ffb547">○ unconnected</Text>
          <Text color="#ff3b3b">○ short</Text>
          <Text color="#f5d76e">— outline</Text>
        </Box>
        <Text>
          {markers.length
            ? `${markers.length} blocking: ${[...counts].map(([t, n]) => `${t.replace(/_/g, ' ')} ${n}`).join(', ')}`
            : b ? 'No blocking DRC markers.' : 'No board exported yet.'}
        </Text>
        {sel && (
          <Text wrap="wrap" color={'#' + markerColor(sel).toString(16).padStart(6, '0')}>
            {focus + 1}/{markers.length} {sel.type.replace(/_/g, ' ')}: {sel.items.map(i => i.description).join(' ↔ ') || sel.description}
          </Text>
        )}
        <Box flexDirection="row" gap={1}>
          {markers.length > 0 && (
            <Button key="next" label="Next issue" hotkey="n" onPress={() => update($, focusA, f => ((f ?? -1) + 1) % markers.length)} />
          )}
          {sel && <Button key="zoom" label={zoom ? 'Whole board' : 'Zoom in'} hotkey="z" onPress={() => update($, zoomA, z => !z)} />}
          <Button key="side" label={`Side: ${side}`} hotkey="s" onPress={() => update($, sideA, s => (s === 'both' ? 'front' : s === 'front' ? 'back' : 'both'))} />
          <Button
            key="check"
            label="Check"
            hotkey="c"
            variant="primary"
            onPress={async () => {
              const path = await read($, targetA)
              if (path) await runChecks($, path, snap.revision).catch(() => {})
            }}
          />
          <Button
            key="reload"
            label="Reload"
            hotkey="r"
            onPress={async () => {
              const path = await read($, targetA)
              if (path) await load($, path).catch(() => {})
            }}
          />
        </Box>
        {status && <Text dimColor wrap="truncate-end">{status}</Text>}
        <Text dimColor wrap="truncate-start">{snap.project.board ?? snap.project.root}</Text>
      </Box>
    )
  })
}
