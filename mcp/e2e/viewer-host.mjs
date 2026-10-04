// The circuit viewer in a real browser, mounted by a stand-in for the Codex host
// that forwards the widget's server calls to the REAL server (in-memory MCP
// client in Node), so every view is the actual kicad-cli / tsci export.
//
//   node e2e/viewer-host.mjs            (after `node build.mjs`)
//   OUT=dir                             where screenshots go (default e2e/out)
//   CIRCUIT_VIEWER_FIXTURE=path         the einhander checkout (default ~/sandbox/audiodestrukt/einhander)
import { chromium } from "playwright-core";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { mkdir, readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { loadAssets } from "../dist/assets.js";
import { createServer } from "../dist/server.js";

const FIXTURE = process.env.CIRCUIT_VIEWER_FIXTURE ?? path.join(os.homedir(), "sandbox/audiodestrukt/einhander");
const OUT = process.env.OUT ?? new URL("./out", import.meta.url).pathname;
await mkdir(OUT, { recursive: true });
const widgetHtml = await readFile(new URL("../dist/widget.html", import.meta.url), "utf8");

const server = createServer(await loadAssets());
const [a, b] = InMemoryTransport.createLinkedPair();
const client = new Client({ name: "fake-codex", version: "0" });
await Promise.all([server.connect(a), client.connect(b)]);

const browser = await chromium.launch({ channel: "chrome", headless: true, args: ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const results = [];
const check = (name, ok, detail = "") => {
  results.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  — " + detail : ""}`);
};

/** Runs IN THE PAGE: the host side of the MCP Apps channel. */
function hostScript(html, start, size) {
  const H = (window.H = { context: null, calls: [] });
  const frame = document.createElement("iframe");
  frame.setAttribute("sandbox", "allow-scripts allow-same-origin");
  frame.style.cssText = `width:${size.width}px;height:${size.height}px;border:0;display:block`;
  document.body.style.margin = "0";
  document.body.appendChild(frame);
  const send = (msg) => frame.contentWindow.postMessage({ jsonrpc: "2.0", ...msg }, "*");
  window.addEventListener("message", async (e) => {
    if (e.source !== frame.contentWindow) return;
    const m = e.data;
    if (!m || m.jsonrpc !== "2.0" || !m.method) return;
    const reply = (result) => m.id !== undefined && send({ id: m.id, result });
    switch (m.method) {
      case "ui/initialize":
        return reply({
          protocolVersion: "2026-01-26",
          hostInfo: { name: "fake-codex", version: "0.0.1" },
          hostCapabilities: { experimental: { "openai/modelContext": {}, "openai/message": {} }, updateModelContext: { text: {} }, message: { text: {} }, serverTools: {}, logging: {} },
          hostContext: { theme: "dark", displayMode: "fullscreen", availableDisplayModes: ["inline", "fullscreen"], containerDimensions: { width: size.width, height: size.height }, platform: "desktop" },
        });
      case "ui/notifications/initialized":
        if (start.input) send({ method: "ui/notifications/tool-input", params: { arguments: start.input } });
        if (start.result) send({ method: "ui/notifications/tool-result", params: start.result });
        return;
      case "tools/call": {
        H.calls.push(m.params.arguments?.view ?? m.params.name);
        // Forward to the real server; a real host adds the opened file's path.
        const r = await window.callServer(m.params.name, m.params.arguments ?? {}, start.filePath ?? null);
        return reply(r);
      }
      case "ui/update-model-context":
        H.context = m.params;
        return reply({});
      default:
        if (m.id !== undefined) reply({});
    }
  });
  frame.srcdoc = html;
}

async function mount(start, size = { width: 1180, height: 720 }) {
  const page = await browser.newPage({ viewport: size });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 300)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text().slice(0, 300)));
  await page.exposeFunction("callServer", (name, args, filePath) =>
    client.callTool({ name, arguments: args, ...(filePath ? { _meta: { "openai/resource": { path: filePath } } } : {}) }),
  );
  await page.setContent("<body></body>");
  await page.evaluate(`(${hostScript.toString()})(${JSON.stringify(widgetHtml)}, ${JSON.stringify(start)}, ${JSON.stringify(size)})`);
  const w = page.frames()[1];
  return { page, w, errors };
}

const until = async (fn, ms = 60000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const v = await fn().catch(() => null);
    if (v) return v;
    await new Promise((r) => setTimeout(r, 300));
  }
  return null;
};
const status = (w) => w.evaluate(() => document.getElementById("status").textContent);
const tab = (w, t) => w.click(`#tabs button[data-tab="${t}"]`);

// ---- 1. the model opens the shipped board -------------------------------------
{
  const opened = await client.callTool({ name: "open_board", arguments: { path: path.join(FIXTURE, "pcb") } });
  const { page, w, errors } = await mount({ input: { path: path.join(FIXTURE, "pcb") }, result: opened });
  const layers = await until(() => w.evaluate(() => [...document.querySelectorAll("#board-canvas g[data-layer]")].filter((g) => g.childNodes.length).length >= 7 && document.querySelectorAll("#drc label, #drc .hint").length > 0));
  check("board tab draws all 7 layers and the DRC panel", !!layers);
  const name = await w.evaluate(() => document.getElementById("name").textContent);
  check("project is named", name === "einhander/pcb", name);
  const ctx = await page.evaluate(() => window.H.context?.content?.[0]?.text ?? "");
  check("the model is told what is open", /einhander\/pcb/.test(ctx) && /1463\.8 mm track, 49 vias/.test(ctx), ctx.split("\n")[0]);
  const inner = await w.evaluate(() => document.querySelector('g[data-layer="In1.Cu"]').style.display);
  check("inner planes start hidden", inner === "none");
  await page.screenshot({ path: `${OUT}/1-board.png` });

  await tab(w, "schematic");
  const sch = await until(() => w.evaluate(() => !!document.querySelector("#sch-canvas svg.pz")), 240000);
  check("schematic renders from the tscircuit design", !!sch);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/2-schematic.png` });

  await tab(w, "netlist");
  await until(() => w.evaluate(() => document.getElementById("netlist").textContent.includes("RP2040")));
  await w.fill("#net-filter", "QSPI_SCLK");
  const net = await w.evaluate(() => document.getElementById("netlist").textContent);
  check("netlist filters to a net", /QSPI_SCLK/.test(net) && !/KEY7/.test(net), net.split("\n").filter((l) => /QSPI_SCLK/.test(l)).slice(0, 2).join(" | "));
  await page.screenshot({ path: `${OUT}/3-netlist.png` });

  await tab(w, "3d");
  const three = await until(() => w.evaluate(() => /orbit/.test(document.getElementById("status").textContent)), 120000);
  check("3D view loads the GLB", !!three, await status(w));
  await page.waitForTimeout(800);
  await page.screenshot({ path: `${OUT}/4-3d.png` });

  await tab(w, "checks");
  const verdict = await until(() => w.evaluate(() => document.querySelector("#checks .verdict.ok, #checks .verdict.bad")?.textContent), 120000);
  check("checks: the shipped board passes every gate", verdict === "All gates pass", verdict ?? "");
  const ctx2 = await page.evaluate(() => window.H.context?.content?.[0]?.text ?? "");
  check("the check result reaches the model", /Checks: .*all gates pass/.test(ctx2));
  await page.screenshot({ path: `${OUT}/5-checks.png` });
  check("no page errors (shipped)", errors.length === 0, errors.join(" | "));
  await page.close();
}

// ---- 2. the unattended re-route: DRC markers and stepping -------------------------
{
  const opened = await client.callTool({ name: "open_board", arguments: { path: path.join(FIXTURE, "pcb-rerun") } });
  const { page, w, errors } = await mount({ input: { path: path.join(FIXTURE, "pcb-rerun") }, result: opened });
  const n = await until(() => w.evaluate(() => document.querySelectorAll('#board-canvas g[data-type="unconnected_items"] circle').length || 0));
  check("unconnected items are marked on the board", n === 4, `${n} marker circles (2 items x 2 ends)`);
  await w.click('#drc label:has-text("unconnected items") .t');
  const s = await status(w);
  check("clicking a marker type zooms to the first one", /^unconnected items 1\/2/.test(s), s.slice(0, 110));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/6-rerun-marker.png` });
  await tab(w, "checks");
  const verdict = await until(() => w.evaluate(() => document.querySelector("#checks .verdict.ok, #checks .verdict.bad")?.textContent), 120000);
  check("checks: the re-route fails drc_check", /Failing: drc_check/.test(verdict ?? ""), verdict ?? "");
  await page.screenshot({ path: `${OUT}/7-rerun-checks.png` });
  check("no page errors (rerun)", errors.length === 0, errors.join(" | "));
  await page.close();
}

// ---- 3. opened as a workspace file (file entrypoint) ------------------------------------
{
  const board = path.join(FIXTURE, "pcb", "index.circuit.kicad_pcb");
  const file = { name: "index.circuit.kicad_pcb", resourceUri: "host-resource://index.circuit.kicad_pcb" };
  const { page, w, errors } = await mount({ input: { file }, result: { content: [{ type: "text", text: "Opened." }], structuredContent: { file } }, filePath: board });
  const ok = await until(() => w.evaluate(() => document.getElementById("name").textContent === "einhander/pcb" && document.querySelectorAll("#board-canvas g[data-layer]").length === 7));
  check("a .kicad_pcb opened from the workspace loads via the host's file path", !!ok);
  check("no page errors (file)", errors.length === 0, errors.join(" | "));
  await page.close();
}

// ---- 4. the sidebar app: no project, pick one ----------------------------------------------
{
  const { page, w, errors } = await mount({ input: {}, result: { content: [{ type: "text", text: "Opened the circuit viewer." }], structuredContent: {} } }, { width: 760, height: 560 });
  const picker = await until(() => w.evaluate(() => !document.getElementById("picker").hidden));
  check("with nothing open, the viewer offers a path picker", !!picker);
  await page.screenshot({ path: `${OUT}/8-picker.png` });
  await w.fill("#pick-path", path.join(FIXTURE, "pcb-rerun"));
  await w.click("#pick-go");
  const ok = await until(() => w.evaluate(() => document.getElementById("name").textContent === "einhander/pcb-rerun"));
  check("a typed path opens the project", !!ok);
  await until(() => w.evaluate(() => document.querySelectorAll("#board-canvas g[data-layer]").length === 7));
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/9-narrow.png` });
  check("no page errors (sidebar)", errors.length === 0, errors.join(" | "));
  await page.close();
}

// ---- live refresh: actual exports, tool-input-only host, preserved viewport/layers ----
{
  const root = await mkdtemp(path.join(os.tmpdir(), "circuit-live-e2e-"));
  const board = path.join(root, "live.kicad_pcb");
  const content = await readFile(path.join(FIXTURE,"pcb-rerun","index.circuit.kicad_pcb"),"utf8");
  await writeFile(board, content);
  const {page,w,errors} = await mount({input:{path:board}});
  try {
    const ready = await until(() => w.evaluate(() => document.querySelectorAll("#drc label").length > 0));
    check("tool input opens the project without requiring a tool result", !!ready);
    await w.click('#layers input[data-key="In1.Cu"]');
    await w.click('#drc input[data-key="unconnected_items"]');
    await w.click('#drc label:has-text("unconnected items") .t');
    const before = await w.evaluate(() => document.querySelector("#board-canvas svg").getAttribute("viewBox"));
    const callsBefore = await page.evaluate(() => window.H.calls.filter(x => x === "project").length);
    await writeFile(board+".routing.json",JSON.stringify({backend:"fastroute",state:"running",message:"test progress"}));
    check("router progress appears without reopening", !!await until(() => w.evaluate(() => document.getElementById("progress").textContent.includes("test progress"))));
    await writeFile(board,content+"\n");
    check("a saved board automatically refreshes", !!await until(() => page.evaluate(n => window.H.calls.filter(x => x === "project").length > n,callsBefore)));
    await until(() => w.evaluate(() => document.querySelectorAll("#drc label").length > 0));
    const after = await w.evaluate(() => ({box:document.querySelector("#board-canvas svg").getAttribute("viewBox"),inner:document.querySelector('#layers input[data-key="In1.Cu"]').checked}));
    check("live refresh retains zoom and layer choice",after.box === before && after.inner);
    await tab(w,"netlist");
    await w.fill("#net-filter","QSPI");
    await writeFile(board,content+"\n\n");
    await page.waitForTimeout(6500);
    check("live refresh keeps the selected tab and filter",await w.evaluate(() => document.querySelector('#tabs button[data-tab="netlist"]').getAttribute("aria-selected")==="true" && document.getElementById("net-filter").value==="QSPI"));
    check("no page errors (live)",errors.length===0,errors.join(" | "));
  } finally { await page.close(); await rm(root,{recursive:true,force:true}); }
}

await browser.close();
const failed = results.filter((r) => !r).length;
console.log(`\n${results.length - failed}/${results.length} passed · screenshots in ${OUT}`);
process.exit(failed ? 1 : 0);
