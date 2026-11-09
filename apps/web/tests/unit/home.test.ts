import { describe, expect, it } from "vitest";
import { alertTone, auditLabel, coverageCounts, freshItems, gpuSummary, homeSummary, oldestObserved } from "@/lib/home";
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

describe("Home-samenvatting", () => {
  it("zonder gegevens: onbekend en eerst TrueNAS koppelen", () => {
    const s = homeSummary({});
    expect(s.overall.tone).toBe("unknown");
    expect(s.actions[0]?.href).toBe("/onboarding/truenas");
  });

  it("gezonde pools maken het geheel nooit ‘in orde’ zolang app-gezondheid onbekend is", () => {
    const s = homeSummary({ truenas: connected, pools: pools([{ naam: "p", gezond: true }]) });
    expect(s.parts.find((p) => p.id === "opslag")?.view.tone).toBe("ok");
    expect(s.overall.tone).toBe("unknown");
    expect(s.overall.label).toBe("Deels onbekend");
  });

  it("ongezonde pool → actie nodig", () => {
    const s = homeSummary({ truenas: connected, pools: pools([{ naam: "p", gezond: false }]) });
    expect(s.overall.tone).toBe("bad");
    expect(s.actions.some((a) => a.id === "pools")).toBe(true);
  });

  it("verouderde inventaris telt als onbekend, ook al was de laatste waarde gezond", () => {
    const stale = pools([{ naam: "p", gezond: true }], "unknown", true);
    const f = freshItems(stale);
    expect(f.fresh).toBe(false);
    expect(f.items).toEqual([]);
    const s = homeSummary({ truenas: connected, pools: stale });
    expect(s.parts.find((p) => p.id === "opslag")?.view.tone).toBe("unknown");
    expect(s.actions.some((a) => a.id === "inventaris")).toBe(true);
  });

  it("mislukte verbindingstest is een actie", () => {
    const bad = { ...connected, laatste_test: { ...connected.laatste_test!, status: "unknown", melding: "TrueNAS weigerde de API-key." } };
    const s = homeSummary({ truenas: bad });
    expect(s.actions[0]?.tekst).toContain("TrueNAS weigerde de API-key.");
  });

  it("meldingen per niveau", () => {
    expect(alertTone("CRITICAL")).toBe("bad");
    expect(alertTone("WARNING")).toBe("warn");
    expect(alertTone("INFO")).toBe("info");
    expect(alertTone(undefined)).toBe("unknown");
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
