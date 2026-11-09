/**
 * Reparaties uit de Peil-ontwerpreview (docs/ontwerp/PEIL_REVIEW.md): stabiel querypad (geen eindeloos ophalen),
 * gaten in een grafiek, echte meervouden, leesbare bron en de StatKaart zonder badge bij een verse waarde.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { gaten } from "@/components/LineChart";
import { StatCard } from "@/components/StatCard";
import { aantal } from "@/lib/format";
import { bronLabel, queryPath } from "@/lib/metrics";

describe("Peil-review: grafieken", () => {
  it("queryPath is binnen dezelfde minuut gelijk en laat 'tot' aan de Hub (geen nieuw pad per weergave)", () => {
    const t = Date.parse("2026-11-09T21:53:09.360Z");
    const a = queryPath(4, "6u", t);
    const b = queryPath(4, "6u", t + 20_000);
    expect(a).toBe(b);
    expect(a).not.toContain("tot=");
    expect(decodeURIComponent(a)).toContain("van=2026-11-09T15:53:00.000Z");
    expect(queryPath(4, "6u", t + 60_000)).not.toBe(a);
  });

  it("gaten: aaneengesloten stukken zonder meting, van het punt ervóór tot het punt erna (nooit 0)", () => {
    const r = [{ key: "v", label: "CPU", kleur: "var(--chart-1)" }];
    const p = [
      { t: 1, v: 10 },
      { t: 2, v: null },
      { t: 3, v: null },
      { t: 4, v: 12 },
      { t: 5, v: 13 },
    ];
    expect(gaten(p, r)).toEqual([{ x1: 1, x2: 4 }]);
    expect(gaten([{ t: 1, v: 1 }, { t: 2, v: 2 }], r)).toEqual([]);
    // Meerdere reeksen: alleen een gat als álle reeksen leeg zijn.
    const r2 = [...r, { key: "w", label: "Net", kleur: "var(--chart-2)" }];
    expect(gaten([{ t: 1, v: 1, w: 1 }, { t: 2, v: null, w: 3 }, { t: 3, v: 2, w: 2 }], r2)).toEqual([]);
  });

  it("bron is leesbaar", () => {
    expect(bronLabel("truenas.reporting.realtime")).toBe("TrueNAS (reporting.realtime)");
    expect(bronLabel("beszel")).toBe("Beszel");
    expect(bronLabel("iets.anders")).toBe("iets.anders");
    expect(bronLabel(null)).toBeNull();
  });
});

describe("Peil-review: woorden en badges", () => {
  it("echte meervouden in plaats van 'pool(s)' of 'kanaal/kanalen'", () => {
    expect(aantal(1, "pool", "pools")).toBe("1 pool");
    expect(aantal(3, "kanaal", "kanalen")).toBe("3 kanalen");
    expect(aantal(0, "regel", "regels")).toBe("0 regels");
  });

  it("StatKaart met een verse waarde heeft geen statusbadge (versheid is nooit een badge, Peil §4.4)", () => {
    const html = renderToStaticMarkup(
      <StatCard id="cpu" title="CPU-gebruik" value="23,5%" kwaliteit="gemeten" status={[]} bron="TrueNAS" observedAt="2026-11-09T10:00:00Z" action={{ href: "/x", label: "Meer" }} />,
    );
    expect(html).not.toContain("data-status");
    expect(html).toContain("· gemeten");
  });
});
