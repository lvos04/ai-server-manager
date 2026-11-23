/**
 * Appbeheer in de Hub (S-P2-180; ontwerp docs/ontwerp/HUB_P2_ONTWERP.md S-044 t/m S-048): welke actie een app krijgt,
 * welke klasse het beleid noemt, wanneer bijwerken of terugzetten een getypt doel heeft, en de stand van een
 * installatieplan. De server beslist; deze hulpen bepalen alleen wat de UI aanbiedt. Bij twijfel: geen knop.
 */
import type { ActieVerzoek, Beleid, BeleidsActie } from "./acties";
import type { CatalogDetail } from "./catalog";

export const APP_DOEL = (naam: string) => ({ host_id: "nas-primary", app_id: naam });

/** De appacties in de volgorde van het ontwerp (S-045); alleen wat ook in het beleid staat, verschijnt. */
const VOLGORDE = ["app.restart", "app.start", "app.stop", "app.update", "app.rollback", "app.uninstall"] as const;

/** HARDE EIS (STAPPEN_P2 S-P2-180 bouwpunt 6): een beschermde app krijgt nooit een knop om te stoppen, bij te werken of te verwijderen. */
const BESCHERMD_ALTIJD = new Set(["app.stop", "app.update", "app.rollback", "app.uninstall"]);

export const CATALOGUS_NOG_NIET = "Nog niet beschikbaar — de Hub kan de installeerbare manifests nog niet ophalen";

export const EMBY_ZIN = "Emby blijft beschikbaar. Alleen jij kunt Emby verwijderen.";

/** Een vaste, herkenbare naam (zoals de herkenning in het beleid); al het andere telt niet als naam. */
const NAAM_RE = /^[a-z0-9][a-z0-9_.-]{0,63}$/;

function namen(app: Pick<CatalogDetail, "app_id" | "naam" | "runtime_id">): Set<string> {
  return new Set([app.app_id, app.naam, app.runtime_id].filter((n): n is string => typeof n === "string" && NAAM_RE.test(n)));
}

/** De beschermingsregels uit `policy/apps.yaml` (sectie `beschermd`) die op deze app slaan. */
export function beschermingVoor(beleid: Pick<Beleid, "beschermd">, app: Pick<CatalogDetail, "app_id" | "naam" | "runtime_id">): Beleid["beschermd"] {
  const n = namen(app);
  return beleid.beschermd.filter((r) => n.has(r.app));
}

export function isEmby(regels: Beleid["beschermd"]): boolean {
  return regels.some((r) => r.app === "emby");
}

/** Of deze actie voor een app met deze regels geweigerd wordt (en dus geen knop krijgt). */
export function beschermd(regels: Beleid["beschermd"], actionId: string): boolean {
  if (!regels.length) return false;
  return BESCHERMD_ALTIJD.has(actionId) || regels.some((r) => r.acties === null || r.acties.includes(actionId));
}

export interface AppActie {
  actie: BeleidsActie;
  klasse: string;
  /** null = toegestaan; anders de vaste uitleg uit het beleid waarom hier geen knop staat. */
  weigering: string | null;
}

/** De klasse zoals het beleid haar voor dit soort doel noemt: kritiek, Custom App of de basisklasse. */
export function klasseVoor(actie: BeleidsActie, app: Pick<CatalogDetail, "app_id" | "installatiewijze">, kritiek: string[]): string {
  if (app.app_id && kritiek.includes(app.app_id) && actie.risk_class_kritiek) return actie.risk_class_kritiek;
  if (app.installatiewijze === "custom_app" && actie.risk_class_custom_app) return actie.risk_class_custom_app;
  return actie.risk_class;
}

export function appActies(beleid: Beleid, app: CatalogDetail): AppActie[] {
  const regels = beschermingVoor(beleid, app);
  return VOLGORDE.flatMap((id) => {
    const actie = beleid.acties.find((a) => a.action_id === id && a.doel === "app");
    if (!actie) return [];
    const weigering = beschermd(regels, id) ? (regels.find((r) => r.acties === null || r.acties.includes(id)) ?? regels[0]!).reden : null;
    return [{ actie, klasse: klasseVoor(actie, app, beleid.kritieke_apps ?? []), weigering }];
  });
}

export function wieBeslist(klasse: string): string {
  if (klasse === "R2" || klasse === "R3") return "Een beheerder keurt goed";
  if (klasse === "R0" || klasse === "R1") return "Een operator voert uit, zonder goedkeuring";
  return "Onbekend";
}

// ------------------------------------------------------------------ versies (S-044)
const VERSIE_RE = /^\d{1,6}(\.\d{1,6}){1,3}$/; // zoals VERSION_RE in asm_policy.params

export type UpdateDoel = { parameters: { catalog_version: string }; naar: string } | { reden: string };

/**
 * Het getypte doel voor ‘Bijwerken’: alleen een catalogusapp waarvoor TrueNAS zelf een nieuwere catalogusversie meldt.
 * Een Custom App heeft geen goedgekeurde doelversie in de Hub; dan staat er een reden (geen vrij image-veld).
 */
export function updateDoel(app: Pick<CatalogDetail, "installatiewijze" | "catalogus">): UpdateDoel {
  if (app.installatiewijze !== "catalog_app") {
    return { reden: "Nog niet beschikbaar — de Hub kan voor deze app nog geen goedgekeurde doelversie ophalen." };
  }
  const c = app.catalogus ?? {};
  const naar = c.nieuwste_versie;
  if (c.upgrade_beschikbaar !== true || typeof naar !== "string" || !VERSIE_RE.test(naar)) {
    return { reden: c.upgrade_beschikbaar === false ? "TrueNAS meldt geen nieuwere catalogusversie." : "Beschikbare versie onbekend." };
  }
  return { parameters: { catalog_version: naar }, naar };
}

/** Eigen, uitgevoerde bijwerkingen van deze app: alleen die geven een bevestigd terugzetpad (`herstel_van`). */
export function terugzetPunten(lijst: ActieVerzoek[], naam: string): { request_id: string; uitgevoerd_op: string | null }[] {
  return lijst
    .filter((v) => v.action_id === "app.update" && v.status === "uitgevoerd" && v.target?.app_id === naam)
    .map((v) => ({ request_id: v.request_id, uitgevoerd_op: v.uitgevoerd_op }));
}

// ------------------------------------------------------------------ installatieplan (S-047)
export interface InstallPlan {
  plan_id: string;
  app_id: string;
  app_name: string;
  step_id: string;
  status: string;
  reden: string | null;
  expires_at: string | null;
  request_id: string | null;
  release: { catalog?: unknown; image_digests?: unknown } | null;
  controles_na_installatie: { id: string; soort: string; beschrijving_nl: string }[];
}

export const PLAN_VERLOPEN = "Installatieplan verlopen. Maak een nieuw plan.";

const PLAN_REDEN: Record<string, string> = {
  voorganger_onbevestigd: "Een eerdere stap van dit plan is nog niet bevestigd.",
  planner_niet_klaar: "De controle vooraf is nog niet afgerond door de planner.",
  niet_gemeld: "De uitkomst van de installatie is niet bij de planner gemeld; elk vervolg is geblokkeerd.",
};

/** Waarom de controle vooraf de wizard tegenhoudt, of null. Een onbekende status is nooit ‘klaar’. */
export function planBlokkade(plan: InstallPlan, nu: Date): string | null {
  if (plan.expires_at === null || Date.parse(plan.expires_at) <= nu.getTime()) return PLAN_VERLOPEN;
  if (plan.status === "klaar_voor_voorstel" || plan.status === "voorgesteld") return null;
  if (plan.status === "geblokkeerd") return PLAN_REDEN[plan.reden ?? ""] ?? "De controle vooraf blokkeert dit plan.";
  return "De stand van dit plan is onbekend.";
}

const DIGEST_RE = /^sha256:[0-9a-f]{64}$/;
const CATALOGUS_RE = /^[a-z0-9][a-z0-9_.-]{0,63}$/;

/** Alleen geldige digests uit `release.image_digests` (catalogus.yaml); elk ander veld blijft buiten beeld. */
export function planDigests(plan: InstallPlan): string[] {
  const d = plan.release?.image_digests;
  return Array.isArray(d) ? d.filter((x): x is string => typeof x === "string" && DIGEST_RE.test(x)) : [];
}

/** De catalogusapp (trein, app, versie) uit `release.catalog`, of null als een deel geen vaste vorm heeft. */
export function planCatalogus(plan: InstallPlan): { train: string; app: string; version: string } | null {
  const c = plan.release?.catalog as Record<string, unknown> | null | undefined;
  const { train, app, version } = c ?? {};
  if (typeof train !== "string" || typeof app !== "string" || typeof version !== "string") return null;
  return CATALOGUS_RE.test(train) && CATALOGUS_RE.test(app) && VERSIE_RE.test(version) ? { train, app, version } : null;
}
