import { readFile } from "node:fs/promises";
import type { ServerOptions } from "./server.js";

/**
 * Loads the files the server serves, from next to the running script: both the
 * unbundled dist/ layout and the bundled plugin layout keep widget.html and
 * icon.svg beside the entry file.
 */
export async function loadAssets(): Promise<ServerOptions> {
  const [widgetHtml, iconSvg] = await Promise.all([
    readFile(new URL("./widget.html", import.meta.url), "utf8"),
    readFile(new URL("./icon.svg", import.meta.url), "utf8"),
  ]);
  return { widgetHtml, iconSvg };
}
