// Maakt de PNG-iconen van de PWA uit de SVG's (eenmalig/bij wijziging; resultaat staat in Git).
// Gebruikt de Chromium van Playwright: `npm run icons`.
import { chromium } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";

const dir = path.resolve(import.meta.dirname, "..", "public", "icons");
const jobs = [
  ["icon.svg", "icon-192.png", 192],
  ["icon.svg", "icon-512.png", 512],
  ["icon-maskable.svg", "icon-maskable-512.png", 512],
];
const browser = await chromium.launch(process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {});
for (const [src, out, size] of jobs) {
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  const svg = readFileSync(path.join(dir, src), "utf8");
  await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace("<svg ", `<svg width="${size}" height="${size}" `)}</body></html>`);
  await page.screenshot({ path: path.join(dir, out), omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
  await page.close();
  console.log(`gemaakt: ${out}`);
}
await browser.close();
