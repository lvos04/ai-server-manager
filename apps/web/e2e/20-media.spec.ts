import { expect, test, type Page, type TestInfo } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { expectAccessible, expectNoHorizontalScroll, ready } from "./helpers";

// Alleen de adapterlijst is gesimuleerd; sessie, schil en navigatie zijn de echte Hub.
const route = "**/api/v1/adapterkoppelingen?*";
const onbekend = { status: "unknown", observed_at: null, reason_code: "geen_alleen_lezen_bron" };
const metingen = Object.fromEntries(["wanted", "status", "downloads", "av1", "incidenten", "mediaservers", "noodstop"].map((k) => [k, onbekend]));

function mediaguard() {
  return { id: randomUUID(), app_id: "mediaguard", catalog_app_id: randomUUID(), basis_url: "https://media.example", laatste4: "TST4",
    ingevoerd_op: null, version: 1, verbinding: onbekend, gezondheid: onbekend, mediaguard: metingen };
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

test("(a) gekoppeld met onbekende MediaGuard-bron: onbekend in plaats van nul, en geen actieknoppen", async ({ page }, info) => {
  const nu = new Date();
  await page.clock.install({ time: nu });
  await page.route(route, (r) => r.fulfill({ json: { items: [mediaguard(), mso(new Date(nu.getTime() - 60_000).toISOString())], next_cursor: null } }));
  await page.goto("/media");
  await ready(page);
  for (const id of ["wanted", "status", "downloads", "av1", "incidenten"]) {
    const tegel = page.getByTestId("cijfer-" + id);
    await expect(tegel).toContainText("Onbekend");
    await expect(tegel).toContainText("geen alleen-lezen bron");
    await expect(tegel).not.toContainText(/\b0\b/);
  }
  await expect(page.getByTestId("pauzebalk")).toHaveCount(0);
  await expect(page.getByTestId("mso-gezondheid")).toContainText("Bereikbaar · gemeten");
  await expect(page.locator("main")).toContainText("Open wijzigingen");
  await expect(page.locator("main")).toContainText("onbekend: leesrecht niet bevestigd");
  await expect(page.locator("main").getByRole("link", { name: "open in MediaGuard" }).first()).toHaveAttribute("href", "https://media.example/ontbrekend");
  await expect(page.locator("main")).toContainText("Gepland in fase P4");
  await expect(page.locator("main").getByRole("button")).toHaveCount(0);
  await controleer(page, "media gevuld");
  await afdruk(page, info, "gevuld");
});

test("verouderd: een MSO-meting ouder dan vijftien minuten staat grijs als laatst gemeten", async ({ page }, info) => {
  const nu = new Date();
  await page.clock.install({ time: nu });
  await page.route(route, (r) => r.fulfill({ json: { items: [mso(new Date(nu.getTime() - 20 * 60_000).toISOString())], next_cursor: null } }));
  await page.goto("/media");
  await ready(page);
  const gezondheid = page.getByTestId("mso-gezondheid");
  await expect(gezondheid).toContainText("Laatst gemeten");
  await expect(gezondheid).toContainText("Verouderd");
  await expect(gezondheid).not.toContainText("Bereikbaar · gemeten");
  await expect(page.locator("main")).toContainText("MediaGuard is niet gekoppeld");
  await controleer(page, "media verouderd");
  await afdruk(page, info, "verouderd");
});
