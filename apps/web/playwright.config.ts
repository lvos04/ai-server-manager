import { defineConfig, type Project } from "@playwright/test";
import path from "node:path";

/**
 * Web-E2E tegen de ECHTE Hub-API met de fake TrueNAS-simulator (geen gemockte antwoorden).
 *
 * Standaard start Playwright zelf: tests/e2e/web_stack.py (API + worker + fake NAS, eigen tijdelijke database) en de
 * productie-build van de web-UI via server/hub-server.mjs (zelfde server als in de image).
 * Met HUB_E2E_BASE_URL (bv. http://127.0.0.1:30400) draait dezelfde suite tegen de alles-in-één image; start dan
 * `web_stack.py --alleen-nas` voor de fake NAS en geef de setupcode uit de containerlog mee in HUB_E2E_SETUP_CODE.
 */
const WEB_PORT = Number(process.env.HUB_E2E_WEB_PORT ?? 39400);
const API_PORT = Number(process.env.HUB_E2E_API_PORT ?? 39401);
const CONTROL_PORT = Number(process.env.HUB_E2E_CONTROL_PORT ?? 39402);
const external = process.env.HUB_E2E_BASE_URL;
const repoRoot = path.resolve(__dirname, "..", "..");
const python = process.env.HUB_E2E_PYTHON ?? path.join(repoRoot, ".venv", "bin", "python");
export const STATE_DIR = process.env.HUB_E2E_STATE_DIR ?? path.join(__dirname, "e2e", ".state");
const ADMIN_STATE = path.join(__dirname, "e2e", ".auth", "beheerder.json");

const viewports: { name: string; width: number; height: number; mobile: boolean }[] = [
  { name: "mobiel-360", width: 360, height: 740, mobile: true },
  { name: "mobiel-390", width: 390, height: 844, mobile: true },
  { name: "tablet-768", width: 768, height: 1024, mobile: true },
  { name: "desktop-1440", width: 1440, height: 900, mobile: false },
];

const viewportProjects: Project[] = viewports.map((v) => ({
  name: v.name,
  dependencies: ["opzet"],
  testMatch: /10-.*\.spec\.ts/,
  use: {
    viewport: { width: v.width, height: v.height },
    isMobile: v.mobile && v.width < 700,
    hasTouch: v.mobile,
    deviceScaleFactor: v.mobile ? 2 : 1,
    storageState: ADMIN_STATE,
  },
}));

const stackEnv = {
  HUB_E2E_API_PORT: String(API_PORT),
  HUB_E2E_CONTROL_PORT: String(CONTROL_PORT),
  HUB_E2E_STATE_DIR: STATE_DIR,
  PYTHONDONTWRITEBYTECODE: "1",
};

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: external ?? `http://127.0.0.1:${WEB_PORT}`,
    locale: "nl-NL",
    timezoneId: "Europe/Amsterdam",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  webServer: external
    ? [
        {
          command: `"${python}" ${path.join(repoRoot, "tests", "e2e", "web_stack.py")} --alleen-nas`,
          url: `http://127.0.0.1:${CONTROL_PORT}/`,
          env: stackEnv,
          timeout: 60_000,
          reuseExistingServer: false,
          stdout: "pipe",
          gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
        },
      ]
    : [
        {
          command: `"${python}" ${path.join(repoRoot, "tests", "e2e", "web_stack.py")}`,
          url: `http://127.0.0.1:${API_PORT}/readyz`,
          env: stackEnv,
          timeout: 90_000,
          reuseExistingServer: false,
          stdout: "pipe",
          // SIGTERM i.p.v. SIGKILL: de teststack verwijdert dan zelf zijn tijdelijke database.
          gracefulShutdown: { signal: "SIGTERM", timeout: 15_000 },
        },
        {
          command: "node server/hub-server.mjs",
          url: `http://127.0.0.1:${WEB_PORT}/`,
          env: { PORT: String(WEB_PORT), HOSTNAME: "127.0.0.1", HUB_API_URL: `http://127.0.0.1:${API_PORT}` },
          timeout: 60_000,
          reuseExistingServer: false,
          gracefulShutdown: { signal: "SIGTERM", timeout: 10_000 },
        },
      ],
  projects: [
    { name: "opzet", testMatch: /00-.*\.spec\.ts/, use: { viewport: { width: 1440, height: 900 } } },
    ...viewportProjects,
    {
      name: "afsluiting",
      dependencies: viewports.map((v) => v.name),
      testMatch: /90-.*\.spec\.ts/,
      use: { viewport: { width: 1440, height: 900 }, storageState: ADMIN_STATE },
    },
  ],
});
