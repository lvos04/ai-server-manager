/**
 * Appbeheer in de Hub (S-P2-180; ontwerp docs/ontwerp/HUB_P2_ONTWERP.md S-044 t/m S-048): welke actie een app krijgt,
 * welke klasse het beleid noemt, wanneer bijwerken of terugzetten een getypt doel heeft, en de stand van een
 * installatieplan. De server beslist; deze hulpen bepalen alleen wat de UI aanbiedt. Bij twijfel: geen knop.
 */
import type { ActieVerzoek, Beleid, BeleidsActie, Blokkade } from "./acties";
import { risicoKlasse } from "./acties";
import type { CatalogDetail } from "./catalog";

export const APP_DOEL = (naam: string) => ({ host_id: "nas-primary", app_id: naam });

/** De appacties in de volgorde van het ontwerp (S-045); alleen wat ook in het beleid staat, verschijnt. */
const VOLGORDE = ["app.restart", "app.start", "app.stop", "app.update", "app.rollback", "app.uninstall"] as const;

export const CATALOGUS_NOG_NIET = "Nog niet beschikbaar — de Hub kan de installeerbare manifests nog niet ophalen";

export const EMBY_ZIN = "Emby blijft beschikbaar. Alleen jij kunt Emby verwijderen.";

const ONBEKEND: Blokkade = {
  id: "onbekend",
  code: "actiebeleid_onbekend",
  reden: "De bescherming van deze app is onbekend. Vernieuw de inventaris om de beschikbare acties te zien.",
};

export interface AppActie {
  actie: BeleidsActie;
  klasse: string;
  blokkades: Blokkade[];
}

export function appActies(beleid: Beleid, app: CatalogDetail): AppActie[] {
  const oordeel = app.actiebeleid;
  const zelfdeBeleid = oordeel && oordeel.policy_hash === beleid.policy_hash;
  return VOLGORDE.flatMap((id) => {
    const actie = beleid.acties.find((a) => a.action_id === id && a.doel === "app");
    if (!actie) return [];
    const regel = zelfdeBeleid ? oordeel.acties?.[id] : undefined;
    const klasse = risicoKlasse(regel?.risk_class);
    if (!klasse || !Array.isArray(regel?.blokkades)) return [{ actie, klasse: "Onbekend", blokkades: [ONBEKEND] }];
    return [{ actie, klasse, blokkades: regel.blokkades }];
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
