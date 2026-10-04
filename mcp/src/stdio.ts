// Local entry point: the server the Codex / ChatGPT desktop plugin launches over
// stdio (see plugin/circuit-skills/.mcp.json). No network listener.
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadAssets } from "./assets.js";
import { createServer } from "./server.js";

const server = createServer(await loadAssets());
await server.connect(new StdioServerTransport());
