import { describe, expect, it } from "vitest";
import { alertErnst, alertTone, auditLabel, coverageCounts, freshItems, gpuSummary, homeSummary, oldestObserved, partCount, type CatalogSummary } from "@/lib/home";
import type { Coverage, InventoryKind, Pool, TrueNasStatus } from "@/lib/types";

const connected: TrueNasStatus = {
  nas_url: "wss://nas/api/current",
  nas_adres_bron: "D03",
  api_key: { ingesteld: true, laatste4: "1234", ingesteld_op: null, ingesteld_door: null },
  tls: { modus: "systeem_ca", vingerafdruk: null, bevestigd_door: null, bevestigd_op: null },
  laatste_test: { op: "2026-11-09T10:00:00Z", url: null, status: "ok", reason_code: null, melding: "", advies: "" },
  alleen_lezen: true,
};

function pools(items: Partial<Pool>[], status: "ok" | "unknown" = "ok", verouderd = false): InventoryKind<Pool> {
  return {
    kind: "pools",
    status,
    reason_code: status === "ok" ? null : "unreachable",
    melding: status === "ok" ? "" : "NAS niet bereikbaar.",
    advies: "",
    observed_at: "2026-11-09T10:00:00Z",
    laatste_poging: "2026-11-09T10:00:00Z",
    verouderd,
    bron: { methode: "pool.query", nas: "x" },
    items: items as Pool[],
  };
}

function catalog(per: Partial<CatalogSummary["per_status"]>, verouderd = false): CatalogSummary {
  const per_status = { healthy: 0, degraded: 0, down: 0, unknown: 0, ...per };
  const totaal = Object.values(per_status).reduce((a, b) => a + b, 0);
  return {
    items: [{ id: "1", titel: "Jellyfin", runtime_id: "jellyfin", gezondheid: { status: per.down ? "down" : "healthy", melding: "De app is gestopt in TrueNAS." } }],
    totaal,
    per_status,
    next_cursor: null,
    inventaris: { status: verouderd ? "unknown" : "ok", observed_at: "2026-11-09T10:00:00Z", verouderd, reason_code: null },
    observed_at: "2026-11-09T10:00:00Z",
  };
}

const gezondeBron = [{ id: "k", soort: "uptime_kuma", naam: "Kuma", ingeschakeld: true, status: { status: "ok", reden: null, melding: "", laatste_poging: null, laatste_ok: null, verouderd: false } }];
const geenIncidenten = { per_status: {}, actief: 0, groepen: [], bijgewerkt_op: "2026-11-09T10:00:00Z" };

describe("Home-samenvatting (P1-bronnen, Peil)", () => {
  it("zonder gegevens: Deels onbekend en eerst TrueNAS koppelen", () => {
    const s = homeSummary({});
    expect(s.overall.tone).toBe("unknown");
    expect(s.overall.label).toBe("Deels onbekend");
    expect(s.actions.some((a) => a.href === "/onboarding/truenas")).toBe(true);
  });

  it("alles vers en gezond → ‘Alles gezond’; neutraal (TrueNAS verbonden, kanaal Aan) en nog-niet tellen niet mee", () => {
    const s = homeSummary({
      truenas: connected,
      pools: pools([{ naam: "p", gezond: true, status: "ONLINE" }]),
      alerts: { ...pools([]), kind: "alerts", items: [] } as never,
      catalog: catalog({ healthy: 3 }),
      incidents: geenIncidenten,
      sources: gezondeBron,
      channels: [{ id: "c", naam: "Telefoon", ingeschakeld: true, status: { laatste_status: "ok", laatste_reden: null, melding: "", laatste_op: null } }],
      gates: [{ id: "backup_gate", naam: "Back-upgate", status: "toegestaan", toegestaan: true, redenen: [], afgeleid_op: "" }],
    });
    expect(s.parts.find((p) => p.id === "truenas")?.view.tone).toBe("neutral");
    expect(s.parts.find((p) => p.id === "meldingen")?.view.label).toBe("Aan");
    expect(s.parts.find((p) => p.id === "media")?.view.tone).toBe("not_yet");
    expect(s.overall).toEqual({ tone: "healthy", label: "Alles gezond" });
  });

  it("onbekende apps maken het geheel nooit ‘gezond’", () => {
    const s = homeSummary({ truenas: connected, pools: pools([{ naam: "p", gezond: true }]), catalog: catalog({ healthy: 2, unknown: 1 }), incidents: geenIncidenten, sources: gezondeBron });
    expect(s.parts.find((p) => p.id === "opslag")?.view.tone).toBe("healthy");
    expect(s.parts.find((p) => p.id === "apps")?.view.tone).toBe("unknown");
    expect(s.overall.label).toBe("Deels onbekend");
  });

  it("gemeten beperking weegt zwaarder dan onbekend (OB-06); een gestopte app is Storing", () => {
    expect(homeSummary({ truenas: connected, pools: pools([{ naam: "p", gezond: true, status: "DEGRADED" }]) }).overall.label).toBe("Beperkt");
    const s = homeSummary({ truenas: connected, catalog: catalog({ down: 1, unknown: 2 }) });
    expect(s.overall.label).toBe("Storing");
    expect(s.parts.find((p) => p.id === "apps")?.detail).toContain("Jellyfin");
  });

  it("verouderde inventaris: laatst bekende items blijven (O-03), status Verouderd, en een actie", () => {
    const stale = pools([{ naam: "p", gezond: true }], "unknown", true);
    const f = freshItems(stale);
    expect(f.fresh).toBe(false);
    expect(f.items).toHaveLength(1);
    const s = homeSummary({ truenas: connected, pools: stale });
    expect(s.parts.find((p) => p.id === "opslag")?.view.tone).toBe("stale");
    expect(s.overall.tone).not.toBe("healthy");
    expect(s.actions.some((a) => a.id === "inventaris")).toBe(true);
  });

  it("incidenten: kritiek = Storing en bovenaan in ‘Wat actie nodig heeft’; zonder verse monitoring ‘geen problemen’ = Onbekend", () => {
    const s = homeSummary({
      truenas: connected,
      incidents: { per_status: { open: { kritiek: 1, waarschuwing: 1 } }, actief: 2, groepen: [], bijgewerkt_op: "" },
      activeIncidents: [
        { id: "b", titel: "Waarschuwing", ernst: "waarschuwing", status: "open", actief: true, bron: "x", laatste_gebeurtenis: "2026-11-09T11:00:00Z", aantal_gebeurtenissen: 1 },
        { id: "a", titel: "Kritiek", ernst: "kritiek", status: "open", actief: true, bron: "x", laatste_gebeurtenis: "2026-11-09T10:00:00Z", aantal_gebeurtenissen: 100 },
      ],
      gates: [{ id: "backup_gate", naam: "Back-upgate", status: "geblokkeerd", toegestaan: false, redenen: [{ soort: "besluit", id: "D04", status: "Open", tekst: "D04 is Open" }], afgeleid_op: "" }],
    });
    expect(s.parts.find((p) => p.id === "problemen")?.view.tone).toBe("down");
    expect(s.actions[0]?.href).toBe("/problemen/a");
    expect(s.actions[1]?.href).toBe("/problemen/b");
    const gate = s.actions.find((a) => a.id === "gate-backup_gate");
    expect(gate?.as.soort).toBe("gate");
    expect(s.parts.find((p) => p.id === "backups")?.view.tone).toBe("gate");
    expect(homeSummary({ incidents: geenIncidenten }).parts.find((p) => p.id === "problemen")?.view.tone).toBe("unknown");
  });

  it("monitoring en meldingen: geen bron = Onbekend, bron mislukt = Storing, kanaal gestopt = Storing", () => {
    const s = homeSummary({ sources: [], channels: [] });
    expect(s.parts.find((p) => p.id === "monitoring")?.view.tone).toBe("unknown");
    expect(s.parts.find((p) => p.id === "meldingen")?.view.tone).toBe("unknown");
    const f = homeSummary({
      sources: [{ ...gezondeBron[0]!, naam: "Beszel", status: { status: "fout", reden: "credential_geweigerd", melding: "inloggen geweigerd", laatste_poging: null, laatste_ok: null, verouderd: false } }],
      channels: [{ id: "c", naam: "Telefoon", ingeschakeld: true, status: { laatste_status: "fout", laatste_reden: "token_geweigerd", melding: "", laatste_op: null } }],
    });
    expect(f.parts.find((p) => p.id === "monitoring")?.detail).toContain("Beszel: inloggen geweigerd");
    expect(f.parts.find((p) => p.id === "meldingen")?.view.tone).toBe("down");
  });

  it("mislukte verbindingstest = gemeten falen en een actie", () => {
    const bad = { ...connected, laatste_test: { ...connected.laatste_test!, status: "unknown", melding: "TrueNAS weigerde de API-key." } };
    const s = homeSummary({ truenas: bad });
    expect(s.parts[0]?.view.tone).toBe("down");
    expect(s.actions.find((a) => a.id === "truenas")?.uitleg).toContain("TrueNAS weigerde de API-key.");
  });

  it("dichte gates: de back-upgate apart, de rest als één regel (geen storing, overstemt de lijst niet)", () => {
    const gate = (id: string, naam: string) => ({ id, naam, status: "geblokkeerd" as const, toegestaan: false, redenen: [{ soort: "besluit", id: "D01", status: "Open", tekst: "D01 is Open" }], afgeleid_op: "" });
    const s = homeSummary({ gates: [gate("backup_gate", "Back-upgate"), gate("a", "Gate A"), gate("b", "Gate B"), gate("c", "Gate C"), gate("d", "Gate D")] });
    const gates = s.actions.filter((a) => a.as.soort === "gate");
    expect(gates).toHaveLength(2);
    expect(gates[1]?.titel).toBe("4 gates wachten op een voorwaarde");
    expect(gates[1]?.uitleg).toContain("Dit is geen storing");
  });

  it("telling in één zin en meldingen per niveau", () => {
    const s = homeSummary({});
    expect(partCount(s.parts)).toContain("nog niet beschikbaar");
    expect(alertTone("CRITICAL")).toBe("down");
    expect(alertTone("WARNING")).toBe("degraded");
    expect(alertTone(undefined)).toBe("unknown");
    expect(alertErnst("CRITICAL")).toBe("kritiek");
    expect(alertErnst("WARNING")).toBe("middel");
  });
});

describe("hulpfuncties", () => {
  it("oudste waarneming; ontbreekt er één, dan onbekend", () => {
    expect(oldestObserved(["2026-11-09T10:00:00Z", "2026-11-09T09:00:00Z"])).toBe("2026-11-09T09:00:00Z");
    expect(oldestObserved(["2026-11-09T10:00:00Z", null])).toBeNull();
    expect(oldestObserved([])).toBeNull();
  });

  it("dekking telt alleen als alle bronnen vers zijn", () => {
    const c = {
      apps: [{ volledige_appbackup: false }, { volledige_appbackup: true }],
      datasets: [],
      bronnen: { a: { status: "ok", reason_code: null, observed_at: "2026-11-09T10:00:00Z", verouderd: false } },
      opmerking: "",
      afgeleid_op: "",
    } as unknown as Coverage;
    expect(coverageCounts(c)).toEqual({ totaal: 2, volledig: 1, fresh: true, observedAt: "2026-11-09T10:00:00Z" });
    const stale = { ...c, bronnen: { a: { ...c.bronnen.a!, verouderd: true } } } as Coverage;
    expect(coverageCounts(stale).fresh).toBe(false);
    expect(coverageCounts(undefined).fresh).toBe(false);
  });

  it("GPU- en auditlabels", () => {
    expect(gpuSummary({ fresh: true, items: [{ herkend_als: "a310" }, { herkend_als: null, beschrijving: "X" }] as never, observedAt: null, bron: null, verouderd: false, melding: "" })).toBe("Intel Arc A310, X");
    expect(auditLabel("decision.measured")).toBe("Besluit gemeten");
    expect(auditLabel("nieuw.iets")).toBe("nieuw.iets");
  });
});
