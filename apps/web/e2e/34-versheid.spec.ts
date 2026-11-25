import { expect, test, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
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

test("E15 · een verse lijst houdt de eigen meettijd van elke uitvoering in goedkeuringen en flowhistorie", async ({ page }) => {
  const nu = Date.now() - 1000;
  const tijden = [new Date(nu - dag).toISOString(), new Date(nu).toISOString()];
  const items = tijden.map(tijd => ({
    request_id: randomUUID(), action_id: "app.restart", status: "uitgevoerd", risk_class: "R1",
    target: { app_id: "proef-app" }, actor: { type: "flow", id: `flow:${flow}` }, goedkeuring_nodig: true,
    aangemaakt_op: tijd, uitgevoerd_op: tijd, bijgewerkt_op: tijd,
  }));
  const lijst = { items, next_cursor: null, bijgewerkt_op: tijden[1] };
  await page.route("**/api/v1/actions?status=alle&limit=50", r => r.fulfill({ json: lijst }));
  await page.route("**/api/v1/actions?limit=50", r => r.fulfill({ json: lijst }));
  for (const pad of ["/goedkeuringen", "/automatisering/historie"]) {
    await page.goto(pad);
    await ready(page);
    if (pad === "/goedkeuringen") await page.getByTestId("filter").selectOption("alle");
    const oud = page.locator('main [data-status="stale"]');
    await expect(oud).toHaveText(`Verouderd · stand van ${await brondatum(page, tijden[0]!)}`);
    await expect(oud.locator("svg.lucide-check")).toHaveCount(0);
    await expect(page.getByText("Uitgevoerd en gecontroleerd", { exact: true })).toHaveCount(1);
  }
});

test("E15 · alleen actuele bevestiging van elke vereiste kloon opent de hersteltest", async ({ page }) => {
  const nu = Date.now();
  await page.clock.install({ time: nu });
  const tijd = (leeftijd: number) => new Date(nu - leeftijd).toISOString();
  const punt = randomUUID(), checkpoint = randomUUID();
  const datasets = ["proef/app", "proef/db"];
  const ids = datasets.map(() => randomUUID());
  let tweedeKloon = tijd(2000);
  await page.route("**/api/v1/backups/herstelpunten", r => r.fulfill({ json: { observed_at: tijd(1000), items: [{
    id: punt, app: "proef", gemaakt_op: tijd(3 * dag), checkpoint_id: checkpoint, snapshot: { actie_id: checkpoint, datasets },
  }] } }));
  await page.route(`**/api/v1/actions/${checkpoint}`, r => r.fulfill({ json: {
    request_id: checkpoint, action_id: "zfs.snapshot.create", status: "uitgevoerd", target: { dataset: "proef" },
    bijgewerkt_op: tijd(1000), preview: { wijziging: { soort: "snapshot_maken", snapshot: "proef@punt" } },
    resultaat: { readback: { aanwezig: true, leden: { "proef/app": "4", "proef/db": "4" } } },
  } }));
  await page.route("**/api/v1/actions?*action_id=zfs.snapshot.clone_to_sandbox*", r => r.fulfill({ json: {
    bijgewerkt_op: tijd(1000), next_cursor: null, items: datasets.map((dataset, i) => ({
      request_id: ids[i], action_id: "zfs.snapshot.clone_to_sandbox", status: "uitgevoerd", risk_class: "R1",
      target: { snapshot: `${dataset}@punt` }, bijgewerkt_op: tijd(2000), uitgevoerd_op: tijd(2000),
      resultaat: { uitgevoerd_op: i === 1 ? tweedeKloon : tijd(2000), readback: { aanwezig: true, dataset: `proef/asm-sandbox/proef-${punt}-${i + 1}` } },
    })),
  } }));
  let robotaanroepen = 0;
  await page.route(`**/api/v1/backups/herstelpunten/${punt}/hersteltest`, r => {
    robotaanroepen++;
    return r.fulfill({ json: {} });
  });
  await page.goto("/backups/hersteltests");
  const reden = page.locator("#robotreden");
  const start = page.getByRole("button", { name: "Hersteltest in zandbak starten" });
  await expect(reden).toContainText("Bevestigde zandbakklonen · 2");
  await expect(start).toBeEnabled();

  tweedeKloon = tijd(dag);
  await page.reload();
  await expect(reden).toContainText(`Laatst bekend · stand van ${await brondatum(page, tweedeKloon)}`);
  await expect(reden.locator("time")).toHaveAttribute("datetime", tweedeKloon);
  await expect(reden).not.toContainText("Bevestigde zandbakklonen");
  await expect(start).toBeDisabled();
  await start.click({ force: true });
  await start.press("Enter");
  await start.press("Space");
  expect(robotaanroepen).toBe(0);

  tweedeKloon = tijd(14 * 60_000);
  await page.reload();
  await expect(reden).toContainText("Bevestigde zandbakklonen · 2");
  await expect(start).toBeEnabled();
  await page.clock.fastForward(61_000);
  await expect(start).toBeDisabled();
  await expect(reden.locator("time")).toHaveAttribute("datetime", tweedeKloon);
  expect(robotaanroepen).toBe(0);
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
