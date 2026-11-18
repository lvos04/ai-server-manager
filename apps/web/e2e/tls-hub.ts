/** Alleen de test: echte TLS vóór de bestaande webproxy; geen schemaheader vanuit de browser. */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { request } from "node:http";
import { createServer } from "node:https";
import { tmpdir } from "node:os";
import path from "node:path";

export async function startTlsHub(upstream: string): Promise<{ url: string; close: () => Promise<void> }> {
  const dir = mkdtempSync(path.join(tmpdir(), "hub-oidc-tls-"));
  const cert = path.join(dir, "cert.pem");
  const key = path.join(dir, "key.pem");
  execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-subj", "/CN=localhost", "-addext", "subjectAltName=IP:127.0.0.1,DNS:localhost", "-days", "1", "-keyout", key, "-out", cert], { stdio: "ignore" });
  const server = createServer({ cert: readFileSync(cert), key: readFileSync(key) }, (incoming, response) => {
    const target = new URL(incoming.url ?? "/", upstream);
    const outgoing = request(target, { localAddress: "127.0.0.2", method: incoming.method, headers: { ...incoming.headers, "x-forwarded-proto": "https", "x-forwarded-for": "127.0.0.1" } }, (res) => {
      response.writeHead(res.statusCode ?? 502, res.headers);
      res.pipe(response);
    });
    outgoing.on("error", () => { response.writeHead(502); response.end(); });
    incoming.pipe(outgoing);
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Test-TLS heeft geen poort");
  return {
    url: `https://127.0.0.1:${address.port}`,
    close: async () => {
      server.closeAllConnections();
      await new Promise<void>((resolve, reject) => server.close((err) => err ? reject(err) : resolve()));
      rmSync(dir, { recursive: true, force: true });
    },
  };
}
