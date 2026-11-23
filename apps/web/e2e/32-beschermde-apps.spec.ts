import { expect, test, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { control, expectAccessible, leesToegestaneBackupGate, nasMutations, ready, stackState, VIEWER } from "./helpers";

// De inventaris en het leesplan worden uitsluitend in de eigen, tijdelijke Hub-stack aangemaakt.
test.skip(Boolean(process.env.HUB_E2E_BASE_URL), "Deze regressieproeven gebruiken de eigen lokale Hub en simulator.");

async function appId(page: Page, naam: string) {
  const r = await page.request.get("/api/v1/apps?limit=200");
  expect(r.status()).toBe(200);
  const { items } = await r.json();
  const app = items.find((item: { runtime_id: string }) => item.runtime_id === naam);
  expect(app).toBeTruthy();
  return app.id as string;
}

test("Acties en Versies tonen de vier verboden bedieningen bij geen van de zes gewone namen", async ({ page }) => {
  const beleidsantwoord = await page.request.get("/api/v1/policy");
  const regels = (await beleidsantwoord.json()).beschermd as { app: string }[];
  const lijst = await (await page.request.get("/api/v1/apps?limit=200")).json();
  for (const [i, regel] of regels.entries()) {
    if (!lijst.items.some((app: { runtime_id: string }) => app.runtime_id === regel.app)) {
      expect((await control("/nas/app", { naam: regel.app, image: `voorbeeld/${regel.app}:1.0`, poort: 31230 + i })).status).toBe(200);
    }
  }
  await page.goto("/server");
  await ready(page);
  await page.getByTestId("inventaris-vernieuwen").click();
  await expect(page.getByTestId("vernieuwen-status")).toContainText("Inventaris vernieuwd", { timeout: 60_000 });
  const voor = await nasMutations();
  const continuBeschikbaar = ["emby", "jelly-leon", "jellyfin", "mediaguard"];
  for (const regel of regels) {
    const id = await appId(page, regel.app);
    await page.goto(`/apps/${id}?tab=acties`);
    await expect(page.getByTestId("app-acties").getByTestId("beschermd")).toBeVisible();
    for (const actie of ["stop", "uninstall"]) await expect(page.getByTestId(`actie-app.${actie}`)).toHaveCount(0);
    await expect(page.getByTestId("app-acties").getByRole("link", { name: /Via Versies/ })).toHaveCount(0);
    if (continuBeschikbaar.includes(regel.app)) await expect(page.getByTestId("actie-app.restart")).toHaveCount(0);
    await page.goto(`/apps/${id}?tab=versies`);
    await expect(page.getByTestId("app-versies").getByTestId("beschermd")).toBeVisible();
    await expect(page.getByTestId("bijwerken")).toHaveCount(0);
    await expect(page.getByTestId("terugzetpunten")).toHaveCount(0);
  }
  expect(await nasMutations()).toEqual(voor);
  expect(regels.map((r) => r.app)).toEqual(expect.arrayContaining([...continuBeschikbaar, "ai-server-manager", "ai-server-manager-executor"]));
});

for (const staat of ["RUNNING", "STOPPED"]) {
  test(`beide tabs verbergen de bediening bij een image-alias of ontbrekende image (${staat})`, async ({ page }) => {
    const naam = `kijkkamer-${staat.toLowerCase()}`;
    expect((await control("/nas/app", { naam, image: "emby/embyserver:4.8.10", poort: 31229, staat })).status).toBe(200);
    await page.goto("/server");
    await ready(page);
    await page.getByTestId("inventaris-vernieuwen").click();
    await expect(page.getByTestId("vernieuwen-status")).toContainText("Inventaris vernieuwd", { timeout: 60_000 });
    const id = await appId(page, naam);
    const voor = await nasMutations();
    for (const tab of ["acties", "versies"]) {
      await page.goto(`/apps/${id}?tab=${tab}`);
      const paneel = page.getByTestId(`app-${tab}`);
      await expect(paneel.getByTestId("beschermd")).toContainText(staat === "RUNNING" ? "Emby blijft beschikbaar" : "weigert elke actie");
      await expect(paneel.locator('[data-testid^="actie-app."], [data-testid="bijwerken"], [data-testid="terugzetpunten"]')).toHaveCount(0);
      await expect(paneel.getByRole("link", { name: /Via Versies/ })).toHaveCount(0);
    }
    const csrf = (await page.context().cookies()).find((c) => c.name === "hub_csrf")!.value;
    const antwoord = await page.request.post("/api/v1/actions", {
      headers: { "X-CSRF-Token": csrf, "Idempotency-Key": randomUUID() },
      data: { action_id: "app.stop", target: { host_id: "nas-primary", app_id: naam }, parameters: {}, reason: "Veiligheidscontrole" },
    });
    expect(antwoord.status()).toBe(403);
    expect(await nasMutations()).toEqual(voor);
  });
}

test("foutbericht en details blijven buiten de DOM van de wizard en het appbeheer", async ({ page }) => {
  const bericht = "proefbericht-" + randomUUID();
  const detail = "proefdetail-" + randomUUID();
  const code = "onbekende-code-" + randomUUID();
  const trace = "ongeldige-referentie-" + randomUUID();
  const fout = {status: 503, json: {code, message: bericht, details: {info: detail}, trace_id: trace}};
  const plan = randomUUID();
  const doel = await appId(page, "mediaguard");
  const uit: boolean[][] = [];
  for (const [api, scherm] of [
    [`/api/v1/catalog/plans/${plan}`, `/apps/installeren?plan=${plan}`],
    ["/api/v1/policy", `/apps/${doel}?tab=acties`],
  ] as const) {
    await page.route("**" + api, (r) => r.fulfill(fout));
    await page.goto(scherm);
    await expect(page.getByTestId("error-panel")).toBeVisible();
    const html = await page.content();
    uit.push([bericht, detail, code, trace].map((veld) => html.includes(veld)));
    await page.unroute("**" + api);
  }
  console.log("FOUTMARKERINGEN wizard/beleid", JSON.stringify(uit));
  expect(uit).toEqual([[false, false, false, false], [false, false, false, false]]);
});

test("een geweigerd voorstel toont vaste tekst en een geldige trace-ID", async ({ page }) => {
  const markering = `proefveld-${randomUUID()}`;
  const trace = randomUUID();
  const fout = { status: 403, json: { code: "actie_geweigerd", message: markering, details: { reden: markering }, trace_id: trace } };
  const id = await appId(page, "media-source-optimizer");
  await page.route("**/api/v1/actions", (route) => route.fulfill(fout));
  await page.goto(`/apps/${id}?tab=acties`);
  await page.getByTestId("actie-app.restart").click();
  const paneel = page.getByTestId("error-panel");
  await expect(paneel).toContainText("Het risicobeleid weigert deze actie.");
  await expect(paneel).toContainText(trace);
  expect(await page.content()).not.toContain(markering);

  const planId = randomUUID();
  await page.route(`**/api/v1/catalog/plans/${planId}`, (route) => route.fulfill({ json: {
    plan_id: planId, app_id: "proefapp", app_name: "proefapp", status: "klaar_voor_voorstel", step_id: "installeren",
    request_id: null, reden: null, expires_at: new Date(Date.now() + 600_000).toISOString(), release: {}, controles_na_installatie: [],
  } }));
  await page.route("**/steps/installeren/propose", (route) => route.fulfill(fout));
  await page.goto(`/apps/installeren?plan=${planId}`);
  await page.getByTestId("wizard-volgende").click();
  await expect(paneel).toContainText("Het risicobeleid weigert deze actie.");
  await expect(paneel).toContainText(trace);
  expect(await page.content()).not.toContain(markering);
});

test("ongeldige en afwezige plannen sluiten de wizard voor muis en toetsenbord", async ({ page }) => {
  let aanvragen = 0;
  page.on("request", (r) => { if (r.method() === "POST" && r.url().includes("/propose")) aanvragen++; });
  for (const [id, melding] of [["geen-plan", "kies-app-nog-niet"], [randomUUID(), "plan-niet-gevonden"]] as const) {
    await page.goto(`/apps/installeren?plan=${id}`);
    await expect(page.getByTestId(melding)).toBeVisible();
    const knop = page.getByTestId("wizard-volgende");
    await expect(knop).toHaveAttribute("aria-disabled", "true");
    await knop.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Space");
    await knop.evaluate((element: HTMLButtonElement) => element.click());
    await expectAccessible(page, melding);
  }
  console.log("ONGELDIG twee geblokkeerde pagina's; voorstellen", aanvragen);
  expect(aanvragen).toBe(0);
});

test("een lezer opent het plan van een andere testgebruiker met uitsluitend leesrechten", async ({ page, browser, baseURL }) => {
  const plan = stackState().leesplan!;
  const { id: planId, markering } = plan;
  const csrf = (await page.context().cookies()).find(c => c.name === "hub_csrf")!.value;
  const planlezer = { ...VIEWER, username: "planlezer" };
  const gebruiker = await page.request.post("/api/v1/users", {
    data: {...planlezer, role: "viewer"}, headers: {"X-CSRF-Token": csrf, "Idempotency-Key": randomUUID()},
  });
  expect([200, 201, 409]).toContain(gebruiker.status());
  const leescontext = await browser.newContext({baseURL, storageState: {cookies: [], origins: []}});
  try {
    const lezer = await leescontext.newPage();
    expect((await lezer.request.post("/api/v1/auth/login", {data: planlezer})).status()).toBe(200);
    const voor = await nasMutations();
    await lezer.goto(`/apps/installeren?plan=${planId}`);
    const preview = lezer.getByTestId("installatiepreview");
    await expect(preview).toContainText("review-app");
    expect(await lezer.content()).not.toContain(markering);
    await expect(lezer.getByTestId("wizard-volgende")).toHaveAttribute("aria-disabled", "true");
    await lezer.getByTestId("wizard-volgende").evaluate((e: HTMLButtonElement) => e.click());
    await expect(lezer.getByTestId("volgende-reden")).toContainText("operator");
    expect(await nasMutations()).toEqual(voor);
    console.log("ANDER PLAN kijker leest preview; voorstel uit; extra planveld buiten DOM");
  } finally {
    await leescontext.close();
  }
});

test("bijwerken toont de concrete back-upblokkade en verwijderen benoemt het behoud in beide stappen", async ({ page }) => {
  const id = await appId(page, "media-source-optimizer");
  const api = "/api/v1/apps/" + id;
  const detail = await (await page.request.get(api)).json();
  await page.route("**" + api, r => r.fulfill({json: {...detail, installatiewijze: "catalog_app",
    catalogus: {upgrade_beschikbaar: true, nieuwste_versie: "1.4.15"}}}));
  const voor = await nasMutations();
  await page.goto(`/apps/${id}?tab=versies`);
  await expect(page.getByTestId("bijwerken")).toHaveAttribute("aria-disabled", "true");
  await expect(page.locator("#versies-backupreden")).toBeVisible();
  await leesToegestaneBackupGate(page);
  await page.reload();
  await page.getByTestId("bijwerken").click();
  await expect(page.getByTestId("beslis-blokkade")).toContainText(/back-up|herstelpunt|checkpoint/i);
  const knop = page.getByTestId("goedkeuren");
  await expect(knop).toHaveAttribute("aria-disabled", "true");
  let goedkeuringen = 0;
  page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/approve")) goedkeuringen++; });
  await knop.evaluate((e: HTMLButtonElement) => e.click());
  await page.goto(`/apps/${id}?tab=acties`);
  await page.getByTestId("actie-app.uninstall").click();
  await expect(page.getByTestId("verwijderen-annuleren")).toBeFocused();
  await expect(page.getByTestId("data-blijft")).toContainText("Je gegevens blijven bewaard");
  await expect(page.getByTestId("verwijderen-controle").getByRole("checkbox")).toHaveCount(0);
  await page.getByTestId("verwijderen-volgende").click();
  await expect(page.getByTestId("diff-gevolgen")).toContainText("App-data in ix-volumes blijft staan");
  expect(goedkeuringen).toBe(0);
  expect(await nasMutations()).toEqual(voor);
  console.log("BEHOUD concrete back-upblokkade; twee data-uitleggen; nul goedkeuringen en schrijfaanroepen");
});
