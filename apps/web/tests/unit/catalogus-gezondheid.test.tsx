import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AppDetail } from "@/app/apps/[id]/AppDetail";
import { AppsScreen } from "@/app/apps/AppsScreen";
import { actueleMeting, catalogusTellingen, type CatalogApp, type CatalogList } from "@/lib/catalog";
import { HubApiError } from "@/lib/api";
import { formatTime } from "@/lib/format";

// Alleen de gegevensgrens en de router zijn nagebootst. Beide schermen renderen hun eigen statuscomponenten.
const proef = vi.hoisted(() => ({ uitval: false, eersteOphaling: false, app: "my_house", verlopenStoring: false, nieuweMeting: false, zonderVervalgrens: false, oudeInventaris: false }));
const meettijd = "2026-11-18T12:00:00Z";
const ophaaltijd = "2026-11-18T12:01:00Z";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/apps/proef",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/session", async (oorspronkelijk) => ({
  ...(await oorspronkelijk<Record<string, unknown>>()), useRole: () => "viewer",
}));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string | null) => {
    const antwoord = {
      stale: proef.uitval, lastOk: ophaaltijd, reload: vi.fn(), loading: false,
      error: proef.uitval ? new HubApiError(503, "tijdelijk", "De Hub is tijdelijk onbereikbaar.") : undefined,
    };
    if (!pad?.startsWith("/api/v1/apps")) return { data: { items: [] }, loading: false };
    if (proef.eersteOphaling) return { ...antwoord, data: undefined, loading: !proef.uitval, stale: false, lastOk: null };
    const oud = proef.verlopenStoring;
    const gezondheid = {
      ...(proef.zonderVervalgrens ? {} : { geldig_tot: proef.nieuweMeting ? "2026-11-18T12:23:00Z" : "2026-11-18T12:02:00Z" }),
      status: oud ? "unknown" : "healthy", reason_code: oud ? "meting_verouderd" : null,
      melding: oud ? "De laatste meting is ouder dan toegestaan en geldt daarom als onbekend." : "",
      observed_at: proef.nieuweMeting ? "2026-11-18T12:21:00Z" : meettijd, laatst_getest: meettijd, oorzaak: oud ? "adapter_p3" : null,
      binnenkant_vereist: proef.app === "my_house",
    };
    const item = {
      id: "proef", runtime_id: proef.app, naam: proef.app, titel: proef.app, app_id: proef.app,
      soort: "bestaand", installatiewijze: "custom_app", image: {}, eigenaar: { soort: "bestaand" },
      aanwezig: true, eerst_gezien: meettijd, laatst_gezien: meettijd, gezondheid,
      runtime_staat: "RUNNING", deep_link_detail: {}, datasets: [], poorten: [], image_historie: [],
      gezondheidsprofiel: { binnenkant: proef.app === "my_house" ? "adapter_p3" : null },
    };
    const inventaristijd = proef.oudeInventaris ? "2026-11-17T12:00:00Z" : gezondheid.observed_at;
    if (pad.includes("?")) {
      return { ...antwoord, data: { items: [item], totaal: 1, observed_at: gezondheid.observed_at, inventaris: { status: "ok", observed_at: inventaristijd },
        per_status: { healthy: 1, degraded: 0, down: 0, unknown: 0 } } };
    }
    const bron = proef.app === "my_house" ? "adapter_p3" : "uptime_kuma:proef";
    const component = {
      ...gezondheid, bron, soort: proef.app === "my_house" ? "binnenkant" : "buitenkant",
      laatste_status: oud ? "down" : null, verouderd: oud,
    };
    return { ...antwoord, data: { ...item, bron: { observed_at: inventaristijd }, gezondheid: { ...gezondheid, componenten: [component] } } };
  },
}));

function weergave(scherm: string) {
  return renderToStaticMarkup(scherm === "detail" ? <AppDetail id="proef" /> : <AppsScreen />);
}

beforeEach(() => {
  proef.uitval = false;
  proef.eersteOphaling = false;
  proef.verlopenStoring = false;
  proef.nieuweMeting = false;
  proef.zonderVervalgrens = false;
  proef.oudeInventaris = false;
  proef.app = "my_house";
  vi.setSystemTime(new Date(ophaaltijd));
});

afterEach(() => vi.useRealTimers());

it("een lijstlezing maakt oude inventarisgegevens en lege datasets of poorten niet actueel", () => {
  expect(weergave("lijst")).toContain('data-status="healthy"');
  const vers = weergave("detail");
  expect(vers).toContain("<dt>Data-datasets</dt><dd>geen gevonden</dd>");
  expect(vers).toContain("<dt>Poorten</dt><dd>geen</dd>");
  proef.oudeInventaris = true;
  expect(weergave("lijst")).not.toContain('data-status="healthy"');
  const oud = weergave("detail");
  expect(oud).toContain("<dt>Data-datasets</dt><dd>onbekend</dd>");
  expect(oud).toContain("<dt>Poorten</dt><dd>onbekend</dd>");
});

for (const app of ["my_house", "emby"]) {
  for (const scherm of ["detail", "lijst"]) {
    it.each([
      ["op dezelfde minuut een ophaalfout", true, ophaaltijd],
      ["een ophaalfout na twintig minuten", true, "2026-11-18T12:20:00Z"],
      ["de bronvervalgrens zonder ophaalfout", false, "2026-11-18T12:02:00.001Z"],
    ] as const)(`${app} ${scherm} trekt groen in bij %s`, (_geval, uitval, tijd) => {
      proef.app = app;
      expect(weergave(scherm)).toContain('data-status="healthy"');
      proef.uitval = uitval;
      vi.setSystemTime(new Date(tijd));
      const html = weergave(scherm);
      if (uitval) expect(html).toContain(scherm === "detail" ? "vernieuwen is mislukt" : "HTTP 503");
      expect(html).not.toContain('data-status="healthy"');
      expect(html).toContain("Laatst bekend");
      expect(html).toContain(formatTime(meettijd));
      if (scherm === "lijst") {
        const tekst = html.replace(/<[^>]*>/g, "");
        expect(tekst).toContain("Gezond (0)");
        expect(tekst).toContain("Onbekend (1)");
      }
      proef.uitval = false;
      proef.nieuweMeting = true;
      vi.setSystemTime(new Date("2026-11-18T12:21:10Z"));
      expect(weergave(scherm)).toContain('data-status="healthy"');
    });
  }
}

it("toont een verlopen storing met haar oorspronkelijke meettijd", () => {
  proef.verlopenStoring = true;
  vi.setSystemTime(new Date("2026-11-18T12:20:00Z"));
  const html = weergave("detail");
  expect(html).toContain("Laatst bekend: Storing.");
  expect(html).toContain(formatTime(meettijd));
  expect(html).not.toContain('data-status="healthy"');
});

for (const scherm of ["detail", "lijst"]) {
  it(`${scherm} toont laden en een initiële fout zonder gezonde status`, () => {
    proef.eersteOphaling = true;
    const laden = weergave(scherm);
    expect(laden).toContain('data-testid="loading"');
    expect(laden).not.toContain('data-status="healthy"');
    proef.uitval = true;
    const fout = weergave(scherm);
    expect(fout).toContain("HTTP 503");
    expect(fout).toContain("Opnieuw proberen");
    expect(fout).not.toContain('data-status="healthy"');
  });
}

it.each([null, "geen datum", "2026-11-19T12:00:00Z"])("weigert groen met onzekere bronmeettijd %s", (observed_at) => {
  const m = { status: "healthy", observed_at, reason_code: null, melding: "" };
  expect(actueleMeting(m, false, Date.parse(ophaaltijd))).toMatchObject({ status: "unknown", observed_at: null });
});

it("laat ook buiten de geladen pagina geen gezonde telling door na uitval of veroudering", () => {
  const app = { gezondheid: { status: "healthy" } } as CatalogApp;
  const lijst = { totaal: 3, items: [app], per_status: { healthy: 2, down: 1, degraded: 0, unknown: 0 }, overige_geldig_tot: ophaaltijd } as CatalogList;
  const onbekend = { gezondheid: { status: "unknown" } } as CatalogApp;
  const nu = Date.parse(ophaaltijd);
  expect(catalogusTellingen(lijst, [app], false, nu)).toEqual(lijst.per_status);
  expect(catalogusTellingen(lijst, [onbekend], true, nu)).toEqual({ healthy: 0, down: 0, degraded: 0, unknown: 3 });
  expect(catalogusTellingen(lijst, [app], false, nu + 1)).toEqual({ healthy: 1, down: 0, degraded: 0, unknown: 2 });
});

it.each([undefined, null, "geen tijdstip", "2026-11-18T12:02:00"])("toont zonder geldige bronvervalgrens alleen de vorige meting (%s)", (geldig_tot) => {
  const m = { status: "healthy", observed_at: meettijd, geldig_tot, reason_code: null, melding: "" };
  for (const tijd of [ophaaltijd, "2026-11-18T12:01:12Z"]) {
    expect(actueleMeting(m, false, Date.parse(tijd))).toMatchObject({ status: "unknown", laatste_status: "healthy", observed_at: meettijd });
  }
});

for (const scherm of ["lijst", "detail"]) {
  it(`${scherm} houdt een ouder API-antwoord zonder vervaltijd vanaf ontvangst historisch`, () => {
    proef.zonderVervalgrens = true;
    for (const tijd of [ophaaltijd, "2026-11-18T12:01:12Z"]) {
      vi.setSystemTime(new Date(tijd));
      const html = weergave(scherm);
      expect(html).not.toContain('data-status="healthy"');
      expect(html).toContain("Laatst bekend");
      expect(html).toContain(formatTime(meettijd));
      if (scherm === "lijst") expect(html.replace(/<[^>]*>/g, "")).toContain("Gezond (0)");
    }
  });
}
