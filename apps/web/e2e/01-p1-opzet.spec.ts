/**
 * P1-gedrag (desktop, na de opzet) tegen de ECHTE Hub-API met simulators (fake TrueNAS, Uptime Kuma, Beszel, Gotify,
 * OIDC-issuer en een simulator-dienst): appcatalogus, monitoringbronnen en meldingen, diensten koppelen (H5),
 * noodaccount (H6), incidenten-inbox en SSO-instellingen. Alles Sim-getest; niets op een echte NAS.
 */
import { expect, test, type Page } from "@playwright/test";
import { generateKeyPairSync } from "node:crypto";
import { request as httpRequest } from "node:http";
import { startTlsHub } from "./tls-hub";
import { ADMIN, ADMIN_STATE, NOOD, control, expectAccessible, ready, saveP1State, stackState, totp } from "./helpers";

test.describe.configure({ mode: "serial" });
test.use({ storageState: ADMIN_STATE, viewport: { width: 1440, height: 900 }, trace: "off", screenshot: "off", video: "off" });

test("catalogusdoorgang weigert een GET-body met vaste lengte of in chunks", async ({ request, baseURL }) => {
  const appId = "jelly-leon-platform";
  const { cookies } = await request.storageState();
  const csrf = cookies.find(({ name }) => name === "hub_csrf")?.value ?? "";
  const grant = await request.post("/api/v1/services/enrollment-tokens", {
    headers: { "X-CSRF-Token": csrf }, data: { app_id: appId },
  });
  expect(grant.status()).toBe(201);
  const { publicKey } = generateKeyPairSync("ed25519");
  const enrollment = await request.post("/api/v1/services/enroll", {
    data: {
      app_id: appId, version: "0.1.0", base_url: null, enrollment_token: (await grant.json()).enrollment_token,
      public_key_jwk: publicKey.export({ format: "jwk" }),
    },
  });
  expect(enrollment.status()).toBe(200);
  const authorization = `Bearer ${(await enrollment.json()).service_token}`;
  const url = new URL("/api/v1/catalog/availability?train=stable&app=ix-app&version=1.4.8", baseURL);
  expect((await request.get(url.href, { headers: { authorization } })).status()).toBe(200);

  const sendBody = (content: Buffer, chunked: boolean) => new Promise<{ status: number; body: unknown }>((resolve, reject) => {
    const framing = chunked ? { "Transfer-Encoding": "chunked" } : { "Content-Length": content.length };
    const req = httpRequest(url, { method: "GET", headers: { authorization, ...framing } }, (res) => {
      let payload = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => { payload += chunk; });
      res.on("end", () => {
        try { resolve({ status: res.statusCode ?? 0, body: JSON.parse(payload) }); } catch (err) { reject(err); }
      });
      res.on("error", reject);
    });
    req.setTimeout(10_000, () => req.destroy(new Error("Geen antwoord van de webdoorgang")));
    req.on("error", reject);
    req.end(content);
  });

  for (const chunked of [false, true]) {
    expect(await sendBody(Buffer.from("{}"), chunked)).toMatchObject({
      status: 422, body: { code: "validation_error", details: { fouten: [{ veld: "body", type: "extra_forbidden" }] } },
    });
    expect(await sendBody(Buffer.alloc(1024 * 1024 + 1), chunked)).toMatchObject({
      status: 413, body: { code: "payload_too_large", details: { max_bytes: 1024 * 1024 } },
    });
  }
});

async function refreshInventory(page: Page): Promise<void> {
  await page.goto("/server");
  await ready(page);
  await page.getByTestId("inventaris-vernieuwen").click();
  await expect(page.getByTestId("vernieuwen-status")).toHaveText("Inventaris vernieuwd.", { timeout: 60_000 });
}

test("appcatalogus: slechtste status eerst, ‘Draait’ is nooit gezond, acties volgen in P2", async ({ page }) => {
  await page.goto("/apps");
  await ready(page);
  await page.getByTestId("catalogus-bijwerken").click();
  await expect(page.getByTestId("catalogus-status")).toContainText("op de NAS is niets gewijzigd");
  const lijst = page.getByTestId("app-lijst");
  await expect(lijst).toBeVisible();
  // Jellyfin is gestopt (gemeten falen) → staat bovenaan; de chips tonen aantallen uit per_status.
  await expect(lijst.locator("tbody tr").first()).toHaveAttribute("data-testid", "app-jellyfin");
  await expect(page.getByRole("button", { name: /^Storing \(1\)$/ })).toBeVisible();
  await expect(page.getByTestId("app-mediaguard").locator("[data-status]").first()).toHaveAttribute("data-status", "unknown");
  await expect(page.getByTestId("app-mediaguard").getByRole("link", { name: /Openen\s*:\s*MediaGuard/ })).toHaveAttribute("target", "_blank");
  // Filter: alleen Storing.
  await page.getByRole("button", { name: /^Storing \(1\)$/ }).click();
  await expect(page.getByTestId("app-teller")).toContainText("1 app");

  await page.getByRole("button", { name: /^Alle/ }).click();
  await page.getByTestId("app-mediaguard").getByRole("link", { name: "MediaGuard", exact: true }).click();
  await ready(page);
  await expect(page.locator("main h1")).toHaveText("MediaGuard");
  const gezond = page.getByTestId("app-gezondheid");
  await expect(gezond.locator("[data-status]").first()).not.toHaveAttribute("data-status", "healthy");
  await expect(gezond).toContainText("Deze app is nog niet gekoppeld. Ga naar Instellingen → Diensten.");
  await expect(gezond).toContainText("Draait");
  await expect(gezond).toContainText("Draaien alleen is geen bewijs van gezond.");
  await expect(gezond).toContainText("Resourcegrenzen");
  const appId = page.url().split("/apps/")[1]!.split("?")[0]!;
  saveP1State({ app_id: appId });

  await page.getByRole("tab", { name: "Acties" }).click();
  await expect(page).toHaveURL(/tab=acties/);
  const acties = page.getByTestId("app-acties");
  // S-P2-180, HARDE EIS: MediaGuard is beschermd (policy/apps.yaml) → geen knop voor stoppen, bijwerken, terugzetten of
  // verwijderen, wel de uitleg waarom niet; herstarten blijft een gewoon voorstel.
  await expect(acties.getByTestId("beschermd")).toBeVisible();
  for (const id of ["app.stop", "app.update", "app.rollback", "app.uninstall"]) {
    await expect(acties.getByTestId(`actie-${id}`)).toHaveCount(0);
    await expect(acties.getByTestId(`rij-${id}`)).toContainText("Niet in de Hub");
  }
  await expect(acties.getByTestId("actie-app.restart")).toBeVisible();
  await expect(acties).toContainText("De klasse komt uit het risicobeleid");
  await page.getByRole("tab", { name: "Metrieken" }).click();
  await expect(page.getByTestId("capability-per-app")).toContainText("capability_unavailable");
  await page.goBack();
  await expect(page).toHaveURL(/tab=acties/);
  await expectAccessible(page, "appdetail");
});

test("monitoring: Kuma uitgelezen, Beszel met fout wachtwoord opgeslagen + ‘Uitlezen mislukt’, Gotify-testmelding aangenomen", async ({ page }) => {
  const st = stackState();
  await page.goto("/instellingen/monitoring");
  await ready(page);
  await page.getByRole("button", { name: "Bron toevoegen" }).click();
  const form = page.getByTestId("bron-toevoegen");
  await expect(form.getByTestId("opslaan-en-testen")).toHaveAttribute("aria-disabled", "true");
  await form.getByLabel("Uptime Kuma").check();
  await form.getByLabel("Naam", { exact: true }).fill("Kuma");
  await form.getByLabel("Adres", { exact: true }).fill(st.kuma_url!);
  await form.getByLabel("API-sleutel (voor /metrics)").fill(st.kuma_key!);
  await form.getByTestId("opslaan-en-testen").click();
  await expect(form.getByTestId("bron-testuitkomst")).toContainText("Opgeslagen en uitgelezen", { timeout: 30_000 });
  const kuma = page.getByTestId("bron-Kuma");
  await expect(kuma).toContainText("Uitgelezen om");
  await expect(kuma.locator("[data-status]").first()).toHaveAttribute("data-status", "neutral");
  await expect(kuma).toContainText("••••cdef");
  await expect(page.locator("body")).not.toContainText(st.kuma_key!);

  await form.getByLabel("Beszel").check();
  await form.getByLabel("Naam", { exact: true }).fill("Beszel");
  await form.getByLabel("Adres", { exact: true }).fill(st.beszel_url!);
  await form.getByLabel("Readonly-gebruiker (e-mailadres)").fill(st.beszel_user!);
  await form.getByLabel("Wachtwoord", { exact: true }).fill("Fout-Wachtwoord-123");
  await form.getByTestId("opslaan-en-testen").click();
  await expect(form.getByTestId("bron-testuitkomst")).toContainText("Opgeslagen; uitlezen mislukt", { timeout: 30_000 });
  const beszel = page.getByTestId("bron-Beszel");
  await expect(beszel).toContainText("Uitlezen mislukt");
  await expect(beszel.locator("[data-status]").first()).toHaveAttribute("data-status", "down");

  await page.getByRole("button", { name: "Kanaal toevoegen" }).click();
  const kf = page.getByTestId("kanaal-toevoegen");
  await kf.getByLabel("Naam", { exact: true }).fill("Telefoon");
  await kf.getByLabel("Adres van Gotify").fill(st.gotify_url!);
  await kf.getByLabel("Applicatietoken").fill(st.gotify_token!);
  await kf.getByRole("button", { name: "Kanaal toevoegen" }).click();
  const kanaal = page.getByTestId("kanaal-Telefoon");
  await expect(kanaal).toContainText("Aan");
  await kanaal.getByTestId("testmelding").click();
  await expect(kanaal.getByTestId("testmelding-uitkomst")).toContainText("door Gotify aangenomen");
  await expect(kanaal.getByTestId("testmelding-uitkomst")).toContainText("kan de Hub niet zien");
  await expect(page.getByTestId("out-of-band")).toContainText("Als de hele NAS uitvalt");
  await expectAccessible(page, "instellingen monitoring");
});

test("diensten (H5): koppelcode + vingerafdruk + aftellen; simulator koppelt → ‘Gekoppeld’ (neutraal); rotatie", async ({ page }) => {
  await page.goto("/instellingen/diensten");
  await ready(page);
  const vingerafdruk = await page.getByTestId("vingerafdruk-hub").locator("code").first().textContent();
  expect(vingerafdruk).toMatch(/^[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
  const koppel = page.getByTestId("dienst-koppelen");
  await expect(koppel.getByTestId("koppel-maken")).toHaveAttribute("aria-disabled", "true");

  // Enrollment-token: de drie omgevingsvariabelen met exact deze namen, één keer getoond.
  await koppel.getByLabel("Welke dienst?").selectOption("appstore-en-fork");
  await koppel.getByLabel(/Enrollment-token in het Custom App-formulier/).check();
  await koppel.getByTestId("koppel-maken").click();
  await expect(koppel.getByTestId("env-hub-url")).toContainText("HUB_URL");
  await expect(koppel.getByTestId("env-token").locator("code")).toHaveText(/^enr_/);
  await expect(koppel.getByTestId("env-fingerprint").locator("code")).toHaveText(vingerafdruk!);

  await koppel.getByLabel("Welke dienst?").selectOption("home-control-hub");
  await koppel.getByLabel(/Koppelcode op de statuspagina/).check();
  await koppel.getByTestId("koppel-maken").click();
  const kaart = koppel.getByTestId("koppelcode");
  await expect(kaart).toBeVisible();
  const code = (await kaart.getByTestId("koppelcode-waarde").locator("code").textContent())!.trim();
  await expect(kaart.getByTestId("koppelcode-vingerafdruk").locator("code")).toHaveText(vingerafdruk!);
  await expect(kaart.getByTestId("aftellen")).toContainText(/\d\d:\d\d/);
  await expect(kaart).toContainText("Een nieuwe code maakt deze niet ongeldig.");
  await expectAccessible(page, "diensten met koppelcode");

  const res = await control("/dienst/koppel", { app_id: "home-control-hub", code });
  expect(res.status).toBe(200);
  await expect(kaart.getByTestId("koppeling-gemeld")).toBeVisible({ timeout: 20_000 });
  const dienst = page.getByTestId("dienst-home-control-hub");
  await expect(dienst).toContainText("Gekoppeld");
  await expect(dienst.locator('[data-status="healthy"]')).toHaveCount(0);
  // Contract 1.3 §4.4 (C1.3-ASM-07/16): de vaste leesscopes staan per dienst in de Hub-UI.
  await expect(dienst.getByTestId("dienst-scopes")).toContainText("catalogus.lezen");
  await expect(dienst.getByTestId("dienst-scopes")).not.toContainText("besluiten.lezen");
  // Koppelstatus zoals de dienst hem meldt: zonder gemeten adres eerlijk "onbekend", nooit "gekoppeld" gegokt.
  await dienst.getByTestId("koppelstatus-lezen").click();
  await expect(dienst.getByTestId("koppelstatus-home-control-hub")).toContainText("Koppelstatus onbekend");
  await expect(dienst.getByTestId("koppelstatus-home-control-hub")).toContainText("dienst_adres_onbekend");

  await dienst.getByRole("button", { name: /Rotatie aanvragen/ }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Rotatie aanvragen" }).click();
  await expect(dienst.getByTestId("rotatie-aangevraagd")).toContainText("Rotatie aangevraagd");
});

for (const [uitkomst, code, details] of [
  ["verbindingsfout", "service_unreachable", { reason: "niet_bereikbaar" }],
  ["weigering", "unlink_refused", { status: 403, code: "forbidden" }],
] as const) {
  test(`diensten (H5): ontkoppelen bij ${uitkomst} geeft ook bij herhaling ${code}`, async ({ page }) => {
    expect((await control("/dienst/ontkoppelproef", { uitkomst })).status).toBe(200);
    const poort = Number(new URL(stackState().control_url).port);
    const registratie = await control("/nas/app", {
      naam: "home-control-hub", image: "ghcr.io/lvos04/home-control-hub:0.1.0", poort, container_poort: 30420,
    });
    expect(registratie.status).toBe(200);
    await refreshInventory(page);
    await page.goto("/instellingen/diensten");
    await ready(page);
    const dienst = page.getByTestId("dienst-home-control-hub");
    await dienst.getByRole("button", { name: /Ontkoppelen/ }).click();
    for (let poging = 0; poging < 2; poging++) {
      const antwoord = page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/unlink"));
      await dienst.getByTestId("ontkoppelen-bevestigen").click();
      const res = await antwoord;
      expect(res.status()).toBe(502);
      expect(await res.json()).toMatchObject({ code, details });
      await expect(dienst.getByTestId("error-panel")).toHaveAttribute("data-code", code);
    }
    await page.reload();
    await ready(page);
    await expect(dienst).toContainText("Gekoppeld");
  });
}

test("problemen: 100 identieke events → één incident ×100; hypothese als woord; herstelvoorstel zonder uitvoerknop; oplossen bij actieve bron geweigerd", async ({ page }) => {
  const sent = await control("/dienst/events", { app_id: "home-control-hub", aantal: 100 });
  expect(sent.body.verstuurd).toBe(100);
  await page.goto("/problemen");
  await ready(page);
  const rij = page.getByTestId("incidenten-inbox").locator('[data-testid^="incident-"]', { hasText: "Node-RED" });
  // De worker verwerkt de 100 events in batches; de inbox ververst maar elke 30 s. Wacht dus (met herladen) tot alle
  // 100 meetellen, anders is "×32" een wedloop in de test en geen fout in de Hub.
  await expect(async () => {
    await page.reload();
    await expect(rij).toBeVisible({ timeout: 2_000 });
    await expect(rij).toContainText("×100", { timeout: 2_000 });
  }).toPass({ timeout: 90_000 });
  await expect(rij).toContainText("Kritiek");
  await rij.click();
  await ready(page);
  const detail = page.getByTestId("incident-detail");
  await expect(detail).toBeVisible();
  saveP1State({ incident_id: page.url().split("/problemen/")[1] });
  await expect(detail.getByTestId("hypothese")).toContainText("Ik weet het niet");
  await expect(detail.getByTestId("hypothese")).not.toContainText("%");
  await detail.getByTestId("bewijs").locator("summary").click();
  await expect(detail.getByTestId("bewijs")).toContainText("Regel");
  await detail.getByRole("button", { name: "Onderzoek" }).click();
  await expect(detail.getByTestId("stappenplan")).toContainText("Observeren");
  await detail.getByRole("button", { name: "Herstel voorstellen" }).click();
  await expect(detail.getByTestId("herstelvoorstel")).toBeVisible();
  await expect(detail.getByRole("button", { name: /Uitvoeren|Goedkeuring aanvragen/ })).toHaveCount(0);
  await expectAccessible(page, "incidentdetail");

  // De monitoringbron Beszel faalt nog (readback actief) → oplossen wordt geweigerd met nog_actief.
  await page.goto("/problemen");
  await ready(page);
  const bron = page.getByTestId("incidenten-inbox").locator('[data-testid^="incident-"]', { hasText: "Beszel" });
  await expect(async () => {
    await page.reload();
    await expect(bron).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 60_000 });
  await bron.click();
  await ready(page);
  await page.getByLabel("Reden van oplossen").fill("test vanuit de UI");
  await page.getByTestId("oplossen").click();
  await expect(page.getByTestId("nog-actief")).toContainText("Oplossen kan niet");
  await expect(page.getByTestId("nog-actief")).toContainText("meldt het probleem nog");
});

test("noodaccount (H6): geheim één keer, foute code → veldfout, goede code → werkt; zelftest toont bron-IP; noodlogin vanaf 127.0.0.1 geweigerd", async ({ page, browser }) => {
  await page.goto("/instellingen/noodaccount");
  await ready(page);
  await expect(page.getByTestId("nood-werkt-niet")).toContainText("er is nog geen noodaccount ingesteld");
  const form = page.getByTestId("noodaccount-instellen");
  await form.getByLabel("Je eigen wachtwoord").fill(ADMIN.password);
  await form.getByLabel("Gebruikersnaam van het noodaccount").fill(NOOD.username);
  await form.getByLabel("Nieuw noodwachtwoord").fill(NOOD.password);
  await form.getByTestId("nood-volgende").click();
  const stap = page.getByTestId("totp-stap");
  await expect(stap).toContainText("Dit geheim zie je maar één keer");
  const geheim = (await stap.getByTestId("totp-geheim").locator("code").getAttribute("data-waarde"))!;
  expect(geheim).toMatch(/^[A-Z2-7]{16,}$/);
  await expect(stap.getByTestId("totp-uri").locator("code")).toContainText("otpauth://totp/");
  await stap.getByLabel("Code uit de authenticator-app").fill("000000");
  await stap.getByTestId("totp-bevestigen").click();
  await expect(stap).toContainText("Deze code klopt niet");
  await stap.getByLabel("Code uit de authenticator-app").fill(totp(geheim));
  await stap.getByTestId("totp-bevestigen").click();
  await expect(page.getByTestId("nood-werkt")).toBeVisible();
  await expect(page.getByTestId("noodaccount-status")).toContainText("Ingesteld");
  // Het geheim is na bevestigen (en na herladen) niet meer te zien.
  await page.reload();
  await ready(page);
  await expect(page.getByTestId("totp-stap")).toHaveCount(0);
  await expect(page.locator("body")).not.toContainText(geheim);
  await expect(page.getByTestId("noodaccount-instellen")).toContainText("Bewaar beide voordat je uitlogt.");

  await page.getByTestId("zelftest-uitvoeren").click();
  await expect(page.getByTestId("zelftest-samenvatting")).toContainText("noodlogin werkt nu");
  const bronIp = page.getByTestId("zelftest-controles").locator('[data-controle="bron_ip"]');
  await expect(bronIp).toContainText("127.0.0.1");
  await expect(bronIp).toHaveAttribute("data-uitkomst", "beleid");
  // Contract 1.3 §4.1 (C1.3-ASM-05): 100.64.0.0/10 telt standaard niet als privé; de zelftest toont het.
  const cgnatControle = page.getByTestId("zelftest-controles").locator('[data-controle="bereik_cgnat"]');
  await expect(cgnatControle).toHaveAttribute("data-uitkomst", "beleid");
  const cgnat = page.getByTestId("noodaccount-cgnat");
  await expect(cgnat.getByTestId("cgnat-stand")).toContainText("Telt niet als privé");
  await expect(cgnat).toContainText("Tailscale niet met anderen deelt");
  await expect(cgnat.getByTestId("cgnat-aan")).toHaveAttribute("aria-disabled", "true");
  await expectAccessible(page, "noodaccount");
  // Een beheerder kan het toestaan (na bevestigen) en weer uitzetten; de zelftest volgt de instelling.
  await cgnat.getByTestId("cgnat-bevestig").check();
  await cgnat.getByTestId("cgnat-aan").click();
  await expect(cgnat.getByTestId("cgnat-stand")).toContainText("Telt als privé");
  await page.getByTestId("zelftest-uitvoeren").click();
  await expect(cgnatControle).toHaveAttribute("data-uitkomst", "ok");
  await cgnat.getByTestId("cgnat-uit").click();
  await expect(cgnat.getByTestId("cgnat-stand")).toContainText("Telt niet als privé");

  const ctx = await browser.newContext({ storageState: undefined });
  const p = await ctx.newPage();
  await p.goto("/inloggen");
  await p.getByRole("link", { name: "Noodlogin (alleen vanaf je eigen netwerk)" }).click();
  await expect(p).toHaveURL(/\/inloggen\/nood$/);
  await p.getByLabel("Gebruikersnaam").fill(NOOD.username);
  await p.getByLabel("Wachtwoord").fill(NOOD.password);
  await p.getByLabel("Code uit de authenticator-app").fill(totp(geheim));
  await p.getByRole("button", { name: "Noodlogin" }).click();
  await expect(p.getByTestId("error-panel")).toHaveAttribute("data-code", "source_not_private");
  await expect(p.getByTestId("error-panel")).toContainText("Noodlogin kan alleen vanaf je eigen netwerk");
  await expectAccessible(p, "noodlogin");
  await ctx.close();
});

test.describe("SSO via HTTPS", () => {
  test.skip(Boolean(process.env.HUB_E2E_BASE_URL), "TLS-proef vereist de eigen teststack met vertrouwde testproxy.");

  test("SSO: gate zichtbaar zonder D17, issuer gecontroleerd, testlogin tegen de fake-issuer zonder sessie, ‘OIDC verplicht’ uit", async ({ page: httpPage, browser }) => {
    await httpPage.goto("/instellingen/toegang");
    await ready(httpPage);
    await expect(httpPage.locator("#sso-geheim")).toHaveCount(0);
    await expect(httpPage.getByTestId("sso")).toContainText("invoeren kan alleen via HTTPS");
    const tls = await startTlsHub(new URL(httpPage.url()).origin);
    const context = await browser.newContext({ storageState: ADMIN_STATE, ignoreHTTPSErrors: true, baseURL: tls.url });
    try {
      const page = await context.newPage();
      const st = stackState();
      await page.goto("/instellingen/toegang");
      await ready(page);
      const sso = page.getByTestId("sso");
      await sso.getByLabel("Issuer-adres").fill(st.oidc_issuer!);
      await sso.getByLabel("Client-ID").fill(st.oidc_client_id!);
      await sso.getByLabel("Clientgeheim").fill(st.oidc_client_secret!);
      await sso.getByLabel("Groep 1").fill("hub-admins");
      await sso.getByLabel("Rol 1").selectOption("admin");
      await page.route("**/api/v1/auth/oidc", (route) => route.request().method() === "PUT" ? route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "testfout", message: "Tijdelijke testfout" }) }) : route.continue());
      await sso.getByTestId("sso-opslaan").click();
      await expect(sso.getByTestId("error-panel")).toBeVisible();
      await expect(sso.locator("#sso-geheim")).toHaveValue("");
      await page.unroute("**/api/v1/auth/oidc");
      await sso.locator("#sso-geheim").fill(st.oidc_client_secret!);
      await sso.getByTestId("sso-opslaan").click();
      await expect(sso.locator("#sso-geheim")).toHaveValue("");
      await expect(sso.getByTestId("sso-controleren")).toBeVisible();
      await sso.getByTestId("sso-controleren").click();
      await expect(sso.getByTestId("sso-controles").locator('[data-controle="sleutels"]')).toHaveAttribute("data-uitkomst", "ok");
      await expect(sso.getByTestId("sso-gate")).toContainText("D17");
      await expect(sso.getByRole("button", { name: "SSO aanzetten" })).toHaveAttribute("aria-disabled", "true");
      await expect(sso.getByTestId("oidc-verplicht")).toHaveAttribute("aria-disabled", "true");
      await sso.getByTestId("sso-testlogin").click();
      await page.waitForURL(/\/api\/v1\/auth\/oidc\/callback/, { timeout: 20_000 });
      await expect(page.locator("body")).toContainText("Testlogin klaar", { timeout: 20_000 });
      await page.goto("/instellingen/toegang");
      await ready(page);
      await expect(page.getByTestId("sso-testuitkomst")).toContainText("Geslaagd");
      await expect(page.getByTestId("sso-testuitkomst")).toContainText("Er is geen sessie gemaakt");
      await expectAccessible(page, "toegang en SSO");
      await expect(page.locator("#sso-geheim")).toHaveValue("");
    } finally {
      await context.close();
      await tls.close();
    }
  });
});
