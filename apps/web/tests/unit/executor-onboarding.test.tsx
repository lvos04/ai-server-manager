import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import Page from "@/app/onboarding/executor/page";

// Alleen de vaste teksten van de pagina; het koppelblok haalt gegevens op en zit in de e2e-test (90-afsluiting).
vi.mock("@/app/onboarding/executor/ExecutorKoppelen", () => ({ ExecutorKoppelen: () => null }));

describe("Executor installeren en koppelen", () => {
  it("de intro noemt niet elke actie goedgekeurd (R1 loopt zonder goedkeuring, Peil §4.5) en leest zonder 'uit uit'", () => {
    const html = renderToStaticMarkup(<Page />);
    const intro = /<h1[^>]*>Executor installeren en koppelen<\/h1><p[^>]*>([^<]+)<\/p>/.exec(html)?.[1] ?? "";
    expect(intro).toContain("Hij voert alleen acties uit een vaste lijst uit die de Hub heeft ondertekend — nooit shell, sudo of Docker.");
    expect(intro).not.toMatch(/goedgekeurd/i);
    expect(intro).not.toMatch(/\buit uit\b/);
  });
});
