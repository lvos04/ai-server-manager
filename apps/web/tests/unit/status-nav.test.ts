import { describe, expect, it } from "vitest";
import { activeDesktopHref, activeMobileHref, DESKTOP_NAV, isActive, isKindPath, KIND_NAV, MOBILE_NAV, MORE_LINKS, PLANNED, PRODUCT, PUBLIC_PATHS, safeReturnPath } from "@/lib/nav";
import {
  appState,
  coverageStatus,
  decisionStatus,
  ernstVan,
  gateStatus,
  healthView,
  kindStatus,
  measurementStatus,
  poolHealth,
  testResult,
  TOTAAL_LABEL,
  worstTone,
  zekerheidVan,
  ZEKERHEID_LABEL,
} from "@/lib/status";

describe("navigatie exact volgens 08_UI", () => {
  it("mobiel: Home, Apps, Problemen, AI, Meer", () => {
    expect(MOBILE_NAV.map((i) => i.label)).toEqual(["Home", "Apps", "Problemen", "AI", "Meer"]);
  });

  it("desktop: Home, Server, Media, Huis, Netwerk, Automatisering, Backups, Kosten, Instellingen", () => {
    expect(DESKTOP_NAV.map((i) => i.label)).toEqual([
      "Home", "Server", "Media", "Huis", "Netwerk", "Automatisering", "Backups", "Kosten", "Instellingen",
    ]);
  });

  it("‘Meer’ bevat alles uit de zijbalk behalve Home, plus de onboarding", () => {
    const hrefs = MORE_LINKS.map((i) => i.href);
    for (const item of DESKTOP_NAV.filter((i) => i.href !== "/")) expect(hrefs).toContain(item.href);
    expect(hrefs).toContain("/onboarding");
  });

  it("actief menu-item", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/", "/server")).toBe(false);
    expect(isActive("/onboarding", "/onboarding/besluit/D03/")).toBe(true);
    expect(activeMobileHref("/server")).toBe("/meer");
    expect(activeMobileHref("/apps")).toBe("/apps");
    expect(activeMobileHref("/")).toBe("/");
    expect(activeDesktopHref("/apps")).toBe("/server");
    expect(activeDesktopHref("/onboarding/truenas")).toBe("/instellingen");
    expect(activeDesktopHref("/problemen")).toBeNull();
  });

  it("kindschil: Home · Kijken · Zoeken · Ik (O-05); productnaam (O-07); noodlogin publiek", () => {
    expect(KIND_NAV.map((i) => i.label)).toEqual(["Home", "Kijken", "Zoeken", "Ik"]);
    expect(isKindPath("/kijken")).toBe(true);
    expect(isKindPath("/server")).toBe(false);
    expect(PRODUCT).toBe("TrueNAS Home Platform");
    expect(PUBLIC_PATHS).toContain("/inloggen/nood");
  });

  it("latere fasen volgens 06_FASERING (Problemen is in P1 echt)", () => {
    expect(PLANNED.problemen).toBeUndefined();
    expect(PLANNED.ai?.fase).toBe("P2");
    expect(PLANNED.automatisering?.fase).toBe("P2");
    expect(PLANNED.huis?.fase).toBe("P3");
    expect(PLANNED.netwerk?.fase).toBe("P5");
    expect(PLANNED.kosten?.fase).toBe("P5");
  });

  it("terugsprong na inloggen alleen naar interne paden (geen open redirect)", () => {
    expect(safeReturnPath("/server")).toBe("/server");
    expect(safeReturnPath(null)).toBe("/");
    expect(safeReturnPath("https://kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("//kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/\\kwaadaardig")).toBe("/");
    expect(safeReturnPath("/inloggen?terug=/x")).toBe("/");
    // Tab/CR/LF verdwijnen in de browser uit een URL: "/\t/evil" zou "//evil" (ander domein) worden.
    expect(safeReturnPath("/\t/kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/\n/kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/\r/kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/ /kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/x/https://kwaadaardig.example")).toBe("/");
    expect(safeReturnPath("/" + "a".repeat(300))).toBe("/");
    expect(safeReturnPath("/apps/3?tab=logs")).toBe("/apps/3?tab=logs");
  });
});

describe("statussen in Peil: groen alleen voor gemeten en goed", () => {
  it("inventaris: vers = geen badge, verouderd = Verouderd, anders Onbekend", () => {
    expect(kindStatus("ok")).toBeNull();
    expect(kindStatus("ok", true)?.tone).toBe("stale");
    expect(kindStatus("unknown")?.tone).toBe("unknown");
    expect(kindStatus(undefined)?.label).toBe("Onbekend");
  });

  it("pool: alleen gezond als vers gemeten; DEGRADED = Beperkt; FAULTED = Storing", () => {
    expect(poolHealth(true, true).tone).toBe("healthy");
    expect(poolHealth(true, false).tone).toBe("unknown");
    expect(poolHealth(false, true)).toEqual({ tone: "down", label: "Storing" });
    expect(poolHealth(true, true, "DEGRADED").label).toBe("Beperkt");
    expect(poolHealth(false, true, "FAULTED").tone).toBe("down");
    expect(poolHealth(null, true).tone).toBe("unknown");
  });

  it("‘Draait’ volgens TrueNAS is een neutrale pil, nooit gezond; gecrasht = Storing", () => {
    expect(appState("draait")).toEqual({ tone: "neutral", label: "Draait", icon: "draait" });
    expect(appState("RUNNING").tone).toBe("neutral");
    expect(appState("gecrasht").tone).toBe("down");
    expect(appState("iets").tone).toBe("unknown");
  });

  it("besluiten en gates zijn nooit rood of groen; open is geen storing", () => {
    for (const st of ["Open", "Ingevuld", "Getest", "N.v.t."]) expect(decisionStatus(st).tone).toBe("neutral");
    expect(decisionStatus("Geblokkeerd").tone).toBe("gate");
    expect(gateStatus("toegestaan").tone).toBe("neutral");
    expect(gateStatus("geblokkeerd").tone).toBe("gate");
    expect(gateStatus("unknown").tone).toBe("unknown");
  });

  it("dekking, metingen en hersteltests: geslaagd is neutraal, gemeten falen is Storing/Beperkt", () => {
    expect(coverageStatus("gedekt").tone).toBe("neutral");
    expect(coverageStatus("overschreden").tone).toBe("degraded");
    expect(coverageStatus("verouderd").tone).toBe("stale");
    expect(coverageStatus("unknown").tone).toBe("unknown");
    expect(measurementStatus("geslaagd").tone).toBe("neutral");
    expect(measurementStatus("voorstel").tone).toBe("info");
    expect(measurementStatus("mislukt").tone).toBe("down");
    expect(testResult("geslaagd").tone).toBe("neutral");
    expect(testResult(undefined).tone).toBe("unknown");
  });

  it("API-gezondheid: verouderd gaat altijd voor, onbekende waarden zijn Onbekend", () => {
    expect(healthView("healthy").label).toBe("Gezond");
    expect(healthView("healthy", true).tone).toBe("stale");
    expect(healthView("degraded").label).toBe("Beperkt");
    expect(healthView("down").label).toBe("Storing");
    expect(healthView("iets").tone).toBe("unknown");
  });

  it("totaalstatus (OB-06): Storing > Beperkt > Deels onbekend > Alles gezond; neutraal telt niet mee", () => {
    expect(worstTone(["healthy", "unknown"])).toBe("unknown");
    expect(worstTone(["healthy", "unknown", "degraded"])).toBe("degraded");
    expect(worstTone(["healthy", "down", "degraded"])).toBe("down");
    expect(worstTone(["healthy", "stale"])).toBe("unknown");
    expect(worstTone(["healthy", "neutral", "gate", "not_yet", "info"])).toBe("healthy");
    expect(worstTone(["neutral"])).toBe("unknown");
    expect(worstTone([])).toBe("unknown");
    expect(TOTAAL_LABEL.healthy).toBe("Alles gezond");
    expect(TOTAAL_LABEL.unknown).toBe("Deels onbekend");
  });

  it("ernst (OB-05) en zekerheid als woord, nooit als percentage (OB-04)", () => {
    expect(ernstVan("kritiek")).toBe("kritiek");
    expect(ernstVan("waarschuwing")).toBe("middel");
    expect(ernstVan("info")).toBe("info");
    expect(zekerheidVan(0.9)).toBe("zeker");
    expect(zekerheidVan(0.85)).toBe("zeker");
    expect(zekerheidVan(0.6)).toBe("waarschijnlijk");
    expect(zekerheidVan(0.5)).toBe("onzeker");
    expect(zekerheidVan(null)).toBe("weet_niet");
    expect(ZEKERHEID_LABEL.weet_niet).toBe("Ik weet het niet");
    for (const w of Object.values(ZEKERHEID_LABEL)) expect(w).not.toMatch(/%/);
  });
});
