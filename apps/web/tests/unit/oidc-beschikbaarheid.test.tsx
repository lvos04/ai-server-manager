import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Login } from "@/app/inloggen/Login";
import { NoodaccountScreen } from "@/app/instellingen/noodaccount/NoodaccountScreen";
import { ToegangScreen } from "@/app/instellingen/toegang/ToegangScreen";

const reden = "oidc_clientgeheim_ontbreekt";
const noodTotpReden = "nood_totp_kluisrij_ontbreekt";
const scenario = vi.hoisted(() => ({ herstelroute: true, authBron: "lokaal", noodlogin: false, noodTotpOntbreekt: false }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/session", async (importOriginal) => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useRole: () => "admin",
  useSession: () => ({
    state: { status: "auth", me: { user: { role: "admin", auth_bron: scenario.authBron, break_glass: scenario.noodlogin } } },
  }),
}));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string) => ({
    data: pad === "/api/v1/auth/oidc/beschikbaar"
      ? scenario.noodTotpOntbreekt
        ? {
          ingeschakeld: true, login_url: "/api/v1/auth/oidc/login", reden: noodTotpReden,
          noodlogin: scenario.herstelroute
            ? "De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar. Je kunt lokaal inloggen met een bestaand beheerdersaccount. Vernieuw het wachtwoord en de TOTP via Instellingen → Noodaccount."
            : "De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar. Laat een beheerder met toegang tot de Hub-console python -m hub herstel-lokale-beheerder <nieuwe-gebruikersnaam> uitvoeren.",
        }
        : { ingeschakeld: false, login_url: null, reden }
      : pad === "/api/v1/auth/oidc"
        ? {
          ingeschakeld: true, reden: scenario.noodTotpOntbreekt ? noodTotpReden : reden,
          verplicht: scenario.noodTotpOntbreekt, noodaccount_werkend: false,
          lokale_herstelroute: scenario.herstelroute, lokale_beheerder_aanwezig: scenario.herstelroute,
          client_secret: { ingesteld: scenario.noodTotpOntbreekt, laatste4: null },
          gate_authentik: { status: "toegestaan", redenen: [] },
          issuer: "https://issuer.example", rolkoppelingen: [],
          discovery: { status: "onbekend" }, jwks: { sleutels: [] },
        }
        : pad === "/api/v1/auth/break-glass"
          ? {
            noodaccount: { username: "nood", sessieduur_minuten: 60 }, werkend: false, reden: noodTotpReden,
            uitleg: "De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar. Vernieuw het wachtwoord en de TOTP via Instellingen → Noodaccount.",
          }
          : null,
  }),
}));

describe("SSO-beschikbaarheid", () => {
  afterEach(() => {
    Object.assign(scenario, { herstelroute: true, authBron: "lokaal", noodlogin: false, noodTotpOntbreekt: false });
    vi.unstubAllGlobals();
  });

  it("toont de Nederlandse reden op Inloggen zonder SSO-knop", () => {
    const html = renderToStaticMarkup(<Login />);
    expect(html).toContain("Het clientgeheim voor SSO ontbreekt");
    expect(html).not.toContain('data-testid="sso-inloggen"');
    expect(html).toContain('name="username"');
    expect(html).toContain('href="/inloggen/nood"');
  });

  it("toont de oorzaak en de herstelactie bij SSO-instellingen", () => {
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("SSO staat aan maar werkt niet: het clientgeheim ontbreekt");
    expect(html).toContain("Stel het clientgeheim in via HTTPS of zet SSO uit.");
  });

  it("legt lokale aanmelding uit bij ontbrekende nood-TOTP en behoudt de SSO-knop", () => {
    scenario.noodTotpOntbreekt = true;
    const html = renderToStaticMarkup(<Login />);
    expect(html).toContain("De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar");
    expect(html).toContain("Je kunt lokaal inloggen met een bestaand beheerdersaccount.");
    expect(html).toContain('data-testid="sso-inloggen"');
    expect(html).not.toContain('data-testid="sso-fout"');
    expect(html).toContain("Instellingen → Noodaccount");
    expect(html).not.toContain('href="/inloggen/nood"');
  });

  it("verwijst bij SSO-instellingen naar het vernieuwen van het noodaccount", () => {
    scenario.noodTotpOntbreekt = true;
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar");
    expect(html).toContain('href="/instellingen/noodaccount#nood-instellen-titel"');
  });

  it("verwijst bij ontbrekende nood-TOTP en geen lokale beheerder naar de Hub-console", () => {
    scenario.noodTotpOntbreekt = true;
    scenario.herstelroute = false;
    scenario.authBron = "oidc";
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("herstel-lokale-beheerder");
    expect(html).not.toContain("Vraag een lokale beheerder");
    expect(html).not.toContain("Meld je aan als lokale beheerder of via de noodlogin");
    expect(html).not.toContain('href="/instellingen/noodaccount#nood-instellen-titel"');
    const inloggen = renderToStaticMarkup(<Login />);
    expect(inloggen).toContain("herstel-lokale-beheerder");
    expect(inloggen).not.toContain("bestaand beheerdersaccount");
    expect(inloggen).not.toContain('href="/inloggen/nood"');
  });

  it("toont op Noodaccount waarom noodlogin faalt en waar je die herstelt", () => {
    const html = renderToStaticMarkup(<NoodaccountScreen />);
    expect(html).toContain("De kluisrij voor de nood-TOTP ontbreekt of is onleesbaar");
    expect(html).toContain('href="#nood-instellen-titel"');
    expect(html).toContain('data-testid="nood-werkt-niet"');
  });

  it("waarschuwt vooraf voor ontbreken van herstelroute en afmelding", () => {
    scenario.herstelroute = false;
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("Maak een lokale beheerder of een noodaccount aan");
    expect(html).toContain("Ook je eigen SSO-sessie eindigt.");
  });

  it("verwijst een SSO-beheerder zonder herstelroute naar de noodlogin of een lokale beheerder", () => {
    scenario.herstelroute = false;
    scenario.authBron = "oidc";
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("Gebruik de noodlogin of vraag een lokale beheerder om hulp");
    expect(html).not.toContain("Maak een lokale beheerder of een noodaccount aan");
  });

  it.each([
    { naam: "SSO-beheerder", bron: "oidc", noodlogin: false, toegang: false },
    { naam: "lokale beheerder", bron: "lokaal", noodlogin: false, toegang: true },
    { naam: "noodsessie", bron: "lokaal", noodlogin: true, toegang: true },
  ])("toetst het clientgeheimveld via HTTPS voor een $naam", ({ bron, noodlogin, toegang }) => {
    scenario.authBron = bron;
    scenario.noodlogin = noodlogin;
    vi.stubGlobal("window", { location: { origin: "https://hub.example", protocol: "https:" } });
    const html = renderToStaticMarkup(<ToegangScreen />);
    if (toegang) {
      expect(html).toContain('id="sso-geheim"');
    } else {
      expect(html).not.toContain('id="sso-geheim"');
      expect(html).toContain("Meld je aan als lokale beheerder of via de noodlogin");
    }
  });
});
