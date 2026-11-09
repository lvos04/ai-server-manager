/**
 * Afleiding van de Home-samenvatting (S-020, P1-bronnen; HUB_PEIL_ONTWERP §4.6). Puur en getest. Regels:
 * - een onderdeel toont alleen een echte, verse meting of Onbekend; onbekend telt nooit als gezond;
 * - totaalstatus (OB-06) = Storing > Beperkt > Deels onbekend > Alles gezond, nooit beter dan het slechtste onderdeel;
 * - gates die op invulwerk wachten, meldingskanalen ("Aan") en nog-niet-beschikbare onderdelen tellen niet mee.
 */
import {
  ernstVan,
  ERNST_RANG,
  TOTAAL_LABEL,
  worstTone,
  type Ernst,
  type StatusView,
  type Tone,
} from "./status";
import type { AlertInfo, Coverage, DecisionList, Gate, Gpu, InventoryKind, Pool, TrueNasStatus } from "./types";

export interface Fresh<T> {
  fresh: boolean;
  /** Vers: de items; verouderd (O-03): de laatst bekende items (gedempt tonen, nooit als actueel). */
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
    items: fresh || k.verouderd ? (k.items ?? []) : [],
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
  href: string;
}

export interface Action {
  id: string;
  /** As van het item: ernst (incident), gate of onboarding. */
  as: { soort: "ernst"; ernst: Ernst } | { soort: "gate" } | { soort: "onboarding" } | { soort: "onbekend" };
  titel: string;
  uitleg: string;
  href: string;
  knop: string;
}

/** Appcatalogus (GET /api/v1/apps) — alleen wat Home nodig heeft. */
export interface CatalogSummary {
  items: { id: string; titel: string; runtime_id: string; gezondheid: { status: string; melding: string } }[];
  totaal: number;
  per_status: Record<"healthy" | "degraded" | "down" | "unknown", number>;
  next_cursor: string | null;
  inventaris: { status: string | null; observed_at: string | null; verouderd: boolean | null; reason_code: string | null };
  observed_at: string;
}

export interface IncidentSummary {
  per_status: Record<string, Record<string, number>>;
  actief: number;
  groepen: { oorzaak: string; aantal: number; laatste: string }[];
  bijgewerkt_op: string;
}

export interface IncidentItem {
  id: string;
  titel: string;
  ernst: string;
  status: string;
  actief: boolean;
  bron: string;
  laatste_gebeurtenis: string;
  aantal_gebeurtenissen: number;
}

export interface MonitorSource {
  id: string;
  soort: string;
  naam: string;
  ingeschakeld: boolean;
  status: { status: string; reden: string | null; melding: string; laatste_poging: string | null; laatste_ok: string | null; verouderd: boolean; versie?: string | null };
}

export interface Channel {
  id: string;
  naam: string;
  ingeschakeld: boolean;
  status: { laatste_status: string; laatste_reden: string | null; melding: string; laatste_op: string | null };
}

export interface HomeInputs {
  truenas?: TrueNasStatus;
  pools?: InventoryKind<Pool>;
  alerts?: InventoryKind<AlertInfo>;
  catalog?: CatalogSummary;
  incidents?: IncidentSummary;
  activeIncidents?: IncidentItem[];
  sources?: MonitorSource[];
  channels?: Channel[];
  decisions?: DecisionList;
  gates?: Gate[];
  coverage?: Coverage;
}

export function alertTone(niveau: string | null | undefined): Tone {
  const n = (niveau ?? "").toUpperCase();
  if (["CRITICAL", "ERROR", "ALERT", "EMERGENCY"].includes(n)) return "down";
  if (n === "WARNING") return "degraded";
  if (n === "NOTICE" || n === "INFO") return "neutral";
  return "unknown";
}

/** TrueNAS-meldingsniveau → ErnstLabel (vaste woorden). */
export function alertErnst(niveau: string | null | undefined): Ernst {
  const n = (niveau ?? "").toUpperCase();
  if (["CRITICAL", "ALERT", "EMERGENCY"].includes(n)) return "kritiek";
  if (n === "ERROR") return "hoog";
  if (n === "WARNING") return "middel";
  if (n === "NOTICE") return "laag";
  return "info";
}

const v = (tone: Tone, label: string, icon?: StatusView["icon"]): StatusView => ({ tone, label, icon });

function poolPart(inp: HomeInputs): Part {
  const pools = freshItems(inp.pools);
  const base = { id: "opslag", label: "Opslag", href: "/server#pools" };
  if (!inp.pools) return { ...base, view: v("unknown", "Onbekend"), detail: "Nog niet geladen." };
  if (pools.verouderd) return { ...base, view: v("stale", "Verouderd"), detail: `Laatst bekend: ${pools.items.length} pool(s). ${pools.melding}` };
  if (!pools.fresh || pools.items.length === 0) return { ...base, view: v("unknown", "Onbekend"), detail: pools.melding || "Geen pools gemeten." };
  const down = pools.items.filter((p) => p.gezond === false || ["FAULTED", "UNAVAIL", "OFFLINE"].includes((p.status ?? "").toUpperCase()));
  const degraded = pools.items.filter((p) => (p.status ?? "").toUpperCase() === "DEGRADED");
  if (down.length) return { ...base, view: v("down", "Storing"), detail: `Storing: ${down.map((p) => p.naam).join(", ")} (pool.query).` };
  if (degraded.length) return { ...base, view: v("degraded", "Beperkt"), detail: `Beperkt: ${degraded.map((p) => p.naam).join(", ")} (DEGRADED).` };
  return { ...base, view: v("healthy", "Gezond"), detail: `${pools.items.length} pool(s) gezond volgens pool.query.` };
}

function appsPart(inp: HomeInputs): Part {
  const base = { id: "apps", label: "Apps", href: "/apps" };
  const c = inp.catalog;
  if (!c) return { ...base, view: v("unknown", "Onbekend"), detail: "Catalogus niet geladen." };
  if (c.inventaris.verouderd || c.inventaris.status !== "ok")
    return { ...base, view: v(c.inventaris.verouderd ? "stale" : "unknown", c.inventaris.verouderd ? "Verouderd" : "Onbekend"), detail: "De inventaris is niet vers; de gezondheid per app is daardoor onbekend." };
  if (c.totaal === 0) return { ...base, view: v("unknown", "Onbekend"), detail: "Nog geen apps in de catalogus." };
  const ps = c.per_status;
  const worst = (s: string) => c.items.find((a) => a.gezondheid.status === s);
  if (ps.down) {
    const a = worst("down");
    return { ...base, view: v("down", "Storing"), detail: `${ps.down} met storing${a ? `, o.a. ${a.titel}: ${a.gezondheid.melding}` : ""}` };
  }
  if (ps.degraded) {
    const a = worst("degraded");
    return { ...base, view: v("degraded", "Beperkt"), detail: `${ps.degraded} beperkt${a ? `, o.a. ${a.titel}: ${a.gezondheid.melding}` : ""}` };
  }
  if (ps.unknown) return { ...base, view: v("unknown", "Onbekend"), detail: `${ps.unknown} van ${c.totaal} apps onbekend (geen verse controle).` };
  return { ...base, view: v("healthy", "Gezond"), detail: `${c.totaal} apps gezond (gemeten).` };
}

function incidentsPart(inp: HomeInputs, monitoringFresh: boolean): Part {
  const base = { id: "problemen", label: "Problemen", href: "/problemen" };
  const s = inp.incidents;
  if (!s) return { ...base, view: v("unknown", "Onbekend"), detail: "Niet geladen." };
  let kritiek = 0;
  let waarschuwing = 0;
  for (const per of Object.values(s.per_status)) {
    kritiek += per["kritiek"] ?? 0;
    waarschuwing += per["waarschuwing"] ?? 0;
  }
  if (kritiek) return { ...base, view: v("down", "Storing"), detail: `${s.actief} actief, waarvan ${kritiek} kritiek.` };
  if (waarschuwing) return { ...base, view: v("degraded", "Beperkt"), detail: `${s.actief} actief, waarvan ${waarschuwing} met ernst middel.` };
  if (s.actief) return { ...base, view: v("neutral", `${s.actief} ter info`, "open"), detail: `${s.actief} actief (ernst info).` };
  if (!monitoringFresh) return { ...base, view: v("unknown", "Onbekend"), detail: "Geen actieve problemen bekend, maar de monitoring is niet vers: we weten het niet zeker." };
  return { ...base, view: v("healthy", "Gezond"), detail: "Geen actieve problemen." };
}

function monitoringPart(inp: HomeInputs): Part {
  const base = { id: "monitoring", label: "Monitoring", href: "/instellingen/monitoring" };
  const src = (inp.sources ?? []).filter((s) => s.ingeschakeld);
  if (!inp.sources) return { ...base, view: v("unknown", "Onbekend"), detail: "Niet geladen." };
  if (!src.length) return { ...base, view: v("unknown", "Onbekend"), detail: "Geen monitoringbron ingesteld (Uptime Kuma of Beszel)." };
  const failed = src.filter((s) => s.status.status === "fout" || s.status.status === "down" || (s.status.reden && s.status.status !== "ok"));
  if (failed.length) return { ...base, view: v("down", "Storing"), detail: failed.map((s) => `${s.naam}: ${s.status.melding || s.status.reden || "uitlezen mislukt"}`).join(" · ") };
  const stale = src.filter((s) => s.status.verouderd || s.status.status !== "ok");
  if (stale.length) return { ...base, view: v("stale", "Verouderd"), detail: `${stale.map((s) => s.naam).join(", ")}: geen verse uitlezing.` };
  return { ...base, view: v("healthy", "Gezond"), detail: `${src.length} bron(nen) uitgelezen.` };
}

function channelsPart(inp: HomeInputs): Part {
  const base = { id: "meldingen", label: "Meldingen", href: "/instellingen/monitoring#meldingen" };
  if (!inp.channels) return { ...base, view: v("unknown", "Onbekend"), detail: "Niet geladen." };
  const on = inp.channels.filter((c) => c.ingeschakeld);
  if (!on.length) return { ...base, view: v("unknown", "Onbekend"), detail: "Geen meldingskanaal ingesteld (Gotify)." };
  const stopped = on.filter((c) => c.status.laatste_reden === "token_geweigerd" || c.status.laatste_status === "gestopt");
  if (stopped.length) return { ...base, view: v("down", "Storing"), detail: `Kanaal gestopt: ${stopped.map((c) => c.naam).join(", ")} (token geweigerd).` };
  // Een kanaal is geen gezondheid: neutraal "Aan", telt niet mee.
  return { ...base, view: v("neutral", "Aan", "aan"), detail: `${on.length} kanaal/kanalen aan. Of meldingen aankomen, kan de Hub niet zien.` };
}

function backupPart(inp: HomeInputs): Part {
  const base = { id: "backups", label: "Back-ups", href: "/backups" };
  const g = inp.gates?.find((x) => x.id === "backup_gate");
  if (!g) return { ...base, view: v("unknown", "Onbekend"), detail: "Back-upgate niet geladen." };
  if (g.toegestaan) return { ...base, view: v("neutral", "Gate open", "slot-open"), detail: "Voorwaarden voor back-ups aangetoond." };
  // Alleen een gemeten falen (pool niet gezond, EX11) is een storing; een ontbrekende back-up of een open besluit is een
  // voorwaarde (gate), geen storing.
  const measured = g.redenen.find((r) => r.soort === "meting" && r.id === "pools" && r.status === "geblokkeerd");
  if (measured) return { ...base, view: v("down", "Storing"), detail: measured.tekst };
  return { ...base, view: v("gate", "Gate dicht"), detail: `${g.redenen[0]?.tekst ?? "Voorwaarden niet aangetoond."} Dit is geen storing; er wacht een voorwaarde.` };
}

function truenasPart(inp: HomeInputs): Part {
  const base = { id: "truenas", label: "TrueNAS-koppeling", href: "/onboarding/truenas" };
  const t = inp.truenas;
  if (!t || !t.nas_url || !t.api_key.ingesteld) return { ...base, view: v("unknown", "Niet ingesteld"), detail: "Nog geen NAS-adres (D03) of alleen-lezen-key." };
  if (t.laatste_test?.status === "ok") return { ...base, view: v("neutral", "Verbonden (alleen-lezen)", "gekoppeld"), detail: "Laatste verbindingstest geslaagd." };
  if (t.laatste_test) return { ...base, view: v("down", "Storing"), detail: t.laatste_test.melding || "Verbindingstest mislukt." };
  return { ...base, view: v("unknown", "Niet bevestigd"), detail: "Nog niet getest." };
}

function alertsPart(inp: HomeInputs): Part {
  const base = { id: "nasmeldingen", label: "TrueNAS-meldingen", href: "/server#meldingen" };
  const a = freshItems(inp.alerts);
  if (!a.fresh) return { ...base, view: v(a.verouderd ? "stale" : "unknown", a.verouderd ? "Verouderd" : "Onbekend"), detail: a.melding };
  const open = a.items.filter((x) => !x.genegeerd);
  if (!open.length) return { ...base, view: v("healthy", "Gezond"), detail: "Geen open meldingen (alert.list)." };
  const tone = worstTone(open.map((x) => alertTone(x.niveau)));
  return { ...base, view: v(tone, tone === "down" ? "Storing" : tone === "degraded" ? "Beperkt" : tone === "healthy" ? "Gezond" : "Onbekend"), detail: `${open.length} open: ${open[0]?.tekst ?? ""}` };
}

const NOT_YET: Part[] = [
  { id: "media", label: "Media", href: "/media", view: v("not_yet", "Nog niet beschikbaar"), detail: "Volgt in fase P3 (MediaGuard, MSO) en P4 (Jelly Leon)." },
  { id: "huis", label: "Huis", href: "/huis", view: v("not_yet", "Nog niet beschikbaar"), detail: "Volgt in fase P3 (my_house)." },
  { id: "netwerk", label: "Netwerk", href: "/netwerk", view: v("not_yet", "Nog niet beschikbaar"), detail: "Volgt in fase P5." },
];

export function homeSummary(inp: HomeInputs): { overall: StatusView & { tone: "healthy" | "degraded" | "down" | "unknown" }; parts: Part[]; actions: Action[] } {
  const monitoring = monitoringPart(inp);
  const monitoringFresh = monitoring.view.tone === "healthy";
  const parts: Part[] = [
    truenasPart(inp),
    appsPart(inp),
    poolPart(inp),
    incidentsPart(inp, monitoringFresh),
    monitoring,
    channelsPart(inp),
    alertsPart(inp),
    backupPart(inp),
    ...NOT_YET,
  ];
  const actions: Action[] = [];

  // 1. Actieve incidenten, kritiek eerst.
  const inc = [...(inp.activeIncidents ?? [])].filter((i) => i.actief);
  inc.sort((a, b) => ERNST_RANG[ernstVan(a.ernst)] - ERNST_RANG[ernstVan(b.ernst)] || Date.parse(b.laatste_gebeurtenis) - Date.parse(a.laatste_gebeurtenis));
  for (const i of inc.slice(0, 5)) {
    actions.push({
      id: `incident-${i.id}`,
      as: { soort: "ernst", ernst: ernstVan(i.ernst) },
      titel: i.titel,
      uitleg: `${i.bron} · ${i.aantal_gebeurtenissen}× gezien`,
      href: `/problemen/${i.id}`,
      knop: "Incident bekijken",
    });
  }
  // 2. (P2: goedkeuringen.) 3. Dichte gates: de back-upgate apart, de rest samen (anders overstemmen ze de lijst).
  const dicht = (inp.gates ?? []).filter((g) => !g.toegestaan);
  const backup = dicht.find((g) => g.id === "backup_gate");
  if (backup) {
    actions.push({
      id: "gate-backup_gate",
      as: { soort: "gate" },
      titel: `Geblokkeerd door de ${backup.naam.toLowerCase()}`,
      uitleg: backup.redenen[0]?.tekst ?? "Voorwaarden niet aangetoond.",
      href: "/backups",
      knop: "Invullen",
    });
  }
  const overig = dicht.filter((g) => g.id !== "backup_gate");
  if (overig.length) {
    actions.push({
      id: "gates",
      as: { soort: "gate" },
      titel: `${overig.length} ${overig.length === 1 ? "gate wacht" : "gates wachten"} op een voorwaarde`,
      uitleg: `${overig.slice(0, 3).map((g) => g.naam).join(", ")}${overig.length > 3 ? ` en nog ${overig.length - 3}` : ""}. Dit is geen storing.`,
      href: "/onboarding#gates",
      knop: "Invullen",
    });
  }
  // 4. TrueNAS-koppeling en onboarding.
  const t = parts[0]!;
  if (t.view.tone === "unknown" || t.view.tone === "down") {
    actions.push({ id: "truenas", as: { soort: "onboarding" }, titel: "TrueNAS koppelen (alleen-lezen)", uitleg: t.detail, href: "/onboarding/truenas", knop: "Onboarding verder" });
  }
  const pools = freshItems(inp.pools);
  if (inp.pools && !pools.fresh && t.view.tone !== "unknown") {
    actions.push({ id: "inventaris", as: { soort: "onbekend" }, titel: "Inventaris onbekend of verouderd", uitleg: "Vernieuw de inventaris (alleen-lezen).", href: "/server", knop: "Inventaris vernieuwen" });
  }
  if (inp.decisions) {
    const open = inp.decisions.items.filter((d) => d.status === "Open").length;
    if (open > 0) {
      actions.push({
        id: "onboarding",
        as: { soort: "onboarding" },
        titel: `${open} van ${inp.decisions.items.length} besluiten staan nog open`,
        uitleg: "Vul ze in of laat de Hub ze alleen-lezen meten.",
        href: "/onboarding",
        knop: "Onboarding verder",
      });
    }
  }

  const tone = worstTone(parts.map((p) => p.view.tone));
  return { overall: { tone, label: TOTAAL_LABEL[tone] }, parts, actions };
}

/** Telling in één zin: "1 storing · 1 beperkt · 1 onbekend · 3 gezond · 3 nog niet beschikbaar". */
export function partCount(parts: Part[]): string {
  const c = (f: (t: Tone) => boolean) => parts.filter((p) => f(p.view.tone)).length;
  const out: string[] = [];
  const add = (n: number, w: string) => n && out.push(`${n} ${w}`);
  add(c((t) => t === "down"), "storing");
  add(c((t) => t === "degraded"), "beperkt");
  add(c((t) => t === "unknown" || t === "stale" || t === "unlinked"), "onbekend");
  add(c((t) => t === "healthy"), "gezond");
  add(c((t) => t === "not_yet"), "nog niet beschikbaar");
  return out.join(" · ");
}

/** Oudste waarneming van een set bronnen: "bijgewerkt" is nooit verser dan de oudste bron. */
export function oldestObserved(values: (string | null | undefined)[]): string | null {
  const ts = values.filter((x): x is string => Boolean(x)).map((x) => [x, Date.parse(x)] as const).filter(([, n]) => !Number.isNaN(n));
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

export function gpuLabel(x: Pick<Gpu, "herkend_als" | "beschrijving" | "pci_slot">): string {
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
  "auth.break_glass.used": "Noodlogin gebruikt",
  "auth.break_glass.setup": "Noodaccount ingesteld",
  "auth.break_glass.confirmed": "Noodaccount-TOTP bevestigd",
  "auth.break_glass.rotated": "Noodaccount vernieuwd",
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
  "auth.oidc.updated": "SSO-instellingen gewijzigd",
  "auth.oidc.discovered": "SSO-issuer gecontroleerd",
  "auth.oidc.discover_failed": "SSO-issuercontrole mislukt",
  "auth.oidc.tested": "SSO-testlogin",
  "auth.oidc.enabled": "SSO aangezet",
  "monitoring.source.tested": "Monitoringbron getest",
  "notification.channel.tested": "Testmelding verstuurd",
  "catalog.discovery": "Appcatalogus bijgewerkt",
  "backup.self_requested": "Hub-back-up gestart",
  "backup.self_reverified": "Hub-back-up opnieuw geverifieerd",
  "backup.restore_test_recorded": "Hersteltest vastgelegd",
  "service.enrollment_token_created": "Enrollment-token gemaakt",
  "service.pairing_code_created": "Koppelcode gemaakt",
  "service.enrolled": "Dienst gekoppeld",
  "service.rotation_requested": "Rotatie aangevraagd",
  "service.revoked": "Dienst ingetrokken",
  "service.unlinked": "Dienst ontkoppeld",
  "service.unlink_failed": "Ontkoppelen mislukt",
  "incident.acknowledged": "Incident erkend",
  "incident.resolved": "Incident opgelost",
  "monitoring.source_created": "Monitoringbron toegevoegd",
  "notification.channel_created": "Meldingskanaal toegevoegd",
};

/** Nederlandse omschrijving van een auditactie; onbekende acties tonen hun technische naam. */
export function auditLabel(action: string): string {
  return AUDIT_LABEL[action] ?? action;
}
