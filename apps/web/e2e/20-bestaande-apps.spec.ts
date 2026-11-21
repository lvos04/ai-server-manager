import { expect, test, type Locator, type TestInfo } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import type { Koppeling } from "../src/app/instellingen/diensten/adapterweergave";
import { expectAccessible, expectNoHorizontalScroll, ready } from "./helpers";

const route = "/api/v1/adapterkoppelingen";

async function afdruk(kaart: Locator, info: TestInfo, naam: string) {
  if (info.project.name !== "desktop-1440") return;
  const map = process.env.HUB_KOPPELSCHERM_SHOTS ?? info.outputDir;
  await mkdir(map, { recursive: true });
  // De vaste paginakop zou bij het fotograferen van een lange kaart over de bovenste regels vallen.
  await kaart.screenshot({
    path: path.join(map, naam + ".png"), animations: "disabled", scale: "css",
    style: "header.sticky { position: static !important; }",
  });
}

test("my_house doorloopt de vijf kaarttoestanden en vergeet de invoer", async ({ page }, info) => {
  // Alleen de adapter en haar catalogusinstallatie zijn hier gesimuleerd. De gewone Hub-sessie blijft actief.
  const doel = { id: randomUUID(), app_id: "my_house", naam: "Proefwoning", soort: "bestaand", aanwezig: true, deep_link: "https://huis.example" };
  const server = randomUUID();
  const koppelingId = randomUUID();
  const waarde = "ABCD-" + "EFGH";
  const tijd = new Date();
  let link: Koppeling | null = null;
  let posten = 0;
  let getest = 0;
  let verwijderd = 0;
  const sleutels = new Set<string>();
  let laatTestDoor!: () => void;
  const antwoord = new Promise<void>((resolve) => { laatTestDoor = resolve; });
  await page.route("**/api/v1/apps?soort=bestaand&*", (r) => r.fulfill({
    json: { items: [doel], next_cursor: null, inventaris: { status: "ok" } },
  }));
  await page.route("**" + route + "**", async (r) => {
    const req = r.request();
    if (req.method() === "GET") return r.fulfill({ json: { items: link ? [link] : [], next_cursor: null } });
    if (req.method() === "DELETE") {
      expect(req.headers()["if-match"]).toBe('"2"');
      verwijderd++;
      link = null;
      return r.fulfill({ json: { verwijderd: true } });
    }
    if (new URL(req.url()).pathname.endsWith("/test")) {
      getest++;
      await antwoord;
      link = { ...link!, version: 2, verbinding: { status: "healthy", observed_at: tijd.toISOString(), reason_code: null } };
      return r.fulfill({ json: { id: koppelingId, version: 2 } });
    }
    expect(req.method()).toBe("POST");
    expect(req.postDataJSON()).toEqual({ app_id: "my_house", catalog_app_id: doel.id, basis_url: doel.deep_link, doel_bevestigd: true, server_id: server });
    expect(Boolean(req.headers()["x-csrf-token"])).toBe(true);
    sleutels.add(req.headers()["idempotency-key"]!);
    posten++;
    if (posten === 1) return r.fulfill({ status: 422, json: {
      code: "validation_error", details: { reason: "bron_recht_ongeldig" }, message: "De bron heeft de rol geweigerd.",
    } });
    expect(req.headers()["x-adapter-credential"] === waarde).toBe(true);
    link = { id: koppelingId, app_id: "my_house", catalog_app_id: doel.id, basis_url: doel.deep_link,
      laatste4: "TST4", ingevoerd_op: tijd.toISOString(), version: 1,
      verbinding: { status: "unknown", observed_at: null, reason_code: "meettijd_onbekend" } };
    return r.fulfill({ status: 201, json: { id: koppelingId, version: 1 } });
  });

  await page.clock.install({ time: tijd });
  await page.goto("/instellingen/diensten");
  await ready(page);
  const kaart = page.getByRole("article", { name: "my_house" });
  const code = kaart.getByLabel("Koppelcode", { exact: true });
  await expect(kaart.getByText("Niet gekoppeld", { exact: true })).toBeVisible();
  await expect(code).toHaveAttribute("type", "password");
  await expect(code).toHaveValue("");
  await expect(kaart.getByRole("button", { name: "Testen" })).toBeDisabled();
  await afdruk(kaart, info, "leeg");

  await code.fill("WXYZ-" + "ABCD");
  await kaart.getByLabel("Server-ID", { exact: true }).fill(server);
  await kaart.getByRole("checkbox").check();
  const opslaan = kaart.getByRole("button", { name: "Opslaan" });
  await opslaan.focus();
  await page.keyboard.press("Enter");
  await expect(kaart.getByRole("alert")).toContainText("kijker");
  await expect(code).toHaveAttribute("aria-invalid", "true");
  await expect(code).toHaveAccessibleDescription(/kijker/);
  await afdruk(kaart, info, "fout");

  await code.fill(waarde);
  await opslaan.click();
  await expect(kaart.getByText("Ingesteld", { exact: true })).toBeVisible();
  await expect(code).toHaveValue("");
  await expect(kaart).toContainText("TST4");
  expect(sleutels.size).toBe(2);
  const inPagina = await page.evaluate((geheim) =>
    document.documentElement.outerHTML.includes(geheim) || Array.from(document.querySelectorAll("input")).some((i) => i.value.includes(geheim)), waarde);
  expect(inPagina).toBe(false);

  const testen = kaart.getByRole("button", { name: "Testen" });
  await testen.focus();
  await page.keyboard.press("Enter");
  await expect(testen).toHaveAttribute("aria-busy", "true");
  await page.keyboard.press("Enter");
  await afdruk(kaart, info, "bezig");
  laatTestDoor();
  await expect(kaart.getByText("Gekoppeld", { exact: true })).toBeVisible();
  expect(getest).toBe(1);
  await afdruk(kaart, info, "gekoppeld");
  await expectNoHorizontalScroll(page, "Bestaande apps");
  await expectAccessible(page, "Bestaande apps");

  await page.clock.fastForward(901_000);
  await expect(kaart.getByText("Verouderd", { exact: true })).toBeVisible();
  await expect(kaart.locator("time")).toHaveAttribute("datetime", tijd.toISOString());
  await afdruk(kaart, info, "verouderd");

  const ontkoppel = kaart.getByRole("button", { name: "Ontkoppelen" });
  await ontkoppel.focus();
  await page.keyboard.press("Enter");
  const dialoog = page.getByRole("alertdialog");
  await expect(dialoog).toContainText("Trek de toegang van deze Hub ook in my_house zelf in");
  await expect(dialoog.getByRole("button", { name: "Annuleren" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(dialoog).toHaveCount(0);
  await expect(ontkoppel).toBeFocused();
  expect(verwijderd).toBe(0);
  await ontkoppel.click();
  await dialoog.getByRole("button", { name: "Ontkoppelen" }).click();
  await expect(kaart.getByText("Niet gekoppeld", { exact: true })).toBeVisible();
  expect(verwijderd).toBe(1);
  await expect(kaart).not.toContainText("TST4");
});

test("de openbare MSO-koppeling verstuurt geen machinesleutel", async ({ page }) => {
  const doel = { id: randomUUID(), app_id: "media-source-optimizer", naam: "Proefinstallatie", soort: "bestaand", aanwezig: true, deep_link: "https://mso.example" };
  await page.route("**/api/v1/apps?soort=bestaand&*", (r) => r.fulfill({
    json: { items: [doel], next_cursor: null, inventaris: { status: "ok" } },
  }));
  let posten = 0;
  await page.route("**" + route + "**", async (r) => {
    if (r.request().method() === "GET") return r.fulfill({ json: { items: [], next_cursor: null } });
    posten++;
    expect(r.request().headers()["x-adapter-credential"]).toBeUndefined();
    return r.fulfill({ status: 409, json: { code: "conflict", message: "Doel geweigerd.", details: { reason: "doelbinding" } } });
  });
  await page.goto("/instellingen/diensten");
  await ready(page);
  const kaart = page.getByRole("article", { name: "Media Source Optimizer (MSO)" });
  await expect(kaart.getByLabel("Machinesleutel")).toBeDisabled();
  await kaart.getByRole("checkbox").check();
  await kaart.getByRole("button", { name: "Opslaan" }).click();
  await expect(kaart.getByRole("alert")).toContainText("Het adres is geweigerd");
  await expect(kaart.getByLabel("HTTPS-adres", { exact: true })).toHaveAccessibleDescription(/adres is geweigerd/);
  expect(posten).toBe(1);
});

test("de Hub-API weigert vanuit de MediaGuard-kaart een onbevestigde bestemming", async ({ page }) => {
  await page.goto("/instellingen/diensten");
  await ready(page);
  const kaart = page.getByRole("article", { name: "MediaGuard" });
  const adres = kaart.getByLabel("HTTPS-adres", { exact: true });
  await adres.fill("https://andere-installatie.example");
  await kaart.getByLabel("API-sleutel", { exact: true }).fill(randomUUID());
  await kaart.getByRole("checkbox").check();
  const antwoord = page.waitForResponse((r) => new URL(r.url()).pathname === route && r.request().method() === "POST");
  await kaart.getByRole("button", { name: "Opslaan" }).click();
  expect((await antwoord).status()).toBe(409);
  await expect(kaart.getByRole("alert")).toContainText("Het adres is geweigerd");
  await expect(adres).toHaveAttribute("aria-invalid", "true");
  await expect(kaart.getByText("Niet gekoppeld", { exact: true })).toBeVisible();
});

test("een MediaGuard-sleutel wordt vervangen zonder hem terug te tonen", async ({ page }) => {
  const doel = { id: randomUUID(), app_id: "mediaguard", naam: "Proefmedia", soort: "bestaand", aanwezig: true, deep_link: "https://media.example" };
  const id = randomUUID();
  const waarde = randomUUID();
  const kenmerk = waarde.slice(-4);
  let versie = 4;
  await page.route("**/api/v1/apps?soort=bestaand&*", (r) => r.fulfill({
    json: { items: [doel], next_cursor: null, inventaris: { status: "ok" } },
  }));
  await page.route("**" + route + "**", async (r) => {
    const req = r.request();
    if (req.method() === "GET") return r.fulfill({ json: { items: [{
      id, app_id: doel.app_id, catalog_app_id: doel.id, basis_url: doel.deep_link,
      laatste4: versie === 4 ? "VOR1" : kenmerk, ingevoerd_op: new Date().toISOString(), version: versie,
      verbinding: { status: "unknown", observed_at: null, reason_code: "geen_alleen_lezen_bron" },
    }], next_cursor: null } });
    expect(new URL(req.url()).pathname).toBe(route + "/" + id);
    expect(req.method()).toBe("PATCH");
    expect(req.headers()["if-match"]).toBe('"4"');
    expect(req.headers()["x-adapter-credential"] === waarde).toBe(true);
    expect(req.postData()?.includes(waarde)).toBe(false);
    versie++;
    return r.fulfill({ json: { id, version: versie } });
  });
  await page.goto("/instellingen/diensten");
  await ready(page);
  const kaart = page.getByRole("article", { name: "MediaGuard" });
  const veld = kaart.getByLabel("API-sleutel", { exact: true });
  await expect(kaart).toContainText("VOR1");
  await expect(veld).toHaveValue("");
  await veld.fill(waarde);
  await kaart.getByRole("checkbox").check();
  await kaart.getByRole("button", { name: "Opslaan" }).click();
  await expect(kaart.getByRole("status")).toHaveText("Koppeling opgeslagen.");
  await expect(veld).toHaveValue("");
  await expect(kaart.locator("code")).toHaveText(kenmerk);
  expect((await page.content()).includes(waarde)).toBe(false);
  await expect(kaart).toContainText("geen veilige leescontrole");
  await expect(kaart.getByText("Gekoppeld", { exact: true })).toHaveCount(0);
});
