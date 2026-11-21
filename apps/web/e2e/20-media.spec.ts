import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { expectAccessible, expectNoHorizontalScroll, ready } from "./helpers";

// Alleen de adapterlijst en het MediaGuard-overzicht zijn gesimuleerd; sessie, schil en navigatie zijn de echte Hub.
const route = "**/api/v1/adapterkoppelingen?*";
const overzichtRoute = "**/api/v1/adapterkoppelingen/*/mediaguard";
const onbekend = { status: "unknown", observed_at: null, reason_code: "geen_alleen_lezen_bron" };
const CIJFERS = ["wanted", "status", "downloads", "av1", "incidenten"];
const DOWNLOADS = "MediaGuard heeft nog geen bijwerkingsvrije downloadbron";
const SERVERS = { status: "onbekend", servers: null, reden: "MediaGuard heeft nog geen bijwerkingsvrije mediaserverbron" };

function mediaguard() {
  return { id: randomUUID(), app_id: "mediaguard", catalog_app_id: randomUUID(), basis_url: "https://media.example", laatste4: "TST4",
    ingevoerd_op: null, version: 1, verbinding: onbekend, gezondheid: onbekend };
}
/**
 * Vorm van hub/adapters/mediaguard_lezen.py::Overzicht. `verouderd`: zoals de Hub een te oude bronmeting teruggeeft,
 * onbekend zonder waarde maar met de oorspronkelijke meettijd. Downloads vraagt de Hub nooit op (bijwerkingen in MediaGuard).
 */
function overzicht(tijd: string | null, noodstopAan = false, verouderd = false, statusGrens = 900) {
  const waarden = [17, 0, null, 3, 6];
  const cijfers = Object.fromEntries(CIJFERS.map((k, i) => [k, k === "downloads"
    ? { status: "onbekend", waarde: null, observed_at: null, reden: DOWNLOADS }
    : tijd && verouderd ? { status: "onbekend", waarde: null, observed_at: tijd, reden: "meting verouderd" }
    : tijd ? { status: "gemeten", waarde: waarden[i], observed_at: tijd, reden: null }
    : { status: "onbekend", waarde: null, observed_at: null, reden: "geen leesrecht" }]));
  const noodstop = tijd && verouderd
    ? { status: "onbekend", actief: null, sinds: null, observed_at: tijd, reden: "meting verouderd" }
    : tijd ? { status: "gemeten", actief: noodstopAan, sinds: noodstopAan ? tijd : null, observed_at: tijd, reden: null }
    : { status: "onbekend", actief: null, sinds: null, observed_at: null, reden: "geen leesrecht" };
  const max_age_s = tijd ? { wanted: 900, status: statusGrens, av1: 900, incidenten: 900 } : {};
  return { correlation_id: randomUUID(), ...cijfers, noodstop, mediaservers: SERVERS, max_age_s };
}
function mso(observedAt: string) {
  return { id: randomUUID(), app_id: "media-source-optimizer", catalog_app_id: randomUUID(), basis_url: "https://mso.example", laatste4: "",
    ingevoerd_op: null, version: 1, verbinding: { status: "healthy", observed_at: observedAt, reason_code: null },
    gezondheid: { status: "unknown", observed_at: null, reason_code: "capability_unavailable" } };
}

async function afdruk(page: Page, info: TestInfo, naam: string) {
  if (info.project.name !== "desktop-1440" && info.project.name !== "mobiel-360") return;
  const map = process.env.HUB_MEDIA_SHOTS ?? info.outputDir;
  await mkdir(map, { recursive: true });
  const breedte = info.project.name === "desktop-1440" ? "breed" : "smal";
  await page.locator("main").screenshot({
    path: path.join(map, `media-${naam}-${breedte}.png`), animations: "disabled", scale: "css",
    style: "header.sticky { position: static !important; }",
  });
}

async function controleer(page: Page, label: string) {
  await expectNoHorizontalScroll(page, label);
  await expectAccessible(page, label);
}

test("(c) zonder koppeling verwijst Media naar het koppelscherm", async ({ page }, info) => {
  await page.route(route, (r) => r.fulfill({ json: { items: [], next_cursor: null } }));
  await page.goto("/media");
  await ready(page);
  await expect(page.getByRole("heading", { name: "Media", level: 1 })).toBeVisible();
  const leeg = page.getByTestId("media-leeg");
  await expect(leeg).toContainText("MediaGuard en MSO zijn nog niet gekoppeld");
  await expect(page.getByTestId("not-yet-available")).toHaveCount(0);
  await controleer(page, "media leeg");
  await afdruk(page, info, "leeg");
  await leeg.getByRole("link", { name: "Naar instellingen voor diensten" }).click();
  await expect(page).toHaveURL(/\/instellingen\/diensten$/);
});

test("bezig en fout: eerst ophalen, een weigering toont de fout zonder cijfers", async ({ page }, info) => {
  let laatDoor!: () => void;
  const wacht = new Promise<void>((resolve) => { laatDoor = resolve; });
  await page.route(route, async (r) => {
    await wacht;
    await r.fulfill({ status: 403, json: { code: "forbidden", message: "Geen toegang tot de koppelingen." } });
  });
  await page.goto("/media");
  await expect(page.getByText("Koppelingen ophalen…")).toBeVisible();
  await afdruk(page, info, "bezig");
  laatDoor();
  await expect(page.getByText("Mediagegevens ontbreken")).toBeVisible();
  await expect(page.getByTestId("cijfer-wanted")).toHaveCount(0);
  await controleer(page, "media fout");
  await afdruk(page, info, "fout");
});

test("(a) gekoppeld met onbekende MediaGuard-bron: onbekend in plaats van nul, en geen actieknoppen", async ({ page }) => {
  const nu = new Date();
  await page.clock.install({ time: nu });
  await page.route(route, (r) => r.fulfill({ json: { items: [mediaguard(), mso(new Date(nu.getTime() - 60_000).toISOString())], next_cursor: null } }));
  await page.route(overzichtRoute, (r) => r.fulfill({ json: overzicht(null) }));
  await page.goto("/media");
  await ready(page);
  for (const id of CIJFERS) {
    const tegel = page.getByTestId("cijfer-" + id);
    await expect(tegel).toContainText(id === "downloads" ? "Onbekend: " + DOWNLOADS : "Onbekend: geen leesrecht");
    await expect(tegel).not.toContainText(/\b0\b/);
  }
  await expect(page.getByTestId("pauzebalk")).toHaveCount(0);
  await expect(page.locator("main")).toContainText("Noodstop · onbekend: geen leesrecht");
  await expect(page.locator("main").getByRole("button")).toHaveCount(0);
  await controleer(page, "media onbekend");
});

test("(b) gevuld: vijf gemeten cijfers, noodstop aan met sinds, mediaservers onbekend en geen actieknoppen", async ({ page }, info) => {
  const nu = new Date();
  const tijd = new Date(nu.getTime() - 60_000).toISOString();
  await page.clock.install({ time: nu });
  await page.route(route, (r) => r.fulfill({ json: { items: [mediaguard(), mso(tijd)], next_cursor: null } }));
  await page.route(overzichtRoute, (r) => r.fulfill({ json: overzicht(tijd, true) }));
  await page.goto("/media");
  await ready(page);
  await expect(page.getByTestId("cijfer-wanted")).toContainText("17 · gemeten");
  await expect(page.getByTestId("cijfer-status")).toContainText("0 · gemeten");
  await expect(page.getByTestId("cijfer-av1")).toContainText("3 · gemeten");
  await expect(page.getByTestId("cijfer-downloads")).toContainText("Onbekend: " + DOWNLOADS);
  await expect(page.getByTestId("pauzebalk")).toContainText("MediaGuard is gepauzeerd (noodstop)");
  await expect(page.locator("main")).toContainText("Onbekend: MediaGuard heeft nog geen bijwerkingsvrije mediaserverbron");
  await expect(page.getByTestId("mso-gezondheid")).toContainText("Bereikbaar · gemeten");
  await expect(page.locator("main")).toContainText("onbekend: leesrecht niet bevestigd");
  await expect(page.locator("main").getByRole("link", { name: "open in MediaGuard" }).first()).toHaveAttribute("href", "https://media.example/ontbrekend");
  await expect(page.locator("main")).toContainText("Gepland in fase P4");
  await expect(page.locator("main").getByRole("button")).toHaveCount(0);
  await controleer(page, "media gevuld");
  await afdruk(page, info, "gevuld");
});

test("verouderd: metingen ouder dan vijftien minuten staan grijs als laatst gemeten, zonder getal", async ({ page }, info) => {
  const nu = new Date();
  const oud = new Date(nu.getTime() - 20 * 60_000).toISOString();
  await page.clock.install({ time: nu });
  await page.route(route, (r) => r.fulfill({ json: { items: [mediaguard(), mso(oud)], next_cursor: null } }));
  await page.route(overzichtRoute, (r) => r.fulfill({ json: overzicht(oud, true, true) }));
  await page.goto("/media");
  await ready(page);
  const gezondheid = page.getByTestId("mso-gezondheid");
  await expect(gezondheid).toContainText("Laatst gemeten");
  await expect(gezondheid).toContainText("Verouderd");
  await expect(gezondheid).not.toContainText("Bereikbaar · gemeten");
  const wanted = page.getByTestId("cijfer-wanted");
  await expect(wanted).toContainText("Laatst gemeten");
  await expect(wanted).toContainText("meting verouderd");
  await expect(wanted).not.toContainText("Nog nooit gemeten");
  await expect(wanted.locator(`time[datetime="${oud}"]`)).toBeVisible();
  await expect(wanted.locator(".text-2xl")).toHaveText(/^Onbekend/);
  await expect(page.getByTestId("pauzebalk")).toHaveCount(0);
  await expect(page.getByTestId("noodstop-uit")).toHaveCount(0);
  await expect(page.locator("main")).toContainText("Noodstop · onbekend: meting verouderd · laatst gemeten");
  await controleer(page, "media verouderd");
  await afdruk(page, info, "verouderd");
});

test("brontermijn van de Hub: het scherm trekt noodstop uit en de nul zelf in zodra de grens tussen twee peilingen verstrijkt", async ({ page }) => {
  // R-VEILIG-4: Hub-grens 60 s voor status; de meting is 59 s oud bij het laden en raakt in de browser verouderd.
  const meting = Date.now() - 120_000;
  const tijd = new Date(meting).toISOString();
  await page.clock.install({ time: new Date(meting) });
  await page.clock.pauseAt(new Date(meting + 59_000));
  await page.route(route, (r) => r.fulfill({ json: { items: [mediaguard(), mso(tijd)], next_cursor: null } }));
  await page.route(overzichtRoute, (r) => r.fulfill({ json: overzicht(tijd, false, false, 60) }));
  await page.goto("/media");
  await ready(page);
  const status = page.getByTestId("cijfer-status");
  await expect(page.getByTestId("noodstop-uit")).toHaveText("Noodstop · uit · gemeten");
  await expect(status).toContainText("0 · gemeten");
  await page.clock.runFor(2_000);
  await expect(page.getByTestId("noodstop-uit")).toHaveCount(0);
  await expect(page.locator("main")).toContainText("Noodstop · onbekend: meting verouderd · laatst gemeten");
  await expect(status.locator(".text-2xl")).not.toHaveText(/^0\s*· gemeten/);
  await expect(status).toContainText("Verouderd");
  await expect(status.locator(`time[datetime="${tijd}"]`)).toBeVisible();
  // Gegevens met de standaardgrens blijven actueel.
  await expect(page.getByTestId("cijfer-wanted")).toContainText("17 · gemeten");
});
