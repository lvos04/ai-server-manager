/**
 * Opzet van de Peil-review: kijker en kind aanmaken via de echte API, zoals de beheerder in Instellingen → Toegang.
 * Eén keer en vóór de parallelle breedtes (review/peil-review.spec.ts). Bestaat de gebruiker al (409), dan is dat goed.
 */
import { expect, test } from "@playwright/test";
import { ADMIN_STATE, KIND, VIEWER, saveP1State } from "../e2e/helpers";

test.use({ storageState: ADMIN_STATE });

test("Peil-review opzet: kijker en kind bestaan", async ({ page }) => {
  await page.goto("/instellingen/toegang");
  for (const [u, rol] of [
    [VIEWER, "viewer"],
    [KIND, "kind"],
  ] as const) {
    const status = await page.evaluate(
      async ({ username, password, role }) => {
        const csrf = decodeURIComponent((document.cookie.split("; ").find((c) => c.startsWith("hub_csrf=")) ?? "=").split("=")[1] ?? "");
        const r = await fetch("/api/v1/users", {
          method: "POST",
          headers: { "content-type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
          body: JSON.stringify({ username, password, role }),
        });
        return r.status;
      },
      { username: u.username, password: u.password, role: rol },
    );
    expect([200, 201, 409]).toContain(status);
  }
});

test("Peil-review opzet: één R2-voorstel dat op goedkeuring wacht (S-P2-170)", async ({ page }) => {
  await page.goto("/goedkeuringen");
  const res = await page.evaluate(async () => {
    const csrf = decodeURIComponent((document.cookie.split("; ").find((c) => c.startsWith("hub_csrf=")) ?? "=").split("=")[1] ?? "");
    const r = await fetch("/api/v1/actions", {
      method: "POST",
      headers: { "content-type": "application/json", "X-CSRF-Token": csrf, "Idempotency-Key": crypto.randomUUID() },
      body: JSON.stringify({ action_id: "app.uninstall", target: { host_id: "nas-primary", app_id: "media-source-optimizer" }, reason: "Peil-review", expires_in_seconds: 86400 }),
    });
    return { status: r.status, body: (await r.json()) as { request_id?: string } };
  });
  expect(res.status).toBe(201);
  saveP1State({ actie_id: res.body.request_id });
});
