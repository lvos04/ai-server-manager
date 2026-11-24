import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RisicoBadge } from "@/components/ActiePreview";
import { ErrorPanel } from "@/components/ErrorPanel";
import { ALLEEN_BEHEERDER, foutVerval, GoedkeuringsPagina, HERSTELPUNT_ONTBREEKT } from "@/components/GoedkeuringsPagina";
import { eindTekst, UitvoeringsTijdlijn } from "@/components/UitvoeringsTijdlijn";
import { Button } from "@/components/ui/button";
import { filterActies } from "@/app/goedkeuringen/beleid/BeleidScreen";
import {
  diffRegels,
  doelNaam,
  naamKlopt,
  REDEN_ONTOONBAAR,
  statusView,
  vervallen,
  VOORSTEL_VERLOPEN,
  vasteFout,
  weigerReden,
  type ActieVerzoek,
  type BeleidsActie,
} from "@/lib/acties";
import { HubApiError } from "@/lib/api";
import type { Role } from "@/lib/types";

const proef = vi.hoisted(() => ({ rol: "admin" as string }));

vi.mock("@/lib/session", () => {
  const rank: Record<string, number> = { kind: 0, viewer: 1, operator: 2, admin: 3 };
  return {
    useRole: () => proef.rol,
    hasRole: (r: string | undefined, min: string) => r !== undefined && rank[r]! >= rank[min]!,
  };
});

const H = (c: string) => `sha256:${c.repeat(64)}`;

function verzoek(extra: Partial<ActieVerzoek> = {}): ActieVerzoek {
  return {
    request_id: "11111111-2222-3333-4444-555555555555",
    status: "wacht_op_goedkeuring",
    action_id: "app.uninstall",
    target: { app_id: "demo-app" },
    actor: { type: "user", id: "beheerder" },
    risk_class: "R2",
    risk_claim: null,
    risk_claim_genegeerd: false,
    rule_ids: ["ACT-APP-UNINSTALL"],
    goedkeuring_nodig: true,
    policy_hash: H("a"),
    uitvoerder: "executor",
    resource_etag: '"etag-1"',
    preview_hash: H("b"),
    preview: {
      omschrijving: "App verwijderen",
      requires_backup: false,
      huidig: { versie: "1.0" },
      wijziging: { soort: "verwijderen", app: "demo-app", alleen_containers: true, remove_ix_volumes: false, remove_images: false },
      dataretentie: "Datasets en data blijven staan.",
      terugdraaien: "Opnieuw installeren.",
    },
    blokkades: [],
    goedkeuring: null,
    resultaat: null,
    aangemaakt_op: new Date().toISOString(),
    bijgewerkt_op: new Date().toISOString(),
    geldig_tot: new Date(Date.now() + 600_000).toISOString(),
    gestart_op: null,
    uitgevoerd_op: null,
    ...extra,
  };
}

const gezien = (v: ActieVerzoek) => ({ preview_hash: v.preview_hash, resource_etag: v.resource_etag, policy_hash: v.policy_hash });
const pagina = (v: ActieVerzoek, verouderd = false) =>
  renderToStaticMarkup(<GoedkeuringsPagina v={v} gezien={gezien(v)} verouderd={verouderd} opnieuw={() => undefined} />);
const knop = (html: string, testId: string) => html.match(new RegExp(`<button[^>]*data-testid="${testId}"[^>]*>`))?.[0] ?? null;

beforeEach(() => {
  proef.rol = "admin";
});

describe("vaste fouttekst na een handeling (R-VEILIG-1, RV-8)", () => {
  it.each([
    [409, "uitvoering_geweigerd"],
    [501, "capability_unavailable"],
    [500, "iets_nieuws"],
  ])("HTTP %s %s: geen vrije executortekst en geen details-JSON in de HTML", (status, code) => {
    const e = new HubApiError(status, code, "VRIJE-EXECUTOR-MELDING-501", { executor: { code: "x_y", message: "VRIJE-EXECUTOR-MELDING" } }, "8db21b66-018b-4091-8c47-11fe08dc40d9");
    const html = renderToStaticMarkup(<ErrorPanel error={e} title="De handeling is niet gelukt" vast={vasteFout} />);
    expect(html).not.toContain("VRIJE-EXECUTOR");
    expect(html).not.toContain("Technische details");
    expect(html).not.toContain("x_y");
    if (code === "iets_nieuws") expect(html).not.toContain(code);
    else expect(html).toContain(code);
    expect(html).toContain("8db21b66-018b-4091-8c47-11fe08dc40d9");
    expect(html).toContain(vasteFout(e));
  });

  it("een onbekende code krijgt een vaste tekst, een bekende code haar eigen tekst", () => {
    expect(vasteFout(new HubApiError(409, "uitvoering_geweigerd", "x"))).toBe("De executor heeft de actie geweigerd; er is niets uitgevoerd.");
    expect(vasteFout(new HubApiError(500, "toString", "x"))).toBe(vasteFout(new HubApiError(500, "raar", "x")));
  });
});

describe("diff (C-20)", () => {
  it("toont van/naar als één gewijzigde regel en laat gelijke velden weg", () => {
    const { regels, onveilig } = diffRegels({ huidig: { app: "x" }, wijziging: { soort: "bijwerken", app: "x", van: "1.0", naar: "1.1" } });
    expect(onveilig).toBe(false);
    expect(regels).toEqual([{ soort: "gewijzigd", veld: "naar", was: "1.0", wordt: "1.1" }]);
  });

  it("toont een geheim alleen als ***", () => {
    const { regels } = diffRegels({ wijziging: { soort: "bijwerken", app: "demo", wachtwoord: "***" } });
    expect(regels).toContainEqual({ soort: "toegevoegd", veld: "wachtwoord", wordt: "*** (geheim, niet getoond)" });
  });

  // R-VEILIG-2 (RV-10): de echte uninstall-preview van de backend (preview.py _wijziging) is eenduidig verwijderen.
  const UNINSTALL = { soort: "verwijderen", app: "my-house", alleen_containers: true, remove_ix_volumes: false, remove_images: false };

  it("verwijderen: alleen 'Was → (verwijderd)', nooit toegevoegd, en zegt wat er met de appdata gebeurt", () => {
    const { regels, onveilig, gevolgen } = diffRegels({ huidig: {}, wijziging: UNINSTALL });
    expect(onveilig).toBe(false);
    expect(regels).toEqual([{ soort: "verwijderd", veld: "app", was: "my-house" }]);
    expect(gevolgen).toEqual([
      "Alleen de containers van de app worden verwijderd.",
      "App-data in ix-volumes blijft staan.",
      "Images blijven staan.",
    ]);
    expect(diffRegels({ wijziging: { ...UNINSTALL, remove_ix_volumes: true } }).gevolgen).toContain("App-data in ix-volumes wordt verwijderd.");
  });

  it.each([
    ["onbekend veld", { ...UNINSTALL, wachtwoord: "***" }],
    ["lot van de appdata ontbreekt", { soort: "verwijderen", app: "my-house", remove_images: false }],
    ["geen ja/nee", { ...UNINSTALL, remove_ix_volumes: "nee" }],
  ])("verwijderen blokkeert als het gevolg niet eenduidig is (%s)", (_n, wijziging) => {
    expect(diffRegels({ wijziging }).onveilig).toBe(true);
  });

  it.each([
    ["te lange tekst", { notes: "x".repeat(301) }],
    ["stuurteken", { notes: "a\u0007b" }],
    ["richtingteken", { notes: `a${String.fromCharCode(0x202e)}b` }],
    ["te diep", { a: { b: { c: { d: { e: { f: 1 } } } } } }],
  ])("blokkeert bij een onveilige regel (%s)", (_naam, wijziging) => {
    expect(diffRegels({ wijziging }).onveilig).toBe(true);
  });

  it("blokkeert zonder wijziging", () => {
    expect(diffRegels(null).onveilig).toBe(true);
  });
});

describe("vervallen en verlopen (EX19)", () => {
  it("een verlopen voorstel kan niet meer beslist worden", () => {
    const v = verzoek({ geldig_tot: new Date(Date.now() - 1000).toISOString() });
    expect(vervallen(v, gezien(v), new Date())).toBe(VOORSTEL_VERLOPEN);
    expect(vervallen(verzoek({ status: "verlopen" }), null, new Date())).toBe(VOORSTEL_VERLOPEN);
  });

  it("een gewijzigd doel na de preview laat de goedkeuring vervallen", () => {
    const v = verzoek();
    expect(vervallen({ ...v, resource_etag: '"etag-2"' }, gezien(v), new Date())).toBe(
      "Goedkeuring vervallen: het doel is gewijzigd na de preview. Vraag een nieuw voorstel aan.",
    );
  });

  it("neemt de vervalreden van de server over", () => {
    const v = verzoek({
      goedkeuring: {
        approval_id: "x", approved_by: "b", approved_at: null, expires_at: null, preview_hash: H("b"), resource_etag: "e", policy_hash: H("a"),
        risk_class: "R2", backup_checkpoint_id: null, gebruikt_op: null, vervallen_op: new Date().toISOString(), vervallen_reden: "gewijzigd:policy_hash,resource_etag",
      },
    });
    expect(vervallen(v, gezien(v), new Date())).toBe(
      "Goedkeuring vervallen: het risicobeleid en het doel zijn gewijzigd na de preview. Vraag een nieuw voorstel aan.",
    );
  });

  it("vertaalt een weigering van de server bij goedkeuren", () => {
    expect(foutVerval(new HubApiError(409, "preview_gewijzigd", "x", { gewijzigd: ["resource_etag"] }))).toMatch(/^Goedkeuring vervallen: het doel is gewijzigd/);
    expect(foutVerval(new HubApiError(409, "voorstel_verlopen", "x"))).toBe(VOORSTEL_VERLOPEN);
    expect(foutVerval(new HubApiError(500, "intern", "x"))).toBeNull();
  });
});

describe("R3: getypte naam", () => {
  it("klopt alleen bij exact dezelfde naam", () => {
    expect(naamKlopt("demo-app", "demo-app")).toBe(true);
    expect(naamKlopt("", "demo-app")).toBe(false);
    expect(naamKlopt(" demo-app", "demo-app")).toBe(false);
    expect(naamKlopt("Demo-app", "demo-app")).toBe(false);
    expect(naamKlopt("demo-app", null)).toBe(false);
  });

  it("haalt de naam alleen uit bekende doelvelden met vaste vorm", () => {
    expect(doelNaam({ app_id: "demo-app" })).toBe("demo-app");
    expect(doelNaam({ app_id: "<script>" })).toBeNull();
    expect(doelNaam({ vrij: "demo" })).toBeNull();
  });

  it("een uitgeschakelde knop doet echt niets (V-065)", () => {
    const klik = vi.fn();
    let voorkomen = false;
    const el = Button({ uit: true, onClick: klik, children: "Verwijderen definitief" }) as { props: { onClick: (e: unknown) => void; "aria-disabled"?: boolean } };
    el.props.onClick({ preventDefault: () => (voorkomen = true) });
    expect(klik).not.toHaveBeenCalled();
    expect(voorkomen).toBe(true);
    expect(el.props["aria-disabled"]).toBe(true);
  });

  it("toont bij R3 eerst de controlestap met de knop naar de bevestiging", () => {
    const html = pagina(verzoek({ risk_class: "R3" }));
    expect(html).toContain("Goedkeuren · stap 1 van 2");
    expect(knop(html, "r3-volgende")).not.toContain('aria-disabled="true"');
    expect(knop(html, "goedkeuren")).toBeNull();
  });
});

describe("rechten komen van de server (O-06)", () => {
  it.each(["viewer", "operator"] as Role[])("een %s ziet geen beslisknoppen maar de rolmelding", (rol) => {
    proef.rol = rol;
    const html = pagina(verzoek());
    expect(html).toContain(ALLEEN_BEHEERDER);
    expect(knop(html, "goedkeuren")).toBeNull();
    expect(knop(html, "weigeren-openen")).toBeNull();
  });

  it("een beheerder kan een vrij voorstel goedkeuren", () => {
    const html = pagina(verzoek());
    expect(knop(html, "goedkeuren")).not.toContain('aria-disabled="true"');
    expect(html.indexOf("Annuleren")).toBeLessThan(html.indexOf('data-testid="goedkeuren"'));
  });

  it.each([
    ["verlopen", verzoek({ geldig_tot: new Date(Date.now() - 1000).toISOString() }), false, VOORSTEL_VERLOPEN],
    ["verlopen volgens de server", verzoek({ status: "verlopen" }), false, VOORSTEL_VERLOPEN],
    ["blokkade", verzoek({ blokkades: [{ id: "GATE", code: "gate_dicht", reden: "De back-upgate is niet groen." }] }), false, "Geblokkeerd: De back-upgate is niet groen."],
    ["back-up zonder herstelpunt", verzoek({ preview: { ...verzoek().preview, requires_backup: true } }), false, HERSTELPUNT_ONTBREEKT],
    ["verouderd", verzoek(), true, "Verouderde gegevens"],
  ])("schakelt goedkeuren uit met een zichtbare reden: %s", (_n, v, oud, tekst) => {
    const html = pagina(v, oud);
    const k = knop(html, "goedkeuren")!;
    expect(k).toContain('aria-disabled="true"');
    expect(k).toMatch(/aria-describedby="[^"]+"/);
    expect(html).toContain(tekst);
  });

  it("een kijker ziet bij een goedgekeurd verzoek geen uitvoerknop", () => {
    proef.rol = "viewer";
    const html = pagina(verzoek({ status: "goedgekeurd" }));
    expect(knop(html, "uitvoeren")).toBeNull();
  });

  it("een operator mag een goedgekeurde R1-herstart uitvoeren na bevestiging", () => {
    proef.rol = "operator";
    const v = verzoek({ action_id: "app.restart", risk_class: "R1", goedkeuring_nodig: true,
      preview: { requires_backup: false, wijziging: { soort: "restart", app: "demo-app", verwacht: { staat: "RUNNING" } } } });
    expect(knop(pagina(v), "uitvoeren")).toBeNull();
    const html = pagina({ ...v, status: "goedgekeurd" });
    expect(knop(html, "uitvoeren")).not.toContain('aria-disabled="true"');
  });

  it.each(["sso.oidc.hub.register", "sso.sessions.revoke"])("toont %s als uitgesteld tot versie 2", action_id => {
    proef.rol = "admin";
    const v = verzoek({ action_id });
    expect(pagina(v)).toContain("uitgesteld tot versie 2");
    expect(knop(pagina(v), "goedkeuren")).toContain('aria-disabled="true"');
    expect(knop(pagina({ ...v, status: "goedgekeurd" }), "uitvoeren")).toContain('aria-disabled="true"');
  });

  it.each(["viewer", "operator", "admin"])("bestaand R1-kloonvoorstel toont de uitvoerknop alleen aan een beheerder (%s)", (rol) => {
    proef.rol = rol;
    const v = verzoek({ action_id: "zfs.snapshot.clone_to_sandbox", status: "klaar", risk_class: "R1", goedkeuring_nodig: false,
      preview: { omschrijving: "Zandbakkloon", requires_backup: false,
        wijziging: { soort: "snapshot_klonen", snapshot: "proef/app@voorbeeld", naar: "proef/asm-sandbox/voorbeeld" } } });
    const uitvoer = knop(pagina(v), "uitvoeren");
    if (rol === "admin") {
      expect(uitvoer).not.toBeNull();
      expect(uitvoer).not.toContain('aria-disabled="true"');
    } else {
      expect(uitvoer).toBeNull();
    }
  });
});

describe("weigeringsreden (R-ONTWERP-1)", () => {
  it("toont alleen een vaste reden", () => {
    expect(weigerReden({ code: "afgewezen", message: "Het risico is te groot." })).toBe("Afgewezen — Het risico is te groot.");
  });

  it.each(["<img src=x onerror=alert(1)>", "Bel 06-12345678 en zet token=abc", "Het risico is te groot. ", ""])("verbergt een afwijkende reden: %j", (m) => {
    expect(weigerReden({ code: "afgewezen", message: m })).toBe(REDEN_ONTOONBAAR);
    const html = pagina(verzoek({ status: "afgewezen", resultaat: { code: "afgewezen", message: m, door: "beheerder" } }));
    expect(html).toContain(REDEN_ONTOONBAAR);
    if (m.trim()) expect(html).not.toContain(m.trim().slice(0, 12));
  });
});

describe("uitvoering (C-23)", () => {
  it("een onbekende uitkomst of een onbekende status is nooit een succes", () => {
    const html = renderToStaticMarkup(<UitvoeringsTijdlijn v={verzoek({ status: "onbekend", gestart_op: new Date().toISOString() })} />);
    expect(html).toContain("Uitkomst onbekend");
    expect(html).not.toContain("Uitgevoerd en gecontroleerd");
    expect(statusView("iets_nieuws")).toEqual({ tone: "unknown", label: "Onbekende status" });
    expect(eindTekst("bezig")).toBe("Uitvoering bezig");
  });

  it("toont voor/na-hash en duur alleen bij teruggelezen succes", () => {
    const start = new Date(Date.now() - 65_000).toISOString();
    const html = renderToStaticMarkup(
      <UitvoeringsTijdlijn v={verzoek({ status: "uitgevoerd", gestart_op: start, uitgevoerd_op: new Date().toISOString(), resultaat: { before_hash: H("c"), after_hash: H("d"), message: "vrije tekst van de executor" } })} />,
    );
    expect(html).toContain("Uitgevoerd en gecontroleerd");
    expect(html).toContain("voor sha256:cccc…cccc");
    expect(html).not.toContain("vrije tekst van de executor");
  });

  it("verouderd houdt het woord ‘Laatst bekend’", () => {
    const html = renderToStaticMarkup(<UitvoeringsTijdlijn v={verzoek({ status: "bezig", gestart_op: new Date().toISOString() })} verouderd />);
    expect(html).toContain("Laatst bekend: Uitvoering bezig");
  });
});

describe("risicobadge en beleid (S-066)", () => {
  it("heeft altijd het vaste woord bij de klasse", () => {
    expect(renderToStaticMarkup(<RisicoBadge klasse="R3" />)).toContain("Destructief — extra bevestiging");
    expect(renderToStaticMarkup(<RisicoBadge klasse="R9" />)).toContain("Risico onbekend");
  });

  it("zoekt in actie en omschrijving", () => {
    const a = (action_id: string, omschrijving: string) => ({ action_id, omschrijving }) as BeleidsActie;
    const lijst = [a("app.stop", "App stoppen"), a("zfs.snapshot.create", "Snapshot maken")];
    expect(filterActies(lijst, "SNAP").map((x) => x.action_id)).toEqual(["zfs.snapshot.create"]);
    expect(filterActies(lijst, "  ")).toHaveLength(2);
    expect(filterActies(lijst, "bestaat niet")).toEqual([]);
  });
});
