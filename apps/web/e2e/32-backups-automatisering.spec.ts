/** Teststack met lokale leesfixtures voor bronuitval, ontbrekend databasebewijs en een meerstaps zandbakproef. */
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { expectAccessible, expectNoHorizontalScroll, p2Afdrukken, ready, VIEWER } from "./helpers";

test("back-upgate, databasebewijs, upload en oefendatum hebben afzonderlijke bronnen", async ({ page }, info) => {
  await page.goto("/backups");
  await ready(page);
  const gate = page.getByTestId("sectie-backupgate");
  await expect(gate).toContainText("Gate dicht");
  await expect(gate.getByRole("link").first()).toBeVisible();
  await p2Afdrukken(page, info, "backups");

  const punt = randomUUID(), checkpoint = randomUUID();
  await page.route("**/api/v1/backups/herstelpunten*", r => r.fulfill({ json: { items: [{
    id: punt, app: "mediaguard", checkpoint_id: checkpoint, gemaakt_op: new Date().toISOString(), status: "geverifieerd",
    snapshot: { actie_id: checkpoint, datasets: ["proef/app"] }, db_export: null, reden: null,
  }] } }));
  await page.getByRole("link", { name: "Herstelpunten", exact: true }).first().click();
  await expect(page.getByText("Telt niet mee. De vereiste database-export ontbreekt.")).toBeVisible();
  await expectNoHorizontalScroll(page, "herstelpunt");
  await p2Afdrukken(page, info, "herstelpunten");
  await page.route("**/api/v1/backups/extern", r => r.fulfill({ json: { status: "ok", max_leeftijd_s: 60, taken: [
    { id: 1, status: "ok", beeindigd: new Date(Date.now() - 3600_000).toISOString(), fout: "interne proefnotitie" },
  ] } }));
  await page.getByRole("link", { name: "Externe back-up", exact: true }).click();
  await expect(page.getByText("Laatste upload te oud").first()).toBeVisible();
  await expect(page.locator("main")).not.toContainText("interne proefnotitie");
  await p2Afdrukken(page, info, "externe-backup");
  await page.getByRole("link", { name: "Rampenscenario’s", exact: true }).click();
  await expect(page.locator("main")).toContainText("Laatste oefening onbekend");
  await expect(page.locator("main ol[data-genummerd] li").first()).toBeVisible();
  await p2Afdrukken(page, info, "rampenscenarios");
});

test("zonder Node-RED blijft de laatste inventarisatietijd herkenbaar en opent geen editor", async ({ page }, info) => {
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
  await p2Afdrukken(page, info, "flows");
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

test("flowhistorie volgt de cursor en toont één regel per verzoek zonder vrije actor- of redenvelden", async ({ page }, info) => {
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
  await p2Afdrukken(page, info, "flowhistorie");
  await expect(page.locator("main")).toContainText("Uitkomst onbekend");
  await expect(page.locator("main")).toContainText("reden niet weer te geven");
  await expect(page.locator("main")).not.toContainText("interne proefnotitie");
});

test("monitoring filtert fouttekst, details, kopieervelden en tijdattributen", async ({ page }) => {
  const vrij = { code: "proef-foutcode", message: "proef-bericht", details: { account: "proef-detail" }, trace_id: "proef-trace" };
  const trace = randomUUID();
  const tijd = new Date(Date.now() - 1000).toISOString();
  let bekend = false;
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", { value: { writeText: async (waarde: string) => { document.documentElement.dataset.kopie = waarde; } } });
  });
  await page.route("**/api/v1/monitoring/sources", r => r.fulfill({ status: 403, json: bekend ? { ...vrij, code: "forbidden", trace_id: trace } : vrij }));
  await page.route("**/api/v1/monitoring/monitorplan", r => r.fulfill({ json: { items: [], observed_at: bekend ? tijd : "proef-meettijd" } }));
  await page.goto("/automatisering");
  await ready(page);
  await page.getByRole("link", { name: "Bekijk het monitorplan per app" }).click();
  const paneel = page.getByTestId("monitoringbronnen").getByTestId("error-panel");
  const plan = page.locator("#monitorplan");
  await expect(paneel).toBeVisible();
  await expect(plan.getByTestId("freshness")).toBeVisible();
  await expect(paneel).toHaveAttribute("data-code", "onbekend");
  await expect(paneel).toContainText("De Hub meldde een onbekende fout.");
  await expect(paneel.locator("details, pre")).toHaveCount(0);
  await expect(paneel.getByRole("button", { name: /Kopiëren/ })).toHaveCount(0);
  expect(await paneel.evaluate(n => n.outerHTML)).not.toMatch(/proef-(foutcode|bericht|detail|trace)/);
  await expect(plan.getByTestId("freshness")).toContainText("Nog nooit gemeten");
  await expect(plan.locator("time")).toHaveCount(0);
  expect(await plan.evaluate(n => n.outerHTML)).not.toContain("proef-meettijd");

  bekend = true;
  await page.reload();
  await expect(paneel).toHaveAttribute("data-code", "forbidden");
  await expect(paneel).toContainText("Je hebt geen recht voor deze handeling.");
  await expect(paneel.locator("details, pre")).toHaveCount(0);
  expect(await paneel.evaluate(n => n.outerHTML)).not.toMatch(/proef-(bericht|detail)/);
  await paneel.getByRole("button", { name: /^Kopiëren\s*:\s*Trace-ID$/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-kopie", trace);
  await expect(plan.locator("time")).toHaveAttribute("datetime", tijd);
});

test("een positieve back-upgate vraagt verse inventaris en de verplichte eigen export", async ({ page }) => {
  const tijd = (delta: number) => new Date(Date.now() + delta).toISOString();
  const mso = "media-source-optimizer";
  const namen = ["mediaguard", "emby_exportarchief", "my_house", mso];
  let inventarisVers = false;
  let exportAanwezig = true;
  await page.route("**/api/v1/gates/backup_gate", r => r.fulfill({ json: { status: "toegestaan", toegestaan: true, redenen: [],
    vereist: { besluiten: [], metingen: ["eigen_backup", ...namen], gates: [] }, afgeleid_op: tijd(-1000) } }));
  const eigen = { id: randomUUID(), status: "geslaagd", beeindigd_op: tijd(-1000), sha256: "a".repeat(64), inhoudsopgave_items: 10 };
  await page.route("**/api/v1/backups/self", r => r.fulfill({ json: { items: exportAanwezig ? [eigen] : [], laatste_geverifieerd: exportAanwezig ? eigen : null } }));
  await page.route("**/api/v1/backups/coverage", r => r.fulfill({ json: { apps: [], datasets: [],
    app_backups: Object.fromEntries(namen.map(id => [id, { vereist: id !== mso, status: id === mso ? "unknown" : "gedekt",
      observed_at: tijd(-1000), geldig_tot: tijd(60_000) }])),
    bronnen: Object.fromEntries(["apps", "datasets", "snapshot_tasks", "latest_snapshots", "replication", "cloudsync"].map(id => {
      const oud = id === "apps" && !inventarisVers;
      return [id, { status: "ok", observed_at: tijd(oud ? -3600_000 : -1000), verouderd: oud }];
    })) } }));
  await page.goto("/backups");
  await ready(page);
  const gate = page.getByTestId("sectie-backupgate");
  await expect(page.getByText("Niet alle bronnen zijn actueel. De dekking is deels onbekend.")).toBeVisible();
  await expect(gate).toContainText("Bijwerken blijft geblokkeerd.");
  await expect(gate.getByText("Toegestaan", { exact: true })).toHaveCount(0);

  inventarisVers = true;
  await page.reload();
  await expect(gate.getByText("Toegestaan", { exact: true })).toBeVisible();
  exportAanwezig = false;
  await page.reload();
  await expect(page.getByTestId("sectie-eigen-backup")).toContainText("Er is nog geen geverifieerde export");
  await expect(gate).toContainText("Eigen Hub-export · Geen geverifieerde export aangetoond");
  await expect(gate).toContainText("Bijwerken blijft geblokkeerd.");
  await expect(gate.getByText("Toegestaan", { exact: true })).toHaveCount(0);
});
