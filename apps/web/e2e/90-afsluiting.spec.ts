/**
 * Afsluitende scenario's (desktop): NAS offline → onbekend/verouderd (nooit groen), browser offline met service
 * worker, rolrechten (kijker kan niets wijzigen), client-IP niet te vervalsen via X-Forwarded-For, en nog steeds
 * geen enkele schrijfaanroep op de (fake) NAS.
 */
import { expect, request as pwRequest, test } from "@playwright/test";
import { ADMIN, KIND, VIEWER, expectAccessible, nasMutations, ready, setNas, shot, stackState } from "./helpers";

test.describe.configure({ mode: "serial" });

test("NAS offline: vernieuwen faalt eerlijk, inventaris wordt verouderd/onbekend en Home toont ‘onbekend’", async ({ page }, info) => {
  await setNas(false);
  try {
    await page.goto("/server");
    await ready(page);
    await page.getByTestId("inventaris-vernieuwen").click();
    await expect(page.getByTestId("vernieuwen-status")).toContainText("niet volledig gelukt", { timeout: 60_000 });
    await expect(page.getByTestId("sectie-pools")).toContainText("Verouderd");
    await expect(page.getByTestId("onbekend-pools")).toContainText("unreachable");
    // O-03: de laatst bekende pool blijft zichtbaar (gedempt), maar nooit meer als gezond.
    await expect(page.getByTestId("sectie-pools")).toContainText("testpool");
    await expect(page.getByTestId("sectie-pools").locator('[data-status="healthy"]')).toHaveCount(0);
    await shot(page, info, "server-nas-offline");
    await page.goto("/");
    await ready(page);
    await expect(page.getByTestId("kaart-opslag")).toContainText("Laatst bekend");
    await expect(page.getByTestId("kaart-opslag")).toContainText("Verouderd");
    await expect(page.getByTestId("waarde-opslag")).toContainText("laatst bekende waarde, verouderd");
    await expect(page.getByTestId("kaart-opslag").locator('[data-status="healthy"]')).toHaveCount(0);
    await expect(page.getByTestId("totaalstatus")).not.toContainText("Alles gezond");
    await shot(page, info, "home-nas-offline");
  } finally {
    await setNas(true);
  }
  await page.goto("/server");
  await ready(page);
  await page.getByTestId("inventaris-vernieuwen").click();
  await expect(page.getByTestId("vernieuwen-status")).toHaveText("Inventaris vernieuwd.", { timeout: 60_000 });
  await expect(page.getByTestId("sectie-pools")).toContainText("Gezond");
});

test("browser offline: duidelijke offline-status; app-schil uit de service worker, gegevens onbekend", async ({ page, context }) => {
  await page.goto("/instellingen/apparaat");
  await ready(page);
  await expect(page.getByTestId("pwa-status")).toHaveAttribute("data-state", "actief", { timeout: 30_000 });
  await page.goto("/server");
  await ready(page);
  await context.setOffline(true);
  try {
    await expect(page.getByTestId("offline-banner")).toBeVisible();
    await expect(page.getByTestId("offline-banner")).toContainText("Gegevens zijn niet actueel");
    // Herladen terwijl offline: de bewaarde schil laadt, maar gegevens blijven onbekend (nooit uit een oude kopie).
    await page.reload();
    await expect(page.getByTestId("offline-banner")).toBeVisible();
    await expect(page.getByTestId("error-panel")).toContainText("Geen verbinding met de Hub");
    // Een nog nooit bezochte pagina: de offlinepagina.
    await page.goto("/kosten");
    await expect(page.getByTestId("offline-pagina")).toContainText("Geen verbinding met de Hub");
  } finally {
    await context.setOffline(false);
  }
  await page.goto("/server");
  await ready(page);
  await expect(page.getByTestId("offline-banner")).toHaveCount(0);
  await expect(page.getByTestId("sectie-pools")).toContainText("Gezond");
});

test("rolrechten: beheerder maakt een kijker; de kijker kan niets invullen, meten of koppelen", async ({ page, browser }) => {
  // Oud anker: /instellingen#gebruikers stuurt door naar de subpagina.
  await page.goto("/instellingen#gebruikers");
  await expect(page).toHaveURL(/\/instellingen\/toegang$/);
  await ready(page);
  const users = page.getByTestId("gebruikers");
  await users.getByRole("button", { name: "Gebruiker toevoegen" }).click();
  await users.getByLabel("Gebruikersnaam").fill(VIEWER.username);
  await users.getByLabel("Eerste wachtwoord").fill(VIEWER.password);
  await expect(users.getByRole("button", { name: "Gebruiker aanmaken" })).toHaveAttribute("aria-disabled", "true");
  await users.getByLabel(/^Kijker/).check();
  await users.getByRole("button", { name: "Gebruiker aanmaken" }).click();
  await expect(users).toContainText(`Gebruiker ${VIEWER.username} aangemaakt.`);

  const ctx = await browser.newContext({ storageState: undefined, extraHTTPHeaders: { "X-Forwarded-For": "203.0.113.9" } });
  const v = await ctx.newPage();
  await v.goto("/inloggen");
  await v.getByLabel("Gebruikersnaam").fill(VIEWER.username);
  await v.getByLabel("Wachtwoord").fill(VIEWER.password);
  await v.getByRole("button", { name: "Inloggen" }).click();
  await expect(v).toHaveURL(/\/$/);
  await ready(v);
  await v.goto("/onboarding/besluit/D03");
  await ready(v);
  await expect(v.getByText("Invullen kan alleen een beheerder.")).toBeVisible();
  await expect(v.getByTestId("opslaan")).toHaveCount(0);
  await expect(v.getByTestId("meten")).toHaveCount(0);
  await expect(v.getByText("Meten kan vanaf de rol operator.")).toBeVisible();
  await v.goto("/onboarding/truenas");
  await ready(v);
  await expect(v.getByTestId("key-opslaan")).toHaveCount(0);
  await expect(v.getByTestId("verbinding-testen")).toHaveCount(0);
  await v.goto("/server");
  await ready(v);
  await expect(v.getByTestId("inventaris-vernieuwen")).toHaveCount(0);
  await expectAccessible(v, "server als kijker");
  // Diensten en noodaccount: kijker ziet geen koppel-, rotatie- of intrekknoppen (RolMelding).
  await v.goto("/instellingen/diensten");
  await ready(v);
  await expect(v.getByTestId("rolmelding")).toBeVisible();
  await expect(v.getByTestId("dienst-koppelen")).toHaveCount(0);
  await expect(v.getByRole("button", { name: /Intrekken|Ontkoppelen|Rotatie/ })).toHaveCount(0);
  await v.goto("/instellingen/noodaccount");
  await ready(v);
  await expect(v.getByTestId("rolmelding")).toBeVisible();
  await expect(v.getByTestId("noodaccount-instellen")).toHaveCount(0);
  // Incidenten: kijker kan lezen maar niet erkennen of oplossen.
  await v.goto("/problemen");
  await ready(v);
  await expect(v.getByTestId("incidenten-inbox")).toBeVisible();
  await expect(v.getByTestId("oplossen")).toHaveCount(0);
  // De API weigert het ook (niet alleen de UI): rechtstreekse schrijfpoging als kijker → 403.
  const res = await v.evaluate(async () => {
    const csrf = document.cookie.split("; ").find((c) => c.startsWith("hub_csrf="))?.split("=")[1] ?? "";
    const r = await fetch("/api/v1/truenas/api-key", {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ api_key: "kijker-probeert-dit-0123456789" }),
    });
    return { status: r.status, body: await r.json() };
  });
  expect(res.status).toBe(403);
  expect(res.body.code).toBe("forbidden");
  // Een vervalste X-Forwarded-For van de browser wordt niet overgenomen: de sessie toont het echte adres.
  await v.goto("/instellingen#sessies");
  await expect(v).toHaveURL(/\/instellingen\/account$/);
  await ready(v);
  await expect(v.getByTestId("sessies")).toContainText("127.0.0.1");
  await expect(v.getByTestId("sessies")).not.toContainText("203.0.113.9");
  await ctx.close();
});

test("kind (O-05): eigen schil Home · Kijken · Zoeken · Ik, geen zijbalk of systeemstatus; beheerroutes kindvriendelijk 403", async ({ page, browser }, info) => {
  await page.goto("/instellingen/toegang");
  await ready(page);
  const users = page.getByTestId("gebruikers");
  await users.getByRole("button", { name: "Gebruiker toevoegen" }).click();
  await users.getByLabel("Gebruikersnaam").fill(KIND.username);
  await users.getByLabel("Eerste wachtwoord").fill(KIND.password);
  await users.getByLabel(/^Kind/).check();
  await users.getByRole("button", { name: "Gebruiker aanmaken" }).click();
  await expect(users).toContainText(`Gebruiker ${KIND.username} aangemaakt.`);

  for (const width of [390, 1440]) {
    const ctx = await browser.newContext({ storageState: undefined, viewport: { width, height: 900 } });
    const k = await ctx.newPage();
    await k.goto("/inloggen");
    await k.getByLabel("Gebruikersnaam").fill(KIND.username);
    await k.getByLabel("Wachtwoord").fill(KIND.password);
    await k.getByRole("button", { name: "Inloggen" }).click();
    await expect(k.getByTestId("kind-home")).toBeVisible();
    await expect(k.getByTestId("kind-nav").getByRole("link")).toHaveText(["Home", "Kijken", "Zoeken", "Ik"]);
    await expect(k.getByTestId("sidebar")).toHaveCount(0);
    await expect(k.getByTestId("systeemstatus")).toHaveCount(0);
    await expect(k.locator("body")).not.toContainText("Problemen");
    await expectAccessible(k, `kind home ${width}`);
    if (width === 390) await shot(k, info, "kind-home");
    await k.goto("/server");
    await expect(k.getByTestId("kind-403")).toContainText("Dit scherm is niet voor jou");
    await expectAccessible(k, `kind 403 ${width}`);
    await k.getByTestId("kind-nav").getByRole("link", { name: "Kijken" }).click();
    await expect(k.locator("main h1")).toHaveText("Kijken");
    // De API weigert kind zelf ook (de UI is nooit de poortwachter).
    const status = await k.evaluate(async () => (await fetch("/api/v1/inventory")).status);
    expect(status).toBe(403);
    await ctx.close();
  }
});

test("diensten: intrekken pas na het typen van de app-id; daarna ‘Ingetrokken’ (neutraal)", async ({ page }) => {
  await page.goto("/instellingen/diensten");
  await ready(page);
  const dienst = page.getByTestId("dienst-home-control-hub");
  await dienst.getByRole("button", { name: /Intrekken/ }).click();
  const blok = dienst.getByTestId("intrek-blok");
  await expect(blok.getByTestId("intrekken-bevestigen")).toHaveAttribute("aria-disabled", "true");
  await blok.getByLabel("Typ home-control-hub om te bevestigen.").fill("home-control");
  await expect(blok.getByTestId("intrekken-bevestigen")).toHaveAttribute("aria-disabled", "true");
  await blok.getByLabel("Typ home-control-hub om te bevestigen.").fill("home-control-hub");
  await blok.getByTestId("intrekken-bevestigen").click();
  await expect(page.getByTestId("dienst-home-control-hub")).toHaveCount(0);
  await page.getByLabel(/Ingetrokken diensten tonen/).check();
  await expect(page.getByTestId("dienst-home-control-hub")).toContainText("Ingetrokken");
  await expect(page.getByTestId("dienst-home-control-hub").locator('[data-status="healthy"]')).toHaveCount(0);
});

test("executor koppelen via de eigen statuspagina, echt verstuurd in de browser (§3.9; review N-01)", async ({ page, browser, baseURL }) => {
  const st = stackState();
  // Tegen de alles-in-één image (HUB_E2E_BASE_URL) start de teststack geen executor; de rooktest dekt die image.
  test.skip(!st.executor_url && Boolean(process.env.HUB_E2E_BASE_URL), "geen executor in de stack tegen de image");
  expect(st.executor_url, "de teststack hoort de executor te starten").toBeTruthy();
  const executorUrl = st.executor_url!;
  // Hub: koppelcode (30 min) + vingerafdruk via de onboarding, zoals de beheerder dat doet.
  await page.goto("/onboarding/executor");
  await ready(page);
  await page.getByTestId("executor-koppelcode-maken").click();
  const code = await page.getByTestId("koppelcode-waarde").locator("code").getAttribute("data-waarde");
  const vinger = await page.getByTestId("koppelcode-vingerafdruk").locator("code").getAttribute("data-waarde");
  expect(code).toMatch(/^[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}$/);
  expect(vinger).toMatch(/^[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}$/);

  // Executor-statuspagina in een eigen context (geen Hub-sessie), zoals in een nieuw tabblad.
  const ctx = await browser.newContext({ locale: "nl-NL" });
  try {
    const ex = await ctx.newPage();
    const origins: string[] = [];
    ex.on("request", (r) => {
      if (r.method() === "POST") void r.allHeaders().then((h) => origins.push(h["origin"] ?? "(geen)"));
    });
    const eerste = await ex.goto(`${executorUrl}/`);
    expect(eerste?.headers()["referrer-policy"]).toBe("same-origin");
    await expect(ex.getByRole("heading", { name: "Koppelen" })).toBeVisible();
    // Contract 1.3 §3.7 punt 6: negatieve gevallen tegen de echte executor, met de echte formuliercode en cookie van
    // deze browsercontext. Elk geweigerd verzoek → 403, gaat niet naar de Hub en telt niet als poging.
    const csrf = await ex.locator('input[name="csrf"]').getAttribute("value");
    const form = { csrf: csrf!, hub_adres: baseURL!, koppelcode: code!, hub_vingerafdruk: vinger! };
    const weiger = async (headers: Record<string, string>, via = ctx.request) => {
      const r = await via.post(`${executorUrl}/koppelen`, { form, headers, maxRedirects: 0 });
      return { status: r.status(), tekst: await r.text() };
    };
    for (const [naam, headers] of [
      ["Origin: null", { Origin: "null" }],
      ["vreemde Origin", { Origin: "http://aanvaller.invalid" }],
      ["Sec-Fetch-Site: same-site", { Origin: executorUrl, "Sec-Fetch-Site": "same-site" }],
      ["Sec-Fetch-Site: cross-site", { Origin: executorUrl, "Sec-Fetch-Site": "cross-site" }],
    ] as const) {
      const r = await weiger(headers);
      expect(r.status, naam).toBe(403);
      expect(r.tekst, naam).toContain("herkomst_onjuist");
    }
    // Niet-toegestane Host (DNS-rebinding: Origin = Host = een publieke naam).
    const port = new URL(executorUrl).port;
    const host = await weiger({ Host: `rebind.example.com:${port}`, Origin: `http://rebind.example.com:${port}` });
    expect(host.status).toBe(403);
    expect(host.tekst).toContain("host_niet_toegestaan");
    // Geen cookie: een losse context zonder de formuliercookie.
    const zonderCookie = await pwRequest.newContext();
    try {
      const r = await weiger({ Origin: executorUrl }, zonderCookie);
      expect(r.status).toBe(403);
      expect(r.tekst).toContain("formuliercode_onjuist");
    } finally {
      await zonderCookie.dispose();
    }
    // Elk antwoord zette een nieuwe formuliercookie in deze context: laad de pagina opnieuw, zoals een gebruiker.
    await ex.goto(`${executorUrl}/`);
    await expect(ex.getByRole("heading", { name: "Koppelen" })).toBeVisible();
    // Eerst een verkeerde vingerafdruk: de executor koppelt niet en zegt waarom (veldfout), niets opgeslagen.
    await ex.getByLabel("Adres van de Hub").fill(baseURL!);
    await ex.getByLabel("Koppelcode").fill(code!);
    await ex.getByLabel("Vingerafdruk van de Hub").fill("AAAA-BBBB-CCCC-DDDD");
    await ex.getByRole("button", { name: "Koppelen met de Hub" }).click();
    await expect(ex.locator("#vinger-fout")).toBeVisible();
    await expect(ex.getByRole("heading", { name: "Koppelen" })).toBeVisible();
    // Daarna de juiste vingerafdruk met dezelfde code: de code is pas na een geslaagde koppeling verbruikt.
    await ex.getByLabel("Adres van de Hub").fill(baseURL!);
    await ex.getByLabel("Koppelcode").fill(code!);
    await ex.getByLabel("Vingerafdruk van de Hub").fill(vinger!);
    await ex.getByRole("button", { name: "Koppelen met de Hub" }).click();
    await expect(ex.locator("body")).toContainText("Gekoppeld met de Hub");
    // Het formulier is weg na de eerste koppeling (§3.7); de vingerafdruk staat ter vergelijking op de pagina.
    await ex.goto(`${executorUrl}/`);
    await expect(ex.getByRole("heading", { name: "Koppelen" })).toHaveCount(0);
    await expect(ex.locator("body")).toContainText(vinger!);
    // De browser stuurde bij beide POST's de echte oorsprong mee, nooit `null` (N-01).
    await expect.poll(() => origins.length).toBe(2);
    expect(new Set(origins)).toEqual(new Set([executorUrl]));
  } finally {
    await ctx.close();
  }
  // De Hub ziet de executor als gekoppeld (neutraal, geen groen: koppelen zegt niets over gezondheid).
  await expect(page.getByTestId("koppeling-gemeld")).toBeVisible({ timeout: 30_000 });
  await page.reload();
  await ready(page);
  await expect(page.getByTestId("executor-koppelen")).toContainText("Gekoppeld");
  await expect(page.getByTestId("executor-koppelen").locator('[data-status="healthy"]')).toHaveCount(0);
});

test("na alle scenario’s: geen enkele schrijfaanroep op de NAS; uitloggen sluit de sessie", async ({ page }) => {
  expect(await nasMutations()).toEqual([]);
  await page.goto("/instellingen/account");
  await ready(page);
  await page.getByTestId("uitloggen-instellingen").click();
  await expect(page).toHaveURL(/\/inloggen$/);
  const me = await page.evaluate(async () => (await fetch("/api/v1/auth/me")).status);
  expect(me).toBe(401);
  expect(ADMIN.username).toBe("beheerder");
});
