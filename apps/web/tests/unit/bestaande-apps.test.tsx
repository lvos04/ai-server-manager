import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DienstenScreen } from "@/app/instellingen/diensten/DienstenScreen";
import { ADAPTERS, allePaginas } from "@/app/instellingen/diensten/adapterweergave";
import { HubApiError } from "@/lib/api";
import type * as Session from "@/lib/session";
import type { Role } from "@/lib/types";
import type { ApiState } from "@/lib/use-api";

const proef = vi.hoisted(() => ({
  rol: "admin" as Role,
  lijst: {} as Partial<ApiState<unknown>>,
  catalogus: {} as Partial<ApiState<unknown>>,
}));
vi.mock("@/lib/session", async (original) => ({
  ...await original<typeof Session>(), useRole: () => proef.rol,
}));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string | null) => ({
    reload: vi.fn(), ...(pad?.includes("adapterkoppelingen") ? proef.lijst : pad?.startsWith("/api/v1/apps?") ? proef.catalogus : {}),
  }),
}));

const ids = ["mediaguard", "media-source-optimizer", "my_house"];
const huis = {
  id: "koppeling", app_id: "my_house", catalog_app_id: "installatie-my_house", basis_url: "https://huis.example",
  laatste4: "ABCD", ingevoerd_op: "2026-10-14T09:00:00Z", version: 3,
};
function kaart() {
  const html = renderToStaticMarkup(<DienstenScreen />);
  const start = html.indexOf('id="bestaande-apps"');
  expect(start).toBeGreaterThan(-1);
  return html.slice(start).split("</section>")[0]!;
}
function meting(status: string, observed_at: string | null, reason_code: string | null = null) {
  proef.lijst = { data: { items: [{ ...huis, verbinding: { status, observed_at, reason_code } }], next_cursor: null } };
}

describe("Bestaande apps onder Diensten", () => {
  beforeEach(() => {
    proef.rol = "admin";
    proef.lijst = { data: { items: [], next_cursor: null } };
    proef.catalogus = { data: { items: ids.map((id) => ({
      id: "installatie-" + id, app_id: id, naam: id, aanwezig: true, soort: "bestaand", deep_link: null,
    })), inventaris: { status: "ok" }, next_cursor: null } };
  });
  it("toont na een lege meting drie herkenbare kaarten met een eigen bestemming", () => {
    const html = kaart();
    for (const naam of ["MediaGuard", "Media Source Optimizer", "my_house"]) expect(html).toContain(naam);
    expect(html.match(/Niet gekoppeld/g)).toHaveLength(3);
    expect(html).toContain("API-sleutels");
    expect(html).toContain("Server-ID");
    expect(html).toContain("Machinesleutel");
  });
  it("houdt de lijst tijdens het ophalen onbekend", () => {
    proef.lijst = { loading: true };
    expect(kaart()).toContain("Koppelingen ophalen");
    expect(kaart()).not.toContain("Niet gekoppeld");
  });
  it("toont recent bevestigd contact met meettijd en sleutelkenmerk", () => {
    const tijd = new Date(Date.now() - 20_000).toISOString();
    meting("healthy", tijd);
    const html = kaart();
    expect(html).toContain(">Gekoppeld<");
    expect(html).toContain('dateTime="' + tijd + '"');
    expect(html).toContain("ABCD");
    expect(html).toContain("14 okt 2026");
    expect(html).not.toMatch(/type="password"[^>]+value="[^"]+"/);
  });
  it.each([
    ["expliciet verouderd", "unknown", new Date(Date.now() - 20_000).toISOString(), "meting_verouderd", "Verouderd", "De laatste contactmeting is verlopen."],
    ["inmiddels verlopen", "healthy", "2020-01-01T10:00:00Z", null, "Verouderd", "Laatst bekend · Bereikbaar"],
    ["ontbrekende meettijd", "healthy", null, null, "Onbekend", "Er is geen bevestigde verbinding."],
    ["ongeldige meettijd", "healthy", "onbekend", null, "Onbekend", "Meettijd onbekend"],
    ["toekomstige meettijd", "healthy", "2999-01-01T10:00:00Z", null, "Onbekend", "Meettijd onbekend"],
    ["opgeslagen zonder proef", "unknown", null, "meettijd_onbekend", "Ingesteld", "De bestemming is opgeslagen."],
    ["onbevestigde rol", "unknown", null, "bron_recht_ongeldig", "Contact onbekend", "De rechten passen niet bij leestoegang."],
    ["adres geweigerd", "unknown", null, "doelbinding", "Contact onbekend", "Het adres is geweigerd."],
    ["app onbereikbaar", "unknown", null, "niet_bereikbaar", "Contact onbekend", "De app is niet bereikbaar."],
    ["ongeldige code", "unknown", null, "bron_koppelcode_ongeldig", "Contact onbekend", "De code of de toegang is ongeldig of verlopen."],
  ] as const)("%s geeft een concrete toestand zonder bevestigd contact", (_, status, tijd, reden, pil, uitleg) => {
    meting(status, tijd, reden);
    const html = kaart().match(/<article\b[^>]*>[\s\S]*?<\/article>/g)?.find((deel) => deel.includes(">my_house</h3>"));
    expect(html).toContain(">" + pil + "<");
    expect(html).toContain(uitleg);
    expect(html).not.toContain(">Gekoppeld<");
  });
  it.each(["viewer", "operator"] as const)("biedt de rol %s alleen de leesweergave", (rol) => {
    proef.rol = rol;
    meting("healthy", new Date().toISOString());
    const html = kaart();
    expect(html).toContain(">Gekoppeld<");
    expect(html).not.toMatch(/<(input|form)\b|>Ontkoppelen<|>Testen</);
  });
  it("biedt poolleesrecht alleen op de bestaande MediaGuard-koppeling aan de beheerder", () => {
    const link = { ...huis, app_id: "mediaguard", catalog_app_id: "installatie-mediaguard",
      verbinding: { status: "unknown", observed_at: null }, poolleesrecht: false };
    proef.lijst = { data: { items: [link], next_cursor: null } };
    expect(kaart().match(/Poolleesrecht toekennen/g)).toHaveLength(1);
    link.poolleesrecht = true;
    expect(kaart()).toContain("Poolleesrecht intrekken");
    expect(kaart()).toContain("Pooltoken vervangen");
    proef.rol = "viewer";
    expect(kaart()).not.toContain("Poolleesrecht intrekken");
  });
  it("toont na weigering geen oude koppeling en biedt opnieuw ophalen aan", () => {
    meting("healthy", new Date().toISOString());
    proef.lijst.error = new HubApiError(403, "forbidden", "Geen toegang.");
    proef.lijst.stale = true;
    const html = kaart();
    expect(html).toContain("Opnieuw proberen");
    expect(html).not.toMatch(/ABCD|>Gekoppeld<|type="password"/);
  });
  it("bewaart bij een verbindingsfout alleen de laatst bekende meting met haar brontijd", () => {
    const tijd = new Date().toISOString();
    meting("healthy", tijd);
    proef.lijst.error = new HubApiError(0, "network_error", "Geen verbinding.");
    proef.lijst.stale = true;
    const html = kaart();
    expect(html).toContain("Laatst bekend");
    expect(html).toContain('dateTime="' + tijd + '"');
    expect(html).not.toMatch(/>Gekoppeld<|type="password"/);
  });
});

describe("volledige koppellijst", () => {
  const pad = ADAPTERS + "?limit=200";
  it("leest ook installaties op een vervolgpagina en geeft de cursor ongewijzigd door", async () => {
    const ophalen = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(Response.json({ items: ["eerste"], next_cursor: "volgende/+" }))
      .mockResolvedValueOnce(Response.json({ items: ["tweede"], next_cursor: null }));
    const lijst = await allePaginas(pad, { fetchImpl: ophalen });
    expect(lijst.data.items).toEqual(["eerste", "tweede"]);
    expect(ophalen.mock.calls[1]?.[0]).toBe(pad + "&cursor=volgende%2F%2B");
  });
  it("geeft bij een herhaalde cursor geen gedeeltelijke lijst door", async () => {
    const ophalen = vi.fn<typeof fetch>(async () => Response.json({ items: ["eerste"], next_cursor: "herhaald" }));
    await expect(allePaginas(pad, { fetchImpl: ophalen })).rejects.toMatchObject({ code: "cursor_herhaald" });
    expect(ophalen).toHaveBeenCalledTimes(2);
  });
});
