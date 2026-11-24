import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, expect, it, vi } from "vitest";
import { puntenReden, uploadStand, type Herstelpunt } from "@/lib/backups";
import { Hersteltests } from "@/app/backups/Hersteltests";
import { AppsScreen } from "@/app/apps/AppsScreen";
import { GoedkeuringenScreen } from "@/app/goedkeuringen/GoedkeuringenScreen";
import { BeleidScreen } from "@/app/goedkeuringen/beleid/BeleidScreen";
import { BackupsScreen } from "@/app/backups/BackupsScreen";
import { Monitorplan } from "@/app/instellingen/monitoring/Monitorplan";
import { LIJST_MAX_LEEFTIJD_MS, lijstIsVers } from "@/lib/lijstversheid";
import { formatDateTime } from "@/lib/format";
import { Extern, Herstelpunten, Rampenscenarios } from "@/app/backups/BackupDetails";
import { Automatisering } from "@/app/automatisering/Automatisering";

const bron = vi.hoisted(() => ({ rol: "admin", data: {} as Record<string, unknown> }));
vi.mock("@/lib/session", async (origineel) => ({ ...(await origineel<object>()), useRole: () => bron.rol }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/backups" }));
vi.mock("@/lib/use-api", () => ({ useApi: (pad: string) => ({ data: bron.data[pad], stale: false, reload: vi.fn() }) }));

const nu = Date.parse("2026-11-20T10:00:00Z");
const id = "99999999-2222-4333-8444-555555555555";
const punt: Herstelpunt = {
  id, app: "mediaguard", checkpoint_id: id, gemaakt_op: new Date(nu - 3600_000).toISOString(),
  snapshot: { actie_id: id, datasets: ["proef/app"] },
  db_export: { bron: "pg_dump", sha256: "a".repeat(64), id }, status: "geverifieerd", reden: null,
};

beforeEach(() => { bron.rol = "admin"; bron.data = {}; });

it("alleen een geverifieerd punt binnen de RPO telt, met vereist databasebewijs", () => {
  expect(puntenReden(punt, "mediaguard", 2, nu)).toBeNull();
  expect(puntenReden({ ...punt, db_export: null }, "mediaguard", 2, nu)).toMatch(/database/i);
  expect(puntenReden({ ...punt, app: "andere-naam", db_export: null }, "emby", 2, nu)).toMatch(/database/i);
  expect(puntenReden(punt, "mediaguard", 0.5, nu)).toMatch(/RPO/);
  expect(puntenReden({ ...punt, status: "ongezond" }, "mediaguard", 2, nu)).toMatch(/hersteltest/i);
  expect(puntenReden({ ...punt, gemaakt_op: new Date(nu + 1).toISOString() }, "mediaguard", 2, nu)).toBeTruthy();
});

it("de eindtijd van de upload bepaalt de leeftijd, ook bij een nieuwe lezing", () => {
  const taak = { id: 7, status: "ok", beeindigd: new Date(nu - 3_600_000).toISOString() };
  expect(uploadStand(taak, 3600, nu)).toBe("ok");
  expect(uploadStand(taak, 3600, nu + 1)).toBe("verouderd");
  expect(uploadStand({ ...taak, beeindigd: null }, 3600, nu)).toBe("unknown");
});

it("aanmelding verlopen blijft zichtbaar en vrije taaktekst blijft buiten de pagina", () => {
  bron.data["/api/v1/backups/extern"] = { status: "aanmelding_verlopen", max_leeftijd_s: 60, taken: [
    { id: 2, status: "aanmelding_verlopen", fout: "interne proefnotitie" },
  ] };
  const html = renderToStaticMarkup(<Extern />);
  expect(html).toContain("Aanmelding verlopen");
  expect(html).toContain('href="/problemen"');
  expect(html).not.toContain("interne proefnotitie");
});

it("een kijker leest alleen het bewijsrecord en ziet geen hersteltestknop", () => {
  bron.rol = "viewer";
  bron.data["/api/v1/backups/restore-tests"] = { items: [{ id, soort: "dataset", resultaat: "onbekend", omschrijving: "interne proefnotitie" }] };
  const html = renderToStaticMarkup(<Hersteltests />);
  expect(html).toContain("Onbekend");
  expect(html).not.toMatch(/Nieuwe hersteltest|interne proefnotitie/);
});

it("een hersteltest levert geen oefendatum op en de instructies komen uit de vaste lijst", () => {
  bron.data["/api/v1/backups/rampenscenario"] = { scenarios: [{ id: "poolverlies", stappen: ["interne proefnotitie"] }], laatste_hersteltests: [{ uitgevoerd_op: new Date(nu).toISOString() }] };
  const html = renderToStaticMarkup(<Rampenscenarios />);
  expect(html).toContain("Laatste oefening onbekend");
  expect(html).toContain("<ol");
  expect(html).not.toContain("interne proefnotitie");
});

it("zonder flowbron blijven de flowstatus en het editoradres onbekend", () => {
  const html = renderToStaticMarkup(<Automatisering onderdeel="flows" />);
  expect(html).toContain("Flowstatus onbekend");
  expect(html).toContain("Editoradres niet bevestigd");
  expect(html).not.toMatch(/Geen flows|href="https?:/i);
});

it("een kloonvoorstel gebruikt de uitgevoerde snapshot en exact het eigen zandbakdoel", async () => {
  const { kloonDoelen } = await import("@/app/backups/Hersteltests");
  const v = { request_id: id, action_id: "zfs.snapshot.create", status: "uitgevoerd", target: { dataset: "proef/app" },
    preview: { wijziging: { soort: "snapshot_maken", snapshot: "proef/app@meetpunt" } },
    resultaat: { readback: { aanwezig: true, leden: { "proef/app": "42" } } } };
  expect(kloonDoelen(punt, v as never)).toEqual([{ snapshot: "proef/app@meetpunt", doel: `proef/asm-sandbox/proef-${id}-1` }]);
  expect(kloonDoelen(punt, { ...v, status: "onbekend" } as never)).toEqual([]);
  expect(kloonDoelen(punt, { ...v, resultaat: {} } as never)).toEqual([]);
});

it("flowherstel vereist menselijk R2 en overeenkomende readback, vrije nodevelden blokkeren de preview", async () => {
  const { FLOWHERSTEL, flowStatus, menselijkHerstel, flowDiff } = await import("@/lib/flowherstel");
  const sha = "a".repeat(64);
  const voorstel = { action_id: FLOWHERSTEL, status: "uitgevoerd", risk_class: "R2", actor: { type: "user" },
    target: { app_id: "home-control-hub", resource: "node_red" }, resultaat: { after_hash: `sha256:${sha}`,
      readback: { gelezen: true, snapshot_id: id, checksum_sha256: sha, gelijk_aan_momentopname: true } } };
  expect(flowStatus(voorstel as never, false)).toBe("uitgevoerd");
  expect(flowStatus(voorstel as never, true)).toBe("onbekend");
  expect(flowStatus({ ...voorstel, resultaat: {} } as never, false)).toBe("onbekend");
  expect(flowStatus({ ...voorstel, resultaat: { ...voorstel.resultaat, after_hash: "sha256:" + "b".repeat(64) } } as never, false)).toBe("onbekend");
  expect(menselijkHerstel({ ...voorstel, actor: { type: "flow" } } as never)).toBe(false);
  const diff = { afgekapt: false, waarden_getoond: false, aantallen: { toegevoegd: 1, gewijzigd: 0, verwijderd: 0 }, toegevoegd: [{ id: "aa", z: null, type: "inject" }], gewijzigd: [], verwijderd: [] };
  const wijziging = { soort: FLOWHERSTEL, eigenaar: "home-control-hub", diff };
  expect(flowDiff({ wijziging }).onveilig).toBe(false);
  expect(flowDiff({ wijziging: { ...wijziging, diff: { ...diff, toegevoegd: [{ id: "aa", z: null, type: "interne proefnotitie" }] } } })).toEqual({ regels: [], onveilig: true });
});

it("handmatig bevestigd is neutraal en vervalt zodra plan en bevestiging verschillen", async () => {
  const { monitorStand } = await import("@/app/instellingen/monitoring/Monitorplan");
  const sha = "sha256:" + "a".repeat(64);
  const regel = { stand: "handmatig bevestigd", bewaakt: true, plan_sha256: sha, bevestiging: { plan_sha256: sha }, bevestiging_verouderd: false };
  expect(monitorStand(regel as never, false)).toMatchObject({ tone: "neutral", label: "Handmatig bevestigd" });
  expect(monitorStand({ ...regel, plan_sha256: "sha256:" + "b".repeat(64) } as never, false).label).toBe("Niet bewaakt");
  expect(monitorStand(regel as never, true).tone).toBe("unknown");
});

it("vrije foutcodes, foutberichten en ongeldige trace-ID’s worden niet getoond of kopieerbaar", async () => {
  const { HubApiError } = await import("@/lib/api");
  const { toonbareFout, vasteFout } = await import("@/lib/acties");
  const { ErrorPanel } = await import("@/components/ErrorPanel");
  const vrij = "interne proefnotitie";
  const html = renderToStaticMarkup(<ErrorPanel vast={vasteFout} error={toonbareFout(new HubApiError(500, vrij, vrij, { detail: vrij }, vrij))} />);
  expect(html).not.toContain(vrij);
  expect(html).not.toContain("Kopieer");
  expect(html).toContain("onbekend");
});

it("geen onbekende of verlopen appmeting opent de gate; een ontbrekende MSO-leesroute blijft onbekend", async () => {
  const { backupGate, BRONNAMEN } = await import("@/lib/backups");
  const tijd = { observed_at: new Date(nu - 1).toISOString(), geldig_tot: new Date(nu + 1).toISOString() };
  const app_backups = Object.fromEntries(Object.keys(BRONNAMEN).map(naam => [naam, { ...tijd,
    status: naam === "media-source-optimizer" ? "unknown" : "gedekt", vereist: naam !== "media-source-optimizer" }]));
  const gate = { status: "toegestaan", toegestaan: true, redenen: [], afgeleid_op: new Date(nu).toISOString(),
    vereist: { besluiten: [], metingen: Object.keys(BRONNAMEN), gates: [] } };
  const dekking = { app_backups, apps: [], bronnen: { apps: { status: "ok", observed_at: tijd.observed_at, verouderd: false } } };
  expect(backupGate(gate as never, { app_backups } as never, false, nu)).toBe("unknown");
  expect(backupGate(gate as never, dekking as never, false, nu)).toBe("toegestaan");
  expect(backupGate(gate as never, dekking as never, false, nu + 2)).toBe("unknown");
  expect(backupGate(gate as never, dekking as never, true, nu)).toBe("unknown");
  app_backups["media-source-optimizer"]!.vereist = true;
  expect(backupGate(gate as never, dekking as never, false, nu)).toBe("unknown");
});

it("het monitorplan geeft alleen een bestaand meettijdstip weer in het datetime-attribuut", async () => {
  const { Monitorplan } = await import("@/app/instellingen/monitoring/Monitorplan");
  const pad = "/api/v1/monitoring/monitorplan";
  for (const observed_at of ["proef-meettijd", "2026-02-30T10:00:00Z", new Date(Date.now() + 3600_000).toISOString()]) {
    bron.data[pad] = { items: [], observed_at };
    const html = renderToStaticMarkup(<Monitorplan admin />);
    expect(html).toContain("Nog nooit gemeten");
    expect(html).not.toMatch(/<time\b/);
    expect(html).not.toContain(observed_at);
  }
  bron.data[pad] = { items: [], observed_at: "2024-02-29T11:00:00+01:00" };
  expect(renderToStaticMarkup(<Monitorplan admin />)).toContain('dateTime="2024-02-29T10:00:00.000Z"');
});

it.each([
  ["goedkeuringen", "/api/v1/actions?status=wacht_op_goedkeuring&limit=50", () => <GoedkeuringenScreen />, "Geen openstaande goedkeuringen."],
  ["beleidsbron", "/api/v1/policy", () => <BeleidScreen />, "De beleidsbron bevat geen acties."],
  ["herstelpunten", "/api/v1/backups/herstelpunten", () => <Herstelpunten />, "Geen herstelpunten gevonden."],
  ["hersteltests", "/api/v1/backups/restore-tests", () => <Hersteltests />, "Nog geen hersteltests."],
  ["oefenbewijs", "/api/v1/backups/rampenscenario", () => <Rampenscenarios />, "Nog geen hersteltests vastgelegd."],
  ["externe back-up", "/api/v1/backups/extern", () => <Extern />, "Geen passende uploadtaak"],
  ["gebeurtenissen", "/api/v1/events?source_app=home-control-hub&limit=50", () => <Automatisering onderdeel="eventtypen" />, "Geen gebeurtenissen ontvangen voor dit filter."],
  ["flowhistorie", "/api/v1/actions?limit=50", () => <Automatisering onderdeel="historie" />, "Geen actieverzoeken van flows."],
  ["flowdetail", "/api/v1/actions?limit=50", () => <Automatisering onderdeel="detail" flow={id} />, "Geen actieverzoeken van flows."],
  ["flowherstel", "/api/v1/actions?action_id=automation.flows.restore&limit=50", () => <Automatisering onderdeel="versies" />, "Geen herstelverzoeken gevonden."],
  ["monitorplan", "/api/v1/monitoring/monitorplan", () => <Monitorplan admin />, "Geen apps voor dit monitorplan."],
  ["eigen export", "/api/v1/backups/self", () => <BackupsScreen />, "Er is nog geen geverifieerde export van de Hub-database."],
] as const)("%s laat een verouderde lezing nooit een actuele leegmelding geven", (_naam, pad, scherm, leeg) => {
  const vers = Date.now() - 1000;
  const inhoud = { items: [], next_cursor: null, acties: [], scenarios: [], laatste_hersteltests: [], status: "ontbreekt", taken: [], laatste_geverifieerd: null };
  for (const uren of [0, 24]) {
    const tijd = new Date(vers - uren * 3600_000).toISOString();
    // usePaginaLijst geeft de oudste pagina als observed_at door aan het scherm.
    bron.data[pad] = { ...inhoud, observed_at: tijd, afgeleid_op: tijd, bijgewerkt_op: tijd };
    const html = renderToStaticMarkup(scherm());
    if (uren === 0) expect(html).toContain(leeg);
    else {
      expect(html).not.toContain(leeg);
      expect(html).toContain("Verouderd");
    }
  }
});

it("de meetgrens geldt ook zonder herladen en onbruikbare tijden bewijzen geen lege lijst", () => {
  const tijd = new Date(nu).toISOString();
  expect(lijstIsVers(tijd, nu + LIJST_MAX_LEEFTIJD_MS)).toBe(true);
  expect(lijstIsVers(tijd, nu + LIJST_MAX_LEEFTIJD_MS + 1)).toBe(false);
  for (const t of [null, undefined, "", "ongeldig", "2026-02-30T00:00:00Z", new Date(nu + 1000).toISOString()]) {
    expect(lijstIsVers(t, nu)).toBe(false);
  }
});

it("een verse ophaling maakt een oude app- of datasetinventaris niet actueel", () => {
  const vers = Date.now() - 1000;
  for (const oud of [false, true]) {
    const inventaris = { status: "ok", verouderd: false, observed_at: new Date(vers - (oud ? 24 * 3600_000 : 0)).toISOString() };
    bron.data["/api/v1/apps?limit=200"] = { items: [], totaal: 0, next_cursor: null, per_status: {},
      observed_at: new Date(vers).toISOString(), inventaris };
    bron.data["/api/v1/backups/coverage"] = { apps: [], datasets: [], bronnen: { datasets: inventaris } };
    const apps = renderToStaticMarkup(<AppsScreen />);
    const backups = renderToStaticMarkup(<BackupsScreen />);
    expect(apps.includes("Nog geen apps in de catalogus.")).toBe(!oud);
    expect(backups.includes("Geen datasets voor deze selectie.")).toBe(!oud);
    if (oud) {
      expect(apps).toContain("Inventaris verouderd");
      expect(backups).toContain("Datasets onbekend.");
      expect(apps).toContain(formatDateTime(inventaris.observed_at));
      expect(backups).toContain(formatDateTime(inventaris.observed_at));
    }
  }
});
