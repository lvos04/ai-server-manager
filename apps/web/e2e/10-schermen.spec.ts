/**
 * Alle schermen (P0 + P1 + contract 1.2) op 360/390/768/1440 px (één Playwright-project per breedte), in licht én
 * donker (Peil, ONTWERPTAAL §12): navigatie volgens 08_UI, geen horizontaal scrollen, aanraakdoelen ≥ 44 px,
 * toetsenbord (skiplink), axe (WCAG 2.2 A/AA) zonder overtredingen, echte gegevens uit de API (simulators) en eerlijke
 * 'nog niet beschikbaar'-schermen. Schermafbeeldingen naar docs/screenshots/p1/<project>/<naam>-<thema>.jpg.
 */
import { expect, test } from "@playwright/test";
import { expectAccessible, expectNoHorizontalScroll, expectTouchTargets, p1State, ready, setTheme, shot } from "./helpers";

const MOBILE_NAV = ["Home", "Apps", "Problemen", "AI", "Meer"];
const DESKTOP_NAV = ["Home", "Server", "Media", "Huis", "Netwerk", "Automatisering", "Backups", "Kosten", "Instellingen"];

interface Screen {
  path: string | (() => string | null);
  name: string;
  heading: RegExp;
  shot?: boolean;
}

const SCREENS: Screen[] = [
  { path: "/", name: "home", heading: /^Home$/, shot: true },
  { path: "/server", name: "server", heading: /^Server$/, shot: true },
  { path: "/server/metrieken", name: "server-metrieken", heading: /^Metrieken$/, shot: true },
  { path: "/server/meetdekking", name: "server-meetdekking", heading: /^Meetdekking$/ },
  { path: "/server/logs", name: "server-logs", heading: /^Logs$/ },
  { path: "/apps", name: "apps", heading: /^Apps$/, shot: true },
  { path: () => (p1State().app_id ? `/apps/${p1State().app_id}` : null), name: "apps-detail", heading: /^MediaGuard$/, shot: true },
  { path: "/problemen", name: "problemen", heading: /^Problemen$/, shot: true },
  { path: () => (p1State().incident_id ? `/problemen/${p1State().incident_id}` : null), name: "problemen-detail", heading: /Node-RED|^Problemen$/, shot: true },
  { path: "/backups", name: "backups", heading: /^Backups$/, shot: true },
  { path: "/onboarding", name: "onboarding", heading: /^Onboarding$/, shot: true },
  { path: "/onboarding/besluit/D03", name: "besluit-D03", heading: /^D03 — /, shot: true },
  { path: "/onboarding/besluit/D10", name: "besluit-D10", heading: /^D10 — / },
  { path: "/onboarding/truenas", name: "truenas", heading: /^TrueNAS koppelen/, shot: true },
  { path: "/onboarding/executor", name: "executor", heading: /^Executor/, shot: true },
  { path: "/instellingen", name: "instellingen", heading: /^Instellingen$/, shot: true },
  { path: "/instellingen/account", name: "instellingen-account", heading: /^Account$/ },
  { path: "/instellingen/toegang", name: "instellingen-toegang", heading: /^Gebruikers en toegang$/, shot: true },
  { path: "/instellingen/noodaccount", name: "noodaccount", heading: /^Noodaccount$/, shot: true },
  { path: "/instellingen/diensten", name: "diensten", heading: /^Diensten$/, shot: true },
  { path: "/instellingen/monitoring", name: "instellingen-monitoring", heading: /^Monitoring en meldingen$/, shot: true },
  { path: "/instellingen/apparaat", name: "instellingen-apparaat", heading: /^Apparaat en app$/ },
  { path: "/instellingen/audit", name: "instellingen-audit", heading: /^Auditspoor$/ },
  { path: "/instellingen/over", name: "instellingen-over", heading: /^Over deze Hub$/ },
  { path: "/meer", name: "meer", heading: /^Meer$/ },
  { path: "/ai", name: "ai", heading: /^AI$/ },
  { path: "/media", name: "media", heading: /^Media$/ },
  { path: "/huis", name: "huis", heading: /^Huis$/ },
  { path: "/netwerk", name: "netwerk", heading: /^Netwerk$/ },
  { path: "/automatisering", name: "automatisering", heading: /^Automatisering$/ },
  { path: "/kosten", name: "kosten", heading: /^Kosten$/ },
];

test("navigatie volgens 08_UI: ondernavigatie op mobiel/tablet, zijbalk op desktop; merk TrueNAS Home Platform", async ({ page }, info) => {
  await page.goto("/");
  await ready(page);
  await expect(page).toHaveTitle("Home — TrueNAS Home Platform");
  await expect(page.getByTestId("merk").first()).toContainText("TrueNAS Home Platform");
  const width = page.viewportSize()?.width ?? 0;
  if (width < 1024) {
    const nav = page.getByTestId("bottom-nav");
    await expect(nav).toBeVisible();
    await expect(page.getByTestId("sidebar")).toBeHidden();
    // De Problemen-teller staat in de link (aria-hidden cijfer + sr-tekst ", n actief").
    await expect(nav.getByRole("link")).toHaveText(MOBILE_NAV.map((l) => new RegExp(l)));
    await expect(nav.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    await nav.getByRole("link", { name: "Meer" }).click();
    await expect(page).toHaveURL(/\/meer$/);
    await expect(nav.getByRole("link", { name: "Meer" })).toHaveAttribute("aria-current", "page");
    for (const label of DESKTOP_NAV.filter((l) => l !== "Home")) {
      await expect(page.getByTestId("meer-lijst").getByRole("link", { name: label })).toBeVisible();
    }
    await page.getByTestId("meer-lijst").getByRole("link", { name: "Server" }).click();
    await expect(page).toHaveURL(/\/server$/);
    // Na een routewissel krijgt de h1 de focus (schermlezer hoort de nieuwe pagina).
    await expect(page.locator("main h1")).toBeFocused();
  } else {
    const side = page.getByTestId("sidebar");
    await expect(side).toBeVisible();
    await expect(page.getByTestId("bottom-nav")).toBeHidden();
    await expect(side.getByRole("navigation").getByRole("link")).toHaveText(DESKTOP_NAV);
    await side.getByRole("link", { name: "Backups" }).click();
    await expect(page).toHaveURL(/\/backups$/);
    await expect(side.getByRole("link", { name: "Backups" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByTestId("kop-problemen")).toBeVisible();
  }
  expect(info.project.name).toBeTruthy();
});

test("toetsenbord: eerste Tab is de skiplink naar de inhoud", async ({ page }) => {
  await page.goto("/server");
  await ready(page);
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Naar de inhoud" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main#inhoud")).toBeFocused();
});

for (const s of SCREENS) {
  test(`scherm ${s.name}: licht en donker toegankelijk, geen horizontaal scrollen, aanraakdoelen ≥ 44 px`, async ({ page }, info) => {
    const path = typeof s.path === "function" ? s.path() : s.path;
    test.skip(!path, "geen id uit de opzet");
    await page.goto(path!);
    await ready(page);
    await expect(page.locator("main h1").first()).toHaveText(s.heading);
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.locator("main [data-testid=error-panel]")).toHaveCount(0);
    for (const thema of ["licht", "donker"] as const) {
      await setTheme(page, thema);
      await expectNoHorizontalScroll(page, `${s.name} (${thema})`);
      await expectTouchTargets(page, `${s.name} (${thema})`);
      await expectAccessible(page, `${s.name} (${thema})`);
      if (s.shot) await shot(page, info, `${s.name}-${thema}`);
    }
    await setTheme(page, "licht");
  });
}

test("Home: elke kaart heeft waarde of eerlijk onbekend, bron en ‘Bijgewerkt’ en precies één vervolglink", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  for (const id of ["opslag", "apps", "gpu", "problemen", "backups", "onboarding", "acties", "downloads", "huis"]) {
    const card = page.getByTestId(`kaart-${id}`);
    await expect(card).toBeVisible();
    await expect(card.getByTestId("freshness")).toContainText("Bijgewerkt");
    await expect(card.getByTestId("freshness")).toContainText("Bron");
    await expect(card.getByRole("link")).toHaveCount(1);
  }
  await expect(page.getByTestId("waarde-opslag")).toContainText("1 van 1");
  await expect(page.getByTestId("kaart-opslag")).toContainText("pool.query");
  await expect(page.getByTestId("waarde-gpu")).toContainText("2");
  await expect(page.getByTestId("kaart-gpu")).toContainText("nooit 0 °C");
  await expect(page.getByTestId("waarde-downloads")).toHaveText("onbekend");
  await expect(page.getByTestId("waarde-huis")).toHaveText("onbekend");
  // Een gestopte app (gemeten) en onbekende apps: de totaalstatus is nooit ‘Alles gezond’.
  await expect(page.getByTestId("totaalstatus")).not.toContainText("Alles gezond");
  await expect(page.getByTestId("onderdeel-media")).toContainText("Nog niet beschikbaar");
});

test("Server: inventaris met bron en ‘Bijgewerkt’, bestaande apps zichtbaar zonder mutatie", async ({ page }) => {
  await page.goto("/server");
  await ready(page);
  await expect(page.getByTestId("sectie-pools")).toContainText("Gezond");
  await expect(page.getByTestId("sectie-pools").getByTestId("freshness")).toContainText("pool.query");
  for (const app of ["mediaguard", "media-source-optimizer", "my-house"]) {
    await expect(page.getByTestId("sectie-apps")).toContainText(app);
  }
  await expect(page.getByTestId("sectie-gpus")).toContainText("Intel Arc A310");
  await expect(page.getByTestId("sectie-gpus")).toContainText(/onbekend/i);
});

test("Metrieken: GPU-temperatuur altijd onbekend (nooit 0 °C), A310 en UHD 770 apart", async ({ page }) => {
  await page.goto("/server/metrieken");
  await ready(page);
  const gpus = page.getByTestId("gpus");
  await expect(gpus).toContainText("Intel Arc A310");
  await expect(gpus).toContainText("Intel UHD 770");
  for (const t of await gpus.getByTestId("gpu-temperatuur").all()) {
    await expect(t).toContainText("Onbekend");
    await expect(t).not.toContainText(/^0 °C/);
  }
});

test("Backups: dekking per app, sync ≠ herstelgarantie, back-upgate dicht (geen storing)", async ({ page }) => {
  await page.goto("/backups");
  await ready(page);
  await expect(page.getByTestId("sectie-backupgate")).toContainText("Geblokkeerd");
  await expect(page.getByTestId("dekking-apps")).toContainText("capability_unavailable");
  await expect(page.locator("main")).toContainText("Synchronisatie is geen herstelgarantie");
});

test("nog niet beschikbare schermen tonen eerlijk de fase en geen gegevens", async ({ page }) => {
  const expected: Record<string, string> = {
    "/ai": "P2",
    "/media": "P3 en P4",
    "/huis": "P3",
    "/netwerk": "P5",
    "/automatisering": "P2",
    "/kosten": "P5",
  };
  for (const [path, fase] of Object.entries(expected)) {
    await page.goto(path);
    await ready(page);
    const box = page.getByTestId("not-yet-available");
    await expect(box).toContainText(`Nog niet beschikbaar — volgt in fase ${fase}`);
    await expect(page.locator("main table")).toHaveCount(0);
  }
});

test("thema Systeem volgt het apparaat: het themascript zet altijd het opgeloste thema", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/instellingen/account");
  await ready(page);
  await page.getByTestId("thema-systeem").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.getByTestId("thema-donker").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByTestId("thema-licht").click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
