import { expect, test } from "@playwright/test";
import { huisMeting } from "../tests/unit/fixtures/huis";
import { expectAccessible, expectNoHorizontalScroll, expectTouchTargets, ready, setTheme } from "./helpers";

const koppelingen = "/api/v1/adapterkoppelingen";
const overzicht = `${koppelingen}/proef/huis`;

test("Huis leest, markeert verouderde sensoren en herstelt met het toetsenbord", async ({ page }) => {
  const meting = huisMeting();
  let status = 503;
  const methodes: string[] = [];
  await page.route(`**${koppelingen}/**`, async (route) => {
    methodes.push(route.request().method());
    if (new URL(route.request().url()).pathname.endsWith("/my-house")) {
      await route.fulfill({ json: { items: ["proef"], next_cursor: null } });
    } else if (route.request().url().endsWith(overzicht)) {
      const code = status === 409 ? "bron_token_verlopen" : "my_house_unavailable";
      await route.fulfill({ status, json: status === 200 ? meting : { code, message: "De leesverbinding is niet beschikbaar." } });
    } else {
      await route.abort();
    }
  });

  await page.goto("/huis");
  await ready(page);
  const main = page.locator("main");
  const fout = main.getByRole("alert");
  const opnieuw = fout.getByRole("button", { name: "Opnieuw proberen" });
  await expect(fout).toContainText("De leesverbinding is niet beschikbaar.");
  for (const thema of ["licht", "donker"] as const) {
    await setTheme(page, thema);
    await expectNoHorizontalScroll(page, "Huis");
    await expectTouchTargets(page, "Huis");
    await expectAccessible(page, "Huis");
    await expect(opnieuw).toBeInViewport();
  }

  const skiplink = page.getByRole("link", { name: "Naar de inhoud" });
  await skiplink.focus();
  await page.keyboard.press("Enter");
  await page.keyboard.press("Tab");
  await expect(opnieuw).toBeFocused();
  status = 200;
  await page.keyboard.press("Enter");
  await expect(main.getByRole("heading", { name: "Proefwoning" })).toBeVisible();
  await expect(main.getByText("20,5 °C", { exact: true })).toBeVisible();
  await expect(main.getByText("Verouderd", { exact: true })).toBeVisible();
  await expect(main.getByRole("link", { name: "Open in my_house" })).toHaveAttribute("href", "https://huis.example");
  await expect(main.locator("form, button, input, [role=switch]")).toHaveCount(0);
  await expectNoHorizontalScroll(page, "Huis");
  await expectTouchTargets(page, "Huis");
  await expectAccessible(page, "Huis");

  status = 409;
  await page.reload();
  await expect(main.getByRole("alert")).toContainText("koppeling verlopen");
  await expect(main.getByRole("link", { name: "Naar instellingen voor diensten" })).toHaveAttribute("href", "/instellingen/diensten");
  expect(methodes.length).toBeGreaterThanOrEqual(5);
  expect(new Set(methodes)).toEqual(new Set(["GET"]));
});
