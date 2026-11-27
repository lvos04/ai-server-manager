/**
 * S-P2-170: goedkeuringen, actie-preview, uitvoering en risicobeleid (ontwerp HUB_P2_ONTWERP.md S-061 t/m S-066).
 * Tegen de echte Hub-API met de fake TrueNAS (Sim-getest). Alleen het R3-geval gebruikt een gesimuleerd verzoek: het
 * echte beleid kent geen R3-actie die op goedkeuring wacht (een R3-patroon wordt altijd geweigerd).
 */
import { documentatieAdres } from "../tests/adressen";
import { expect, test, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { expectAccessible, expectNoHorizontalScroll, expectTouchTargets, nasMutations, p2Afdrukken, ready } from "./helpers";

const DOEL = (app: string) => ({ host_id: "nas-primary", app_id: app });
const KIJKER = { username: "kijker-acties", password: "Kijker-Acties-Lang-2026" }; // gitleaks:allow -- synthetische testwaarde

async function csrf(ctx: BrowserContext): Promise<string> {
  return (await ctx.cookies()).find((c) => c.name === "hub_csrf")?.value ?? "";
}

async function post(req: APIRequestContext, ctx: BrowserContext, pad: string, data: unknown) {
  return req.post(pad, { data, headers: { "X-CSRF-Token": await csrf(ctx), "Idempotency-Key": randomUUID() } });
}

async function stelVoor(page: Page, action_id: string, app: string, extra: Record<string, unknown> = {}) {
  const res = await post(page.request, page.context(), "/api/v1/actions", { action_id, target: DOEL(app), reason: "e2e S-P2-170", ...extra });
  expect(res.status(), await res.text()).toBe(201);
  return (await res.json()) as { request_id: string; status: string; risk_class: string; blokkades: unknown[] };
}

test("R2-voorstel: in de wachtlijst en de kopteller, detail met preview, diff, ‘Waarom R2?’ en gebonden velden", async ({ page }, info) => {
  const v = await stelVoor(page, "app.uninstall", "media-source-optimizer");
  expect(v.risk_class).toBe("R2");
  expect(v.status).toBe("wacht_op_goedkeuring");
  await page.goto("/goedkeuringen");
  await ready(page);
  await expect(page.getByTestId("kop-goedkeuringen-teller")).toBeVisible();
  const rij = page.getByTestId(`verzoek-${v.request_id}`);
  await expect(rij).toContainText("Goedkeuring nodig");
  await expect(rij).toContainText("Wacht op goedkeuring");
  await expectAccessible(page, "goedkeuringen");
  await expectNoHorizontalScroll(page, "goedkeuringen");
  await expectTouchTargets(page, "goedkeuringen");
  await p2Afdrukken(page, info, "goedkeuringen");

  await rij.click();
  await ready(page);
  await expect(page.locator("main h1")).toHaveText("Goedkeuring beoordelen");
  const preview = page.getByTestId("actie-preview");
  await expect(preview).toContainText("app.uninstall");
  await expect(preview.locator("[data-risico=R2]")).toBeVisible();
  // R-VEILIG-2 (RV-10): de echte uninstall-preview is eenduidig "Was → (verwijderd)" en zegt wat er met de data gebeurt.
  await expect(page.getByTestId("diff").locator("[data-diff]")).toHaveCount(1);
  await expect(page.getByTestId("diff").locator("[data-diff=verwijderd]")).toContainText("media-source-optimizer");
  await expect(page.getByTestId("diff").locator("[data-diff=toegevoegd]")).toHaveCount(0);
  await expect(page.getByTestId("diff-gevolgen")).toContainText("App-data in ix-volumes blijft staan.");
  await expect(preview).toContainText("Back-up vereist");
  // De vrije reden van het voorstel komt nergens in beeld.
  await expect(page.locator("main")).not.toContainText("e2e S-P2-170");
  await page.getByTestId("waarom-klasse").locator("summary").click();
  await expect(page.getByTestId("waarom-klasse")).toContainText("Regels");
  await page.getByTestId("gebonden-velden").locator("summary").click();
  await expect(page.getByTestId("gebonden-velden")).toContainText("preview_hash");
  // Annuleren staat in de leesvolgorde vóór de beslisknop.
  const knoppen = await page.getByTestId("beslissen").locator("a, button").allInnerTexts();
  expect(knoppen.findIndex((t) => t.includes("Annuleren"))).toBeLessThan(knoppen.findIndex((t) => t.includes("Goedkeuren")));
  await expectAccessible(page, "goedkeuring-r2");
  await expectNoHorizontalScroll(page, "goedkeuring-r2");
  await expectTouchTargets(page, "goedkeuring-r2");
  await p2Afdrukken(page, info, "actie-preview-r2");
});

test("een uitgeschakelde of geblokkeerde goedkeurknop doet echt niets (V-065)", async ({ page }) => {
  const v = await stelVoor(page, "app.uninstall", "media-source-optimizer");
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/approve")) posts.push(r.url());
  });
  await page.goto(`/goedkeuringen/${v.request_id}`);
  await ready(page);
  const knop = page.getByTestId("goedkeuren");
  await expect(knop).toBeVisible();
  if ((await knop.getAttribute("aria-disabled")) === "true") {
    const reden = await knop.getAttribute("aria-describedby");
    await expect(page.locator(`[id="${reden}"]`)).toBeVisible();
    // force: Playwright wacht anders op een ingeschakelde knop; de klik moet echt aankomen en niets doen.
    await knop.click({ force: true });
    await knop.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Space");
    await page.waitForTimeout(500);
    expect(posts).toEqual([]);
  } else {
    // Vrij voorstel: twee keer snel klikken geeft één goedkeuring.
    await knop.dblclick();
    await expect(page.getByTestId("verzoek-status")).toContainText(/Goedgekeurd/);
    expect(posts).toHaveLength(1);
  }
});

test("R1-herstart wacht op goedkeuring van de preview en daarna op bevestiging van uitvoeren", async ({ page }) => {
  const v = await stelVoor(page, "app.restart", "my-house");
  expect(v.risk_class).toBe("R1");
  const posts: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/execute")) posts.push(r.url());
  });
  await page.goto(`/goedkeuringen/${v.request_id}`);
  await ready(page);
  await expect(page.getByTestId("verzoek-status")).toHaveText("Wacht op goedkeuring");
  const knop = page.getByTestId("uitvoeren");
  expect(v.status).toBe("wacht_op_goedkeuring");
  await expect(page.getByTestId("actie-preview")).toContainText("app.restart");
  await expect(knop).toHaveCount(0);
  const geweigerd = await post(page.request, page.context(), `/api/v1/actions/${v.request_id}/execute`, {});
  expect(geweigerd.status()).toBe(409);
  expect((await geweigerd.json()).code).toBe("goedkeuring_nodig");
  expect(await nasMutations()).toEqual([]);
  await page.getByTestId("goedkeuren").click();
  await expect(page.getByTestId("verzoek-status")).toContainText("Goedgekeurd");
  await expect(page.getByTestId("uitvoering-eind")).toHaveText("Nog niet uitgevoerd");
  await knop.click();
  const dialoog = page.getByRole("alertdialog");
  await expect(dialoog).toBeVisible();
  await expect(dialoog.getByRole("button", { name: "Annuleren" })).toBeFocused();
  await expectAccessible(page, "uitvoeren-bevestigen");
  await dialoog.getByRole("button", { name: "Uitvoeren" }).dblclick();
  await expect(dialoog).toHaveCount(0);
  await expect.poll(() => posts.length).toBe(1);
  await page.waitForTimeout(500);
  expect(posts).toHaveLength(1);
  // De tweede tik kan op smalle schermen op de link eronder landen; daarom het verzoek opnieuw openen.
  // De executor is in deze stack pas in e2e/90 gekoppeld: zonder teruggelezen bewijs nooit "Uitgevoerd en gecontroleerd".
  await page.goto(`/goedkeuringen/${v.request_id}`);
  await ready(page);
  await expect(page.getByTestId("uitvoering-eind")).not.toHaveText("Uitgevoerd en gecontroleerd");
});

test("EX18: een kijker ziet geen goedkeurknop en de route weigert met 403", async ({ page, browser }) => {
  const v = await stelVoor(page, "app.uninstall", "my-house");
  const maak = await post(page.request, page.context(), "/api/v1/users", { ...KIJKER, role: "viewer" });
  expect([201, 409, 422]).toContain(maak.status());
  const ctx = await browser.newContext({ storageState: undefined, extraHTTPHeaders: { "X-Forwarded-For": documentatieAdres(17) } });
  try {
    const k = await ctx.newPage();
    const login = await k.request.post("/api/v1/auth/login", { data: KIJKER });
    expect(login.status(), await login.text()).toBe(200);
    await k.goto(`/goedkeuringen/${v.request_id}`);
    await ready(k);
    await expect(k.getByTestId("rolmelding")).toContainText("Alleen een beheerder kan dit goedkeuren.");
    await expect(k.getByTestId("goedkeuren")).toHaveCount(0);
    await expect(k.getByTestId("weigeren-openen")).toHaveCount(0);
    const detail = await (await k.request.get(`/api/v1/actions/${v.request_id}`)).json();
    const r = await post(k.request, ctx, `/api/v1/actions/${v.request_id}/approve`, {
      preview_hash: detail.preview_hash, resource_etag: detail.resource_etag, policy_hash: detail.policy_hash,
    });
    expect(r.status()).toBe(403);
    await expectAccessible(k, "goedkeuring-kijker");
  } finally {
    await ctx.close();
  }
});

test("een verlopen voorstel kan niet worden goedgekeurd", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "wachten op het verlopen alleen op één breedte");
  test.setTimeout(150_000);
  const v = await stelVoor(page, "app.uninstall", "my-house", { expires_in_seconds: 60 });
  await page.goto(`/goedkeuringen/${v.request_id}`);
  await ready(page);
  await expect(page.getByTestId("beslis-blokkade")).toContainText("Voorstel verlopen. Vraag een nieuw voorstel aan.", { timeout: 80_000 });
  await expect(page.getByTestId("goedkeuren")).toHaveAttribute("aria-disabled", "true");
  const detail = await (await page.request.get(`/api/v1/actions/${v.request_id}`)).json();
  const r = await post(page.request, page.context(), `/api/v1/actions/${v.request_id}/approve`, {
    preview_hash: detail.preview_hash, resource_etag: detail.resource_etag, policy_hash: detail.policy_hash,
  });
  expect(r.status()).toBe(409);
  expect((await r.json()).code).toBe("voorstel_verlopen");
});

test("R3 (gesimuleerd verzoek): twee stappen, naam typen; zonder naam doet de gevaarknop niets, dubbel drukken één keer", async ({ page }, info) => {
  const id = randomUUID();
  const nu = Date.now();
  const H = (c: string) => `sha256:${c.repeat(64)}`;
  const verzoek = {
    request_id: id, status: "wacht_op_goedkeuring", action_id: "app.uninstall", target: { host_id: "nas-primary", app_id: "proef-app" },
    actor: { type: "user", id: "beheerder" }, risk_class: "R3", risk_claim: "R1", risk_claim_genegeerd: true, rule_ids: ["PROEF-R3"],
    goedkeuring_nodig: true, policy_hash: H("a"), uitvoerder: "executor", resource_etag: '"proef-1"', preview_hash: H("b"),
    preview: { omschrijving: "App verwijderen", requires_backup: false, kritiek: false, huidig: {}, wijziging: { soort: "verwijderen", app: "proef-app", alleen_containers: true, remove_ix_volumes: false, remove_images: false }, dataretentie: "Data blijft staan.", terugdraaien: "Opnieuw installeren." },
    blokkades: [], goedkeuring: null, resultaat: null, aangemaakt_op: new Date(nu).toISOString(), bijgewerkt_op: new Date(nu).toISOString(),
    geldig_tot: new Date(nu + 900_000).toISOString(), gestart_op: null, uitgevoerd_op: null,
  };
  let goedgekeurd = 0;
  await page.route(`**/api/v1/actions/${id}**`, async (r) => {
    if (r.request().method() === "POST") {
      goedgekeurd++;
      expect(r.request().postDataJSON()).toEqual({ preview_hash: H("b"), resource_etag: '"proef-1"', policy_hash: H("a"), bevestig_naam: "proef-app" });
      await new Promise((ok) => setTimeout(ok, 300));
      return r.fulfill({ json: { ...verzoek, status: "goedgekeurd" } });
    }
    return r.fulfill({ json: goedgekeurd ? { ...verzoek, status: "goedgekeurd" } : verzoek });
  });
  await page.goto(`/goedkeuringen/${id}`);
  await ready(page);
  await expect(page.getByTestId("waarom-klasse")).toContainText("De aanvrager stelde R1 voor; het beleid bepaalt R3.");
  await page.getByTestId("r3-volgende").click();
  await expect(page.getByTestId("r3-stap-2")).toBeVisible();
  const gevaar = page.getByTestId("r3-definitief");
  await expect(gevaar).toHaveAttribute("aria-disabled", "true");
  await gevaar.click({ force: true });
  await expect(page.getByTestId("r3-naam")).toBeFocused();
  await expect(page.locator("#r3-naam-status")).toHaveText("Typ eerst de exacte naam van het doel");
  await page.getByTestId("r3-naam").fill("Proef-app");
  await gevaar.click({ force: true });
  expect(goedgekeurd).toBe(0);
  await page.getByTestId("r3-naam").fill("proef-app");
  await expect(gevaar).not.toHaveAttribute("aria-disabled", "true");
  await expectAccessible(page, "goedkeuring-r3-stap-2");
  await expectTouchTargets(page, "goedkeuring-r3-stap-2");
  await p2Afdrukken(page, info, "goedkeuring-r3");
  await gevaar.dblclick();
  await expect(page.getByTestId("verzoek-status")).toContainText("Goedgekeurd");
  expect(goedgekeurd).toBe(1);
});

test("risicobeleid: alleen lezen met policy_hash en de vaste zin", async ({ page }, info) => {
  await page.goto("/goedkeuringen/beleid");
  await ready(page);
  await expect(page.locator("main")).toContainText("Het beleid kan niet door de AI worden gewijzigd.");
  await expect(page.getByTestId("policy-hash")).toContainText(/sha256:[0-9a-f]{64}/);
  await expect(page.getByTestId("beleid-acties")).toContainText("app.uninstall");
  await expect(page.locator("main")).toContainText("Wordt nooit uitgevoerd");
  await page.getByLabel("Zoek een actie").fill("bestaat-niet");
  await expect(page.getByTestId("geen-regel")).toHaveText("Geen regel gevonden voor dit filter.");
  // Uitsluitend leesbediening: geen knoppen behalve kopiëren en de schil.
  const knoppen = await page.locator("main button").allInnerTexts();
  expect(knoppen.every((t) => t.startsWith("Kopiëren"))).toBe(true);
  await page.getByLabel("Zoek een actie").fill("");
  await expectAccessible(page, "risicobeleid");
  await expectNoHorizontalScroll(page, "risicobeleid");
  await expectTouchTargets(page, "risicobeleid");
  await p2Afdrukken(page, info, "risicobeleid");
});

test("R-VEILIG-1 (RV-8): na uitvoeren nooit de vrije executormelding of details-JSON in de DOM", async ({ page }, info) => {
  for (const [status, code, tekst] of [
    [409, "uitvoering_geweigerd", "De executor heeft de actie geweigerd; er is niets uitgevoerd."],
    [501, "capability_unavailable", "Deze handeling is nog niet beschikbaar bij de uitvoerder; er is niets uitgevoerd."],
  ] as const) {
    const id = randomUUID();
    const nu = Date.now();
    const H = (c: string) => `sha256:${c.repeat(64)}`;
    await page.route(`**/api/v1/actions/${id}**`, (r) =>
      r.request().method() === "POST"
        ? r.fulfill({ status, json: { code, message: "VRIJE-EXECUTOR-MELDING-1", details: { request_id: id, executor: { code: "x_y", message: "VRIJE-EXECUTOR-MELDING-2" } }, trace_id: "t-rv8" } })
        : r.fulfill({
            json: {
              request_id: id, status: "klaar", action_id: "app.start", target: { host_id: "nas-primary", app_id: "proef-app" }, actor: { type: "user", id: "beheerder" },
              risk_class: "R1", risk_claim: null, risk_claim_genegeerd: false, rule_ids: ["PROEF"], goedkeuring_nodig: false, policy_hash: H("a"), uitvoerder: "executor",
              resource_etag: '"proef-1"', preview_hash: H("b"), preview: { omschrijving: "App starten", requires_backup: false, huidig: {}, wijziging: { soort: "start", app: "proef-app" } },
              blokkades: [], goedkeuring: null, resultaat: null, aangemaakt_op: new Date(nu).toISOString(), bijgewerkt_op: new Date(nu).toISOString(),
              geldig_tot: new Date(nu + 900_000).toISOString(), gestart_op: null, uitgevoerd_op: null,
            },
          }),
    );
    await page.goto(`/goedkeuringen/${id}`);
    await ready(page);
    await page.getByTestId("uitvoeren").click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Uitvoeren" }).click();
    const paneel = page.getByTestId("error-panel");
    await expect(paneel).toContainText(tekst);
    await expect(paneel).toContainText(code);
    expect(await page.content()).not.toContain("VRIJE-EXECUTOR-MELDING");
    await expect(paneel).not.toContainText("Technische details");
    if (status === 409) await p2Afdrukken(page, info, "uitvoering-geweigerd");
  }
});
