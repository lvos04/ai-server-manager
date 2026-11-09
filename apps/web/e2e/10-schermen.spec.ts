/**
 * Alle P0-schermen op 360/390/768/1440 px (één Playwright-project per breedte): navigatie volgens 08_UI, geen
 * horizontaal scrollen, aanraakdoelen ≥ 44 px, toetsenbord (skiplink), toegankelijkheid (axe) in licht én donker,
 * echte gegevens uit de API (fake TrueNAS) en eerlijke 'nog niet beschikbaar'-schermen. Schermafbeeldingen naar
 * docs/screenshots/p0/<project>/.
 */
import { expect, test } from "@playwright/test";
import { expectAccessible, expectNoHorizontalScroll, expectTouchTargets, ready, shot } from "./helpers";

const MOBILE_NAV = ["Home", "Apps", "Problemen", "AI", "Meer"];
const DESKTOP_NAV = ["Home", "Server", "Media", "Huis", "Netwerk", "Automatisering", "Backups", "Kosten", "Instellingen"];

const SCREENS: { path: string; name: string; heading: RegExp; shot?: boolean }[] = [
  { path: "/", name: "home", heading: /^Home$/, shot: true },
  { path: "/server", name: "server", heading: /^Server$/, shot: true },
  { path: "/apps", name: "apps", heading: /^Apps$/, shot: true },
  { path: "/backups", name: "backups", heading: /^Backups$/, shot: true },
  { path: "/onboarding", name: "onboarding", heading: /^Onboarding$/, shot: true },
  { path: "/onboarding/besluit/D03", name: "besluit-D03", heading: /^D03 — /, shot: true },
  { path: "/onboarding/besluit/D10", name: "besluit-D10", heading: /^D10 — / },
  { path: "/onboarding/truenas", name: "truenas", heading: /^TrueNAS koppelen/, shot: true },
  { path: "/onboarding/executor", name: "executor", heading: /^Executor/, shot: true },
  { path: "/instellingen", name: "instellingen", heading: /^Instellingen$/, shot: true },
  { path: "/meer", name: "meer", heading: /^Meer$/ },
  { path: "/problemen", name: "problemen", heading: /^Problemen$/, shot: true },
  { path: "/ai", name: "ai", heading: /^AI$/ },
  { path: "/media", name: "media", heading: /^Media$/ },
  { path: "/huis", name: "huis", heading: /^Huis$/ },
  { path: "/netwerk", name: "netwerk", heading: /^Netwerk$/ },
  { path: "/automatisering", name: "automatisering", heading: /^Automatisering$/ },
  { path: "/kosten", name: "kosten", heading: /^Kosten$/ },
];

test("navigatie volgens 08_UI: ondernavigatie op mobiel/tablet, zijbalk op desktop", async ({ page }, info) => {
  await page.goto("/");
  await ready(page);
  const width = page.viewportSize()?.width ?? 0;
  if (width < 1024) {
    const nav = page.getByTestId("bottom-nav");
    await expect(nav).toBeVisible();
    await expect(page.getByTestId("sidebar")).toBeHidden();
    await expect(nav.getByRole("link")).toHaveText(MOBILE_NAV);
    await expect(nav.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
    await nav.getByRole("link", { name: "Meer" }).click();
    await expect(page).toHaveURL(/\/meer$/);
    await expect(nav.getByRole("link", { name: "Meer" })).toHaveAttribute("aria-current", "page");
    for (const label of DESKTOP_NAV.filter((l) => l !== "Home")) {
      await expect(page.getByTestId("meer-lijst").getByRole("link", { name: label })).toBeVisible();
    }
    await page.getByTestId("meer-lijst").getByRole("link", { name: "Server" }).click();
    await expect(page).toHaveURL(/\/server$/);
  } else {
    const side = page.getByTestId("sidebar");
    await expect(side).toBeVisible();
    await expect(page.getByTestId("bottom-nav")).toBeHidden();
    await expect(side.getByRole("navigation").getByRole("link")).toHaveText(DESKTOP_NAV);
    await side.getByRole("link", { name: "Backups" }).click();
    await expect(page).toHaveURL(/\/backups$/);
    await expect(side.getByRole("link", { name: "Backups" })).toHaveAttribute("aria-current", "page");
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
  test(`scherm ${s.path}: laadt, toegankelijk, geen horizontaal scrollen, aanraakdoelen ≥ 44 px`, async ({ page }, info) => {
    await page.goto(s.path);
    await ready(page);
    await expect(page.locator("main h1").first()).toHaveText(s.heading);
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.getByTestId("error-panel")).toHaveCount(0);
    await expectNoHorizontalScroll(page, s.path);
    await expectTouchTargets(page, s.path);
    await expectAccessible(page, s.path);
    if (s.shot && (info.project.name === "mobiel-390" || info.project.name === "desktop-1440")) {
      await shot(page, info, s.name);
    }
  });
}

test("Home: elke kaart heeft waarde, bron en ‘laatst bijgewerkt’; ongekoppelde bronnen zijn onbekend", async ({ page }) => {
  await page.goto("/");
  await ready(page);
  for (const id of ["opslag", "apps", "gpu", "backups", "onboarding", "acties", "downloads", "huis"]) {
    const card = page.getByTestId(`kaart-${id}`);
    await expect(card).toBeVisible();
    await expect(card.getByTestId("freshness")).toContainText("Laatst bijgewerkt");
    await expect(card.getByTestId("freshness")).toContainText("Bron");
    await expect(card.getByRole("link")).toHaveCount(1);
  }
  // Echte waarden uit de (fake) TrueNAS na de opzet: 1 pool, 5 apps, 2 GPU's — met bron.
  await expect(page.getByTestId("waarde-opslag")).toContainText("1 van 1");
  await expect(page.getByTestId("kaart-opslag")).toContainText("pool.query");
  await expect(page.getByTestId("waarde-gpu")).toContainText("2");
  // Niet gekoppelde bronnen: eerlijk onbekend.
  await expect(page.getByTestId("waarde-downloads")).toHaveText("onbekend");
  await expect(page.getByTestId("waarde-huis")).toHaveText("onbekend");
  // App-gezondheid is in P0 onbekend → totaalstatus nooit 'in orde'.
  await expect(page.getByTestId("totaalstatus")).toContainText("Deels onbekend");
});

test("Server: inventaris met bron en ‘laatst bijgewerkt’, bestaande apps zichtbaar zonder mutatie", async ({ page }) => {
  await page.goto("/server");
  await ready(page);
  await expect(page.getByTestId("sectie-pools")).toContainText("Gezond");
  await expect(page.getByTestId("sectie-pools").getByTestId("freshness")).toContainText("pool.query");
  for (const app of ["mediaguard", "media-source-optimizer", "my-house"]) {
    await expect(page.getByTestId("sectie-apps")).toContainText(app);
  }
  await expect(page.getByTestId("sectie-gpus")).toContainText("Intel Arc A310");
  await expect(page.getByTestId("sectie-gpus")).toContainText("onbekend");
});

test("Backups: dekking per app, sync ≠ herstelgarantie, back-upgate dicht", async ({ page }) => {
  await page.goto("/backups");
  await ready(page);
  await expect(page.getByTestId("sectie-backupgate")).toContainText("Geblokkeerd");
  await expect(page.getByTestId("dekking-apps")).toContainText("capability_unavailable");
  await expect(page.locator("main")).toContainText("Synchronisatie is geen herstelgarantie");
});

test("nog niet beschikbare schermen tonen eerlijk de fase en geen gegevens", async ({ page }) => {
  const expected: Record<string, string> = {
    "/problemen": "P1",
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
    await expect(box).toContainText(`Nog niet beschikbaar (volgt in fase ${fase})`);
    await expect(page.locator("main table")).toHaveCount(0);
  }
});

test("donker thema: toegankelijk en schermafbeelding", async ({ page }, info) => {
  await page.emulateMedia({ colorScheme: "dark" });
  for (const p of ["/", "/onboarding/besluit/D03", "/backups"]) {
    await page.goto(p);
    await ready(page);
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });
    await expectAccessible(page, `${p} (donker)`);
  }
  if (info.project.name === "mobiel-390" || info.project.name === "desktop-1440") {
    await page.goto("/");
    await ready(page);
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 20_000 });
    await shot(page, info, "home-donker");
  }
});
