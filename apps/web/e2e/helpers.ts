import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, type TestInfo } from "@playwright/test";
import { mkdirSync, readFileSync } from "node:fs";
import path from "node:path";

export const STATE_DIR = process.env.HUB_E2E_STATE_DIR ?? path.join(__dirname, ".state");
export const ADMIN_STATE = path.join(__dirname, ".auth", "beheerder.json");
export const SCREENSHOT_DIR = path.resolve(__dirname, "..", "..", "..", "docs", "screenshots", "p0");
export const ADMIN = { username: "beheerder", password: "Correct-Paard-Batterij-Nietje-42" };
export const VIEWER = { username: "kijker", password: "Kijker-Wachtwoord-Lang-2026" };

export interface StackState {
  api_url?: string;
  control_url: string;
  fake_nas_port: number;
  readonly_key: string;
  write_key: string;
}

export function stackState(): StackState {
  return JSON.parse(readFileSync(path.join(STATE_DIR, "state.json"), "utf8")) as StackState;
}

/** De setupcode staat (net als in de image) alleen in de log; de teststack schrijft hem ook in een bestand. */
export function setupCode(): string {
  if (process.env.HUB_E2E_SETUP_CODE) return process.env.HUB_E2E_SETUP_CODE;
  return readFileSync(path.join(STATE_DIR, "setupcode.txt"), "utf8").trim();
}

export async function nasMutations(): Promise<string[]> {
  const res = await fetch(`${stackState().control_url}/`);
  const body = (await res.json()) as { mutaties_op_nas: string[] };
  return body.mutaties_op_nas;
}

export async function setNas(online: boolean): Promise<void> {
  const res = await fetch(`${stackState().control_url}/nas/${online ? "online" : "offline"}`, { method: "POST" });
  expect(res.ok).toBeTruthy();
}

/** Toegankelijkheid (axe-core, WCAG 2.2 A/AA). Elke overtreding laat de test falen. */
export async function expectAccessible(page: Page, label: string): Promise<void> {
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  const summary = res.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).slice(0, 5).join(" | ")}`);
  expect(summary, `axe-overtredingen op ${label}`).toEqual([]);
}

/** Geen horizontaal scrollen van de hele pagina (tabellen scrollen binnen hun eigen kader). */
export async function expectNoHorizontalScroll(page: Page, label: string): Promise<void> {
  const res = await page.evaluate(() => {
    const cw = document.documentElement.clientWidth;
    const wide: string[] = [];
    for (const el of Array.from(document.querySelectorAll<HTMLElement>("body *"))) {
      if (el.closest(".table-wrap")) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.right > cw + 1) {
        wide.push(`${el.tagName.toLowerCase()}.${el.className || "-"} "${(el.textContent ?? "").trim().slice(0, 40)}" right=${Math.round(r.right)}`);
      }
    }
    return { sw: document.documentElement.scrollWidth, cw, wide: wide.slice(0, 8) };
  });
  expect(res.sw, `horizontaal scrollen op ${label}: ${res.wide.join(" | ")}`).toBeLessThanOrEqual(res.cw + 1);
}

/** Aanraakdoelen ≥ 44×44 px voor knoppen, invoer, navigatie en keuzelabels (zichtbare elementen). */
export async function expectTouchTargets(page: Page, label: string): Promise<void> {
  const small = await page.evaluate(() => {
    const sel = [
      "button",
      ".btn",
      "input:not([type=checkbox]):not([type=radio]):not([type=hidden])",
      "select",
      "summary",
      "nav a",
      ".link-list a",
      "label.choice",
    ].join(",");
    const out: string[] = [];
    for (const el of Array.from(document.querySelectorAll<HTMLElement>(sel))) {
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      if (r.width === 0 || r.height === 0 || style.visibility === "hidden" || el.closest(".sr-only")) continue;
      if (el.classList.contains("skip-link")) continue;
      if (r.height < 43.5 || r.width < 43.5) out.push(`${el.tagName.toLowerCase()} "${(el.textContent ?? "").trim().slice(0, 30)}" ${Math.round(r.width)}×${Math.round(r.height)}`);
    }
    return out;
  });
  expect(small, `te kleine aanraakdoelen op ${label}`).toEqual([]);
}

export async function shot(page: Page, info: TestInfo, name: string, fullPage = true): Promise<void> {
  const dir = path.join(SCREENSHOT_DIR, info.project.name);
  mkdirSync(dir, { recursive: true });
  // JPEG (kwaliteit 70) houdt de repo klein; volledige pagina als bewijs.
  await page.screenshot({ path: path.join(dir, `${name}.jpg`), fullPage, animations: "disabled", type: "jpeg", quality: 70 });
}

/** Wacht tot de app-schil klaar is met laden (aanmelding gecontroleerd, geen 'Laden…' meer in de kop). */
export async function ready(page: Page): Promise<void> {
  await expect(page.locator("main h1").first()).toBeVisible();
  await expect(page.getByText("Aanmelding controleren…")).toHaveCount(0);
}
