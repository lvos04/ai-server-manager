import { describe, expect, it } from "vitest";
import { activeDesktopHref, activeMobileHref, DESKTOP_NAV, isActive, MOBILE_NAV, MORE_LINKS, PLANNED, safeReturnPath } from "@/lib/nav";
import { appState, coverageStatus, decisionStatus, gateStatus, kindStatus, measurementStatus, poolHealth, testResult, worstTone } from "@/lib/status";

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

  it("latere fasen volgens 06_FASERING", () => {
    expect(PLANNED.problemen?.fase).toBe("P1");
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
  });
});

describe("statussen: onbekend is nooit groen", () => {
  it("inventaris", () => {
    expect(kindStatus("ok").tone).toBe("ok");
    expect(kindStatus("ok", true).tone).toBe("unknown");
    expect(kindStatus("unknown").tone).toBe("unknown");
    expect(kindStatus(undefined).tone).toBe("unknown");
  });

  it("pool alleen gezond als vers gemeten", () => {
    expect(poolHealth(true, true).tone).toBe("ok");
    expect(poolHealth(true, false).tone).toBe("unknown");
    expect(poolHealth(false, true).tone).toBe("bad");
    expect(poolHealth(null, true).tone).toBe("unknown");
  });

  it("‘draait’ volgens TrueNAS is geen gezond", () => {
    expect(appState("draait").tone).toBe("info");
    expect(appState("gecrasht").tone).toBe("bad");
    expect(appState("iets").tone).toBe("unknown");
  });

  it("besluiten, gates, dekking, metingen en hersteltests", () => {
    expect(decisionStatus("Getest").tone).toBe("ok");
    expect(decisionStatus("Ingevuld").tone).toBe("info");
    expect(decisionStatus("N.v.t.").tone).toBe("neutral");
    expect(gateStatus("toegestaan").tone).toBe("ok");
    expect(gateStatus("unknown").tone).toBe("unknown");
    expect(coverageStatus("gedekt").tone).toBe("ok");
    expect(coverageStatus("binnen").tone).toBe("ok");
    expect(coverageStatus("overschreden").tone).toBe("bad");
    expect(coverageStatus("unknown").tone).toBe("unknown");
    expect(measurementStatus("voorstel").tone).toBe("info");
    expect(testResult(undefined).tone).toBe("unknown");
  });

  it("slechtste toon wint; onbekend weegt zwaarder dan ok", () => {
    expect(worstTone(["ok", "unknown"])).toBe("unknown");
    expect(worstTone(["ok", "bad", "unknown"])).toBe("bad");
    expect(worstTone(["ok", "ok"])).toBe("ok");
    expect(worstTone([])).toBe("unknown");
  });
});
