import type { NextConfig } from "next";
import { readFileSync } from "node:fs";
import path from "node:path";

// Versie van de Hub (bron: VERSION in de repo-root) — zichtbaar in Instellingen en gebruikt als cachesleutel van de
// service worker. Geen NAS-gegevens of geheimen in de build.
function hubVersion(): string {
  try {
    return readFileSync(path.join(process.cwd(), "..", "..", "VERSION"), "utf8").trim();
  } catch {
    return process.env.HUB_VERSION ?? "0.0.0-dev";
  }
}

// Strikte beveiligingsheaders. 'unsafe-inline' voor scripts is nodig voor de inline-hydratie van Next.js en het
// themascript; externe scripts/verbindingen zijn verboden (alles draait lokaal op het LAN, geen CDN).
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "manifest-src 'self'",
  "worker-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
];

const config: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: process.cwd(),
  // Geen beeldoptimalisatie (images.unoptimized): sharp/libvips (~47 MB) hoort niet in de image.
  outputFileTracingExcludes: { "*": ["node_modules/sharp/**", "node_modules/@img/**", "node_modules/@emnapi/**"] },
  reactStrictMode: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_HUB_VERSION: hubVersion() },
  async headers() {
    const prod = process.env.NODE_ENV === "production";
    return [
      {
        source: "/:path*",
        headers: prod ? [...securityHeaders, { key: "Content-Security-Policy", value: csp }] : securityHeaders,
      },
      {
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

export default config;
