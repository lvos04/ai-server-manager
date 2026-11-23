/**
 * S-P2-180: Versies, Acties, Appstore, installatiewizard en verwijderen (ontwerp HUB_P2_ONTWERP.md S-044 t/m S-048).
 * Tegen de echte Hub-API met de fake TrueNAS (Sim-getest). Alleen waar de fake NAS het geval niet kent, vervangt een
 * page.route één leesantwoord: een Emby-app, een catalogusapp met een nieuwere versie en een installatieplan (de Hub
 * heeft nog geen browserroute om een plan te kiezen). Elke schrijfroute naar /api/v1/actions blijft de echte server.
 */
import { expect, test, type BrowserContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { expectAccessible, expectNoHorizontalScroll, expectTouchTargets, ready } from "./helpers";

async function csrf(ctx: BrowserContext): Promise<string> {
  return (await ctx.cookies()).find((c) => c.name === "hub_csrf")?.value ?? "";
}

async function stelVoor(page: Page, action_id: string, app: string, parameters: Record<string, unknown> = {}) {
  return page.request.post("/api/v1/actions", {
    data: { action_id, target: { host_id: "nas-primary", app_id: app }, parameters, reason: "e2e S-P2-180" },
    headers: { "X-CSRF-Token": await csrf(page.context()), "Idempotency-Key": randomUUID() },
  });
}

/** Het catalogus-ID van een app van de fake NAS (via de echte lijst). */
async function appId(page: Page, runtime: string): Promise<string> {
  await page.goto("/apps");
  await ready(page);
  const res = await page.request.get("/api/v1/apps?limit=200");
  const items = ((await res.json()) as { items: { id: string; runtime_id: string }[] }).items;
  const a = items.find((i) => i.runtime_id === runtime);
  expect(a, `app ${runtime} in de catalogus`).toBeTruthy();
  return a!.id;
}

/** Vervang alleen het detail van deze app door het echte detail met aanpassingen. */
async function detailMet(page: Page, id: string, extra: Record<string, unknown>): Promise<void> {
  const echt = (await (await page.request.get(`/api/v1/apps/${id}`)).json()) as Record<string, unknown>;
  await page.route(`**/api/v1/apps/${id}`, (r) => r.fulfill({ json: { ...echt, ...extra } }));
}

const geenKnop = async (page: Page) => {
  for (const id of ["app.stop", "app.update", "app.rollback", "app.uninstall"]) await expect(page.getByTestId(`actie-${id}`)).toHaveCount(0);
  await expect(page.getByTestId("bijwerken")).toHaveCount(0);
  await expect(page.getByTestId("terugzetpunten")).toHaveCount(0);
};

test("HARDE EIS · Emby: geen knop in Acties of Versies, de vaste zin staat er, en de route weigert met 403", async ({ page }) => {
  const id = await appId(page, "my-house");
  await detailMet(page, id, { naam: "emby", runtime_id: "emby", app_id: "emby", titel: "Emby", installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "4.9.2" } });
  await page.goto(`/apps/${id}?tab=acties`);
  await ready(page);
  await expect(page.getByTestId("beschermd")).toContainText("Emby blijft beschikbaar. Alleen jij kunt Emby verwijderen.");
  await geenKnop(page);
  await expect(page.getByTestId("actie-app.restart")).toHaveCount(0);
  await expectAccessible(page, "acties-emby");
  await page.getByRole("tab", { name: "Versies" }).click();
  await expect(page.getByTestId("app-versies").getByTestId("beschermd")).toBeVisible();
  await geenKnop(page);
  // Rechtstreeks aanroepen helpt niet: de server weigert elke actie op Emby.
  for (const [actie, params] of [["app.stop", {}], ["app.update", { catalog_version: "4.9.2" }], ["app.uninstall", {}]] as const) {
    const r = await stelVoor(page, actie, "emby", params);
    expect(r.status(), await r.text()).toBe(403);
    expect(((await r.json()) as { code: string }).code).toBe("actie_geweigerd");
  }
});

test("HARDE EIS · MediaGuard (echte app): Versies zonder bijwerk- of terugzetknop, met de uitleg", async ({ page }) => {
  const id = await appId(page, "mediaguard");
  await page.goto(`/apps/${id}?tab=versies`);
  await ready(page);
  await expect(page.getByTestId("app-versies").getByTestId("beschermd")).toBeVisible();
  await geenKnop(page);
});

test("bijwerken zonder herstelpunt: voorstel met preview, blokkade van de back-up zichtbaar en goedkeuren uit", async ({ page }) => {
  const id = await appId(page, "media-source-optimizer");
  await detailMet(page, id, { installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.4.15" } });
  await page.goto(`/apps/${id}?tab=versies`);
  await ready(page);
  await expect(page.getByTestId("terugzetten-geblokkeerd")).toContainText("geen bevestigd terugzetpad");
  await expectAccessible(page, "versies");
  await expectNoHorizontalScroll(page, "versies");
  await expectTouchTargets(page, "versies");
  await page.getByTestId("bijwerken").click();
  await page.waitForURL(/\/goedkeuringen\/[0-9a-f-]{36}$/);
  await ready(page);
  const preview = page.getByTestId("actie-preview");
  await expect(preview).toContainText("app.update");
  await expect(preview.locator("[data-risico]")).toBeVisible();
  await expect(preview).toContainText("Back-up vereist");
  await expect(page.getByTestId("beslis-blokkade")).toBeVisible();
  const knop = page.getByTestId("goedkeuren");
  await expect(knop).toHaveAttribute("aria-disabled", "true");
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/approve")) posts.push(r.url());
  });
  await knop.click({ force: true });
  await page.waitForTimeout(300);
  expect(posts).toEqual([]);
});

test("verwijderen: eerst ‘Controleer wat blijft’ met focus op Annuleren en de datazin, daarna het R2-voorstel", async ({ page }) => {
  const id = await appId(page, "media-source-optimizer");
  await page.goto(`/apps/${id}?tab=acties`);
  await ready(page);
  await expect(page.getByTestId("rij-app.uninstall")).toContainText("Goedkeuring nodig");
  await page.getByTestId("actie-app.uninstall").click();
  const controle = page.getByTestId("verwijderen-controle");
  await expect(controle).toContainText("Controleer wat blijft · stap 1 van 2");
  await expect(page.getByTestId("data-blijft")).toHaveText("Alleen de container wordt verwijderd. Je gegevens blijven bewaard.");
  await expect(page.getByTestId("verwijderen-annuleren")).toBeFocused();
  await expect(controle.locator("input")).toHaveCount(0);
  await expectAccessible(page, "verwijderen-controle");
  await page.getByTestId("verwijderen-annuleren").click();
  await expect(controle).toHaveCount(0);
  await page.getByTestId("actie-app.uninstall").click();
  await page.getByTestId("verwijderen-volgende").click();
  await page.waitForURL(/\/goedkeuringen\/[0-9a-f-]{36}$/);
  await ready(page);
  await expect(page.getByTestId("actie-preview")).toContainText("app.uninstall");
  await expect(page.getByTestId("verzoek-status")).toContainText("Wacht op goedkeuring");
});

test("appstore en wizard zonder manifestbron: C-12, ‘Volgende’ uit, Enter maakt niets, geen YAML- of compose-veld", async ({ page }) => {
  await page.goto("/apps/catalogus");
  await ready(page);
  await expect(page.getByTestId("catalogus-nog-niet")).toContainText("de Hub kan de installeerbare manifests nog niet ophalen");
  await expectAccessible(page, "appstore");
  await expectNoHorizontalScroll(page, "appstore");
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && /\/api\/v1\/(catalog|actions)/.test(r.url())) posts.push(r.url());
  });
  await page.goto("/apps/installeren");
  await ready(page);
  await expect(page.getByTestId("wizard-stap")).toHaveText("Stap 1 van 7: Kies app");
  const volgende = page.getByTestId("wizard-volgende");
  await expect(volgende).toHaveAttribute("aria-disabled", "true");
  await expect(page.getByTestId("volgende-reden")).toHaveText("Kies eerst een app.");
  await volgende.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Space");
  await page.waitForTimeout(300);
  expect(posts).toEqual([]);
  await expect(page.locator("main textarea, main input")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText(/yaml|compose/i);
  await expectAccessible(page, "wizard-kies-app");
  await expectNoHorizontalScroll(page, "wizard-kies-app");
  await expectTouchTargets(page, "wizard-kies-app");
});

const PLAN = (extra: Record<string, unknown> = {}) => ({
  plan_id: "99999999-2222-4333-8444-555555555555",
  app_id: "fotos",
  app_name: "fotos",
  step_id: "installeren",
  status: "klaar_voor_voorstel",
  reden: null,
  plan_etag: "etag",
  expires_at: new Date(Date.now() + 600_000).toISOString(),
  request_id: null,
  release: { catalog: { train: "stable", app: "immich", version: "1.4.8" }, image_digests: [`sha256:${"c".repeat(64)}`] },
  koppeling: null,
  registratie: null,
  melding: null,
  controles_na_installatie: [{ id: "web", soort: "http", beschrijving_nl: "De webinterface antwoordt." }],
  ...extra,
});

test("wizard met een plan: geblokkeerde controle vooraf houdt tegen; de preview lekt geen geheim; ‘Volgende’ opent het voorstel", async ({ page }) => {
  const GEHEIM = "GEHEIM-TESTWAARDE-S-P2-180"; // gitleaks:allow -- synthetische testwaarde
  let plan: Record<string, unknown> = PLAN({ status: "geblokkeerd", reden: "planner_niet_klaar" });
  await page.route("**/api/v1/catalog/plans/99999999-2222-4333-8444-555555555555", (r) => r.fulfill({ json: plan }));
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/propose")) posts.push(r.url());
  });
  await page.goto("/apps/installeren?plan=99999999-2222-4333-8444-555555555555");
  await ready(page);
  await expect(page.getByTestId("wizard-stap")).toHaveText("Stap 3 van 7: Controle vooraf");
  await expect(page.getByTestId("controle-vooraf")).toContainText("De controle vooraf is nog niet afgerond");
  const volgende = page.getByTestId("wizard-volgende");
  await expect(volgende).toHaveAttribute("aria-disabled", "true");
  await volgende.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  expect(posts).toEqual([]);

  // Een echt voorstel om naar door te gaan (de propose-route vraagt een echt plan bij de planner, dat deze stack niet heeft).
  const echt = await stelVoor(page, "app.restart", "my-house");
  expect(echt.status(), await echt.text()).toBe(201);
  const requestId = ((await echt.json()) as { request_id: string }).request_id;
  plan = { ...PLAN(), parameters: { wachtwoord: GEHEIM }, release: { ...(PLAN().release as object), geheim: GEHEIM } };
  await page.route("**/api/v1/catalog/plans/*/steps/*/propose", (r) => r.fulfill({ status: 201, json: { request_id: requestId } }));
  await page.reload();
  await ready(page);
  await expect(page.getByTestId("wizard-stap")).toHaveText("Stap 4 van 7: Preview");
  const preview = page.getByTestId("installatiepreview");
  await expect(preview).toContainText(`sha256:${"c".repeat(64)}`);
  await expect(preview).toContainText("Niet beschikbaar — het installatieplan levert dit nog niet aan de browser.");
  await expect(page.getByTestId("controles-na")).toContainText("Open");
  expect(await page.content()).not.toContain(GEHEIM);
  await expectAccessible(page, "wizard-preview");
  await expectNoHorizontalScroll(page, "wizard-preview");
  await page.getByTestId("wizard-volgende").click();
  await page.waitForURL(new RegExp(`/goedkeuringen/${requestId}$`));
  expect(posts).toHaveLength(1);
});
