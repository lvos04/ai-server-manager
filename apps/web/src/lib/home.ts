/**
 * Afleiding van de Home-samenvatting. Puur en getest. Regel: een kaart toont alleen een echte, verse waarde of
 * "onbekend"; onbekend telt nooit als groen, en de totaalstatus is nooit beter dan het slechtste onderdeel.
 */
import { worstTone, type StatusView, type Tone } from "./status";
import type { AlertInfo, AppInfo, Coverage, DecisionList, Gate, Gpu, InventoryKind, Pool, TrueNasStatus } from "./types";

export interface Fresh<T> {
  fresh: boolean;
  items: T[];
  observedAt: string | null;
  bron: string | null;
  verouderd: boolean;
  melding: string;
}

export function freshItems<T>(k: InventoryKind<T> | undefined): Fresh<T> {
  if (!k) return { fresh: false, items: [], observedAt: null, bron: null, verouderd: false, melding: "Niet geladen." };
  const fresh = k.status === "ok" && !k.verouderd;
  return {
    fresh,
    items: fresh ? (k.items ?? []) : [],
    observedAt: k.observed_at,
    bron: k.bron?.methode ? `TrueNAS ${k.bron.methode}` : null,
    verouderd: k.verouderd,
    melding: fresh ? "" : k.melding || "Onbekend.",
  };
}

export interface Part {
  id: string;
  label: string;
  view: StatusView;
  detail: string;
}

export interface Action {
  id: string;
  tekst: string;
  href: string;
  tone: Tone;
}

export interface HomeInputs {
  truenas?: TrueNasStatus;
  pools?: InventoryKind<Pool>;
  apps?: InventoryKind<AppInfo>;
  alerts?: InventoryKind<AlertInfo>;
  decisions?: DecisionList;
  gates?: Gate[];
  coverage?: Coverage;
}

export function alertTone(niveau: string | null | undefined): Tone {
  const n = (niveau ?? "").toUpperCase();
  if (["CRITICAL", "ERROR", "ALERT", "EMERGENCY"].includes(n)) return "bad";
  if (n === "WARNING") return "warn";
  if (n === "NOTICE" || n === "INFO") return "info";
  return "unknown";
}

export function homeSummary(inp: HomeInputs): { overall: StatusView; parts: Part[]; actions: Action[] } {
  const parts: Part[] = [];
  const actions: Action[] = [];

  // TrueNAS-koppeling
  const t = inp.truenas;
  if (!t || !t.nas_url || !t.api_key.ingesteld) {
    parts.push({ id: "truenas", label: "TrueNAS-koppeling", view: { tone: "unknown", label: "Niet ingesteld" }, detail: "Nog geen NAS-adres (D03) of alleen-lezen-key." });
    actions.push({ id: "truenas", tekst: "Koppel TrueNAS (alleen-lezen) om de server te kunnen zien.", href: "/onboarding/truenas", tone: "unknown" });
  } else if (t.laatste_test?.status === "ok") {
    parts.push({ id: "truenas", label: "TrueNAS-koppeling", view: { tone: "ok", label: "Verbonden (alleen-lezen)" }, detail: "Laatste verbindingstest geslaagd." });
  } else {
    const melding = t.laatste_test?.melding || "Nog niet getest.";
    parts.push({ id: "truenas", label: "TrueNAS-koppeling", view: { tone: "unknown", label: "Niet bevestigd" }, detail: melding });
    actions.push({ id: "truenas", tekst: `TrueNAS-koppeling controleren: ${melding}`, href: "/onboarding/truenas", tone: "unknown" });
  }

  // Opslag
  const pools = freshItems(inp.pools);
  if (!pools.fresh || pools.items.length === 0) {
    parts.push({ id: "opslag", label: "Opslag (pools)", view: { tone: "unknown", label: "Onbekend" }, detail: pools.melding || "Geen pools gemeten." });
  } else {
    const bad = pools.items.filter((p) => p.gezond !== true);
    parts.push({
      id: "opslag",
      label: "Opslag (pools)",
      view: bad.length ? { tone: "bad", label: "Niet gezond" } : { tone: "ok", label: "Gezond (gemeten)" },
      detail: bad.length ? `Niet gezond: ${bad.map((p) => p.naam).join(", ")}` : `${pools.items.length} pool(s) gezond volgens pool.query.`,
    });
    if (bad.length) actions.push({ id: "pools", tekst: `Pool niet gezond: ${bad.map((p) => p.naam).join(", ")}. Geen opslagwijzigingen tot dit is opgelost.`, href: "/server#pools", tone: "bad" });
  }

  // Apps: de TrueNAS-staat is geen gezondheid; die volgt pas via connectors (P1/P3).
  parts.push({ id: "apps", label: "App-gezondheid", view: { tone: "unknown", label: "Onbekend" }, detail: "Gezondheid per app volgt via monitoring (P1) en connectors (P3); de TrueNAS-staat alleen is geen bewijs." });

  // TrueNAS-meldingen
  const alerts = freshItems(inp.alerts);
  if (alerts.fresh) {
    const open = alerts.items.filter((a) => !a.genegeerd);
    const tone = open.length ? worstTone(open.map((a) => alertTone(a.niveau))) : "ok";
    parts.push({ id: "meldingen", label: "TrueNAS-meldingen", view: { tone, label: open.length ? `${open.length} open` : "Geen open meldingen" }, detail: open[0]?.tekst ?? "alert.list leeg." });
    if (open.length) actions.push({ id: "meldingen", tekst: `${open.length} TrueNAS-melding(en) bekijken.`, href: "/server#meldingen", tone: tone === "ok" ? "info" : tone });
  } else {
    parts.push({ id: "meldingen", label: "TrueNAS-meldingen", view: { tone: "unknown", label: "Onbekend" }, detail: alerts.melding });
  }

  if (inp.pools && !pools.fresh && t?.nas_url && t.api_key.ingesteld) {
    actions.push({ id: "inventaris", tekst: "De inventaris is onbekend of verouderd. Vernieuw hem.", href: "/server", tone: "unknown" });
  }

  // Onboarding
  if (inp.decisions) {
    const open = inp.decisions.items.filter((d) => d.status === "Open").length;
    if (open > 0) actions.push({ id: "onboarding", tekst: `${open} van ${inp.decisions.items.length} besluiten staan nog open in de onboarding.`, href: "/onboarding", tone: "warn" });
  }

  // Back-upgate
  const bg = inp.gates?.find((g) => g.id === "backup_gate");
  if (bg && !bg.toegestaan) {
    actions.push({ id: "backup_gate", tekst: `Back-upgate dicht: ${bg.redenen[0]?.tekst ?? "voorwaarden niet aangetoond"}`, href: "/backups", tone: bg.status === "geblokkeerd" ? "bad" : "unknown" });
  }

  const tone = worstTone(parts.map((p) => p.view.tone));
  const label: Record<Tone, string> = {
    bad: "Actie nodig",
    unknown: "Deels onbekend",
    warn: "Aandacht nodig",
    info: "Aandacht nodig",
    neutral: "Deels onbekend",
    ok: "In orde (gemeten)",
  };
  return { overall: { tone, label: label[tone] }, parts, actions };
}

/** Oudste waarneming van een set bronnen: "laatst bijgewerkt" is nooit verser dan de oudste bron. */
export function oldestObserved(values: (string | null | undefined)[]): string | null {
  const ts = values.filter((v): v is string => Boolean(v)).map((v) => [v, Date.parse(v)] as const).filter(([, n]) => !Number.isNaN(n));
  if (!ts.length || ts.length < values.length) return null;
  return ts.reduce((a, b) => (b[1] < a[1] ? b : a))[0];
}

export function coverageCounts(c: Coverage | undefined): { totaal: number; volledig: number; fresh: boolean; observedAt: string | null } {
  if (!c) return { totaal: 0, volledig: 0, fresh: false, observedAt: null };
  const bronnen = Object.values(c.bronnen ?? {});
  const fresh = bronnen.length > 0 && bronnen.every((b) => b.status === "ok" && !b.verouderd);
  return {
    totaal: c.apps.length,
    volledig: c.apps.filter((a) => a.volledige_appbackup).length,
    fresh,
    observedAt: oldestObserved(bronnen.map((b) => b.observed_at)),
  };
}

const GPU_LABEL: Record<string, string> = { a310: "Intel Arc A310", uhd770: "Intel UHD 770" };

export function gpuLabel(x: Gpu): string {
  return (x.herkend_als && GPU_LABEL[x.herkend_als]) || x.beschrijving || x.pci_slot || "onbekend";
}

export function gpuSummary(g: Fresh<Gpu>): string {
  return g.items.map(gpuLabel).join(", ");
}

const AUDIT_LABEL: Record<string, string> = {
  "setup.admin_created": "Eerste beheerder aangemaakt",
  "auth.login": "Ingelogd",
  "auth.login_failed": "Mislukte inlogpoging",
  "auth.logout": "Uitgelogd",
  "auth.password_changed": "Wachtwoord gewijzigd",
  "auth.session_revoked": "Sessie ingetrokken",
  "user.created": "Gebruiker aangemaakt",
  "user.updated": "Gebruiker gewijzigd",
  "decision.value_set": "Besluit ingevuld",
  "decision.status_set": "Status van besluit gewijzigd",
  "decision.evidence_added": "Bewijs vastgelegd",
  "decision.measured": "Besluit gemeten",
  "truenas.api_key_set": "TrueNAS-key ingesteld",
  "truenas.tested": "TrueNAS-verbinding getest",
  "truenas.tls_trusted": "TrueNAS-certificaat vertrouwd",
  "truenas.tls_untrusted": "Vertrouwen certificaat ingetrokken",
  "inventory.refresh_requested": "Inventaris vernieuwd",
  "backup.self_requested": "Hub-back-up gestart",
  "backup.self_reverified": "Hub-back-up opnieuw geverifieerd",
  "backup.restore_test_recorded": "Hersteltest vastgelegd",
};

/** Nederlandse omschrijving van een auditactie; onbekende acties tonen hun technische naam. */
export function auditLabel(action: string): string {
  return AUDIT_LABEL[action] ?? action;
}
