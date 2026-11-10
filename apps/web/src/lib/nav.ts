/** Navigatie exact volgens 01_ARCHITECTUUR/08_UI_EN_INTERACTIES.md. */

/** Sleutels van de navigatie-iconen (lucide, vaste koppeling ONTWERPTAAL §7); de schil koppelt ze aan componenten. */
export type IconName =
  | "home" | "apps" | "alert" | "ai" | "more" | "server" | "media" | "house" | "network" | "flow" | "backup"
  | "costs" | "settings" | "wizard" | "logout" | "kijken" | "zoeken" | "ik";

/** Productnaam (besluit gebruiker O-07). "Hub" blijft de naam van de centrale app ín het product. */
export const PRODUCT = "TrueNAS Home Platform";

export interface NavItem {
  href: string;
  label: string;
  icon: IconName;
}

/** Mobiel: ondernavigatie Home, Apps, Problemen, AI, Meer. */
export const MOBILE_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/apps", label: "Apps", icon: "apps" },
  { href: "/problemen", label: "Problemen", icon: "alert" },
  { href: "/ai", label: "AI", icon: "ai" },
  { href: "/meer", label: "Meer", icon: "more" },
];

/** Desktop: zijbalk Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten, Instellingen. */
export const DESKTOP_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/server", label: "Server", icon: "server" },
  { href: "/media", label: "Media", icon: "media" },
  { href: "/huis", label: "Huis", icon: "house" },
  { href: "/netwerk", label: "Netwerk", icon: "network" },
  { href: "/automatisering", label: "Automatisering", icon: "flow" },
  { href: "/backups", label: "Backups", icon: "backup" },
  { href: "/kosten", label: "Kosten", icon: "costs" },
  { href: "/instellingen", label: "Instellingen", icon: "settings" },
];

/** "Meer" op mobiel: alles uit de zijbalk dat niet in de ondernavigatie staat, plus de onboarding. */
export const MORE_LINKS: NavItem[] = [
  { href: "/onboarding", label: "Onboarding (D01–D18)", icon: "wizard" },
  ...DESKTOP_NAV.filter((i) => i.href !== "/"),
];

/** Kindschil (besluit gebruiker O-05): Home · Kijken · Zoeken · Ik, op elke breedte; verder niets. */
export const KIND_NAV: NavItem[] = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/kijken", label: "Kijken", icon: "kijken" },
  { href: "/zoeken", label: "Zoeken", icon: "zoeken" },
  { href: "/ik", label: "Ik", icon: "ik" },
];
export const KIND_PATHS = KIND_NAV.map((i) => i.href);

/** Routes alleen voor de kindschil (andere rollen krijgen er een gewone 'niet gevonden'). */
export function isKindPath(pathname: string): boolean {
  return KIND_PATHS.includes(normalizePath(pathname));
}

/** Schermen zonder login. */
export const PUBLIC_PATHS = ["/eerste-start", "/inloggen", "/inloggen/nood"];

export function normalizePath(pathname: string): string {
  if (!pathname) return "/";
  const p = pathname.replace(/\/+$/, "");
  return p === "" ? "/" : p;
}

export function isActive(href: string, pathname: string): boolean {
  const p = normalizePath(pathname);
  if (href === "/") return p === "/";
  return p === href || p.startsWith(`${href}/`);
}

/** Actief item van de ondernavigatie; schermen buiten de vier hoofdknoppen vallen onder "Meer". */
export function activeMobileHref(pathname: string): string {
  const p = normalizePath(pathname);
  const direct = MOBILE_NAV.find((i) => i.href !== "/meer" && isActive(i.href, p));
  return direct ? direct.href : "/meer";
}

/** Actief item van de zijbalk; schermen die er niet in staan (Apps, onboarding) vallen onder Server/Instellingen. */
export function activeDesktopHref(pathname: string): string | null {
  const p = normalizePath(pathname);
  const direct = DESKTOP_NAV.find((i) => isActive(i.href, p));
  if (direct) return direct.href;
  if (p.startsWith("/apps")) return "/server";
  if (p.startsWith("/onboarding") || p === "/meer") return "/instellingen";
  return null;
}

export interface PlannedScreen {
  titel: string;
  fase: string;
  wat: string;
  bron: string;
}

/** Schermen die pas in latere fasen komen: eerlijk tonen, nooit nepdata (06_FASERING_EN_GATES). */
export const PLANNED: Record<string, PlannedScreen> = {
  ai: {
    titel: "AI",
    fase: "P2",
    wat: "AI-chat die logs uitlegt en plannen maakt; ‘repareer’ leidt altijd naar een actievoorstel met preview, nooit naar een terminal. AI staat standaard uit.",
    bron: "Risicobeleid R0–R3, policy-engine en de gekoppelde executor (B02).",
  },
  media: {
    titel: "Media",
    fase: "P3 en P4",
    wat: "Film, serie, anime, muziek en Live TV met verder kijken, kwaliteit, downloads en verzoekstatus.",
    bron: "MediaGuard en Media Source Optimizer (P3), Jelly Leon / Jellyfin (P4).",
  },
  huis: {
    titel: "Huis",
    fase: "P3",
    wat: "Per kamer verlichting, temperatuur, luchtvochtigheid, doelen, energie en versheid van sensoren. De boiler wordt alleen gemeten, nooit geschakeld.",
    bron: "my_house (eigenaar van fysieke apparaten en readback).",
  },
  netwerk: {
    titel: "Netwerk",
    fase: "P5",
    wat: "Apparaten in het netwerk, DNS-filtering met een geteste terugvalroute en privacy-instellingen.",
    bron: "AdGuard Home en NetAlertX (B10).",
  },
  automatisering: {
    titel: "Automatisering",
    fase: "P2",
    wat: "Flows zonder code met testmodus, geschiedenis en veiligheidsgrenzen; acties alleen via voorstel en beleid.",
    bron: "Node-RED met door het beleid begrensde actienodes (B11).",
  },
  kosten: {
    titel: "Kosten",
    fase: "P5",
    wat: "Energie en kosten per dag/week/maand, alleen waar echt gemeten of verantwoord afgeleid, met meetdekking.",
    bron: "Energie- en resourcemanager (B14) met de stroommeter uit my_house.",
  },
};

/**
 * Alleen interne paden als terugsprong na inloggen (geen open redirect). Alleen zichtbare ASCII zonder spatie: een
 * browser haalt tab/CR/LF uit een URL, waardoor "/<tab>/evil.lan" anders "//evil.lan" (een ander domein) zou worden.
 */
export function safeReturnPath(raw: string | null): string {
  if (!raw || raw.length > 256 || !/^\/(?![/\\])[!-~]*$/.test(raw) || raw.includes("\\") || raw.includes("://")) return "/";
  if (raw.startsWith("/inloggen") || raw.startsWith("/eerste-start")) return "/";
  return raw;
}
