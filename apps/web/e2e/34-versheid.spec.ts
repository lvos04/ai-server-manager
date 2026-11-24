import { expect, test, type Page } from "@playwright/test";
import { ready } from "./helpers";

const dag = 24 * 60 * 60_000;
const legePagina = { items: [], next_cursor: null };
const flow = "8bd80c90-46ac-414e-a4c1-68d779de1899";

function brondatum(page: Page, tijd: string) {
  return page.evaluate(t => new Intl.DateTimeFormat("nl-NL", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(new Date(t)), tijd);
}

interface Lijstproef {
  scherm: string;
  route: string;
  veld: string;
  inhoud: object;
  leeg: string;
  sectie?: string;
}

const proeven: Lijstproef[] = [
  { scherm: "/goedkeuringen", route: "actions?status=wacht_op_goedkeuring&limit=50", veld: "bijgewerkt_op", inhoud: legePagina, leeg: "Geen openstaande goedkeuringen." },
  { scherm: "/automatisering/eventtypen", route: "events?*", veld: "observed_at", inhoud: legePagina, leeg: "Geen gebeurtenissen ontvangen voor dit filter." },
  { scherm: "/automatisering/historie", route: "actions?limit=50", veld: "bijgewerkt_op", inhoud: legePagina, leeg: "Geen actieverzoeken van flows." },
  { scherm: `/automatisering/detail?flow=${flow}`, route: "actions?limit=50", veld: "bijgewerkt_op", inhoud: legePagina, leeg: "Geen actieverzoeken van flows." },
  { scherm: "/automatisering/versies", route: "actions?action_id=*&limit=50", veld: "bijgewerkt_op", inhoud: legePagina, leeg: "Geen herstelverzoeken gevonden." },
  { scherm: "/backups/herstelpunten", route: "backups/herstelpunten", veld: "observed_at", inhoud: { items: [] }, leeg: "Geen herstelpunten gevonden." },
  { scherm: "/backups/hersteltests", route: "backups/restore-tests", veld: "observed_at", inhoud: { items: [] }, leeg: "Nog geen hersteltests." },
  { scherm: "/backups/rampenscenarios", route: "backups/rampenscenario", veld: "observed_at", inhoud: { scenarios: [], laatste_hersteltests: [] }, leeg: "Nog geen hersteltests vastgelegd." },
  { scherm: "/backups/extern", route: "backups/extern", veld: "afgeleid_op", inhoud: { status: "ontbreekt", taken: [], max_leeftijd_s: 60 }, leeg: "Geen passende uploadtaak" },
  { scherm: "/backups", route: "backups/self", veld: "observed_at", inhoud: { items: [], laatste_geverifieerd: null }, leeg: "Er is nog geen geverifieerde export van de Hub-database.", sectie: '[data-testid="sectie-eigen-backup"]' },
  { scherm: "/instellingen/monitoring#monitorplan", route: "monitoring/monitorplan", veld: "observed_at", inhoud: { items: [] }, leeg: "Geen apps voor dit monitorplan.", sectie: "#monitorplan" },
  { scherm: "/goedkeuringen/beleid", route: "policy", veld: "observed_at", inhoud: { acties: [] }, leeg: "De beleidsbron bevat geen acties." },
];

for (const p of proeven) {
  test(`E15 · ${p.scherm} toont een lege selectie alleen bij een verse bron`, async ({ page }) => {
    const vers = Date.now() - 1000;
    let tijd = new Date(vers).toISOString();
    await page.route(`**/api/v1/${p.route}`, r => r.fulfill({ status: 200, json: { ...p.inhoud, [p.veld]: tijd } }));
    await page.goto(p.scherm);
    await ready(page);
    const sectie = page.locator(p.sectie ?? "main");
    const leeg = sectie.getByText(p.leeg, { exact: true });
    await expect(leeg).toBeVisible();
    tijd = new Date(vers - dag).toISOString();
    await page.reload();
    const stand = sectie.getByTestId(/^(bronstand|verouderd)$/).filter({ hasText: "Verouderd" });
    await expect(stand).toBeVisible();
    await expect(stand).toContainText(await brondatum(page, tijd));
    await expect(leeg).toHaveCount(0);
    if (p.scherm === "/goedkeuringen") {
      await expect(page.getByTestId("kop-goedkeuringen")).toHaveAccessibleName(/aantal onbekend/);
      await expect(page.getByTestId("freshness").locator("time")).toHaveAttribute("datetime", tijd);
    }
  });
}

test("E15 · een oude vervolgpagina verklaart ook een lege flowselectie verouderd", async ({ page }) => {
  const tijd = Date.now() - 1000;
  await page.route("**/api/v1/actions?limit=50*", r => {
    const vervolg = new URL(r.request().url()).searchParams.has("cursor");
    return r.fulfill({ json: { items: [], next_cursor: vervolg ? null : "pagina-twee",
      bijgewerkt_op: new Date(vervolg ? tijd - dag : tijd).toISOString() } });
  });
  await page.goto("/automatisering/historie");
  await ready(page);
  await expect(page.getByText("Op deze pagina geen passende verzoeken.")).toBeVisible();
  await page.getByRole("button", { name: "Meer verzoeken laden" }).click();
  await expect(page.locator("main").getByTestId("bronstand")).toContainText("Verouderd");
  await expect(page.getByText("Geen actieverzoeken van flows.")).toHaveCount(0);
});

test("E15 · de appcatalogus en de datasetselectie volgen de onderliggende inventaris", async ({ page }) => {
  const nu = Date.now() - 1000;
  let tijd = new Date(nu).toISOString();
  await page.route("**/api/v1/apps?limit=200", r => r.fulfill({ json: {
    ...legePagina, totaal: 0, observed_at: new Date(nu).toISOString(), per_status: { healthy: 0, degraded: 0, down: 0, unknown: 0 },
    inventaris: { status: "ok", verouderd: false, observed_at: tijd },
  } }));
  await page.route("**/api/v1/backups/coverage", r => r.fulfill({ json: {
    apps: [], datasets: [], bronnen: { datasets: { status: "ok", verouderd: false, observed_at: tijd } },
  } }));
  for (const [pad, leeg, oud] of [
    ["/apps", "Nog geen apps in de catalogus.", "Inventaris verouderd"],
    ["/backups", "Geen datasets voor deze selectie.", "Datasets onbekend."],
  ] as const) {
    tijd = new Date(nu).toISOString();
    await page.goto(pad);
    await expect(page.locator("main").getByText(leeg)).toBeVisible();
    tijd = new Date(nu - dag).toISOString();
    await page.reload();
    await expect(page.locator("main").getByText(oud)).toBeVisible();
    const datum = await brondatum(page, tijd);
    const bron = pad === "/apps" ? `Inventaris verouderd (stand van ${datum})` : `Datasets · Onbekend · gemeten ${datum}`;
    await expect(page.locator("main").getByText(bron, { exact: true })).toBeVisible();
    await expect(page.locator("main").getByText(leeg)).toHaveCount(0);
  }
});

test("E15 · een leeg zoekresultaat in het beleid volgt de tijd van de beleidslezing", async ({ page }) => {
  const nu = Date.now() - 1000;
  let tijd = new Date(nu).toISOString();
  const beleid = await (await page.request.get("/api/v1/policy")).json();
  await page.route("**/api/v1/policy", r => r.fulfill({ json: { ...beleid, observed_at: tijd } }));
  await page.goto("/goedkeuringen/beleid");
  await page.getByRole("searchbox").fill("ontbrekende-proefregel");
  await expect(page.getByTestId("geen-regel")).toBeVisible();
  tijd = new Date(nu - dag).toISOString();
  await page.reload();
  await page.getByRole("searchbox").fill("ontbrekende-proefregel");
  await expect(page.getByTestId("verouderd")).toContainText("Verouderd");
  await expect(page.getByTestId("geen-regel")).toHaveCount(0);
});
