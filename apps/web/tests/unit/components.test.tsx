import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Freshness } from "@/components/Freshness";
import { NotYetAvailable } from "@/components/NotYetAvailable";
import { StatusBadge } from "@/components/StatusBadge";
import { PLANNED } from "@/lib/nav";

describe("componenten", () => {
  it("status heeft symbool én tekst (niet alleen kleur)", () => {
    const html = renderToStaticMarkup(<StatusBadge view={{ tone: "unknown", label: "Onbekend" }} />);
    expect(html).toContain('data-tone="unknown"');
    expect(html).toContain('aria-hidden="true">?</span>');
    expect(html).toContain("Onbekend");
  });

  it("‘laatst bijgewerkt’ en bron zijn altijd zichtbaar, ook als nooit gemeten", () => {
    const html = renderToStaticMarkup(<Freshness observedAt={null} bron={null} />);
    expect(html).toContain("Laatst bijgewerkt");
    expect(html).toContain("nog nooit gemeten");
    expect(html).toContain("Bron");
    expect(html).toContain("onbekend");
    const fresh = renderToStaticMarkup(<Freshness observedAt="2026-11-09T10:00:00Z" bron="TrueNAS pool.query" verouderd />);
    expect(fresh).toContain('dateTime="2026-11-09T10:00:00Z"');
    expect(fresh).toContain("verouderd");
  });

  it("nog niet beschikbaar: fase genoemd, geen gegevens", () => {
    const html = renderToStaticMarkup(<NotYetAvailable screen={PLANNED.problemen!} />);
    expect(html).toContain("Nog niet beschikbaar (volgt in fase P1)");
    expect(html).not.toContain("<table");
  });
});
