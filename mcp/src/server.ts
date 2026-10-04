import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult, ReadResourceResult } from "@modelcontextprotocol/sdk/types.js";
import path from "node:path";
import { projectStatus } from "./status.js";
import { z } from "zod";
import { checkBoard, type CheckReport } from "./checks.js";
import { resolveProject, type Project } from "./project.js";
import { boardDrc, boardGlb, boardInfo, boardLayerNames, layerSvg, netlistText, schematicSvg } from "./views.js";

// circuit-skills as an MCP App, with OpenAI's plugin-extension entrypoints.
//
// One widget, the board viewer (schematic, netlist, routed board with DRC
// markers, 3D, checks), opened by:
//   open_board   the model opens a project folder, .kicad_pcb or .circuit.tsx
//   open_viewer  the SIDEBAR app and the THREAD panel (asks for a path)
//   open_file    the FILE viewer for .kicad_pcb and .circuit.tsx files
// Model tools without the widget: check_board (the pcb-layout gates + routing
// metrics) and get_netlist. The widget fetches each view lazily through the
// app-only load_view tool, so nothing is exported until a tab is looked at.
//
// The server runs on the user's machine (the plugin launches it over stdio) and
// reads the project files and runs kicad-cli / tsci there. It calls no model.

export const SERVER_VERSION = "0.1.0";
const WIDGET_URI = "ui://circuit-skills/viewer-v1.html";
export const FILE_EXTENSIONS = [".kicad_pcb", ".circuit.tsx"];

const READ_ONLY = { readOnlyHint: true, destructiveHint: false, openWorldHint: false, idempotentHint: true };

const pathArg = z
  .string()
  .min(1)
  .describe("Absolute path to a project folder (or a folder with a pcb/ folder in it), a .kicad_pcb board, or a .circuit.tsx tscircuit design.");

const fileInput = z.object({
  file: z.object({
    name: z.string().min(1).describe("File name with extension, no path"),
    resourceUri: z.string().min(1).describe("Opaque host URI for the file"),
  }),
});

const VIEWS = ["status", "project", "layer", "schematic", "netlist", "glb", "drc", "checks"] as const;

export interface ServerOptions {
  /** The built widget page (dist/widget.html). */
  widgetHtml: string;
  /** Monochrome SVG (currentColor) shown in the sidebar and tabs. */
  iconSvg: string;
}

/** What the widget and the model are told about an opened project. */
async function describeProject(project: Project) {
  const info = project.board ? await boardInfo(project.board) : null;
  return {
    ...(await projectStatus(project)),
    project,
    layers: project.board ? await boardLayerNames(project.board) : [],
    board: info
      ? {
          copperLayers: info.copperLayers,
          bbox: info.bbox,
          footprints: info.footprints,
          nets: info.nets.length,
          zoneNets: info.zoneNets,
          metrics: info.metrics,
        }
      : null,
  };
}

function projectText(d: Awaited<ReturnType<typeof describeProject>>): string {
  const p = d.project;
  const lines = [`Opened ${p.name} in the circuit viewer (${p.root}).`];
  lines.push(p.source ? `Design: ${path.basename(p.source)} (tscircuit)` : "Design: none (no .circuit.tsx; schematic unavailable)");
  if (d.board) {
    const b = d.board;
    const size = b.bbox ? `${b.bbox.w.toFixed(1)} x ${b.bbox.h.toFixed(1)} mm, ` : "";
    lines.push(
      `Board: ${path.basename(p.board!)}: ${size}${b.copperLayers.length} copper layers, ${b.footprints} footprints, ${b.nets} nets; ` +
        `${b.metrics.track_mm_total} mm of track, ${b.metrics.vias} vias`,
    );
  } else lines.push("Board: none exported yet (run the pcb-layout export/route step).");
  lines.push("Run check_board for the DRC / DFM / floating-pad gates.");
  return lines.join("\n");
}

function checkText(r: CheckReport, verbose: boolean): string {
  if (!verbose) return r.summary;
  return [r.summary, ...r.gates.map((g) => `\n── ${g.name} (${g.ok ? "pass" : `exit ${g.exitCode}`}) ──\n${g.output}`)].join("\n");
}

function pathFromMeta(extra: unknown): string | undefined {
  const meta = (extra as { _meta?: Record<string, unknown> } | undefined)?._meta;
  const p = (meta?.["openai/resource"] as { path?: unknown } | undefined)?.path;
  return typeof p === "string" && path.isAbsolute(p) ? p : undefined;
}

const fail = (e: unknown): CallToolResult => ({ isError: true, content: [{ type: "text", text: (e as Error).message ?? String(e) }] });

export function createServer({ widgetHtml, iconSvg }: ServerOptions): McpServer {
  const icon = { src: "data:image/svg+xml," + encodeURIComponent(iconSvg), mimeType: "image/svg+xml", sizes: ["any"] };
  const server = new McpServer({ name: "circuit-skills", title: "Circuit viewer", version: SERVER_VERSION, icons: [icon] });

  const ui = (entrypoints: unknown[] = []) => ({
    ui: { resourceUri: WIDGET_URI },
    "openai/outputTemplate": WIDGET_URI,
    ...(entrypoints.length ? { "openai/ui": { entrypoints }, "openai/iconStyle": "monochrome" } : {}),
  });

  server.registerTool(
    "open_board",
    {
      title: "Open in the circuit viewer",
      description:
        "Open a PCB project in the circuit viewer: the schematic and netlist from the tscircuit design, the routed KiCad board layer by layer with DRC markers, a 3D view, and the board checks. " +
        "Use whenever the user wants to see, show, look at, compare or review a board, a schematic or a routing result. " +
        "Give the project folder, a .kicad_pcb, or a .circuit.tsx. The result summarises the board (size, layers, parts, nets, track, vias).",
      inputSchema: { path: pathArg },
      annotations: READ_ONLY,
      _meta: ui(),
    },
    async ({ path: p }): Promise<CallToolResult> => {
      try {
        const d = await describeProject(await resolveProject(p));
        return { content: [{ type: "text", text: projectText(d) }], structuredContent: d };
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerTool(
    "open_viewer",
    {
      title: "Circuit viewer",
      description:
        "Open the circuit viewer without a project, for the user to pick one. Prefer open_board when you know the path.",
      inputSchema: {},
      annotations: READ_ONLY,
      _meta: ui([{ type: "global" }, { type: "thread" }]),
    },
    async (): Promise<CallToolResult> => ({ content: [{ type: "text", text: "Opened the circuit viewer. No project is loaded yet." }], structuredContent: {} }),
  );

  server.registerTool(
    "open_file",
    {
      title: "Circuit viewer",
      description: "Open a .kicad_pcb board or a .circuit.tsx tscircuit design from the workspace in the circuit viewer.",
      inputSchema: fileInput.shape,
      annotations: READ_ONLY,
      _meta: ui([{ type: "file", extensions: FILE_EXTENSIONS }]),
    },
    async ({ file }, extra): Promise<CallToolResult> => {
      const p = pathFromMeta(extra);
      if (p) {
        try {
          const d = await describeProject(await resolveProject(p));
          return { content: [{ type: "text", text: projectText(d) }], structuredContent: { file, ...d } };
        } catch {
          /* fall through: the widget resolves it via load_view */
        }
      }
      return { content: [{ type: "text", text: `Opened ${file.name} in the circuit viewer.` }], structuredContent: { file } };
    },
  );

  server.registerTool(
    "check_board",
    {
      title: "Check a board",
      description:
        "Run the pcb-layout gates on a routed KiCad board and measure its routing: drc_check (DRC triaged into placement, real shorts, unconnected and cosmetic; unconnected items block), " +
        "dfm_check (fab rules KiCad's DRC misses: hole-to-hole spacing, via drill/annular ring), and check_floating (SMD pads reached only by copper on the other layer). " +
        "Also reports track length, vias, and how much track is on plane/pour nets. Use after every routing or finishing step, and before calling a board done or ordering it.",
      inputSchema: { path: pathArg, verbose: z.boolean().optional().describe("Include each gate's full output (default true).") },
      annotations: READ_ONLY,
    },
    async ({ path: p, verbose }): Promise<CallToolResult> => {
      try {
        const project = await resolveProject(p);
        if (!project.board) return fail(new Error(`${project.name} has no .kicad_pcb to check yet.`));
        const report = await checkBoard(project.board);
        return { content: [{ type: "text", text: checkText(report, verbose ?? true) }], structuredContent: report as unknown as Record<string, unknown> };
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerTool(
    "get_netlist",
    {
      title: "Get the netlist",
      description:
        "The project's netlist as text: components and every net with its pins, from the tscircuit design (or from the KiCad board when there is no design). Use to answer connectivity questions or check a design against intent.",
      inputSchema: { path: pathArg },
      annotations: READ_ONLY,
    },
    async ({ path: p }): Promise<CallToolResult> => {
      try {
        const { text, from } = await netlistText(await resolveProject(p));
        return { content: [{ type: "text", text: `Netlist (from the ${from === "tscircuit" ? "tscircuit design" : "KiCad board"}):\n${text}` }] };
      } catch (e) {
        return fail(e);
      }
    },
  );

  // Called by the viewer, never by the model.
  server.registerTool(
    "load_view",
    {
      title: "Load a view",
      description: "Used by the circuit viewer to load one view of the open project. Not for the model.",
      inputSchema: {
        path: z.string().optional(),
        view: z.enum(VIEWS),
        layer: z.string().optional(),
      },
      annotations: READ_ONLY,
      _meta: { ui: { visibility: ["app"] } },
    },
    async ({ path: p, view, layer }, extra): Promise<CallToolResult> => {
      const target = p ?? pathFromMeta(extra);
      if (!target) return fail(new Error("No project path."));
      try {
        const project = await resolveProject(target);
        const needBoard = () => {
          if (!project.board) throw new Error(`${project.name} has no .kicad_pcb yet.`);
          return project.board;
        };
        let data: Record<string, unknown>;
        switch (view) {
          case "status":
            data = await projectStatus(project);
            break;
          case "project":
            data = await describeProject(project);
            break;
          case "layer":
            if (!layer) throw new Error("layer is required");
            data = { layer, svg: await layerSvg(needBoard(), layer) };
            break;
          case "schematic":
            data = { svg: await schematicSvg(project) };
            break;
          case "netlist":
            data = await netlistText(project);
            break;
          case "glb":
            data = { glb: (await boardGlb(needBoard())).toString("base64") };
            break;
          case "drc":
            data = { ...(await boardDrc(needBoard())) };
            break;
          case "checks":
            data = { ...(await checkBoard(needBoard())) };
            break;
        }
        return { content: [{ type: "text", text: view }], structuredContent: data };
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerResource(
    "circuit-viewer",
    WIDGET_URI,
    { title: "Circuit viewer", description: "Schematic, netlist, routed board, 3D and checks for a PCB project", mimeType: "text/html;profile=mcp-app" },
    async (): Promise<ReadResourceResult> => ({
      contents: [
        {
          uri: WIDGET_URI,
          mimeType: "text/html;profile=mcp-app",
          text: widgetHtml,
          _meta: {
            "openai/ui": { preferredDisplayMode: "inline", availableDisplayModes: ["inline", "fullscreen"] },
            // Self-contained: everything is drawn from data the local server returns.
            ui: { csp: { frameDomains: [], resourceDomains: [], connectDomains: [] }, prefersBorder: true },
            "openai/widgetDescription": "The circuit viewer showing a PCB project: schematic, netlist, routed board with DRC markers, 3D view and check results.",
          },
        },
      ],
    }),
  );

  return server;
}
