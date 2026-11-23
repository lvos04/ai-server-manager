import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HubApiError } from "@/lib/api";
import { BRONNAMEN } from "@/lib/backups";
import type { Beleid, BeleidsActie, Blokkade } from "@/lib/acties";
import { appActies, PLAN_VERLOPEN, planBlokkade, planCatalogus, planDigests, terugzetPunten, updateDoel, type InstallPlan } from "@/lib/appbeheer";
import type { CatalogDetail } from "@/lib/catalog";

const proef = vi.hoisted(() => ({
  rol: "admin", data: {} as Record<string, unknown>, fouten: new Map<string, HubApiError>(), oud: new Set<string>(),
}));

vi.mock("@/lib/session", () => {
  const rank: Record<string, number> = { kind: 0, viewer: 1, operator: 2, admin: 3 };
  return {
    useRole: () => proef.rol,
    hasRole: (r: string | undefined, min: string) => r !== undefined && rank[r]! >= rank[min]!,
    ROLE_LABEL: { viewer: "kijker", operator: "operator", admin: "beheerder", kind: "kind" },
  };
});
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: () => undefined }), usePathname: () => "/backups" }));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string | null) => {
    const bron = pad?.split("?")[0] ?? "";
    return { data: proef.data[bron], error: proef.fouten.get(bron), loading: false, stale: proef.oud.has(bron), lastOk: null, etag: null, reload: async () => undefined };
  },
}));

const { Acties, Versies, ALLEEN_CONTAINER, GEEN_TERUGZETPAD } = await import("@/app/apps/[id]/AppBeheer");
const { BackupsScreen } = await import("@/app/backups/BackupsScreen");
const { Installatiewizard } = await import("@/app/apps/installeren/Installatiewizard");

function actie(action_id: string, extra: Partial<BeleidsActie> = {}): BeleidsActie {
  return { action_id, omschrijving: "", uitvoerder: "executor", doel: "app", risk_class: "R1", risk_class_kritiek: null, risk_class_custom_app: null, requires_backup: false, cooldown_seconden: 0, ...extra };
}

const BELEID: Beleid = {
  policy_hash: `sha256:${"a".repeat(64)}`,
  acties: [
    actie("app.restart", { risk_class_kritiek: "R2" }),
    actie("app.stop", { risk_class_custom_app: "R2" }),
    actie("app.update", { risk_class: "R2", requires_backup: true }),
    actie("app.rollback", { risk_class: "R2", requires_backup: true }),
    actie("app.uninstall", { risk_class: "R2" }),
    actie("notification.send", { doel: "geen", risk_class: "R0" }),
  ],
  verboden: [],
  gereserveerd: [],
  beschermd: [],
  kritieke_apps: ["authentik"],
};

const EMBY: Blokkade = { id: "APP-EMBY", code: "emby_nooit_door_platform", reden: "Het platform stopt, updatet of verwijdert Emby nooit." };
const MG: Blokkade = { id: "APP-MEDIAGUARD", code: "mediaguard_upgradebewijs_ontbreekt", reden: "MediaGuard blijft draaien." };

function actiebeleid(blokkades: Blokkade[] = []): NonNullable<CatalogDetail["actiebeleid"]> {
  return {
    policy_hash: BELEID.policy_hash,
    geldig_tot: new Date(Date.now() + 60_000).toISOString(),
    acties: Object.fromEntries(BELEID.acties.filter((a) => a.doel === "app").map((a) => [
      a.action_id, { risk_class: a.risk_class_custom_app ?? a.risk_class, blokkades },
    ])),
  };
}

function app(extra: Partial<CatalogDetail> = {}): CatalogDetail {
  return {
    id: "11111111-2222-3333-4444-555555555555",
    runtime_id: "demo",
    naam: "demo",
    titel: "Demo",
    app_id: null,
    adaptertype: "geen",
    soort: "bestaand",
    installatiewijze: "custom_app",
    image: { repository: "ghcr.io/x/demo", tag: "1.0.0", digest: `sha256:${"b".repeat(64)}` },
    versie: "1.0.0",
    runtime_staat: "RUNNING",
    gezondheid: { status: "unknown", reason_code: null, melding: "", observed_at: null, laatst_getest: null, oorzaak: null, binnenkant_vereist: false, componenten: [] },
    deep_link: null,
    eigenaar: { repo: null, soort: "extern" },
    aanwezig: true,
    eerst_gezien: null,
    laatst_gezien: null,
    verdwenen_sinds: null,
    laatst_getest: null,
    deep_link_detail: { url: null, reden: null, bron: null },
    catalogus: null,
    image_historie: [],
    poorten: [],
    opslag: [{ bron: "/mnt/testpool/apps/demo", doel: "/data", type: "host_path", soort: "data", dataset: "testpool/apps/demo" }],
    datasets: ["testpool/apps/demo"],
    resourcegrenzen: { status: "unknown", reden: "", toelichting: "" },
    documentatie: null,
    gezondheidsprofiel: { binnenkant: null, binnenkant_vereist: false },
    dienst: null,
    bron: null,
    acties: [],
    actiebeleid: actiebeleid(),
    ...extra,
  };
}

const staat = (data: Beleid | undefined, stale = false) => ({ data, error: undefined, loading: false, stale, lastOk: null, etag: null, reload: async () => undefined });
const knoppen = (html: string) => [...html.matchAll(/data-testid="(actie-[^"]+|bijwerken)"/g)].map((m) => m[1]);

beforeEach(() => {
  proef.rol = "admin";
  proef.data = {};
  proef.fouten.clear();
  proef.oud.clear();
});

describe("bescherming (HARDE EIS)", () => {
  it.each([EMBY, MG])("het serveroordeel blokkeert ook onder een vrije naam ($id)", (blokkade) => {
    const alias = app({ naam: "kijkkamer", app_id: null, actiebeleid: actiebeleid([blokkade]) });
    const rijen = appActies(BELEID, alias);
    for (const id of ["app.restart", "app.stop", "app.update", "app.rollback", "app.uninstall"]) {
      expect(rijen.find((r) => r.actie.action_id === id)?.blokkades).toEqual([blokkade]);
    }
    expect(appActies(BELEID, app()).find((r) => r.actie.action_id === "app.uninstall")?.blokkades).toEqual([]);
  });

  it.each([undefined, null, { ...actiebeleid(), policy_hash: "oud" }, { ...actiebeleid(), acties: {} }])(
    "beide tabs blijven dicht zonder passend serveroordeel", (oordeel) => {
      const doel = app({ actiebeleid: oordeel, installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.3.0" } });
      for (const Tab of [Acties, Versies]) {
        const html = renderToStaticMarkup(<Tab app={doel} beleid={staat(BELEID)} />);
        expect(knoppen(html)).toEqual([]);
        expect(html).not.toContain("Via Versies");
        expect(html).toContain("De bescherming van deze app is onbekend");
      }
    },
  );

  it("tab Acties bij Emby: geen enkele actieknop, wel de vaste zin en de reden uit het beleid", () => {
    const html = renderToStaticMarkup(<Acties app={app({ naam: "emby", runtime_id: "emby", app_id: "emby", actiebeleid: actiebeleid([EMBY]) })} beleid={staat(BELEID)} />);
    expect(knoppen(html)).toEqual([]);
    expect(html).toContain("Emby blijft beschikbaar. Alleen jij kunt Emby verwijderen.");
    expect(html).toContain("Het platform stopt, updatet of verwijdert Emby nooit.");
  });

  it.each(["admin", "viewer"])("tab Versies bij MediaGuard: bescherming zichtbaar voor %s zonder bijwerk- of terugzetknop", (rol) => {
    proef.rol = rol;
    const html = renderToStaticMarkup(
      <Versies app={app({ naam: "mediaguard", runtime_id: "mediaguard", app_id: "mediaguard", actiebeleid: actiebeleid([MG]), installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.3.0" } })} beleid={staat(BELEID)} />,
    );
    expect(knoppen(html)).toEqual([]);
    expect(html).not.toContain("Terugzetten naar");
    expect(html).toContain('data-testid="beschermd"');
  });

  it("zonder (vers) beleid geen enkele knop: toegestane acties onbekend", () => {
    expect(knoppen(renderToStaticMarkup(<Acties app={app()} beleid={staat(undefined)} />))).toEqual([]);
    expect(knoppen(renderToStaticMarkup(<Acties app={app()} beleid={staat(BELEID, true)} />))).toEqual([]);
  });
});

describe("tab Acties (S-045)", () => {
  it("klasse per doel: Custom App en kritieke app volgens het beleid", () => {
    const rijen = (a: CatalogDetail) => Object.fromEntries(appActies(BELEID, a).map((r) => [r.actie.action_id, r.klasse]));
    expect(rijen(app())["app.stop"]).toBe("R2");
    const oordeel = actiebeleid();
    oordeel.acties["app.stop"]!.risk_class = "R1";
    oordeel.acties["app.restart"]!.risk_class = "R2";
    expect(rijen(app({ installatiewijze: "catalog_app", actiebeleid: oordeel }))["app.stop"]).toBe("R1");
    expect(rijen(app({ app_id: "authentik", actiebeleid: oordeel }))["app.restart"]).toBe("R2");
    expect(rijen(app())).not.toHaveProperty("notification.send");
  });

  it("operator ziet voorstelknoppen; een kijker alleen de rolmelding", () => {
    proef.rol = "operator";
    expect(knoppen(renderToStaticMarkup(<Acties app={app()} beleid={staat(BELEID)} />))).toEqual(["actie-app.restart", "actie-app.stop", "actie-app.uninstall"]);
    proef.rol = "viewer";
    const html = renderToStaticMarkup(<Acties app={app()} beleid={staat(BELEID)} />);
    expect(knoppen(html)).toEqual([]);
    expect(html).toContain('data-testid="rolmelding"');
  });

  it("de zin over de data staat vast en er is nergens een keuze om data te wissen", () => {
    expect(ALLEEN_CONTAINER).toBe("Alleen de container wordt verwijderd. Je gegevens blijven bewaard.");
    const html = renderToStaticMarkup(<Acties app={app()} beleid={staat(BELEID)} />);
    expect(html).not.toMatch(/type="checkbox"/);
    expect(html).not.toMatch(/uninstall_data|Data wissen/);
  });
});

describe("tab Versies (S-044)", () => {
  it("bijwerken alleen met een getypte catalogusversie van TrueNAS; een Custom App krijgt geen vrij veld", () => {
    expect(updateDoel(app({ installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.4.15" } }))).toEqual({
      parameters: { catalog_version: "1.4.15" },
      naar: "1.4.15",
    });
    expect(updateDoel(app({ installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "latest" } }))).toHaveProperty("reden");
    expect(updateDoel(app({ installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: false } }))).toEqual({ reden: "TrueNAS meldt geen nieuwere catalogusversie." });
    expect(updateDoel(app())).toHaveProperty("reden");
    const html = renderToStaticMarkup(<Versies app={app()} beleid={staat(BELEID)} />);
    expect(html).not.toMatch(/<input|<textarea/);
  });

  it("terugzetten alleen naar een eigen, uitgevoerde bijwerking van deze app; anders geblokkeerd met reden", () => {
    const v = (status: string, app_id: string) => ({ request_id: `r-${status}-${app_id}`, action_id: "app.update", status, target: { app_id }, uitgevoerd_op: "2026-11-20T10:00:00Z" }) as never;
    expect(terugzetPunten([v("uitgevoerd", "demo"), v("mislukt", "demo"), v("uitgevoerd", "ander")], "demo")).toEqual([{ request_id: "r-uitgevoerd-demo", uitgevoerd_op: "2026-11-20T10:00:00Z" }]);
    proef.data["/api/v1/actions"] = { items: [], next_cursor: null, bijgewerkt_op: "" };
    const html = renderToStaticMarkup(<Versies app={app()} beleid={staat(BELEID)} />);
    expect(html).toContain(GEEN_TERUGZETPAD);
    expect(html).toContain('href="/backups"');
  });
});

function plan(extra: Partial<InstallPlan> = {}): InstallPlan {
  return {
    plan_id: "99999999-2222-3333-4444-555555555555",
    app_id: "fotos",
    app_name: "fotos",
    step_id: "installeren",
    status: "klaar_voor_voorstel",
    reden: null,
    expires_at: new Date(Date.now() + 600_000).toISOString(),
    request_id: null,
    release: { catalog: { train: "stable", app: "immich", version: "1.4.8" }, image_digests: [`sha256:${"c".repeat(64)}`] },
    controles_na_installatie: [{ id: "web", soort: "http", beschrijving_nl: "De webinterface antwoordt." }],
    ...extra,
  };
}

describe("installatiewizard (S-047)", () => {
  const nu = new Date();
  it("controle vooraf: verlopen, geblokkeerd of onbekend houdt tegen; klaar niet", () => {
    expect(planBlokkade(plan(), nu)).toBeNull();
    expect(planBlokkade(plan({ expires_at: new Date(Date.now() - 1000).toISOString() }), nu)).toBe(PLAN_VERLOPEN);
    expect(planBlokkade(plan({ status: "geblokkeerd", reden: "planner_niet_klaar" }), nu)).toContain("controle vooraf");
    expect(planBlokkade(plan({ status: "iets_nieuws" }), nu)).toBe("De stand van dit plan is onbekend.");
  });

  it("zonder bron voor manifests: ‘Kies app’ met C-12 en ‘Volgende’ uit met reden", () => {
    const html = renderToStaticMarkup(<Installatiewizard planId={null} />);
    expect(html).toContain("Stap 1 van 7: Kies app");
    expect(html).toContain("de Hub kan de installeerbare manifests nog niet ophalen");
    expect(html).toMatch(/<button[^>]*aria-disabled="true"[^>]*aria-describedby="volgende-reden"[^>]*data-testid="wizard-volgende"/);
    expect(html).not.toMatch(/<textarea|yaml|compose_config/i);
  });

  it("geblokkeerd plan: blijft bij ‘Controle vooraf’, knop uit met de reden", () => {
    proef.data["/api/v1/catalog/plans/p"] = plan({ status: "geblokkeerd", reden: "voorganger_onbevestigd" });
    const html = renderToStaticMarkup(<Installatiewizard planId="p" />);
    expect(html).toContain("Stap 3 van 7: Controle vooraf");
    expect(html).toMatch(/aria-disabled="true"[^>]*aria-describedby="volgende-reden"/);
    expect(html).toContain("Een eerdere stap van dit plan is nog niet bevestigd.");
  });

  it("preview: digests en catalogus, ontbrekende velden ‘niet beschikbaar’, geen geheime of onbekende waarde in de HTML", () => {
    const geheim = "GEHEIM-TESTWAARDE-180"; // gitleaks:allow -- synthetische testwaarde
    proef.data["/api/v1/catalog/plans/p"] = { ...plan(), parameters: { wachtwoord: geheim }, release: { ...plan().release, extra: geheim } };
    const html = renderToStaticMarkup(<Installatiewizard planId="p" />);
    expect(html).toContain("Stap 4 van 7: Preview");
    expect(html).toContain(`sha256:${"c".repeat(64)}`);
    expect(html).toContain("stable / immich / 1.4.8");
    expect(html).toContain("Niet beschikbaar — het installatieplan levert dit nog niet aan de browser.");
    expect(html).not.toContain(geheim);
    expect(planDigests(plan({ release: { image_digests: ["sha256:kort", geheim] } }))).toEqual([]);
    expect(planCatalogus(plan({ release: { catalog: { train: "stable", app: geheim, version: "1.0" } } }))).toBeNull();
  });
});

it("een dichte back-upgate houdt de bijwerkknop uit en toont de reden", () => {
  proef.data["/api/v1/gates/backup_gate"] = { status: "geblokkeerd", toegestaan: false, redenen: [
    { soort: "meting", id: "eigen_backup", status: "geblokkeerd", tekst: "interne proefnotitie" },
  ] };
  const html = renderToStaticMarkup(<Versies app={app({ installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.2.3" } })} beleid={staat(BELEID)} />);
  expect(html.match(/<button[^>]+data-testid="bijwerken"[^>]*>/)?.[0]).toContain('aria-disabled="true"');
  expect(html).toContain("Hub-database");
  expect(html).not.toContain("interne proefnotitie");
});

const catalogusApp = () => app({ installatiewijze: "catalog_app", catalogus: { upgrade_beschikbaar: true, nieuwste_versie: "1.2.3" } });

it.each([
  "gedekt", "verplichte onbekende MSO", "verlopen inventaris", "ontbrekende inventarisbron", "ontbrekende inventarislijst",
  "MSO aanwezig onder een alias", "onherkende app", "ontbrekende export", "export niet geverifieerd", "exportlezing verouderd",
])("overzicht en beide versieknoppen delen de gate bij %s", (situatie) => {
  const doel = catalogusApp();
  const tijd = new Date(Date.now() - 1000).toISOString();
  const geldig = new Date(Date.now() + 60_000).toISOString();
  const mso = "media-source-optimizer";
  const bron = { status: "ok", observed_at: tijd, verouderd: false };
  const exportPad = "/api/v1/backups/self";
  const appRij = { app: doel.naam, herkend_als: situatie === "MSO aanwezig onder een alias" ? mso : situatie === "onherkende app" ? null : doel.naam,
    rpo_rto: { rpo_uren: 24 }, db_export: { status: "geverifieerd", bron: "pg_dump" }, volledige_appbackup: true, lokaal_snapshot: "gedekt" };
  proef.data["/api/v1/gates/backup_gate"] = { status: "toegestaan", toegestaan: true, afgeleid_op: tijd, redenen: [],
    vereist: { metingen: ["eigen_backup", ...Object.keys(BRONNAMEN)], besluiten: [], gates: [] } };
  const bronnen = Object.fromEntries(["apps", "datasets", "snapshot_tasks", "latest_snapshots", "replication", "cloudsync"].map(id => [id, { ...bron }]));
  if (situatie === "verlopen inventaris") bronnen.apps!.observed_at = new Date(Date.now() - 3600_000).toISOString();
  if (situatie === "ontbrekende inventarisbron") delete bronnen.apps;
  proef.data["/api/v1/backups/coverage"] = { apps: situatie === "ontbrekende inventarislijst" ? undefined : [appRij], datasets: [], bronnen,
    app_backups: Object.fromEntries(Object.keys(BRONNAMEN).map(id => [id, { observed_at: tijd, geldig_tot: geldig,
      status: id === mso ? "unknown" : "gedekt", vereist: id !== mso || situatie === "verplichte onbekende MSO" }])) };
  const eigen = { id: doel.id, beeindigd_op: tijd, status: situatie === "export niet geverifieerd" ? "mislukt" : "geslaagd",
    sha256: "a".repeat(64), inhoudsopgave_items: 10 };
  proef.data[exportPad] = situatie === "ontbrekende export" ? { laatste_geverifieerd: null, items: [] } : { laatste_geverifieerd: eigen, items: [eigen] };
  if (situatie === "exportlezing verouderd") proef.oud.add(exportPad);
  proef.data["/api/v1/actions"] = { items: [{ action_id: "app.update", status: "uitgevoerd", target: { app_id: doel.naam }, request_id: doel.id, uitgevoerd_op: tijd }] };
  proef.data["/api/v1/backups/herstelpunten"] = { items: [{ id: doel.id, app: doel.naam, checkpoint_id: doel.id, gemaakt_op: tijd,
    snapshot: { actie_id: doel.id, datasets: ["proef/app"] }, status: "geverifieerd", reden: null }] };

  const overzicht = renderToStaticMarkup(<BackupsScreen />);
  const gate = overzicht.match(/data-testid="sectie-backupgate"[^]*?<\/section>/)?.[0];
  expect(gate).toBeDefined();
  expect(gate!.includes(">Toegestaan<")).toBe(situatie === "gedekt");
  const versies = renderToStaticMarkup(<Versies app={doel} beleid={staat(BELEID)} />);
  const knoppen = [...versies.matchAll(/(<button\b[^>]*>)(Bijwerken naar|Terugzetten naar)/g)];
  expect(knoppen.map(m => m[2])).toEqual(["Bijwerken naar", "Terugzetten naar"]);
  expect(knoppen.map(m => m[1]!.includes('aria-disabled="true"'))).toEqual([situatie !== "gedekt", situatie !== "gedekt"]);
});

it.each(["proef-foutcode", "forbidden"])("Versies filtert de foutcode %s met bijbehorend kopieerveld", (code) => {
  const bekend = code === "forbidden";
  const trace = catalogusApp().id;
  proef.fouten.set("/api/v1/actions", new HubApiError(403, code, "proef-bericht", { extra: "proef-detail" }, bekend ? trace : "proef-trace"));
  const html = renderToStaticMarkup(<Versies app={catalogusApp()} beleid={staat(BELEID)} />);
  expect(html).toContain(bekend ? 'data-code="forbidden"' : 'data-code="onbekend"');
  expect(html).toContain(bekend ? "Je hebt geen recht voor deze handeling." : "De Hub meldde een onbekende fout.");
  expect(html).not.toMatch(/proef-(foutcode|bericht|detail|trace)|Technische details/);
  expect(/Kopiëren<span[^>]*>: Trace-ID<\/span>/.test(html)).toBe(bekend);
  if (bekend) expect(html).toContain(trace);
});
