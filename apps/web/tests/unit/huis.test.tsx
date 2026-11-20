import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/huis/page";
import { HubApiError } from "@/lib/api";
import { PLANNED } from "@/lib/nav";
import type { ApiState } from "@/lib/use-api";
import { huisMeting } from "./fixtures/huis";

const scenario = vi.hoisted(() => ({ lijst: {} as Partial<ApiState<unknown>>, bron: {} as Partial<ApiState<unknown>> }));

vi.mock("@/lib/use-api", () => ({
  useApi: (path: string) => ({
    ...(path.includes("/my-house?") ? scenario.lijst : scenario.bron),
    reload: vi.fn(),
  }),
}));

describe("Huis", () => {
  beforeEach(() => {
    scenario.lijst = { data: { items: ["koppeling"] } };
    scenario.bron = { data: huisMeting() };
  });

  it("toont woningen en metingen met een gewone link naar my_house", () => {
    const html = renderToStaticMarkup(<Page />);
    expect(PLANNED.huis).toBeUndefined();
    for (const text of ["Proefwoning", "20,5", "Plafondlamp", "Leeslamp", "Veilige modus", "Laatste back-up", "Boiler", "Open in my_house"]) {
      expect(html).toContain(text);
    }
    expect(html).toContain('href="https://huis.example"');
    expect(html).toContain("Laatst bekend · 21 °C");
    expect(html).not.toMatch(/<(form|input|button)\b|role="switch"/);
  });

  it("markeert een verouderde sensor bij de zone en toont diens temperatuur niet als actueel", () => {
    const data = huisMeting();
    data.woningen[0]!.zones[1]!.temperature.value = 18.5;
    scenario.bron = { data };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("Verouderd");
    expect(html).not.toContain("18,5");
    expect(html).toContain("20,5");
  });

  it("past de sensorgrens toe zonder de rest van de woning te verouderen", () => {
    const data = huisMeting();
    const sensor = data.woningen[0]!.zones[0]!.temperature;
    sensor.at = new Date(Date.now() - 360_000).toISOString();
    sensor.max_age_s = 420;
    scenario.bron = { data };
    expect(renderToStaticMarkup(<Page />)).toContain("20,5");
    sensor.max_age_s = 300;
    const html = renderToStaticMarkup(<Page />);
    expect(html).not.toContain("20,5");
    expect(html).toContain("Actief");
    expect(html).toContain("1 open melding");
  });

  it("toont ontvangen waarden na bronuitval als laatst bekend", () => {
    scenario.bron = {
      ...scenario.bron, error: new HubApiError(503, "my_house_unavailable", "my_house antwoordt niet."), stale: true,
    };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("Laatst bekend");
    expect(html).toContain("20,5");
    expect(html).toContain("Opnieuw proberen");
    expect(html).not.toContain("Open in my_house");
  });

  it("verwijst bij een verlopen koppeling naar Diensten en houdt eerdere waarden buiten beeld", () => {
    scenario.bron = {
      ...scenario.bron, error: new HubApiError(409, "bron_token_verlopen", "De koppeling is verlopen."), stale: true,
    };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("koppeling verlopen");
    expect(html).toContain('href="/instellingen/diensten"');
    expect(html).not.toContain("20,5");
    expect(html).not.toContain("Open in my_house");
  });

  it("onderscheidt laden van een lege lijst met koppelingen", () => {
    scenario.lijst = { loading: true };
    expect(renderToStaticMarkup(<Page />)).toContain("Koppelingen ophalen");
    scenario.lijst = { data: { items: [] } };
    expect(renderToStaticMarkup(<Page />)).toContain("my_house is nog niet gekoppeld");
  });

  it.each([401, 403, 409, 500])("verbergt alle kaartgegevens bij lijststatus %i, ook als details wegvallen", (status) => {
    scenario.lijst = { ...scenario.lijst, error: new HubApiError(status, "geweigerd", "Lezen geweigerd."), stale: true };
    scenario.bron = { ...scenario.bron, error: new HubApiError(0, "network_error", "Geen verbinding."), stale: true };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("Lezen geweigerd.");
    expect(html).not.toMatch(/Proefwoning|20,5|Veilige modus|Plafondlamp|Open in my_house|Laatst bekend/);
  });

  it("bewaart bij gewone lijstuitval de meting met haar oorspronkelijke tijd", () => {
    const tijd = new Date(Date.now() - 60_000).toISOString();
    scenario.lijst = { ...scenario.lijst, error: new HubApiError(0, "network_error", "Geen verbinding."), stale: true };
    scenario.bron = { data: huisMeting(tijd) };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("Laatst bekend · 20,5 °C");
    expect(html).toContain(`dateTime="${tijd}"`);
  });

  it.each([
    [false, 0, "Uit"], [true, 0, "Aan"], [null, 0, "Onbekend"], [undefined, 0, "Onbekend"],
    ["false", 0, "Onbekend"], [0, 0, "Onbekend"], [true, null, "Onbekend"], [false, "ongeldig", "Onbekend"],
    [true, 60_000, "Onbekend"], [false, -960_000, "Laatst bekend · Uit"],
  ] as const)("lichtveld %s en meettijd %s geven %s", (on, verschil, verwacht) => {
    const data = huisMeting();
    const woning = data.woningen[0]!;
    Object.assign(woning.licht.groups[0]!, { on });
    const last_seen = typeof verschil === "number" ? new Date(Date.now() + verschil).toISOString() : verschil;
    Object.assign(woning.apparaten[0]!, { last_seen });
    scenario.bron = { data };
    const kaart = renderToStaticMarkup(<Page />).split("Plafondlamp</dt>")[1]!.split("<dl")[0]!;
    expect(kaart.replace(/<[^>]+>/g, "")).toBe(verwacht);
  });

  it("toont onbekende deelmetingen zonder een lege lijst, nul of uit te suggereren", () => {
    const data = huisMeting();
    Object.assign(data.woningen[0]!, { licht: null, meldingen: null });
    Object.assign(data.woningen[0]!.zones[0]!, { target_at: null });
    Object.assign(data.instellingen, { safe_mode: null });
    scenario.bron = { data };
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain("20,5 °C");
    expect(html).toMatch(/Lichtgroepen<\/h3><p>Onbekend/);
    expect(html).toMatch(/Open meldingen<\/h3><p[^>]*>Onbekend/);
    expect(html).toMatch(/Veilige modus<\/h3><p>Onbekend/);
    expect(html).toMatch(/Temperatuurdoel<\/p><p>Onbekend/);
  });

  it.each([null, "ongeldig", "2099-01-01T00:00:00Z"])("een apparaatwaarneming vervangt de ontbrekende of ongeldige lichtmeettijd %s niet", (on_at) => {
    const data = huisMeting();
    Object.assign(data.woningen[0]!.licht.groups[0]!, { on_at });
    scenario.bron = { data };
    const kaart = renderToStaticMarkup(<Page />).split("Plafondlamp</dt>")[1]!.split("<dl")[0]!;
    expect(kaart.replace(/<[^>]+>/g, "")).toBe("Onbekend");
  });

  it("toont de doeltemperatuur als actueel bij een recente doelmeting van de gekoppelde unit", () => {
    const data = huisMeting();
    data.woningen[0]!.zones[0]!.target_at = data.observed_at;
    scenario.bron = { data };
    expect(renderToStaticMarkup(<Page />)).toMatch(/Temperatuurdoel<\/p><p>21 °C<\/p>/);
  });
});
