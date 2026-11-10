import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

/**
 * Peil-ontwerpreview (review/README.md): dezelfde teststack als de web-E2E (echte API + simulators), eerst de opzet
 * (e2e/00-01), daarna review/peil-review.spec.ts op 320/360/390/768/1024/1440 × licht/donker.
 *
 * Draaien de API-stack en de web-server al (bv. tijdens het repareren), dan worden ze hergebruikt; zet dan
 * PEIL_REVIEW_ZONDER_OPZET=1 om de opzet over te slaan (die kan maar één keer per database).
 */
const zonderOpzet = Boolean(process.env.PEIL_REVIEW_ZONDER_OPZET);
const servers = (Array.isArray(base.webServer) ? base.webServer : base.webServer ? [base.webServer] : []).map((s) => ({ ...s, reuseExistingServer: true }));

export default defineConfig({
  ...base,
  testDir: ".",
  outputDir: "./review/uit/test-results",
  reporter: [["list"]],
  // Elke breedte is één lange test; drie tegelijk houdt het geheugen binnen de perken (gedeelde machine).
  workers: Number(process.env.PEIL_REVIEW_WORKERS ?? 3),
  use: { ...base.use, actionTimeout: 15_000, navigationTimeout: 30_000 },
  webServer: servers,
  projects: [
    ...(zonderOpzet ? [] : [{ name: "opzet", testMatch: /e2e\/0[0-9]-.*\.spec\.ts/, workers: 1, use: { viewport: { width: 1440, height: 900 } } }]),
    {
      // Kijker en kind één keer aanmaken (gelijktijdig aanmaken door meerdere werkers gaf een 500 in de API).
      name: "review-opzet",
      testMatch: /review\/00-.*\.spec\.ts/,
      dependencies: zonderOpzet ? [] : ["opzet"],
    },
    {
      // Breedtes parallel (alleen lezen); de toestanden (NAS offline) daarna apart, zodat ze niets anders beïnvloeden.
      name: "review",
      testMatch: /review\/peil-review\.spec\.ts/,
      grepInvert: /Peil-review toestanden/,
      fullyParallel: true,
      dependencies: ["review-opzet"],
      timeout: 60 * 60_000,
      // In CI één herkansing: met meerdere browsers tegelijk raakt de API-databasepool (5 + 5 verbindingen) soms vol
      // en blijft een pagina > 30 s op "Aanmelding controleren…" staan (gemeld in PEIL_REVIEW N-07). Een echte
      // ontwerpfout komt bij de herkansing gewoon terug.
      retries: process.env.CI ? 1 : 0,
    },
    {
      name: "review-toestanden",
      testMatch: /review\/peil-review\.spec\.ts/,
      grep: /Peil-review toestanden/,
      dependencies: ["review"],
      timeout: 60 * 60_000,
    },
  ],
});
