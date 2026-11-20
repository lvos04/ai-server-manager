import { expect, test } from "@playwright/test";
import type { CatalogList } from "../src/lib/catalog";
import { ready } from "./helpers";

test("de open catalogus trekt de badge en filtertelling in op de bronvervalgrens", async ({ page }) => {
  const start = new Date();
  await page.clock.install({ time: start });
  let ophalingen = 0;
  await page.route("**/api/v1/apps?*", async (route) => {
    const response = await route.fetch();
    const lijst: CatalogList = await response.json();
    const app = lijst.items[0];
    if (!app) throw new Error("De lokale testinventaris moet ten minste één app bevatten.");
    const gezondheid = {
      ...app.gezondheid, status: "healthy", reason_code: null, melding: "",
      observed_at: start.toISOString(), geldig_tot: new Date(start.getTime() + 25_000).toISOString(),
    };
    ophalingen++;
    await route.fulfill({ response, json: {
      ...lijst, items: [{ ...app, gezondheid }], totaal: 1, next_cursor: null,
      per_status: { healthy: 1, degraded: 0, down: 0, unknown: 0 },
    } });
  });
  await page.goto("/apps");
  await ready(page);
  await expect(page.getByTestId("app-lijst").locator('[data-status="healthy"]')).toHaveCount(1);
  await page.getByRole("button", { name: "Gezond (1)", exact: true }).click();
  await page.clock.fastForward(26_000);
  await expect(page.getByRole("button", { name: "Gezond (0)", exact: true })).toBeVisible();
  await expect(page.getByText("Geen apps met dit filter.")).toBeVisible();
  await page.getByRole("button", { name: "Onbekend (1)", exact: true }).click();
  await expect(page.getByTestId("app-lijst").getByText(/Laatst bekend/)).toBeVisible();
  expect(ophalingen).toBe(1);
});
