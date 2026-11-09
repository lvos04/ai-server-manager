/**
 * Onafhankelijke Peil-ontwerpreview van de ECHTE Hub-UI (ONTWERPTAAL §12, contract §13) — geen prototypes.
 *
 * Draait na de opzet uit e2e/00-01 (echte API + simulators, Sim-getest) en meet per scherm × breedte
 * (320/360/390/768/1024/1440) × thema (licht/donker):
 * - axe-core (WCAG 2.0/2.1/2.2 A+AA), gerenderd tekstcontrast (≥ 4,5:1; groot ≥ 3:1; incl. opacity en arcering),
 *   veld- en stippelranden (≥ 3:1), aanraakdoelen (≥ 44 px), lettergrootte (≥ 14 px), overloop en afkappen;
 * - toetsenbord op 390 en 1440: volledige Tab-doorloop, ring aanwezig en ≥ 3:1, niet bedekt door kop/ondernavigatie;
 * - Peil-semantiek: groen alleen voor gemeten en goed, onbekend/verouderd nooit groen, status nooit alleen kleur;
 * - NL-microcopy tegen de Peil-woordenlijst (§11).
 * Schermafdrukken en ruwe metingen gaan naar review/uit/ (niet in Git); de samenvatting maakt review/samenvat.mjs.
 *
 * Start: zie review/README.md (`make web-review`).
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Browser, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { ADMIN_STATE, KIND, VIEWER, control, p1State, setNas } from "../e2e/helpers";

const UIT = path.join(__dirname, "uit");
const INIT = path.join(__dirname, "in-pagina.js");
const AUTH = path.join(__dirname, "uit", ".auth");
const WIDTHS = (process.env.PEIL_REVIEW_BREEDTES ?? "320,360,390,768,1024,1440").split(",").map(Number);
const THEMES = ["licht", "donker"] as const;
const FOCUS_WIDTHS = new Set([390, 1440]);
const ALLEEN = process.env.PEIL_REVIEW_ALLEEN ? new RegExp(process.env.PEIL_REVIEW_ALLEEN) : null;
const EXECUTOR_URL = process.env.PEIL_REVIEW_EXECUTOR_URL ?? "";

type Rol = "beheerder" | "kijker" | "kind" | "anoniem";
interface Scherm {
  naam: string;
  rol: Rol;
  pad: string | (() => string | null);
  /** Wacht op dit element in plaats van een h1 (statuspagina van de executor, offlinepagina). */
  klaar?: string;
  /** Extern adres (executor-statuspagina) i.p.v. de Hub. */
  extern?: boolean;
  /** Interactie vóór de meting (menu open, fout tonen, …). */
  voor?: (page: Page) => Promise<void>;
}

const appId = () => p1State().app_id ?? null;
const incidentId = () => p1State().incident_id ?? null;

const SCHERMEN: Scherm[] = [
  // Beheerder: alle schermen uit 08_UI + P1 + contract 1.2
  { naam: "home", rol: "beheerder", pad: "/" },
  { naam: "server", rol: "beheerder", pad: "/server" },
  { naam: "server-metrieken", rol: "beheerder", pad: "/server/metrieken" },
  { naam: "server-meetdekking", rol: "beheerder", pad: "/server/meetdekking" },
  { naam: "server-logs", rol: "beheerder", pad: "/server/logs" },
  { naam: "apps", rol: "beheerder", pad: "/apps" },
  { naam: "app-status", rol: "beheerder", pad: () => (appId() ? `/apps/${appId()}` : null) },
  { naam: "app-metrieken", rol: "beheerder", pad: () => (appId() ? `/apps/${appId()}?tab=metrieken` : null) },
  { naam: "app-logs", rol: "beheerder", pad: () => (appId() ? `/apps/${appId()}?tab=logs` : null) },
  { naam: "app-versies", rol: "beheerder", pad: () => (appId() ? `/apps/${appId()}?tab=versies` : null) },
  { naam: "app-acties", rol: "beheerder", pad: () => (appId() ? `/apps/${appId()}?tab=acties` : null) },
  { naam: "problemen", rol: "beheerder", pad: "/problemen" },
  { naam: "probleem-detail", rol: "beheerder", pad: () => (incidentId() ? `/problemen/${incidentId()}` : null) },
  { naam: "backups", rol: "beheerder", pad: "/backups" },
  { naam: "onboarding", rol: "beheerder", pad: "/onboarding" },
  { naam: "besluit-D02", rol: "beheerder", pad: "/onboarding/besluit/D02" },
  { naam: "besluit-D03", rol: "beheerder", pad: "/onboarding/besluit/D03" },
  { naam: "besluit-D10", rol: "beheerder", pad: "/onboarding/besluit/D10" },
  { naam: "besluit-D17", rol: "beheerder", pad: "/onboarding/besluit/D17" },
  { naam: "truenas", rol: "beheerder", pad: "/onboarding/truenas" },
  { naam: "executor-koppelen", rol: "beheerder", pad: "/onboarding/executor" },
  { naam: "instellingen", rol: "beheerder", pad: "/instellingen" },
  { naam: "instellingen-account", rol: "beheerder", pad: "/instellingen/account" },
  { naam: "instellingen-toegang", rol: "beheerder", pad: "/instellingen/toegang" },
  { naam: "noodaccount", rol: "beheerder", pad: "/instellingen/noodaccount" },
  { naam: "diensten", rol: "beheerder", pad: "/instellingen/diensten" },
  { naam: "instellingen-monitoring", rol: "beheerder", pad: "/instellingen/monitoring" },
  { naam: "instellingen-apparaat", rol: "beheerder", pad: "/instellingen/apparaat" },
  { naam: "instellingen-audit", rol: "beheerder", pad: "/instellingen/audit" },
  { naam: "instellingen-over", rol: "beheerder", pad: "/instellingen/over" },
  { naam: "meer", rol: "beheerder", pad: "/meer" },
  { naam: "ai", rol: "beheerder", pad: "/ai" },
  { naam: "media", rol: "beheerder", pad: "/media" },
  { naam: "huis", rol: "beheerder", pad: "/huis" },
  { naam: "netwerk", rol: "beheerder", pad: "/netwerk" },
  { naam: "automatisering", rol: "beheerder", pad: "/automatisering" },
  { naam: "kosten", rol: "beheerder", pad: "/kosten" },
  { naam: "niet-gevonden", rol: "beheerder", pad: "/bestaat-niet" },
  {
    naam: "gebruikersmenu-open",
    rol: "beheerder",
    pad: "/",
    voor: async (page) => {
      await page.getByTestId("gebruikersmenu").click();
      await expect(page.getByRole("menu")).toBeVisible();
    },
  },
  // Kijker: rolmeldingen en uitgeschakelde bediening
  { naam: "kijker-home", rol: "kijker", pad: "/" },
  { naam: "kijker-toegang", rol: "kijker", pad: "/instellingen/toegang" },
  { naam: "kijker-besluit-D03", rol: "kijker", pad: "/onboarding/besluit/D03" },
  { naam: "kijker-diensten", rol: "kijker", pad: "/instellingen/diensten" },
  // Kind (O-05): eigen schil Home · Kijken · Zoeken · Ik en een kindvriendelijke 403
  { naam: "kind-home", rol: "kind", pad: "/" },
  { naam: "kind-kijken", rol: "kind", pad: "/kijken" },
  { naam: "kind-zoeken", rol: "kind", pad: "/zoeken" },
  { naam: "kind-ik", rol: "kind", pad: "/ik" },
  { naam: "kind-403", rol: "kind", pad: "/server" },
  // Niet aangemeld
  { naam: "inloggen", rol: "anoniem", pad: "/inloggen" },
  {
    naam: "inloggen-fout",
    rol: "anoniem",
    pad: "/inloggen",
    voor: async (page) => {
      await page.getByLabel("Gebruikersnaam").fill("iemand");
      await page.getByLabel("Wachtwoord").fill("Fout-Wachtwoord-123456");
      await page.getByRole("button", { name: "Inloggen" }).click();
      await expect(page.getByTestId("error-panel")).toBeVisible();
    },
  },
  { naam: "noodlogin", rol: "anoniem", pad: "/inloggen/nood" },
  { naam: "eerste-start-afgerond", rol: "anoniem", pad: "/eerste-start" },
  // Executor-statuspagina (Peil-sjabloon, HTML zonder JS)
  ...(EXECUTOR_URL
    ? ([
        { naam: "executor-statuspagina", rol: "anoniem", pad: EXECUTOR_URL + "/", extern: true, klaar: "h1" },
        {
          naam: "executor-statuspagina-fout",
          rol: "anoniem",
          pad: EXECUTOR_URL + "/",
          extern: true,
          klaar: "h1",
          voor: async (page: Page) => {
            await page.locator("#hub").fill("http://127.0.0.1:1");
            await page.locator("#koppelcode").fill("AAAA");
            await page.locator("#vingerafdruk").fill("XXXX");
            await page.getByRole("button", { name: /Koppelen/ }).click();
            await page.waitForLoadState("load");
          },
        },
      ] satisfies Scherm[])
    : []),
];

interface Meting {
  scherm: string;
  breedte: number;
  thema: string;
  pad: string;
  h1?: string[];
  [k: string]: unknown;
}

async function wachtKlaar(page: Page, s: Scherm): Promise<void> {
  if (s.klaar) {
    await expect(page.locator(s.klaar).first()).toBeVisible();
  } else {
    await expect(page.locator("main h1").first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Aanmelding controleren…")).toHaveCount(0);
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 30_000 });
  }
  await page.evaluate(() => document.fonts.ready);
}

async function zetThema(page: Page, s: Scherm, thema: "licht" | "donker"): Promise<void> {
  if (s.extern) {
    // De statuspagina volgt prefers-color-scheme (geen JS).
    await page.emulateMedia({ colorScheme: thema === "donker" ? "dark" : "light", reducedMotion: "reduce" });
  } else {
    await page.emulateMedia({ reducedMotion: "reduce", colorScheme: thema === "donker" ? "dark" : "light" });
    await page.evaluate((t) => {
      localStorage.setItem("hub-thema", t);
      window.dispatchEvent(new Event("hub-thema-gewijzigd"));
    }, thema);
    await expect(page.locator("html")).toHaveAttribute("data-theme", thema === "donker" ? "dark" : "light");
  }
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null)))));
  // Kleurovergangen (ook 0,01 ms bij reduced motion) lopen een paar frames na: pas daarna meten.
  await page.waitForTimeout(300);
}

async function focusDoorloop(page: Page): Promise<Record<string, unknown>> {
  const stappen: Record<string, unknown>[] = [];
  for (let i = 0; i < 220; i++) {
    await page.keyboard.press("Tab");
    let f = (await page.evaluate(() => (window as unknown as { __peil: { focus: () => unknown } }).__peil.focus())) as Record<string, number | string | boolean> | null;
    if (f && (f.ost === "none" || Number(f.ow) === 0 || Number(f.ringR) < 3)) {
      await page.waitForTimeout(250);
      f = (await page.evaluate(() => (window as unknown as { __peil: { focus: () => unknown } }).__peil.focus())) as typeof f;
    }
    if (!f) break;
    stappen.push(f);
    if (stappen.length > 3 && f.desc === stappen[0]!.desc) break;
  }
  const s = stappen as { desc: string; ow: number; ost: string; ringR: number; bs: string; inViewport: number; zichtbaarPt: number; geknipt: boolean; rTop: number; rBottom: number; w: number; h: number }[];
  return {
    aantal: s.length,
    eerste: s[0]?.desc,
    zonderRing: [...new Set(s.filter((f) => !(f.ost !== "none" && f.ow > 0)).map((f) => f.desc))],
    zwak: [...new Set(s.filter((f) => f.ow > 0 && f.ringR < 3).map((f) => `${f.desc} ${f.ringR}`))],
    bedekt: [...new Set(s.filter((f) => f.inViewport > 0 && f.zichtbaarPt === 0).map((f) => `${f.desc} top=${f.rTop} bottom=${f.rBottom}`))],
    deelsBedekt: [...new Set(s.filter((f) => f.inViewport > 0 && f.zichtbaarPt > 0 && f.zichtbaarPt < f.inViewport && f.zichtbaarPt < 3).map((f) => `${f.desc} ${f.zichtbaarPt}/${f.inViewport}`))],
    geknipt: [...new Set(s.filter((f) => f.geknipt).map((f) => f.desc))],
    ringMin: s.filter((f) => f.ow > 0).reduce((m, f) => Math.min(m, f.ringR), 99),
  };
}

async function axe(page: Page): Promise<unknown[]> {
  const res = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
  return res.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, voorbeeld: v.nodes.slice(0, 3).map((x) => `${x.target.join(" ")} :: ${(x.failureSummary ?? "").split("\n").slice(1, 2).join("")}`) }));
}

async function inlog(browser: Browser, gebruiker: { username: string; password: string }, bestand: string): Promise<void> {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const p = await ctx.newPage();
  await p.goto("/inloggen");
  await p.getByLabel("Gebruikersnaam").fill(gebruiker.username);
  await p.getByLabel("Wachtwoord").fill(gebruiker.password);
  await p.getByRole("button", { name: "Inloggen" }).click();
  await expect(p).not.toHaveURL(/\/inloggen/);
  await expect(p.locator("main h1").first()).toBeVisible();
  await expect(p.getByText("Aanmelding controleren…")).toHaveCount(0);
  await ctx.storageState({ path: bestand });
  await ctx.close();
}

test.describe.configure({ mode: "parallel" });

let werker = 0;

// Kijker en kind maakt review/00-gebruikers.spec.ts één keer aan (vóór de parallelle breedtes: gelijktijdig
// aanmaken gaf een UniqueViolation/500 in de API). Hier logt elke werker alleen zelf in.
test.beforeAll(async ({ browser }, info) => {
  werker = info.workerIndex;
  mkdirSync(AUTH, { recursive: true });
  await inlog(browser, VIEWER, path.join(AUTH, `kijker-${werker}.json`));
  await inlog(browser, KIND, path.join(AUTH, `kind-${werker}.json`));
});

function staat(rol: Rol): string | undefined {
  if (rol === "beheerder") return ADMIN_STATE;
  if (rol === "kijker") return path.join(AUTH, `kijker-${werker}.json`);
  if (rol === "kind") return path.join(AUTH, `kind-${werker}.json`);
  return undefined;
}

async function meetScherm(ctx: BrowserContext, s: Scherm, breedte: number, uit: Meting[], toestand = ""): Promise<void> {
  const pad = typeof s.pad === "function" ? s.pad() : s.pad;
  if (!pad) {
    uit.push({ scherm: s.naam + toestand, breedte, thema: "-", pad: "-", overgeslagen: "geen id uit de opzet" });
    return;
  }
  const page = await ctx.newPage();
  try {
    await page.goto(pad);
    await wachtKlaar(page, s);
    if (s.voor) await s.voor(page);
    for (const thema of THEMES) {
      await zetThema(page, s, thema);
      const m = (await page.evaluate(() => {
        const w = window as unknown as { __peil: Record<string, () => unknown> };
        return { meet: w.__peil.meet!(), semantiek: w.__peil.semantiek!(), structuur: w.__peil.structuur!() };
      })) as { meet: Record<string, unknown> & { tekst: { r: number; rAlt: number; eis: number; dis?: boolean }[] }; semantiek: unknown; structuur: Record<string, unknown> };
      const { tekst, ...rest } = m.meet;
      // Tweede meting met alle uitklapblokken open (contrast, doelen, overloop van de verborgen inhoud).
      const open = (await page.evaluate(async () => {
        const w = window as unknown as { __peil: Record<string, () => unknown> };
        const n = w.__peil.openDetails!() as number;
        if (!n) return null;
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(null))));
        const res = w.__peil.meet!();
        w.__peil.sluitDetails!();
        return res;
      })) as (Record<string, unknown> & { tekst: { r: number; rAlt: number; eis: number; dis?: boolean }[]; doelen: unknown[]; overloop: number }) | null;
      const run: Meting = {
        scherm: s.naam + toestand,
        breedte,
        thema,
        pad,
        ...rest,
        tekstFout: tekst.filter((x) => x.r < x.eis || x.rAlt < x.eis),
        uitgeklapt: open
          ? { tekstFout: open.tekst.filter((x) => x.r < x.eis || x.rAlt < x.eis), doelen: open.doelen, overloop: open.overloop, kleinFont: open.kleinFont, afgekapt: open.afgekapt }
          : null,
        tekstOnder7: tekst.filter((x) => !x.dis && Math.min(x.r, x.rAlt) < 7).length,
        tekstMin: tekst.filter((x) => !x.dis).reduce((mm, x) => Math.min(mm, x.r, x.rAlt), 99),
        aantalTekst: tekst.length,
        semantiek: m.semantiek,
        structuur: m.structuur,
        axe: await axe(page),
      };
      if (thema === "licht" && (breedte === 390 || breedte === 1440)) {
        run.woorden = await page.evaluate(() => (window as unknown as { __peil: { woorden: () => unknown } }).__peil.woorden());
        run.beweging = await page.evaluate(() => (window as unknown as { __peil: { beweging: () => unknown } }).__peil.beweging());
      }
      const dir = path.join(UIT, "shots", String(breedte));
      mkdirSync(dir, { recursive: true });
      if (!s.extern) await page.evaluate(() => document.documentElement.setAttribute("data-afdruk", ""));
      await page.screenshot({ path: path.join(dir, `${s.naam}${toestand}-${thema}.jpg`), fullPage: true, animations: "disabled", type: "jpeg", quality: 70, scale: "css" });
      if (!s.extern) await page.evaluate(() => document.documentElement.removeAttribute("data-afdruk"));
      if (FOCUS_WIDTHS.has(breedte) && !s.voor) {
        // Volledige Tab-doorloop vanaf het begin van de pagina (opnieuw laden; het thema blijft bewaard).
        const f = await ctx.newPage();
        try {
          await f.goto(pad);
          await wachtKlaar(f, s);
          await zetThema(f, s, thema);
          run.focus = await focusDoorloop(f);
        } finally {
          await f.close();
        }
      }
      uit.push(run);
    }
  } catch (e) {
    uit.push({ scherm: s.naam + toestand, breedte, thema: "-", pad, fout: String(e).slice(0, 400) });
  } finally {
    await page.close();
  }
}

for (const breedte of WIDTHS) {
  test(`Peil-review ${breedte} px: alle schermen × licht/donker`, async ({ browser }) => {
    test.setTimeout(45 * 60_000);
    const uit: Meting[] = [];
    const contexts = new Map<Rol, BrowserContext>();
    try {
      for (const s of SCHERMEN) {
        if (ALLEEN && !ALLEEN.test(s.naam)) continue;
        let ctx = contexts.get(s.rol);
        if (!ctx) {
          ctx = await browser.newContext({
            storageState: staat(s.rol),
            viewport: { width: breedte, height: breedte < 768 ? 800 : breedte < 1024 ? 1024 : 900 },
            hasTouch: breedte < 1024,
            locale: "nl-NL",
            timezoneId: "Europe/Amsterdam",
          });
          await ctx.addInitScript({ path: INIT });
          contexts.set(s.rol, ctx);
        }
        await meetScherm(ctx, s, breedte, uit);
        // Tussentijds wegschrijven: een afgebroken run verliest niets.
        mkdirSync(UIT, { recursive: true });
        writeFileSync(path.join(UIT, `metingen-${breedte}${ALLEEN ? "-deel" : ""}.json`), JSON.stringify(uit, null, 1));
      }
    } finally {
      for (const c of contexts.values()) await c.close();
    }
    mkdirSync(UIT, { recursive: true });
    writeFileSync(path.join(UIT, `metingen-${breedte}${ALLEEN ? "-deel" : ""}.json`), JSON.stringify(uit, null, 1));
    expect(uit.filter((m) => m.fout).map((m) => `${m.scherm}: ${m.fout}`)).toEqual([]);
  });
}

/** Toestanden: NAS onbereikbaar (verouderd/onbekend, nooit groen) en browser offline. */
test("Peil-review toestanden: NAS offline (verouderd) en browser offline", async ({ browser }) => {
  test.setTimeout(30 * 60_000);
  test.skip(Boolean(ALLEEN) && !ALLEEN!.test("toestand"), "deelrun");
  const uit: Meting[] = [];
  const admin = await browser.newContext({ storageState: ADMIN_STATE, viewport: { width: 1440, height: 900 } });
  const p = await admin.newPage();
  await setNas(false);
  try {
    await p.goto("/server");
    await expect(p.locator("main h1").first()).toBeVisible();
    await p.getByTestId("inventaris-vernieuwen").click();
    await expect(p.getByTestId("vernieuwen-status")).toContainText("niet volledig gelukt", { timeout: 60_000 });
    for (const breedte of WIDTHS) {
      const ctx = await browser.newContext({ storageState: ADMIN_STATE, viewport: { width: breedte, height: 900 }, hasTouch: breedte < 1024, locale: "nl-NL", timezoneId: "Europe/Amsterdam" });
      await ctx.addInitScript({ path: INIT });
      for (const s of [
        { naam: "home", rol: "beheerder", pad: "/" },
        { naam: "server", rol: "beheerder", pad: "/server" },
        { naam: "server-metrieken", rol: "beheerder", pad: "/server/metrieken" },
        { naam: "apps", rol: "beheerder", pad: "/apps" },
      ] satisfies Scherm[])
        await meetScherm(ctx, s, breedte, uit, "--nas-offline");
      await ctx.close();
    }
  } finally {
    await setNas(true);
    await p.goto("/server");
    await expect(p.locator("main h1").first()).toBeVisible();
    await p.getByTestId("inventaris-vernieuwen").click();
    await expect(p.getByTestId("vernieuwen-status")).toHaveText("Inventaris vernieuwd.", { timeout: 60_000 });
    await admin.close();
  }
  // Browser offline: banner + verouderde gegevens; alleen op 390 en 1440 (de banner is één component).
  for (const breedte of [390, 1440]) {
    const ctx = await browser.newContext({ storageState: ADMIN_STATE, viewport: { width: breedte, height: 900 }, hasTouch: breedte < 1024 });
    await ctx.addInitScript({ path: INIT });
    const page = await ctx.newPage();
    await page.goto("/server");
    await expect(page.locator("main h1").first()).toBeVisible();
    await expect(page.getByTestId("loading")).toHaveCount(0, { timeout: 30_000 });
    await ctx.setOffline(true);
    await expect(page.getByTestId("offline-banner")).toBeVisible();
    for (const thema of THEMES) {
      await zetThema(page, { naam: "x", rol: "beheerder", pad: "/" }, thema);
      const m = (await page.evaluate(() => {
        const w = window as unknown as { __peil: Record<string, () => unknown> };
        return { meet: w.__peil.meet!(), semantiek: w.__peil.semantiek!(), structuur: w.__peil.structuur!() };
      })) as { meet: Record<string, unknown> & { tekst: { r: number; rAlt: number; eis: number; dis?: boolean }[] }; semantiek: unknown; structuur: unknown };
      const { tekst, ...rest } = m.meet;
      uit.push({ scherm: "server--browser-offline", breedte, thema, pad: "/server", ...rest, tekstFout: tekst.filter((x) => x.r < x.eis || x.rAlt < x.eis), tekstMin: tekst.filter((x) => !x.dis).reduce((mm, x) => Math.min(mm, x.r, x.rAlt), 99), semantiek: m.semantiek, structuur: m.structuur, axe: await axe(page) });
      const dir = path.join(UIT, "shots", String(breedte));
      mkdirSync(dir, { recursive: true });
      await page.screenshot({ path: path.join(dir, `server--browser-offline-${thema}.jpg`), fullPage: true, type: "jpeg", quality: 70, scale: "css" });
    }
    await ctx.setOffline(false);
    await ctx.close();
  }
  writeFileSync(path.join(UIT, "metingen-toestanden.json"), JSON.stringify(uit, null, 1));
  expect(uit.filter((m) => m.fout).map((m) => `${m.scherm}: ${m.fout}`)).toEqual([]);
});

// Hulp voor de samenvatting: welke opzet-ids waren er (zodat een overgeslagen scherm verklaarbaar is).
test.afterAll(() => {
  const f = path.join(UIT, "opzet.json");
  const stand = existsSync(f) ? JSON.parse(readFileSync(f, "utf8")) : {};
  writeFileSync(f, JSON.stringify({ ...stand, ...p1State(), executor: EXECUTOR_URL || null }, null, 1));
  void control;
});
