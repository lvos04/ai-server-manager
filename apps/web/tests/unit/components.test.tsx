import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Controles } from "@/components/Controles";
import { Freshness } from "@/components/Freshness";
import { shortDigest } from "@/components/KopieerVeld";
import { NotYetAvailable } from "@/components/NotYetAvailable";
import { StatCard } from "@/components/StatCard";
import { ErnstLabel, StatusBadge, ZekerheidLabel } from "@/components/StatusBadge";
import { PLANNED } from "@/lib/nav";

describe("Peil-componenten", () => {
  it("StatusBadge: lucide-icoon (aria-hidden) én woord én data-status (niet alleen kleur)", () => {
    const html = renderToStaticMarkup(<StatusBadge view={{ tone: "unknown", label: "Onbekend" }} />);
    expect(html).toContain('data-status="unknown"');
    expect(html).toMatch(/<svg[^>]*aria-hidden="true"/);
    expect(html).toContain("lucide-circle-question-mark");
    expect(html).toContain("Onbekend");
    expect(html).toContain("border-dashed");
  });

  it("neutrale pil voor ‘Draait’/‘Gekoppeld’: geen groen (healthy) en het eigen icoon", () => {
    const html = renderToStaticMarkup(<StatusBadge view={{ tone: "neutral", label: "Draait", icon: "draait" }} />);
    expect(html).toContain('data-status="neutral"');
    expect(html).not.toContain("healthy");
    expect(html).toContain("lucide-power");
  });

  it("Versheid: Bron en Bijgewerkt altijd zichtbaar, ook als nooit gemeten (OB-09)", () => {
    const html = renderToStaticMarkup(<Freshness observedAt={null} bron={null} />);
    expect(html).toContain("Bijgewerkt");
    expect(html).toContain("Nog nooit gemeten");
    expect(html).toContain("Bron");
    expect(html).toContain("onbekend");
    const fresh = renderToStaticMarkup(<Freshness observedAt="2026-11-09T10:00:00Z" bron="TrueNAS pool.query" verouderd geprobeerd={{ op: "2026-11-09T11:00:00Z", uitkomst: "unreachable" }} />);
    expect(fresh).toContain('dateTime="2026-11-09T10:00:00Z"');
    expect(fresh).toContain("verouderd");
    expect(fresh).toContain("Geprobeerd");
  });

  it("StatKaart verouderd (O-03): laatst bekende waarde blijft, gedempt, met ‘Laatst bekend’ en sr-tekst", () => {
    const html = renderToStaticMarkup(
      <StatCard id="x" title="Opslag" value="1 van 1" unit="pools gezond" status={[{ tone: "unknown", label: "Onbekend" }, { tone: "stale", label: "Verouderd" }]} bron="TrueNAS pool.query" observedAt="2026-11-09T10:12:00Z" verouderd action={{ href: "/server", label: "Pools" }} />,
    );
    expect(html).toContain("Laatst bekend");
    expect(html).toContain("1 van 1");
    expect(html).toContain("laatst bekende waarde, verouderd");
    expect(html).toContain("arcering");
    expect(html).not.toContain("healthy");
  });

  it("StatKaart zonder meting toont geen getal (nooit 0)", () => {
    const html = renderToStaticMarkup(<StatCard id="y" title="GPU" value={null} status={{ tone: "unknown", label: "Onbekend" }} bron={null} observedAt={null} action={{ href: "/", label: "x" }} />);
    expect(html).not.toMatch(/>0</);
    expect(html).toContain('data-testid="waarde-y"');
  });

  it("ErnstLabel en ZekerheidLabel: vaste woorden, geen percentage", () => {
    expect(renderToStaticMarkup(<ErnstLabel ernst="middel" />)).toContain("Middel");
    const z = renderToStaticMarkup(<ZekerheidLabel zekerheid="weet_niet" />);
    expect(z).toContain("Ik weet het niet");
    expect(z).not.toContain("%");
  });

  it("Controles: geslaagd neutraal vinkje, mislukt down, onbekend vraagteken", () => {
    const html = renderToStaticMarkup(
      <Controles items={[{ id: "a", naam: "A", uitkomst: "ok" }, { id: "b", naam: "B", uitkomst: "fout" }, { id: "c", naam: "C", uitkomst: "onbekend" }]} />,
    );
    expect(html).toContain('data-uitkomst="ok"');
    expect(html).toContain("text-down");
    expect(html).toContain("Geslaagd: ");
  });

  it("digest kort weergeven, volledig kopiëren", () => {
    expect(shortDigest("sha256:91c4aaaaaaaaaaaaaaaaaaaaaaaaaaaa7d02")).toBe("sha256:91c4…7d02");
    expect(shortDigest(null)).toBe("onbekend");
  });

  it("nog niet beschikbaar: fase genoemd, geen gegevens", () => {
    const html = renderToStaticMarkup(<NotYetAvailable screen={PLANNED.ai!} />);
    expect(html).toContain("Nog niet beschikbaar — volgt in fase P2");
    expect(html).toContain("lucide-hourglass");
    expect(html).not.toContain("<table");
  });
});
