// Webserver van de Hub: Next.js (web-UI) en een strikte doorgang naar de interne Hub-API op één poort.
//
// In de alles-in-één image: `node /opt/hub-web/server/hub-server.mjs` (PORT=30400, HUB_API_URL=http://127.0.0.1:8400).
// In ontwikkeling: `npm run dev` (Next.js dev-modus) met HUB_API_URL naar een lokaal gestarte API.
// Alleen /api/*, /connector/*, /healthz en /readyz gaan naar de API (zie proxy.mjs); de rest is de web-UI.
import { createServer, request as httpRequest } from "node:http";
import { randomUUID } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
import { downstreamHeaders, isApiPath, parseTrusted, unavailableBody, upstreamHeaders } from "./proxy.mjs";

const require = createRequire(import.meta.url);
const dev = process.argv.includes("--dev") || process.env.HUB_WEB_DEV === "1";
const dir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const port = Number(process.env.PORT || (dev ? 3000 : 30400));
const hostname = process.env.HOSTNAME || (dev ? "127.0.0.1" : "0.0.0.0");
const api = new URL(process.env.HUB_API_URL || "http://127.0.0.1:8400");
const trusted = parseTrusted(process.env.HUB_WEB_TRUSTED_PROXIES);
const API_TIMEOUT_MS = 120_000;

function log(msg) {
  console.log(`[hub-web] ${msg}`);
}

if (api.protocol !== "http:" || !["127.0.0.1", "localhost", "::1", "[::1]"].includes(api.hostname)) {
  // De API hoort alleen intern bereikbaar te zijn; een ander doel is een configuratiefout.
  log(`FOUT: HUB_API_URL moet naar de interne API op dezelfde machine wijzen (http://127.0.0.1:<poort>), niet ${api.origin}`);
  process.exit(78);
}

process.env.NODE_ENV = dev ? "development" : "production";
let conf;
if (!dev) {
  const rsf = path.join(dir, ".next", "required-server-files.json");
  if (!existsSync(rsf)) {
    log(`FOUT: geen productie-build gevonden in ${dir}/.next (voer eerst 'npm run build' uit)`);
    process.exit(78);
  }
  conf = JSON.parse(readFileSync(rsf, "utf8")).config;
  process.env.__NEXT_PRIVATE_STANDALONE_CONFIG = JSON.stringify(conf);
}
const next = require("next");
const app = next({ dev, dir, hostname, port, conf, customServer: true });
const handle = app.getRequestHandler();

function proxy(req, res) {
  const traceId = randomUUID();
  const upstream = httpRequest(
    {
      protocol: api.protocol,
      hostname: api.hostname.replace(/^\[|\]$/g, ""),
      port: api.port || 80,
      method: req.method,
      path: req.url,
      headers: upstreamHeaders(req.headers, {
        remoteAddress: req.socket.remoteAddress,
        encrypted: Boolean(req.socket.encrypted),
        trusted,
      }),
      timeout: API_TIMEOUT_MS,
    },
    (up) => {
      res.writeHead(up.statusCode || 502, downstreamHeaders(up.headers));
      up.pipe(res);
    },
  );
  const fail = (err) => {
    if (res.headersSent) {
      res.destroy(err);
      return;
    }
    const body = JSON.stringify(unavailableBody(traceId));
    res.writeHead(502, { "content-type": "application/json", "cache-control": "no-store", "x-trace-id": traceId });
    res.end(body);
  };
  upstream.on("timeout", () => upstream.destroy(new Error("timeout")));
  upstream.on("error", fail);
  req.on("aborted", () => upstream.destroy());
  req.pipe(upstream);
}

await app.prepare();
const upgrade = typeof app.getUpgradeHandler === "function" ? app.getUpgradeHandler() : null;
const server = createServer((req, res) => {
  if (isApiPath(req.url || "/")) {
    proxy(req, res);
    return;
  }
  handle(req, res).catch((err) => {
    log(`fout in de web-UI: ${err && err.message}`);
    if (!res.headersSent) {
      res.statusCode = 500;
      res.end("Interne fout in de web-UI");
    }
  });
});
server.on("upgrade", (req, socket, head) => {
  if (dev && upgrade && !isApiPath(req.url || "/")) {
    upgrade(req, socket, head);
    return;
  }
  socket.destroy();
});
server.keepAliveTimeout = 65_000;
server.listen(port, hostname, () => {
  log(`web-UI op http://${hostname}:${port} (${dev ? "ontwikkeling" : "productie"}); API-doorgang naar ${api.origin}`);
});

function shutdown(signal) {
  log(`signaal ${signal}: netjes stoppen`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 10_000).unref();
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
