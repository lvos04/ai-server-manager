/**
 * Opzet (één keer, desktop): eerste start met setupcode, inloggen/uitloggen, TrueNAS-koppeling via de UI met
 * vingerafdrukbevestiging, inventaris en metingen — allemaal tegen de echte Hub-API en de fake TrueNAS (Sim-getest).
 */
import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { ADMIN, ADMIN_STATE, expectAccessible, nasMutations, ready, setupCode, shot, stackState } from "./helpers";

test.describe.configure({ mode: "serial" });

test("eerste start: zonder beheerder naar ‘Eerste start’ met uitleg waar de setupcode staat", async ({ page }, info) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/eerste-start$/);
  await expect(page.getByRole("heading", { name: "Eerste start" })).toBeVisible();
  const uitleg = page.getByTestId("setupcode-uitleg");
  await expect(uitleg).toContainText("Apps");
  await expect(uitleg).toContainText("ai-server-manager");
  await expect(uitleg).toContainText("Logs");
  await expectAccessible(page, "eerste start");
  await shot(page, info, "eerste-start");
});

test("eerste start: verkeerde setupcode geeft een gerichte Nederlandse fout", async ({ page }) => {
  await page.goto("/eerste-start");
  await page.getByLabel("Setupcode").fill("AAAA-BBBB-CCCC");
  await page.getByLabel("Gebruikersnaam").fill(ADMIN.username);
  await page.getByLabel("Wachtwoord", { exact: true }).fill(ADMIN.password);
  await page.getByLabel("Wachtwoord herhalen").fill(ADMIN.password);
  await page.getByRole("button", { name: "Beheerder aanmaken" }).click();
  await expect(page.getByTestId("error-panel")).toContainText("Setupcode onjuist of verlopen");
  await expect(page.getByTestId("error-panel")).toHaveAttribute("data-code", "invalid_setup_code");
});

test("eerste start: zwak wachtwoord wordt al in de UI geweigerd", async ({ page }) => {
  await page.goto("/eerste-start");
  await page.getByLabel("Setupcode").fill(setupCode());
  await page.getByLabel("Gebruikersnaam").fill(ADMIN.username);
  await page.getByLabel("Wachtwoord", { exact: true }).fill("kort");
  await page.getByLabel("Wachtwoord herhalen").fill("kort");
  await page.getByRole("button", { name: "Beheerder aanmaken" }).click();
  await expect(page.locator("#wachtwoord-fout")).toHaveText("Minstens 12 tekens.");
  await expect(page).toHaveURL(/\/eerste-start$/);
});

test("eerste start: juiste setupcode maakt de beheerder en opent de onboarding", async ({ page }) => {
  await page.goto("/eerste-start");
  await page.getByLabel("Setupcode").fill(setupCode());
  await page.getByLabel("Gebruikersnaam").fill(ADMIN.username);
  await page.getByLabel("Weergavenaam (optioneel)").fill("Beheerder");
  await page.getByLabel("Wachtwoord", { exact: true }).fill(ADMIN.password);
  await page.getByLabel("Wachtwoord herhalen").fill(ADMIN.password);
  await page.getByRole("button", { name: "Beheerder aanmaken" }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
  await ready(page);
  await expect(page.getByRole("heading", { name: "Onboarding", level: 1 })).toBeVisible();
  // Alleen D10 is vooraf ingevuld (vast besluit); er staan geen voorbeeldwaarden.
  await expect(page.getByTestId("besluit-D10")).toContainText("Ingevuld");
  await expect(page.getByTestId("besluit-D03")).toContainText("Open");
  // Na de setup is de eerste-startpagina dicht.
  await page.goto("/eerste-start");
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("uitloggen en weer inloggen (met foute en goede gegevens)", async ({ page }) => {
  // Nieuwe context (niet aangemeld): de eerste-startpagina zegt dat de setup klaar is en verwijst naar inloggen.
  await page.goto("/eerste-start");
  await expect(page.getByRole("heading", { name: "Eerste start is al afgerond" })).toBeVisible();
  await page.getByRole("link", { name: "Naar inloggen" }).click();
  await expect(page).toHaveURL(/\/inloggen$/);
  await page.getByLabel("Gebruikersnaam").fill(ADMIN.username);
  await page.getByLabel("Wachtwoord").fill("Fout-Wachtwoord-123456");
  await page.getByRole("button", { name: "Inloggen" }).click();
  await expect(page.getByTestId("error-panel")).toContainText("Gebruikersnaam of wachtwoord onjuist");
  await page.getByLabel("Wachtwoord").fill(ADMIN.password);
  await page.getByRole("button", { name: "Inloggen" }).click();
  await expect(page).toHaveURL(/\/$/);
  await ready(page);
  await page.getByTestId("gebruikersmenu").click();
  await page.getByTestId("logout").click();
  await expect(page).toHaveURL(/\/inloggen$/);
  await page.goto("/server");
  await expect(page).toHaveURL(/\/inloggen\?terug=%2Fserver$/);
  await page.getByLabel("Gebruikersnaam").fill(ADMIN.username);
  await page.getByLabel("Wachtwoord").fill(ADMIN.password);
  await page.getByRole("button", { name: "Inloggen" }).click();
  await expect(page).toHaveURL(/\/server$/);
  mkdirSync(path.dirname(ADMIN_STATE), { recursive: true });
  await page.context().storageState({ path: ADMIN_STATE });
});

test.describe("met beheerderssessie", () => {
  test.use({ storageState: ADMIN_STATE });

  test("vóór de koppeling: Home toont alles als onbekend, nooit groen", async ({ page }, info) => {
    await page.goto("/");
    await ready(page);
    await expect(page.getByTestId("totaalstatus")).not.toContainText("In orde");
    await expect(page.getByTestId("waarde-opslag")).toHaveText("onbekend");
    await expect(page.getByTestId("waarde-apps")).toHaveText("onbekend");
    await expect(page.getByTestId("acties")).toContainText("TrueNAS koppelen");
    await shot(page, info, "home-voor-koppeling");
  });

  test("TrueNAS-koppeling: adres, foute key, vingerafdruk bevestigen, gerichte fout, juiste key, verbonden", async ({ page }, info) => {
    const st = stackState();
    await page.goto("/onboarding/truenas");
    await ready(page);
    await expect(page.getByTestId("koppeling-status")).toContainText("NAS-adres ontbreekt");
    // Geen voorbeeldwaarden: het adresveld is leeg.
    await expect(page.getByLabel("NAS-adres (LAN-IP of hostnaam)")).toHaveValue("");
    // Ongeldige invoer (met https://) wordt in de UI geweigerd.
    await page.getByLabel("NAS-adres (LAN-IP of hostnaam)").fill("https://127.0.0.1");
    await page.getByTestId("adres-opslaan").click();
    await expect(page.getByText("Alleen het adres, zonder https:// en zonder pad.")).toBeVisible();
    // Simulator-adres (fake TrueNAS op deze machine).
    await page.getByLabel("NAS-adres (LAN-IP of hostnaam)").fill("127.0.0.1");
    await page.getByLabel("HTTPS-poort (optioneel)").fill(String(st.fake_nas_port));
    await page.getByTestId("adres-opslaan").click();
    await expect(page.getByTestId("nas-url")).toHaveText(`wss://127.0.0.1:${st.fake_nas_port}/api/current`);

    // Een key die TrueNAS niet kent.
    await page.getByLabel("API-key (alleen-lezen)").fill("onbekende-key-0123456789abcdef");
    await page.getByTestId("key-opslaan").click();
    await expect(page.getByTestId("key-status")).toContainText("cdef");
    await expect(page.locator("body")).not.toContainText("onbekende-key-0123456789abcdef");

    // Zelfondertekend certificaat: eerst vingerafdruk bevestigen; de key wordt vóór vertrouwen niet verstuurd.
    await page.getByTestId("verbinding-testen").click();
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "tls_untrusted");
    await expect(page.getByTestId("vingerafdruk")).toHaveText(/^([0-9A-F]{2}:){31}[0-9A-F]{2}$/);
    await expect(page.getByTestId("vingerafdruk-vertrouwen")).toBeDisabled();
    await expectAccessible(page, "TrueNAS-koppeling met vingerafdruk");
    await shot(page, info, "truenas-vingerafdruk");
    await page.getByTestId("vingerafdruk-gecontroleerd").check();
    await page.getByTestId("vingerafdruk-vertrouwen").click();

    // Daarna: TrueNAS weigert de key → gerichte fout met NL-advies (B01-001-acceptatie).
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "auth_failed");
    await expect(page.getByTestId("test-resultaat")).toContainText("TrueNAS weigerde de API-key");
    await expect(page.getByTestId("test-resultaat")).toContainText("READONLY_ADMIN");

    // Juiste alleen-lezen-key.
    await page.getByLabel("Nieuwe API-key (vervangt de huidige)").fill(st.readonly_key);
    await page.getByTestId("key-opslaan").click();
    await expect(page.getByTestId("key-status")).toContainText(st.readonly_key.slice(-4));
    await page.getByTestId("verbinding-testen").click();
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "ok");
    await expect(page.getByTestId("test-resultaat")).toContainText("alleen-lezen");
    await expect(page.getByTestId("koppeling-status")).toContainText("Verbonden (alleen-lezen)");
    await shot(page, info, "truenas-verbonden");
  });

  test("key met schrijfrechten wordt geweigerd (key_too_privileged)", async ({ page }) => {
    const st = stackState();
    await page.goto("/onboarding/truenas");
    await ready(page);
    await page.getByLabel("Nieuwe API-key (vervangt de huidige)").fill(st.write_key);
    await page.getByTestId("key-opslaan").click();
    // Eerst wachten tot de key echt is opgeslagen; anders test de knop soms nog de vorige key (wedloop in de test).
    await expect(page.getByTestId("key-status")).toContainText(st.write_key.slice(-4));
    await page.getByTestId("verbinding-testen").click();
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "key_too_privileged");
    // Terug naar de alleen-lezen-key.
    await page.getByLabel("Nieuwe API-key (vervangt de huidige)").fill(st.readonly_key);
    await page.getByTestId("key-opslaan").click();
    await expect(page.getByTestId("key-status")).toContainText(st.readonly_key.slice(-4));
    await page.getByTestId("verbinding-testen").click();
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "ok");
  });

  test("inventaris ophalen en metingen D01, D03, D06, D07 (alleen-lezen)", async ({ page }) => {
    await page.goto("/onboarding/truenas");
    await ready(page);
    await page.getByTestId("verbinding-testen").click();
    await expect(page.getByTestId("test-resultaat")).toHaveAttribute("data-reason", "ok");
    await page.getByTestId("inventaris-vernieuwen").click();
    await expect(page.getByTestId("vernieuwen-status")).toHaveText("Inventaris vernieuwd.", { timeout: 60_000 });
    for (const id of ["D01", "D03", "D06", "D07"]) {
      await page.getByTestId(`meet-${id}`).click();
      await expect(page.getByTestId("snel-meten").locator("li", { hasText: id })).toContainText("Meting geslaagd");
    }
    expect(await nasMutations()).toEqual([]);
  });

  test("D02 via het schemaformulier: leeg opslaan geeft fouten, daarna invullen en meten", async ({ page }, info) => {
    await page.goto("/onboarding/besluit/D02");
    await ready(page);
    await expect(page.getByTestId("besluit-status")).toContainText("Open");
    // Meting zonder waarde: alleen een voorstel met gemeten pools/datasets.
    await page.getByTestId("meten").click();
    await expect(page.getByTestId("meting-resultaat")).toContainText("Voorstel");
    const details = page.getByTestId("meting-resultaat");
    await expect(details).toContainText("testpool");
    // Leeg opslaan: verplichte lijsten.
    await page.getByTestId("opslaan").click();
    await expect(page.getByText("Voeg minstens één item toe.").first()).toBeVisible();
    // Gemeten (simulator)waarden invullen.
    await page.getByRole("button", { name: "Toevoegen: pools" }).click();
    await page.getByLabel("Pools 1", { exact: true }).fill("testpool");
    await page.getByRole("button", { name: "Toevoegen: datasets voor appdata" }).click();
    await page.getByLabel("Datasets voor appdata 1", { exact: true }).fill("testpool/apps");
    await expectAccessible(page, "besluit D02 formulier");
    await page.getByTestId("opslaan").click();
    await expect(page.getByTestId("opslaan-status")).toContainText("Opgeslagen");
    await expect(page.getByTestId("besluit-status")).toContainText("Ingevuld");
    await page.getByTestId("meten").click();
    await expect(page.getByTestId("meting-resultaat")).toContainText("Meting geslaagd");
    await expect(page.getByTestId("besluit-status")).toContainText("Getest");
    await expect(page.getByTestId("bewijslijst")).toContainText("Meting");
    await shot(page, info, "besluit-D02-getest");
  });

  test("schemaformulier: fouten in de UI (D16) en per veld vertaalde serverfout (D04 met plaatshouder)", async ({ page }) => {
    await page.goto("/onboarding/besluit/D16");
    await ready(page);
    await page.getByRole("button", { name: "Toevoegen: per app" }).click();
    await page.getByLabel("App-ID").fill("Ongeldig ID!");
    await page.getByLabel("RPO (uren)").fill("0");
    await page.getByLabel("RTO (uren)").fill("abc");
    await page.getByTestId("opslaan").click();
    await expect(page.getByText("Ongeldig formaat.")).toBeVisible();
    await expect(page.getByText("Moet groter zijn dan 0.")).toBeVisible();
    await expect(page.getByText("Vul een getal in.")).toBeVisible();
    await expect(page.getByTestId("besluit-status")).toContainText("Open");

    // D04: een plaatshouder ('TODO') kent alleen de server; zijn melding komt vertaald bij het juiste veld.
    await page.goto("/onboarding/besluit/D04");
    await ready(page);
    await page.getByLabel("Methode").selectOption("truenas_cloud_sync");
    await page.getByRole("button", { name: "Toevoegen: taken" }).click();
    await page.getByLabel("Taken 1", { exact: true }).fill("TODO");
    await page.getByRole("group", { name: "Versleuteld" }).getByLabel("Ja").check();
    await page.getByRole("button", { name: "Toevoegen: scope (datasets of paden)" }).click();
    await page.getByLabel("Scope (datasets of paden) 1", { exact: true }).fill("alle fotomappen");
    await page.getByLabel("Retentie").fill("dertig dagen");
    await page.getByLabel("Waar liggen de herstelgegevens").fill("in de wachtwoordkluis van het gezin");
    await page.getByTestId("opslaan").click();
    await expect(page.locator("#w-D04-taken-0-fout")).toContainText("plaatshouder");
    await expect(page.getByTestId("besluit-status")).toContainText("Open");
  });
});
