// The circuit viewer: the page an AI host renders for open_board, the sidebar
// app, the thread panel, or an opened .kicad_pcb / .circuit.tsx file.
//
// It holds no circuit logic. Every view comes from the local server's app-only
// load_view tool (kicad-cli / tsci exports and the pcb-layout gates); this page
// draws them, lets the user pan, zoom, toggle layers and step through DRC
// markers, and tells the model what is open and what the checks found.
import { App, applyDocumentTheme, applyHostFonts, applyHostStyleVariables } from "@modelcontextprotocol/ext-apps";
import { OpenAIExtensions, OpenAIFileEntrypointInputSchema } from "@openai/mcp-extensions/app";
import { PanZoom, type Box } from "./panzoom.js";
import { ThreeView } from "./three-view.js";

type Tab = "board" | "schematic" | "netlist" | "3d" | "checks";
type McpUiHostContext = NonNullable<ReturnType<App["getHostContext"]>>;

interface Project {
  name: string;
  root: string;
  board?: string;
  source?: string;
}
interface Described {
  revision?: string;
  routing?: { backend: string; state: string; message?: string };
  project: Project;
  layers: string[];
  board: null | {
    copperLayers: string[];
    bbox: Box | null;
    footprints: number;
    nets: number;
    zoneNets: string[];
    metrics: Record<string, unknown> & { track_mm_total: number; vias: number; zone_net_track_mm: number; segments_total: number };
  };
}
interface Marker {
  kind: "violation" | "unconnected";
  type: string;
  severity: string;
  description: string;
  items: { description: string; x: number; y: number }[];
}
interface Gate {
  name: string;
  ok: boolean;
  exitCode: number;
  output: string;
}
interface CheckReport {
  ok: boolean;
  summary: string;
  gates: Gate[];
  drc: { counts: Record<string, number>; unconnected: number };
}

const INLINE_HEIGHT = 600;
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const nameEl = $("name");
const statusEl = $("status");
const reviewBtn = $<HTMLButtonElement>("review");
const expandBtn = $<HTMLButtonElement>("expand");

const app = new App({ name: "Circuit viewer", version: "0.1.0" }, { availableDisplayModes: ["inline", "fullscreen"] });
const openai = new OpenAIExtensions(app);

let connected = false;
let whenConnected: Promise<void> = Promise.resolve();
let displayMode: "inline" | "fullscreen" | "pip" = "inline";
let current: Described | null = null;
/** The path load_view is called with: the board, else the design. */
let projectPath: string | undefined;
/** Opened from a host file entrypoint: the server resolves the path from host metadata. */
let viaFileEntry = false;
let tab: Tab = "board";
const loaded = new Set<Tab>();
let lastChecks: CheckReport | null = null;

function setStatus(text: string, tone: "" | "good" | "bad" = "") {
  statusEl.textContent = text;
  statusEl.className = `status ${tone}`;
}

function message(title: string, text: string) {
  $("msg-title").textContent = title;
  $("msg-text").textContent = text;
  $("msg").hidden = !title;
}

// ---- server calls ---------------------------------------------------------------

async function loadView<T>(view: string, extra: Record<string, unknown> = {}): Promise<T> {
  const epoch = watchEpoch, target = projectPath;
  await whenConnected;
  const args: Record<string, unknown> = { view, ...extra };
  if (projectPath) args.path = projectPath;
  const result = await app.callServerTool({ name: "load_view", arguments: args });
  if (epoch !== watchEpoch || target !== projectPath) throw new Error("Project changed while loading; retry this view.");
  const text = result.content?.find((c) => c.type === "text") as { text?: string } | undefined;
  if (result.isError) throw new Error(text?.text ?? `Could not load ${view}.`);
  return result.structuredContent as T;
}

// ---- tabs -----------------------------------------------------------------------

const tabButtons = [...document.querySelectorAll<HTMLButtonElement>("#tabs button")];
for (const b of tabButtons) b.addEventListener("click", () => void show(b.dataset.tab as Tab));

async function show(next: Tab) {
  const epoch = watchEpoch;
  tab = next;
  for (const b of tabButtons) b.setAttribute("aria-selected", String(b.dataset.tab === next));
  for (const v of document.querySelectorAll<HTMLElement>(".view")) v.hidden = v.dataset.view !== next;
  message("", "");
  if (!current || loaded.has(next)) return;
  loaded.add(next);
  try {
    if (next === "board") await loadBoard();
    else if (next === "schematic") await loadSchematic();
    else if (next === "netlist") await loadNetlist();
    else if (next === "3d") await loadThree();
    else if (next === "checks") await runChecks();
  } catch (e) {
    if (epoch !== watchEpoch) return;
    loaded.delete(next);
    if (tab === next) message("Couldn't load this view", (e as Error).message);
  }
}

function refreshTabs() {
  const has = { board: !!current?.project.board, schematic: !!current?.project.source, netlist: !!current, "3d": !!current?.project.board, checks: !!current?.project.board };
  for (const b of tabButtons) b.disabled = !has[b.dataset.tab as Tab];
}

// ---- open a project --------------------------------------------------------------

function reset() {
  loaded.clear();
  lastChecks = null;
  $("layers").replaceChildren();
  $("drc").replaceChildren();
  $("board-canvas").replaceChildren();
  $("sch-canvas").replaceChildren();
  $("netlist").textContent = "";
  $("checks").replaceChildren();
  boardView?.pz.dispose();
  boardView = null;
}

async function openProject(d: Described) {
  clearTimeout(watchTimer); watchEpoch++;
  reset();
  current = d;
  projectPath = d.project.board ?? d.project.source ?? d.project.root;
  remember(projectPath);
  nameEl.textContent = d.project.name;
  nameEl.title = d.project.root;
  $("picker").hidden = true;
  reviewBtn.hidden = !d.project.board;
  refreshTabs();
  const m = d.board?.metrics;
  setStatus(m ? `${d.board!.footprints} parts · ${d.board!.nets} nets · ${m.track_mm_total} mm track · ${m.vias} vias` : "no board exported yet");
  reportContext();
  await show(d.project.board ? "board" : "schematic");
  startWatching();
}

async function openPath(p: string) {
  projectPath = p.trim();
  viaFileEntry = false;
  setStatus("opening…");
  try {
    await openProject(await loadView<Described>("project"));
  } catch (e) {
    setStatus((e as Error).message, "bad");
  }
}

function showPicker() {
  if (current) return;
  $("picker").hidden = false;
  for (const v of document.querySelectorAll<HTMLElement>(".view")) v.hidden = true;
  refreshTabs();
  const list = $("recent");
  list.replaceChildren();
  for (const p of recents()) {
    const a = document.createElement("a");
    a.textContent = p;
    a.addEventListener("click", () => void openPath(p));
    list.appendChild(a);
  }
}

// No <form>: hosts sandbox the widget without allow-forms, which blocks submission.
function submitPick() {
  const p = $<HTMLInputElement>("pick-path").value;
  if (p.trim()) void openPath(p);
}
$("pick-go").addEventListener("click", submitPick);
$("pick-path").addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitPick();
});

function recents(): string[] {
  try {
    return JSON.parse(localStorage.getItem("circuit-viewer-recent") ?? "[]") as string[];
  } catch {
    return [];
  }
}
function remember(p: string) {
  try {
    localStorage.setItem("circuit-viewer-recent", JSON.stringify([p, ...recents().filter((r) => r !== p)].slice(0, 6)));
  } catch {
    /* storage unavailable */
  }
}

// Saved boards refresh automatically; router progress is separate from KiCad DRC.
let watchTimer: ReturnType<typeof setTimeout> | undefined;
let watching = false;
let watchEpoch = 0;
let stableRevision: string | undefined;
function showProgress(updateMetrics = false) {
  const m = current?.board?.metrics, r = current?.routing;
  $("progress").textContent = r ? `${r.backend}: ${r.state}${r.message ? " · " + r.message : ""}` : "live";
  if (updateMetrics && tab === "board" && m) setStatus(`${current!.board!.footprints} parts · ${m.track_mm_total} mm track · ${m.vias} vias`);
}
function startWatching() {
  clearTimeout(watchTimer);
  watching = true;
  const epoch = ++watchEpoch;
  stableRevision = current?.revision;
  const tick = async () => {
    if (!watching || epoch !== watchEpoch) return;
    try {
      if (!document.hidden && current) {
        const target = projectPath;
        const status = await loadView<{ revision: string; routing: Described["routing"] }>("status");
        if (epoch !== watchEpoch || target !== projectPath) return;
        current.routing = status.routing;
        if (status.revision !== current.revision) {
          // Wait for two matching samples, so a half-written file is not displayed.
          if (status.revision === stableRevision) {
            const d = await loadView<Described>("project");
            if (epoch !== watchEpoch || target !== projectPath) return;
            const selected = tab;
            const box = boardView?.pz.snapshot();
            const choices = new Map([...document.querySelectorAll<HTMLInputElement>("#layers input, #drc input")].map(x => [x.dataset.key, x.checked]));
            reset(); current = d; refreshTabs();
            await show(selected);
            if (epoch !== watchEpoch) return;
            if (box) boardView?.pz.restore(box);
            for (const input of document.querySelectorAll<HTMLInputElement>("#layers input, #drc input")) {
              if (choices.has(input.dataset.key)) { input.checked = choices.get(input.dataset.key)!; input.dispatchEvent(new Event("change")); }
            }
            showProgress(true); reportContext();
          }
          stableRevision = status.revision;
        } else showProgress();
      }
    } catch (e) { if (epoch === watchEpoch) setStatus(`Live update waiting: ${(e as Error).message}`, "bad"); }
    finally { if (watching && epoch === watchEpoch) watchTimer = setTimeout(tick, 2000); }
  };
  watchTimer = setTimeout(tick, 2000);
}

// ---- board ------------------------------------------------------------------------

const SVG_NS = "http://www.w3.org/2000/svg";
const LAYER_COLORS: Record<string, string> = {
  "F.Cu": "#e5484d",
  "B.Cu": "#3e8ed0",
  "In1.Cu": "#d4a72c",
  "In2.Cu": "#3fb27f",
  "In3.Cu": "#b45cd6",
  "In4.Cu": "#d67a3a",
  "F.Silkscreen": "#e8ecef",
  "B.Silkscreen": "#9a8fd6",
  "Edge.Cuts": "#f5d76e",
};
const layerColor = (l: string) => LAYER_COLORS[l] ?? "#9aa5b1";
/** Inner planes are solid copper and hide everything else; start them hidden. */
const startsVisible = (l: string) => !/^In\d+\.Cu$/.test(l) && l !== "B.Silkscreen";
const MARKER_COLORS: Record<string, string> = { shorting_items: "#ff5d5d", unconnected_items: "#ffb547", tracks_crossing: "#ff5d5d", clearance: "#ff8fd0", hole_clearance: "#ff8fd0", courtyards_overlap: "#c084fc" };
const markerColor = (t: string) => MARKER_COLORS[t] ?? "#9aa5b1";
/**
 * DRC types shown by default: the ones that make a board unbuildable or open
 * (what drc_check blocks on, plus clearance and hole problems). Everything else
 * (silk clipping, dangling stubs, library mismatches) is listed but hidden.
 */
const SERIOUS = /^(shorting_items|tracks_crossing|courtyards_overlap|unconnected_items|copper_edge_clearance|clearance|hole_clearance|hole_to_hole|items_not_allowed|annular_width|drill_out_of_range|via_diameter|track_width)$/;
const COSMETIC = { test: (t: string) => !SERIOUS.test(t) };

let boardView: { svg: SVGSVGElement; pz: PanZoom; markers: SVGGElement; byType: Map<string, Marker[]>; step: Map<string, number> } | null = null;

function importSvg(text: string, color?: string): Element {
  // KiCad's black-and-white export: black is the layer, white is drill holes.
  const coloured = color ? text.replace(/#000000/gi, color).replace(/#FFFFFF/gi, "#101418") : text;
  const doc = new DOMParser().parseFromString(coloured, "image/svg+xml");
  const err = doc.querySelector("parsererror");
  if (err) throw new Error("Could not read the exported SVG.");
  return doc.documentElement;
}

async function loadBoard() {
  if (!current?.project.board) return;
  const host = $("board-canvas");
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.classList.add("pz");
  svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
  host.appendChild(svg);
  const b = current.board?.bbox ?? { x: 0, y: 0, w: 297, h: 210 };
  const pad = Math.max(b.w, b.h) * 0.04;
  const pz = new PanZoom(svg, { x: b.x - pad, y: b.y - pad, w: b.w + 2 * pad, h: b.h + 2 * pad });
  const markers = document.createElementNS(SVG_NS, "g");
  boardView = { svg, pz, markers, byType: new Map(), step: new Map() };

  const list = $("layers");
  setStatus("exporting layers…");
  const layers = current.layers;
  const groups = new Map<string, SVGGElement>();
  for (const layer of layers) {
    const g = document.createElementNS(SVG_NS, "g");
    g.dataset.layer = layer;
    g.style.opacity = /\.Cu$/.test(layer) ? "0.82" : "1";
    g.style.display = startsVisible(layer) ? "" : "none";
    svg.appendChild(g);
    groups.set(layer, g);
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox"${startsVisible(layer) ? " checked" : ""}><span class="swatch" style="background:${layerColor(layer)}"></span><span></span>`;
    (label.lastElementChild as HTMLElement).textContent = layer;
    label.querySelector("input")!.dataset.key = layer;
    label.querySelector("input")!.addEventListener("change", (e) => (g.style.display = (e.target as HTMLInputElement).checked ? "" : "none"));
    list.appendChild(label);
  }
  svg.appendChild(markers);

  // Layers arrive in parallel; each lands in its slot so stacking order holds.
  await Promise.all(
    layers.map(async (layer) => {
      const { svg: text } = await loadView<{ svg: string }>("layer", { layer });
      const root = importSvg(text, layerColor(layer));
      const g = groups.get(layer)!;
      for (const child of [...root.childNodes]) g.appendChild(document.importNode(child, true));
    }),
  );
  showProgress(true);
  await loadMarkers();
  pz.onChange = () => sizeMarkers();
  sizeMarkers();
}

async function loadMarkers() {
  if (!boardView) return;
  const { markers, byType } = boardView;
  const drc = await loadView<{ markers: Marker[]; counts: Record<string, number>; unconnected: number }>("drc");
  for (const m of drc.markers) {
    const list = byType.get(m.type) ?? [];
    list.push(m);
    byType.set(m.type, list);
  }
  const side = $("drc");
  if (!drc.markers.length) side.innerHTML = `<div class="hint" style="margin-top:0;color:var(--accent)">No DRC markers.</div>`;
  const types = [...byType.keys()].sort((a, b) => Number(COSMETIC.test(a)) - Number(COSMETIC.test(b)) || byType.get(b)!.length - byType.get(a)!.length);
  for (const type of types) {
    const g = document.createElementNS(SVG_NS, "g");
    g.dataset.type = type;
    const visible = !COSMETIC.test(type);
    g.style.display = visible ? "" : "none";
    const color = markerColor(type);
    for (const m of byType.get(type)!) {
      const title = document.createElementNS(SVG_NS, "title");
      title.textContent = [m.description, ...m.items.map((i) => i.description)].join("\n");
      if (m.items.length >= 2 && m.kind === "unconnected") {
        const line = document.createElementNS(SVG_NS, "line");
        line.setAttribute("x1", String(m.items[0].x));
        line.setAttribute("y1", String(m.items[0].y));
        line.setAttribute("x2", String(m.items[1].x));
        line.setAttribute("y2", String(m.items[1].y));
        line.setAttribute("stroke", color);
        line.setAttribute("stroke-dasharray", "0.4 0.3");
        line.classList.add("mk-line");
        line.appendChild(title.cloneNode(true));
        g.appendChild(line);
      }
      for (const it of m.items.slice(0, 2)) {
        const c = document.createElementNS(SVG_NS, "circle");
        c.setAttribute("cx", String(it.x));
        c.setAttribute("cy", String(it.y));
        c.setAttribute("fill", "none");
        c.setAttribute("stroke", color);
        c.classList.add("mk");
        c.appendChild(title.cloneNode(true));
        g.appendChild(c);
      }
    }
    markers.appendChild(g);
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox"${visible ? " checked" : ""}><span class="swatch" style="background:${color}"></span><span class="t"></span><span class="count">${byType.get(type)!.length}</span>`;
    (label.querySelector(".t") as HTMLElement).textContent = type.replace(/_/g, " ");
    const box = label.querySelector("input")!;
    box.dataset.key = type;
    box.addEventListener("change", () => (g.style.display = box.checked ? "" : "none"));
    label.querySelector(".t")!.addEventListener("click", (e) => {
      e.preventDefault();
      box.checked = true;
      g.style.display = "";
      stepTo(type);
    });
    side.appendChild(label);
  }
}

/** Zoom to the next marker of a type. */
function stepTo(type: string) {
  if (!boardView) return;
  const list = boardView.byType.get(type) ?? [];
  if (!list.length) return;
  const i = (boardView.step.get(type) ?? -1) + 1;
  boardView.step.set(type, i % list.length);
  const m = list[i % list.length];
  const xs = m.items.map((p) => p.x), ys = m.items.map((p) => p.y);
  const span = Math.max(4, (Math.max(...xs) - Math.min(...xs)) * 2.5, (Math.max(...ys) - Math.min(...ys)) * 2.5);
  boardView.pz.focus((Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2, span);
  setStatus(`${type.replace(/_/g, " ")} ${(i % list.length) + 1}/${list.length}: ${m.description}${m.items[0] ? ` · ${m.items.map((x) => x.description).join(" ↔ ")}` : ""}`);
}

/** Keep markers a constant size on screen whatever the zoom. */
function sizeMarkers() {
  if (!boardView) return;
  const u = boardView.pz.unitsPerPixel();
  for (const c of boardView.markers.querySelectorAll("circle.mk")) {
    c.setAttribute("r", String(9 * u));
    c.setAttribute("stroke-width", String(2 * u));
  }
  for (const l of boardView.markers.querySelectorAll("line.mk-line")) l.setAttribute("stroke-width", String(1.5 * u));
}

// ---- schematic ----------------------------------------------------------------------

async function loadSchematic() {
  const host = $("sch-canvas");
  setStatus("exporting schematic (tscircuit)…");
  const { svg: text } = await loadView<{ svg: string }>("schematic");
  const root = importSvg(text) as SVGSVGElement;
  const w = parseFloat(root.getAttribute("width") ?? "1200");
  const h = parseFloat(root.getAttribute("height") ?? "600");
  const vb = root.getAttribute("viewBox")?.split(/[\s,]+/).map(Number);
  const home: Box = vb && vb.length === 4 ? { x: vb[0], y: vb[1], w: vb[2], h: vb[3] } : { x: 0, y: 0, w, h };
  root.removeAttribute("width");
  root.removeAttribute("height");
  root.classList.add("pz");
  root.setAttribute("preserveAspectRatio", "xMidYMid meet");
  host.appendChild(document.importNode(root, true));
  new PanZoom(host.querySelector("svg") as SVGSVGElement, home);
  setStatus("");
}

// ---- netlist ------------------------------------------------------------------------

let netText = "";
async function loadNetlist() {
  setStatus("exporting netlist…");
  const { text, from } = await loadView<{ text: string; from: string }>("netlist");
  netText = text;
  $("net-from").textContent = from === "tscircuit" ? "from the tscircuit design" : "from the KiCad board";
  renderNetlist();
  setStatus("");
}

function renderNetlist() {
  const q = $<HTMLInputElement>("net-filter").value.trim().toLowerCase();
  const pre = $("netlist");
  if (!q) {
    pre.textContent = netText;
    return;
  }
  // Keep section headers, show matching lines, highlight the match.
  pre.replaceChildren();
  for (const line of netText.split("\n")) {
    const header = /^[A-Z][A-Z \-()]+:\s*$/.test(line.trim());
    const at = line.toLowerCase().indexOf(q);
    if (!header && at < 0) continue;
    if (at < 0) {
      pre.append(line + "\n");
      continue;
    }
    const mark = document.createElement("mark");
    mark.textContent = line.slice(at, at + q.length);
    pre.append(line.slice(0, at), mark, line.slice(at + q.length) + "\n");
  }
}
$("net-filter").addEventListener("input", renderNetlist);

// ---- 3D -------------------------------------------------------------------------------

let three: ThreeView | null = null;
async function loadThree() {
  setStatus("exporting 3D (kicad-cli glb)…");
  const { glb } = await loadView<{ glb: string }>("glb");
  const bytes = Uint8Array.from(atob(glb), (c) => c.charCodeAt(0));
  three ??= new ThreeView($("three"));
  await three.load(bytes.buffer);
  three.resize();
  setStatus("drag to orbit · scroll to zoom · double-click to reset");
}

// ---- checks ---------------------------------------------------------------------------

async function runChecks() {
  const host = $("checks");
  host.innerHTML = `<div class="verdict">Running drc_check, dfm_check, check_floating…</div>`;
  const r = await loadView<CheckReport>("checks");
  lastChecks = r;
  host.replaceChildren();
  const v = document.createElement("div");
  v.className = `verdict ${r.ok ? "ok" : "bad"}`;
  v.textContent = r.ok ? "All gates pass" : `Failing: ${r.gates.filter((g) => !g.ok).map((g) => g.name).join(", ")}`;
  const sum = document.createElement("pre");
  sum.textContent = r.summary.split("\n").slice(1).join("\n");
  host.append(v, sum);
  const m = current?.board?.metrics;
  if (m) {
    const t = document.createElement("table");
    t.className = "metrics";
    const rows: [string, string][] = [
      ["Track", `${m.track_mm_total} mm in ${m.segments_total} segments`],
      ["Vias", String(m.vias)],
      ...(current!.board!.zoneNets.length ? ([["Plane/pour nets as track", `${m.zone_net_track_mm} mm (${current!.board!.zoneNets.join(", ")})`]] as [string, string][]) : []),
    ];
    for (const [k, val] of rows) t.insertAdjacentHTML("beforeend", `<tr><td>${k}</td><td>${val}</td></tr>`);
    host.appendChild(t);
  }
  for (const g of r.gates) {
    const d = document.createElement("details");
    d.className = "gate";
    d.open = !g.ok;
    d.innerHTML = `<summary><span class="pill ${g.ok ? "ok" : "bad"}">${g.ok ? "pass" : "fail"}</span><b></b></summary><pre></pre>`;
    d.querySelector("b")!.textContent = g.name;
    d.querySelector("pre")!.textContent = g.output;
    host.appendChild(d);
  }
  const again = document.createElement("button");
  again.textContent = "Run again";
  again.addEventListener("click", () => {
    loaded.delete("checks");
    void show("checks");
  });
  host.appendChild(again);
  setStatus(r.ok ? "all gates pass" : `gates failing: ${r.gates.filter((g) => !g.ok).map((g) => g.name).join(", ")}`, r.ok ? "good" : "bad");
  reportContext();
}

// ---- model context ------------------------------------------------------------------

function reportContext() {
  if (!connected || !current) return;
  const p = current.project;
  const m = current.board?.metrics;
  const lines = [
    `The circuit viewer has ${p.name} open (${p.root}).`,
    p.board ? `Board: ${p.board}` : "No board exported yet.",
    p.source ? `Design: ${p.source}` : "",
    m ? `Routing: ${m.track_mm_total} mm track, ${m.vias} vias${current.board!.zoneNets.length ? `, ${m.zone_net_track_mm} mm on plane/pour nets` : ""}.` : "",
    lastChecks ? `Checks: ${lastChecks.summary}` : "",
  ].filter(Boolean);
  const params = { content: [{ type: "text" as const, text: lines.join("\n"), _meta: { "openai/title": p.name } }] };
  const update: Promise<unknown> = openai.modelContext ? openai.modelContext.update(params) : app.updateModelContext(params);
  update.catch(() => {});
}

reviewBtn.addEventListener("click", async () => {
  if (!current) return;
  reviewBtn.disabled = true;
  const message = {
    role: "user" as const,
    content: [
      {
        type: "text" as const,
        text: `Review the board open in the circuit viewer (${current.project.board ?? current.project.root}). Run check_board on it, tell me what is blocking fab, and what to fix first: placement, routing, or the finishing tail.`,
      },
    ],
  };
  try {
    await (openai.message ? openai.message.send(message) : app.sendMessage(message));
  } catch (e) {
    console.error(e);
  } finally {
    reviewBtn.disabled = false;
  }
});

// ---- host -> viewer -------------------------------------------------------------------

app.addEventListener("toolinput", ({ arguments: args }) => {
  const input = OpenAIFileEntrypointInputSchema.safeParse(args);
  if (input.success) {
    viaFileEntry = true;
    nameEl.textContent = input.data.file.name;
    setStatus("opening…");
    // The host adds the file's real path to our server calls; resolve it there.
    projectPath = undefined;
    void loadView<Described>("project")
      .then(openProject)
      .catch((e) => setStatus((e as Error).message, "bad"));
    return;
  }
  const p = (args as { path?: unknown } | undefined)?.path;
  if (typeof p === "string" && p !== projectPath) void openPath(p);
});

app.ontoolresult = (result) => {
  if (result.isError) {
    const text = (result.content as { type: string; text?: string }[] | undefined)?.find((c) => c.type === "text") as { text?: string } | undefined;
    setStatus(text?.text ?? "could not open", "bad");
    return;
  }
  const d = result.structuredContent as Partial<Described> | undefined;
  if (d?.project && !(current && current.revision === d.revision && current.project.board === d.project.board)) void openProject(d as Described);
  else if (!viaFileEntry) showPicker();
};

app.onteardown = async () => {
  clearTimeout(watchTimer); watching = false; watchEpoch++; boardView?.pz.dispose();
  return {};
};

function applyHostContext(ctx: McpUiHostContext) {
  if (ctx.theme) applyDocumentTheme(ctx.theme);
  if (ctx.styles?.variables) applyHostStyleVariables(ctx.styles.variables);
  if (ctx.styles?.css?.fonts) applyHostFonts(ctx.styles.css.fonts);
  if (ctx.displayMode) displayMode = ctx.displayMode;
  if (ctx.availableDisplayModes) expandBtn.hidden = !ctx.availableDisplayModes.includes("fullscreen");
  expandBtn.textContent = displayMode === "fullscreen" ? "Shrink" : "Expand";
  const dims = ctx.containerDimensions as { height?: number; maxHeight?: number } | undefined;
  const bar = (document.querySelector(".bar") as HTMLElement).offsetHeight;
  const total = dims?.height ?? (displayMode === "fullscreen" ? (dims?.maxHeight ?? window.innerHeight) : Math.min(INLINE_HEIGHT, dims?.maxHeight ?? INLINE_HEIGHT));
  document.documentElement.style.setProperty("--stage-h", `${Math.max(260, total - bar)}px`);
}
app.onhostcontextchanged = applyHostContext;

expandBtn.addEventListener("click", async () => {
  try {
    const result = await app.requestDisplayMode({ mode: displayMode === "fullscreen" ? "inline" : "fullscreen" });
    displayMode = result.mode;
    applyHostContext({ ...(app.getHostContext() ?? {}), displayMode });
  } catch (e) {
    console.error(e);
  }
});

// ---- start ------------------------------------------------------------------------------

refreshTabs();
for (const v of document.querySelectorAll<HTMLElement>(".view")) v.hidden = true;
whenConnected = app.connect().then(() => {
  connected = true;
  const ctx = app.getHostContext();
  if (ctx) applyHostContext(ctx);
  reportContext();
  // Sidebar / thread with nothing to open: offer the picker after a beat, unless
  // a tool input or result arrives first.
  setTimeout(() => {
    if (!current && !viaFileEntry && !projectPath) showPicker();
  }, 600);
});
