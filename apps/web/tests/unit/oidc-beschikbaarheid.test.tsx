import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { Login } from "@/app/inloggen/Login";
import { ToegangScreen } from "@/app/instellingen/toegang/ToegangScreen";

const reden = "oidc_clientgeheim_ontbreekt";
const scenario = vi.hoisted(() => ({ herstelroute: true }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("@/lib/session", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/session")>()),
  useRole: () => "admin",
  useSession: () => ({ state: { status: "anon" } }),
}));
vi.mock("@/lib/use-api", () => ({
  useApi: (pad: string) => ({
    data: pad === "/api/v1/auth/oidc/beschikbaar"
      ? { ingeschakeld: false, login_url: null, reden }
      : pad === "/api/v1/auth/oidc"
        ? {
          ingeschakeld: true, reden, lokale_herstelroute: scenario.herstelroute,
          client_secret: { ingesteld: false, laatste4: null },
          gate_authentik: { status: "toegestaan", redenen: [] },
          issuer: "https://issuer.example", rolkoppelingen: [],
          discovery: { status: "onbekend" }, jwks: { sleutels: [] },
        }
        : null,
  }),
}));

describe("SSO-beschikbaarheid", () => {
  it("toont de Nederlandse reden op Inloggen zonder SSO-knop", () => {
    const html = renderToStaticMarkup(<Login />);
    expect(html).toContain("Het clientgeheim voor SSO ontbreekt");
    expect(html).not.toContain('data-testid="sso-inloggen"');
    expect(html).toContain('name="username"');
  });

  it("toont de oorzaak en de herstelactie bij SSO-instellingen", () => {
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("SSO staat aan maar werkt niet: het clientgeheim ontbreekt");
    expect(html).toContain("Stel het clientgeheim in via HTTPS of zet SSO uit.");
  });

  it("waarschuwt vooraf voor ontbreken van herstelroute en afmelding", () => {
    scenario.herstelroute = false;
    const html = renderToStaticMarkup(<ToegangScreen />);
    expect(html).toContain("Maak een lokale beheerder of een noodaccount aan");
    expect(html).toContain("Ook je eigen SSO-sessie eindigt.");
  });

});
