import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { p2Afdrukken, ready } from "./helpers";

// De overige P2-afdrukken worden in de bestaande handelingsproeven gemaakt, zodra de getoonde toestand vaststaat.
if (process.env.HUB_E2E_SHOTS === "p2") {
  for (const [pad, naam, kop] of [
    ["/apps", "appcatalogus", "Apps"],
    ["/backups/hersteltests", "hersteltests", "Vastgelegde hersteltests"],
    ["/automatisering/detail", "flowdetail", "Flowdetail onbekend"],
    ["/automatisering/testmodus", "flow-testmodus", "Testuitkomst onbekend"],
    ["/automatisering/eventtypen", "flow-eventtypen", "Ontvangen gebeurtenissen"],
    ["/automatisering/versies", "flowversies", "Herstelverzoeken"],
    ["/ai", "ai", "AI"],
  ] as const) {
    test(`P2-afdruk van ${naam}`, async ({ page }, info) => {
      await page.goto(pad);
      await ready(page);
      await expect(page.getByRole("heading", { name: kop, exact: true })).toBeVisible();
      await expect(page.getByTestId("loading")).toHaveCount(0);
      await p2Afdrukken(page, info, naam);
    });
  }

  test("P2-afdruk van het monitorplan per app", async ({ page }, info) => {
    // Twee leesregels met herkenbare testnamen. Ook het controleadres is een synthetische bestemming.
    const hash = "sha256:" + "a".repeat(64);
    await page.route("**/api/v1/monitoring/monitorplan", route => route.fulfill({ json: {
      observed_at: new Date().toISOString(),
      items: [
        { app: { id: randomUUID(), naam: "proef-app" }, stand: "handmatig bevestigd", bewaakt: true,
          plan_sha256: hash, bevestiging: { plan_sha256: hash }, bevestiging_verouderd: false,
          controle: { soort: "http", adres: "http://proef-app.invalid:8080/health", verwachte_status: 200, timeout_s: 5, interval_s: 60 } },
        { app: { id: randomUUID(), naam: "tweede-app" }, stand: "onvolledig", bewaakt: false,
          reden: "hostpoort_onbekend", plan_sha256: null, bevestiging: null, bevestiging_verouderd: false, controle: null },
      ],
    } }));
    await page.goto("/instellingen/monitoring#monitorplan");
    await ready(page);
    const plan = page.locator("#monitorplan");
    await expect(plan.getByText("Handmatig bevestigd", { exact: true })).toBeVisible();
    await expect(plan.getByText("De hostpoort ontbreekt.", { exact: true })).toBeVisible();
    await p2Afdrukken(page, info, "monitorplan", plan);
  });
}
