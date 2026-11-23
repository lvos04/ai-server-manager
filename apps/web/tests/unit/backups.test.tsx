import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, expect, it, vi } from "vitest";
import { BackupsScreen } from "@/app/backups/BackupsScreen";

const proef = vi.hoisted(() => ({ stale: false, geldigTot: "" }));

vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string) => {
    if (!pad.endsWith("/coverage")) return {};
    const tijd = { observed_at: new Date(Date.now() - 1_000).toISOString(), geldig_tot: proef.geldigTot };
    return {
      stale: proef.stale,
      data: { apps: [], datasets: [], bronnen: {}, app_backups: {
        mediaguard: { ...tijd, naam: "MediaGuard-voortgang", status: "degraded", reden: "Een forkback-up ontbreekt." },
        emby_exportarchief: { naam: "Emby-exportarchief", status: "unknown", reden: "nog niet gemaakt (overname, P4-0)" },
        my_house: { ...tijd, naam: "my_house", status: "gedekt", leeftijd_uren: 1 },
        "media-source-optimizer": { naam: "Media Source Optimizer", status: "unknown", reden: "Geen leesrecht." },
      } },
    };
  },
}));

function rij(html: string, naam: string) {
  return html.match(/<li\b[^>]*>[\s\S]*?<\/li>/g)?.find((item) => item.includes(naam)) ?? "";
}

beforeEach(() => {
  proef.stale = false;
  proef.geldigTot = new Date(Date.now() + 900_000).toISOString();
});

it("toont de vier back-upmeldingen met hun eigen toestand en reden", () => {
  const html = renderToStaticMarkup(<BackupsScreen />);
  expect(rij(html, "MediaGuard-voortgang")).toMatch(/Een forkback-up ontbreekt[^]*Niet gedekt/);
  expect(rij(html, "Emby-exportarchief")).toMatch(/nog niet gemaakt \(overname, P4-0\)[^]*Onbekend/);
  expect(rij(html, "my_house")).toMatch(/Bij controle 1 uur oud[^]*Gedekt/);
  expect(rij(html, "Media Source Optimizer")).toMatch(/Geen leesrecht[^]*Onbekend/);
});

it.each(["verlopen", "ophalen mislukt"])("trekt een bevestiging in bij %s", (reden) => {
  if (reden === "verlopen") proef.geldigTot = new Date(Date.now() - 1).toISOString();
  else proef.stale = true;
  expect(rij(renderToStaticMarkup(<BackupsScreen />), "my_house")).toMatch(/Geen actuele meting[^]*Onbekend/);
});
