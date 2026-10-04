// Builds:
//
//   dist/                            the server for the tests (deps stay in node_modules)
//   ../plugin/circuit-skills/dist/   the installable Codex plugin: ONE bundled stdio
//                                    server + the widget + the icon. Needs Node 18+,
//                                    no `npm install`.
//   ../plugin/circuit-skills/skills/ the circuit skills, copied from the repo root,
//                                    plus the viewer's own skill (mcp/skill/)
//
// The widget is a single self-contained HTML file (three.js included).
import { build } from "esbuild";
import { cp, mkdir, readFile, rm, writeFile, copyFile } from "node:fs/promises";

const PLUGIN = "../plugin/circuit-skills";
const PLUGIN_DIST = `${PLUGIN}/dist`;
const SKILLS = ["pcb-layout", "circuit-sim", "pcb-enclosure-fit", "pcb-3d-render"];
await mkdir("dist", { recursive: true });
await mkdir(PLUGIN_DIST, { recursive: true });

// --- widget ------------------------------------------------------------------
const viewer = await build({
  entryPoints: ["widget/viewer.ts"],
  bundle: true,
  format: "iife",
  target: "es2020",
  minify: true,
  write: false,
  legalComments: "none",
});
const js = viewer.outputFiles[0].text.replaceAll("</script", "<\\/script");
const html = (await readFile("widget/viewer.html", "utf-8")).replace("/*%%VIEWER_JS%%*/", () => js);

// --- server, unbundled (tests) -------------------------------------------------
const ENTRIES = ["stdio", "server", "assets", "project", "views", "kicad", "checks", "status"];
await build({
  entryPoints: ENTRIES.map((n) => `src/${n}.ts`),
  outdir: "dist",
  platform: "node",
  format: "esm",
  target: "node22",
  bundle: false,
});
await writeFile("dist/widget.html", html);
await copyFile("widget/icon.svg", "dist/icon.svg");

// --- plugin: one bundled stdio server -----------------------------------------------
await build({
  entryPoints: ["src/stdio.ts"],
  // .mjs: the plugin folder has no package.json to declare ES modules.
  outfile: `${PLUGIN_DIST}/server.mjs`,
  platform: "node",
  format: "esm",
  target: "node18",
  bundle: true,
  minify: false,
  legalComments: "none",
  banner: { js: "import { createRequire as __createRequire } from 'node:module';\nconst require = __createRequire(import.meta.url);" },
});
await writeFile(`${PLUGIN_DIST}/widget.html`, html);
await copyFile("widget/icon.svg", `${PLUGIN_DIST}/icon.svg`);

// --- plugin: skills ----------------------------------------------------------------
await rm(`${PLUGIN}/skills`, { recursive: true, force: true });
for (const s of SKILLS) {
  await cp(`../${s}`, `${PLUGIN}/skills/${s}`, {
    recursive: true,
    filter: (src) => !/(__pycache__|node_modules|\.pyc$)/.test(src),
  });
}
await cp("skill/circuit-viewer", `${PLUGIN}/skills/circuit-viewer`, { recursive: true });

console.log(`built dist/ and ${PLUGIN}/ (widget ${(html.length / 1024).toFixed(0)} kB, skills: ${[...SKILLS, "circuit-viewer"].join(", ")})`);
