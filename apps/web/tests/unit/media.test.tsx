/** Scherm Media (S-P3-080): toestandstabel met één test per rij, inclusief de negatieve rijen (a), (b) en (c). */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CijferTegel, MediaGuardKaart, MediaInhoud, MediaScreen } from "@/app/media/MediaScreen";
import { ketenLink, mediaguardWeergave, type MediaGuardWeergave, type MediaKoppeling } from "@/app/media/mediaweergave";
import { HubApiError } from "@/lib/api";
import { PLANNED } from "@/lib/nav";
import type { ApiState } from "@/lib/use-api";

const proef = vi.hoisted(() => ({ lijst: {} as Partial<ApiState<unknown>> }));
vi.mock("@/lib/use-api", () => ({ useApi: () => ({ reload: vi.fn(), ...proef.lijst }) }));

const NU = Date.parse("2026-11-21T12:00:00Z");
const onbekend = { status: "unknown", observed_at: null, reason_code: "geen_alleen_lezen_bron" };
const MG: MediaKoppeling = {
  id: "mg-1", app_id: "mediaguard", catalog_app_id: "c-mg", basis_url: "https://media.example", laatste4: "ABCD",
  ingevoerd_op: null, version: 1, verbinding: { ...onbekend },
  mediaguard: Object.fromEntries(["wanted", "status", "downloads", "av1", "incidenten", "mediaservers", "noodstop"].map((k) => [k, onbekend])),
};
function mso(verbinding: MediaKoppeling["verbinding"], extra: Partial<MediaKoppeling> = {}): MediaKoppeling {
  return { id: "mso-1", app_id: "media-source-optimizer", catalog_app_id: "c-mso", basis_url: "https://mso.example", laatste4: "",
    ingevoerd_op: null, version: 1, verbinding, ...extra };
}
const vers = { status: "healthy", observed_at: "2026-11-21T11:58:00Z", reason_code: null };
const inhoud = (k: MediaKoppeling[], verouderd = false) => renderToStaticMarkup(<MediaInhoud koppelingen={k} verouderd={verouderd} nu={NU} />);
const tekst = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

describe("Media: toestanden van het scherm", () => {
  beforeEach(() => { proef.lijst = {}; });

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

  it("(a) adapter unknown: elk MediaGuard-cijfer is onbekend met reden, nooit nul", () => {
    const html = inhoud([MG]);
    for (const id of ["wanted", "status", "downloads", "av1", "incidenten"]) {
      const tegel = tekst(html.split(`data-testid="cijfer-${id}"`)[1]!.split("</div>")[0]!);
      expect(tegel).toContain("Onbekend");
      expect(tegel).not.toMatch(/\b0\b/);
    }
    expect(tekst(html)).toContain("geen alleen-lezen bron");
    expect(tekst(html)).toContain("Mediaservers Onbekend:");
    expect(tekst(html)).toContain("Noodstop · onbekend:");
    expect(html).not.toContain("pauzebalk");
  });

  it("(b) noodstop aan: de balk staat er met sinds wanneer en er is geen knop om hem uit te zetten", () => {
    const mg: MediaGuardWeergave = { ...mediaguardWeergave(MG), noodstop: { actief: true, sinds: "2026-11-21T09:30:00Z", reden: null } };
    const html = renderToStaticMarkup(<MediaGuardKaart mg={mg} />);
    expect(html).toContain('data-testid="pauzebalk"');
    expect(tekst(html)).toContain("gepauzeerd (noodstop)");
    expect(html).toContain('dateTime="2026-11-21T09:30:00Z"');
    expect(html).not.toContain("<button");
    expect(tekst(html)).not.toContain("Noodstop · onbekend");
  });

  it("mediaservers: label, verbonden en kijkpauze als ja/nee/onbekend", () => {
    const mg: MediaGuardWeergave = { ...mediaguardWeergave(MG), servers: [
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
