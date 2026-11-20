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
});
