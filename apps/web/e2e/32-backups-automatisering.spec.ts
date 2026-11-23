/** Teststack met lokale leesfixtures voor bronuitval, ontbrekend databasebewijs en een meerstaps zandbakproef. */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { expectAccessible, expectNoHorizontalScroll, ready, VIEWER } from "./helpers";

test("back-upgate, databasebewijs, upload en oefendatum hebben afzonderlijke bronnen", async ({ page }) => {
  await page.goto("/backups");
  await ready(page);
  const gate = page.getByTestId("sectie-backupgate");
  await expect(gate).toContainText("Gate dicht");
  await expect(gate.getByRole("link").first()).toBeVisible();

  const punt = randomUUID(), checkpoint = randomUUID();
  await page.route("**/api/v1/backups/herstelpunten*", r => r.fulfill({ json: { items: [{
    id: punt, app: "mediaguard", checkpoint_id: checkpoint, gemaakt_op: new Date().toISOString(), status: "geverifieerd",
    snapshot: { actie_id: checkpoint, datasets: ["proef/app"] }, db_export: null, reden: null,
  }] } }));
  await page.getByRole("link", { name: "Herstelpunten", exact: true }).first().click();
  await expect(page.getByText("Telt niet mee. De vereiste database-export ontbreekt.")).toBeVisible();
  await expectNoHorizontalScroll(page, "herstelpunt");
  await page.route("**/api/v1/backups/extern", r => r.fulfill({ json: { status: "ok", max_leeftijd_s: 60, taken: [
    { id: 1, status: "ok", beeindigd: new Date(Date.now() - 3600_000).toISOString(), fout: "interne proefnotitie" },
  ] } }));
  await page.getByRole("link", { name: "Externe back-up", exact: true }).click();
  await expect(page.getByText("Laatste upload te oud").first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText("interne proefnotitie");
  await page.getByRole("link", { name: "Rampenscenario’s", exact: true }).click();
  await expect(page.locator("main")).toContainText("Laatste oefening onbekend");
  await expect(page.locator("main ol[data-genummerd] li").first()).toBeVisible();
});

test("zonder Node-RED blijft de laatste inventarisatietijd herkenbaar en opent geen editor", async ({ page }) => {
  const datum = "2026-09-20T12:15:00Z";
  await page.route("**/api/v1/registry/services", r => r.fulfill({ json: {
    status: "unknown", observed_at: datum, items: [{ app: "node-red", basis_url: "https://editor.example", verouderd: true }],
  } }));
  await page.goto("/automatisering");
  await ready(page);
  await expect(page.getByRole("heading", { name: "Flowstatus onbekend" })).toBeVisible();
  await expect(page.locator(`main time[datetime^="2026-09-20"]`)).toBeVisible();
  await expect(page.getByText("Editoradres niet bevestigd.")).toBeVisible();
  await expect(page.locator("main")).not.toContainText("Geen flows");
  await expect(page.locator('main a[href^="https:"]')).toHaveCount(0);
  await expectAccessible(page, "flowbron-onbekend");
});

test("een echte testkijker leest hersteltests zonder startknop en de robot weigert met 403", async ({ page, browser }) => {
  const account = { ...VIEWER, username: "kijker-herstel" };
  const csrf = (await page.context().cookies()).find(c => c.name === "hub_csrf")?.value ?? "";
  const maak = await page.request.post("/api/v1/users", { data: { ...account, role: "viewer" },
    headers: { "X-CSRF-Token": csrf, "Idempotency-Key": randomUUID() } });
  expect([201, 409]).toContain(maak.status());
  const ctx = await browser.newContext({ storageState: undefined });
  try {
    const kijker = await ctx.newPage();
    expect((await kijker.request.post("/api/v1/auth/login", { data: account })).status()).toBe(200);
    await kijker.goto("/backups/hersteltests");
    await ready(kijker);
    await expect(kijker.getByRole("heading", { name: "Vastgelegde hersteltests" })).toBeVisible();
    await expect(kijker.getByRole("button", { name: "Nieuwe hersteltest" })).toHaveCount(0);
    const token = (await ctx.cookies()).find(c => c.name === "hub_csrf")?.value ?? "";
    const geweigerd = await kijker.request.post(`/api/v1/backups/herstelpunten/${randomUUID()}/hersteltest`, {
      data: { klonen: [randomUUID()] }, headers: { "X-CSRF-Token": token, "Idempotency-Key": randomUUID() },
    });
    expect(geweigerd.status()).toBe(403);
  } finally {
    await ctx.close();
  }
});

test("de zandbakproef begint met één R1-voorstel en doet nog geen uitvoering of robotregistratie", async ({ page }) => {
  const punt = randomUUID(), checkpoint = randomUUID(), verzoek = randomUUID();
  const tijd = new Date(Date.now() - 60_000).toISOString();
  await page.route("**/api/v1/backups/herstelpunten", r => r.fulfill({ json: { items: [{
    id: punt, app: "proef", gemaakt_op: tijd, checkpoint_id: checkpoint, snapshot: { actie_id: checkpoint, datasets: ["proef/app"] },
    status: "geverifieerd", db_export: null, reden: null,
  }] } }));
  await page.route(`**/api/v1/actions/${checkpoint}`, r => r.fulfill({ json: { request_id: checkpoint,
    action_id: "zfs.snapshot.create", status: "uitgevoerd", target: { dataset: "proef/app" },
    preview: { wijziging: { soort: "snapshot_maken", snapshot: "proef/app@punt" } }, resultaat: { readback: { aanwezig: true, leden: { "proef/app": "4" } } },
  } }));
  const posts: string[] = [];
  page.on("request", r => { if (r.method() === "POST") posts.push(new URL(r.url()).pathname); });
  let voorstel;
  await page.route("**/api/v1/actions", async r => { voorstel = r.request().postDataJSON(); await r.fulfill({ status: 201, json: { request_id: verzoek } }); });
  await page.route(`**/api/v1/actions/${verzoek}`, r => r.fulfill({ json: {
    request_id: verzoek, status: "klaar", action_id: "zfs.snapshot.clone_to_sandbox", actor: { type: "user" }, risk_class: "R1", rule_ids: [],
    policy_hash: "sha256:" + "a".repeat(64), target: { snapshot: "proef/app@punt" }, blokkades: [], uitvoerder: "executor",
    preview: { omschrijving: "Kloon naar zandbak", wijziging: { soort: "snapshot_klonen" }, requires_backup: false },
  } }));
  await page.goto("/backups/hersteltests");
  await ready(page);
  await page.getByRole("button", { name: "Nieuwe hersteltest" }).click();
  await expect(page.getByTestId("actie-preview")).toContainText("R1");
  expect(voorstel).toMatchObject({ action_id: "zfs.snapshot.clone_to_sandbox", target: { snapshot: "proef/app@punt" }, parameters: { doel_dataset: `proef/asm-sandbox/proef-${punt}-1` } });
  expect(posts).toEqual(["/api/v1/actions"]);
});

test("pas na elke teruggelezen kloon gaat de robot aan; een afwijkende checksum houdt het punt ongezond", async ({ page }) => {
  const punt = randomUUID(), checkpoint = randomUUID(), ids = [randomUUID(), randomUUID()];
  const ds = ["proef/app", "proef/db"];
  const tijd = new Date(Date.now() - 60_000).toISOString();
  const verzoeken: string[][] = [];
  await page.route("**/api/v1/backups/herstelpunten", r => r.fulfill({ json: { items: [{
    id: punt, app: "proef", gemaakt_op: tijd, checkpoint_id: checkpoint, snapshot: { actie_id: checkpoint, datasets: ds },
  }] } }));
  await page.route(`**/api/v1/actions/${checkpoint}`, r => r.fulfill({ json: {
    request_id: checkpoint, action_id: "zfs.snapshot.create", status: "uitgevoerd", target: { dataset: "proef" },
    preview: { wijziging: { soort: "snapshot_maken", snapshot: "proef@punt" } },
    resultaat: { readback: { aanwezig: true, leden: { "proef/app": "4", "proef/db": "4" } } },
  } }));
  await page.route("**/api/v1/actions?*action_id=zfs.snapshot.clone_to_sandbox*", r => r.fulfill({ json: {
    items: ids.map((id, i) => ({ request_id: id, action_id: "zfs.snapshot.clone_to_sandbox", status: "uitgevoerd", risk_class: "R1",
      uitgevoerd_op: new Date().toISOString(), target: { snapshot: `${ds[i]}@punt` },
      resultaat: { readback: { aanwezig: true, dataset: `proef/asm-sandbox/proef-${punt}-${i + 1}` } },
    })), next_cursor: null,
  } }));
  await page.route(`**/api/v1/backups/herstelpunten/${punt}/hersteltest`, async r => {
    verzoeken.push(r.request().postDataJSON().klonen);
    await r.fulfill({ json: { herstelpunt: punt, restore_test: randomUUID(), resultaat: "mislukt", reden: "checksum_afwijkend",
      kloon: { resultaat: "geslaagd" }, database: { resultaat: "mislukt" }, productie: { resultaat: "geslaagd" } } });
  });
  await page.goto("/backups/hersteltests");
  await ready(page);
  await page.getByRole("button", { name: "Hersteltest in zandbak starten" }).click();
  expect(verzoeken).toEqual([ids]);
  await expect(page.getByText("Hersteltest mislukt", { exact: true })).toBeVisible();
  await expect(page.getByText("De controlesom wijkt af. Het herstelpunt is ongezond.")).toBeVisible();
});

test("flowhistorie volgt de cursor en toont één regel per verzoek zonder vrije actor- of redenvelden", async ({ page }) => {
  const id = randomUUID(), volgende = randomUUID(), flow = randomUUID();
  const eerste = { request_id: id, actor: { type: "flow", id: `flow:${flow}` }, action_id: "app.restart", risk_class: "R2",
    goedkeuring_nodig: true, status: "onbekend", reason: "interne proefnotitie" };
  await page.route("**/api/v1/actions?limit=50*", r => r.fulfill({ json: r.request().url().includes("cursor=")
    ? { items: [eerste, { ...eerste, request_id: volgende, status: "afgewezen", resultaat: { message: "interne proefnotitie" } }], next_cursor: null }
    : { items: [eerste], next_cursor: "vervolg" } }));
  await page.goto("/automatisering/historie");
  await ready(page);
  await page.getByRole("button", { name: "Meer verzoeken laden" }).click();
  await expect(page.getByRole("link", { name: /Bekijk actie-preview/ })).toHaveCount(2);
  await expect(page.locator("main")).toContainText("Uitkomst onbekend");
  await expect(page.locator("main")).toContainText("reden niet weer te geven");
  await expect(page.locator("main")).not.toContainText("interne proefnotitie");
});
