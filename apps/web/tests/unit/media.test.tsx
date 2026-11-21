/** Scherm Media (S-P3-080): toestandstabel met één test per rij, inclusief de negatieve rijen (a), (b) en (c). */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CijferTegel, MediaGuardKaart, MediaInhoud, MediaScreen } from "@/app/media/MediaScreen";
import type { Koppeling } from "@/app/instellingen/diensten/adapterweergave";
import { ketenLink, mediaguardWeergave, type BronCijfer, type MediaGuardOverzicht, type MediaGuardWeergave } from "@/app/media/mediaweergave";
import { HubApiError } from "@/lib/api";
import { PLANNED } from "@/lib/nav";
import type { ApiState } from "@/lib/use-api";

const proef = vi.hoisted(() => ({ lijst: {} as Partial<ApiState<unknown>>, mg: {} as Partial<ApiState<unknown>> }));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string) => ({ reload: vi.fn(), ...(pad.endsWith("/mediaguard") ? proef.mg : proef.lijst) }),
}));

const NU = Date.parse("2026-11-21T12:00:00Z");
const onbekend = { status: "unknown", observed_at: null, reason_code: "geen_alleen_lezen_bron" };
const MG: Koppeling = {
  id: "mg-1", app_id: "mediaguard", catalog_app_id: "c-mg", basis_url: "https://media.example", laatste4: "ABCD",
  ingevoerd_op: null, version: 1, verbinding: { ...onbekend },
};
const VERS = "2026-11-21T11:59:00Z";
const OUD = "2026-11-21T11:40:00Z";
const SERVERS = { status: "onbekend", servers: null, reden: "MediaGuard heeft nog geen bijwerkingsvrije mediaserverbron" } as const;
const gemeten = (waarde: number, observed_at = VERS): BronCijfer => ({ status: "gemeten", waarde, observed_at, reden: null });
const weg = (reden: string): BronCijfer => ({ status: "onbekend", waarde: null, observed_at: null, reden });
function overzicht(extra: Partial<MediaGuardOverzicht> = {}): MediaGuardOverzicht {
  return {
    wanted: gemeten(17), status: gemeten(0), downloads: weg("MediaGuard heeft nog geen bijwerkingsvrije downloadbron"), av1: gemeten(3), incidenten: gemeten(6),
    noodstop: { status: "gemeten", actief: false, sinds: null, observed_at: VERS, reden: null }, mediaservers: SERVERS, ...extra,
  };
}
const ONBEKEND = overzicht(Object.fromEntries(["wanted", "status", "downloads", "av1", "incidenten"].map((k) => [k, weg("geen leesrecht")])));
ONBEKEND.noodstop = { status: "onbekend", actief: null, sinds: null, observed_at: null, reden: "geen leesrecht" };
const tegel = (html: string, id: string) => tekst(html.split(`data-testid="cijfer-${id}"`)[1]!.split("</div>")[0]!);
function mso(verbinding: Koppeling["verbinding"], extra: Partial<Koppeling> = {}): Koppeling {
  return { id: "mso-1", app_id: "media-source-optimizer", catalog_app_id: "c-mso", basis_url: "https://mso.example", laatste4: "",
    ingevoerd_op: null, version: 1, verbinding, ...extra };
}
const vers = { status: "healthy", observed_at: "2026-11-21T11:58:00Z", reason_code: null };
const inhoud = (k: Koppeling[], verouderd = false) => renderToStaticMarkup(<MediaInhoud koppelingen={k} verouderd={verouderd} nu={NU} />);
const tekst = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("Media: toestanden van het scherm", () => {
  beforeEach(() => { proef.lijst = {}; proef.mg = { data: ONBEKEND }; });

  it("(c) leeg: geen koppeling verwijst naar het koppelscherm en toont geen cijfers", () => {
    const html = inhoud([]);
    expect(html).toContain("MediaGuard en MSO zijn nog niet gekoppeld");
    expect(html).toContain('href="/instellingen/diensten"');
    expect(html).not.toContain("cijfer-");
  });

  it("bezig: tijdens het ophalen geen lege of gevulde toestand", () => {
    proef.lijst = { loading: true };
    const html = renderToStaticMarkup(<MediaScreen />);
    expect(html).toContain("Koppelingen ophalen");
    expect(html).not.toContain("niet gekoppeld");
  });

  it("fout: een geweigerde lijst toont de fout en geen eerdere gegevens", () => {
    proef.lijst = { error: new HubApiError(403, "forbidden", "Geen toegang."), data: { items: [MG], next_cursor: null } };
    const html = renderToStaticMarkup(<MediaScreen />);
    expect(html).toContain("Mediagegevens ontbreken");
    expect(html).not.toContain("cijfer-wanted");
  });

  it("verouderd: bij verbindingsuitval blijft de laatst bekende lijst staan, gemarkeerd als verouderd", () => {
    proef.lijst = { error: new HubApiError(503, "api_unavailable", "Niet bereikbaar."), stale: true, data: { items: [mso(vers)], next_cursor: null } };
    const html = renderToStaticMarkup(<MediaScreen />);
    expect(html).toContain("Verouderde mediagegevens");
    expect(html).toContain("Laatst gemeten");
  });

  it("(a) bron onbekend: elk MediaGuard-cijfer is onbekend met reden, nooit nul", () => {
    const html = inhoud([MG]);
    for (const id of ["wanted", "status", "downloads", "av1", "incidenten"]) {
      expect(tegel(html, id)).toContain("Onbekend: geen leesrecht");
      expect(tegel(html, id)).not.toMatch(/\b0\b/);
    }
    expect(tekst(html)).toContain("Mediaservers Onbekend: MediaGuard heeft nog geen bijwerkingsvrije mediaserverbron");
    expect(tekst(html)).toContain("Noodstop · onbekend: geen leesrecht");
    expect(html).not.toContain("pauzebalk");
  });

  it("gevuld: vijf gemeten cijfers met meettijd, ook een gemeten nul, en de noodstop uit", () => {
    proef.mg = { data: overzicht() };
    const html = inhoud([MG]);
    expect(tegel(html, "wanted")).toContain("17 · gemeten");
    expect(tegel(html, "status")).toContain("0 · gemeten");
    expect(tegel(html, "av1")).toContain("AV1 · lopende encodes 3 · gemeten");
    expect(html).toContain('dateTime="2026-11-21T11:59:00Z"');
    expect(html).toContain('data-testid="noodstop-uit"');
    expect(html).not.toContain("pauzebalk");
    expect(tekst(html)).toContain("Mediaservers Onbekend:");
  });

  it("(b) noodstop aan uit de bron: de balk staat er met sinds en er is geen knop om hem uit te zetten", () => {
    proef.mg = { data: overzicht({ noodstop: { status: "gemeten", actief: true, sinds: "2026-11-21T09:30:00Z", observed_at: VERS, reden: null } }) };
    const html = inhoud([MG]);
    expect(html).toContain('data-testid="pauzebalk"');
    expect(html).toContain('dateTime="2026-11-21T09:30:00Z"');
    expect(html).not.toContain("<button");
  });

  it("verouderd: een meting ouder dan vijftien minuten staat grijs en de noodstop is dan onbekend", () => {
    proef.mg = { data: overzicht({ wanted: gemeten(17, OUD), noodstop: { status: "gemeten", actief: true, sinds: OUD, observed_at: OUD, reden: null } }) };
    const html = inhoud([MG]);
    expect(tegel(html, "wanted")).toContain("Laatst gemeten");
    expect(tegel(html, "wanted")).toContain("meting verouderd");
    expect(tegel(html, "wanted")).not.toContain("17 · gemeten");
    expect(html).not.toContain("pauzebalk");
    expect(tekst(html)).toContain("Noodstop · onbekend: meting verouderd");
  });

  it("verouderd volgens de Hub: onbekend zonder getal, met 'Laatst gemeten' en de bronmeettijd, nooit 'Nog nooit gemeten'", () => {
    // Vorm van het echte Hub-antwoord bij een verouderde bron (R-VEILIG-5): onbekend, waarde null, oorspronkelijke meettijd.
    const verouderd: BronCijfer = { status: "onbekend", waarde: null, observed_at: OUD, reden: "meting verouderd" };
    proef.mg = { data: overzicht({ wanted: verouderd, noodstop: { status: "onbekend", actief: null, sinds: null, observed_at: OUD, reden: "meting verouderd" } }) };
    const html = inhoud([MG]);
    const wanted = html.split('data-testid="cijfer-wanted"')[1]!.split("</dl>")[0]!;
    expect(tekst(wanted)).toContain("Onbekend Laatst gemeten");
    expect(wanted).toContain("text-stale-ink");
    expect(wanted).toContain(`dateTime="${OUD}"`);
    expect(tekst(wanted)).toContain("meting verouderd");
    expect(wanted).not.toContain("Nog nooit gemeten");
    expect(tekst(wanted)).not.toMatch(/\b17\b/);
    expect(html).not.toContain("pauzebalk");
    expect(html).not.toContain("noodstop-uit");
    expect(tekst(html)).toContain("Noodstop · onbekend: meting verouderd · laatst gemeten");
    expect(html).toContain(`<time dateTime="${OUD}">`);
  });

  it("nooit gemeten: zonder bronmeettijd blijft 'Nog nooit gemeten' staan", () => {
    const html = inhoud([MG]);
    expect(html.split('data-testid="cijfer-wanted"')[1]!.split("</dl>")[0]).toContain("Nog nooit gemeten");
    expect(tegel(html, "wanted")).not.toContain("Laatst gemeten");
  });

  it("verbindingsuitval: het laatste overzicht blijft grijs staan, nooit als actueel", () => {
    proef.mg = { data: overzicht(), error: new HubApiError(503, "api_unavailable", "Niet bereikbaar."), stale: true };
    const html = inhoud([MG]);
    expect(tegel(html, "wanted")).toContain("Laatst gemeten");
    expect(tegel(html, "wanted")).toContain("De Hub kon MediaGuard niet opnieuw lezen.");
    expect(tekst(html)).toContain("Noodstop · onbekend: De Hub kon MediaGuard niet opnieuw lezen.");
  });

  it("weigering: geen eerdere meting, wel de reden", () => {
    proef.mg = { data: overzicht(), error: new HubApiError(403, "forbidden", "Geen toegang.") };
    const html = inhoud([MG]);
    expect(tegel(html, "wanted")).toContain("Onbekend: Geen toegang.");
    expect(tekst(html)).not.toMatch(/\b17\b/);
  });

  it("bezig: zolang het overzicht wordt opgehaald is elk cijfer onbekend, nooit nul", () => {
    proef.mg = { loading: true };
    expect(tegel(inhoud([MG]), "status")).toContain("Onbekend: wordt opgehaald");
  });

  it("ongeldige meettijd of onbekend met waarde: geen getal", () => {
    const o = overzicht({ wanted: gemeten(17, "2026-11-21T13:00:00Z"), status: { status: "onbekend", waarde: 5, observed_at: VERS, reden: "bron onbereikbaar" } });
    const mg = mediaguardWeergave(MG, o, NU, false, "x");
    expect(mg.cijfers[0]).toMatchObject({ waarde: null, zekerheid: "onbekend" });
    expect(mg.cijfers[1]).toMatchObject({ waarde: null, zekerheid: "onbekend", reden: "bron onbereikbaar" });
  });

  it("noodstop aan: de kaart zelf heeft geen knop", () => {
    const mg: MediaGuardWeergave = { ...mediaguardWeergave(MG, ONBEKEND, NU, false, "x"), noodstop: { actief: true, sinds: "2026-11-21T09:30:00Z", reden: null, observedAt: VERS } };
    const html = renderToStaticMarkup(<MediaGuardKaart mg={mg} />);
    expect(tekst(html)).toContain("gepauzeerd (noodstop)");
    expect(html).not.toContain("<button");
    expect(tekst(html)).not.toContain("Noodstop · onbekend");
  });

  it("mediaservers: label, verbonden en kijkpauze als ja/nee/onbekend", () => {
    const mg: MediaGuardWeergave = { ...mediaguardWeergave(MG, ONBEKEND, NU, false, "x"), servers: [
      { label: "Emby", verbonden: true, kijkpauze: false }, { label: "Tweede", verbonden: null, kijkpauze: null },
    ] };
    const t = tekst(renderToStaticMarkup(<MediaGuardKaart mg={mg} />));
    expect(t).toContain("Emby Verbonden · ja Kijkpauze actief · nee");
    expect(t).toContain("Tweede Verbonden · onbekend Kijkpauze actief · onbekend");
  });

  it("gemeten cijfer: waarde met '· gemeten' en meettijd", () => {
    const t = tekst(renderToStaticMarkup(<CijferTegel bron="MediaGuard" cijfer={{ id: "wanted", titel: "Wanted", waarde: 12, zekerheid: "gemeten", observedAt: "2026-11-21T11:59:00Z", verouderd: false, reden: null }} />));
    expect(t).toContain("12 · gemeten");
    expect(t).not.toContain("Laatst gemeten");
  });

  it("geschat cijfer: '≈' en '· geschat', nooit in dezelfde look als gemeten", () => {
    const t = tekst(renderToStaticMarkup(<CijferTegel bron="MediaGuard" cijfer={{ id: "av1", titel: "AV1", waarde: 3, zekerheid: "geschat", observedAt: "2026-11-21T11:59:00Z", verouderd: false, reden: null }} />));
    expect(t).toContain("≈ 3 · geschat");
  });

  it("verouderd cijfer: oude waarde grijs met 'Laatst gemeten', nooit als actueel", () => {
    const html = renderToStaticMarkup(<CijferTegel bron="MediaGuard" cijfer={{ id: "status", titel: "Status", waarde: 5, zekerheid: "gemeten", observedAt: "2026-11-21T09:00:00Z", verouderd: true, reden: null }} />);
    expect(html).toContain("text-stale-ink");
    expect(tekst(html)).toContain("Laatst gemeten");
    expect(tekst(html)).toContain("Verouderd");
  });

  it("onbekend cijfer met waarde toont toch geen getal", () => {
    const t = tekst(renderToStaticMarkup(<CijferTegel bron="MediaGuard" cijfer={{ id: "x", titel: "X", waarde: 0, zekerheid: "onbekend", observedAt: null, verouderd: false, reden: "geen bevestigde meting" }} />));
    expect(t).toContain("Onbekend");
    expect(t).not.toMatch(/\b0\b/);
  });

  it("MSO vers bereikbaar: gezondheid gemeten, open wijzigingen en kosten onbekend met herkomst en MSO-link", () => {
    const html = inhoud([mso(vers)]);
    const t = tekst(html);
    expect(t).toContain("Bereikbaar · gemeten");
    expect(t).toContain("Open wijzigingen onbekend: leesrecht niet bevestigd · bekijk ze in MSO");
    expect(t).toContain("Kosten onbekend: leesrecht niet bevestigd · herkomst: MSO");
    expect(html).toContain('href="https://mso.example"');
    expect(t).toContain("MediaGuard is niet gekoppeld");
  });

  it("MSO meting ouder dan vijftien minuten: grijs 'Laatst gemeten'", () => {
    const t = tekst(inhoud([mso({ ...vers, observed_at: "2026-11-21T11:00:00Z" })]));
    expect(t).toContain("Laatst gemeten");
    expect(t).not.toContain("Bereikbaar · gemeten");
  });

  it("MSO onbereikbaar na eerder contact: oude stand grijs met de oorzaak", () => {
    const t = tekst(inhoud([mso({ status: "unknown", observed_at: "2026-11-21T11:58:00Z", reason_code: "bron_onbereikbaar", laatste_status: "healthy" })]));
    expect(t).toContain("Laatst gemeten");
    expect(t).toContain("niet bereikbaar");
  });

  it("MSO nooit gemeten: onbekend, geen meettijd", () => {
    const t = tekst(inhoud([mso({ status: "unknown", observed_at: null, reason_code: "meettijd_onbekend" })]));
    expect(t).toContain("Gezondheid (openbare verbindingstest) Onbekend");
    expect(t).toContain("Nog nooit gemeten");
  });

  it("MSO zonder veilig adres: geen link naar MSO", () => {
    const html = inhoud([mso(vers, { basis_url: "http://mso.example" })]);
    expect(html).not.toContain("Open in MSO");
  });

  it("gevuld scherm heeft geen enkele actieknop voor MediaGuard of MSO", () => {
    expect(inhoud([MG, mso(vers)])).not.toContain("<button");
  });

  it("waarom ontbreekt dit: per schakel de eigenaar en een link naar diens scherm", () => {
    const t = tekst(inhoud([MG, mso(vers)]));
    expect(t).toContain("Diagnose van het ontbrekende item · eigenaar MediaGuard");
    expect(t).toContain("Compatibiliteit met MediaGuard · eigenaar MSO");
    expect(ketenLink([MG], "mediaguard", "/ontbrekend")).toBe("https://media.example/ontbrekend");
    expect(ketenLink([MG], "media-source-optimizer", "/downloads")).toBe("/instellingen/diensten");
    expect(ketenLink([mso(vers), mso(vers, { id: "mso-2" })], "media-source-optimizer", "/downloads")).toBe("/instellingen/diensten");
  });

  it("Jelly Leon blijft gepland (P4) en het scherm veronderstelt geen Jellyfin", () => {
    const t = tekst(inhoud([MG]));
    expect(t).toContain("Gepland in fase P4");
    expect(t).not.toContain("Jellyfin");
  });

  it("media staat niet meer in PLANNED", () => {
    expect(PLANNED.media).toBeUndefined();
  });
});
