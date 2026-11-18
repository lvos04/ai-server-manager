import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OidcSecretField, takeOidcSecret, watchOidcSecret } from "@/components/OidcSecretField";

describe("OIDC-clientgeheim", () => {
  it("wist bij verlaten, paginaherstel en ontkoppelen van het veld", () => {
    const input = { value: "testinvoer" } as HTMLInputElement;
    const page = new EventTarget();
    const cleanup = watchOidcSecret(input, page);
    page.dispatchEvent(new Event("pagehide"));
    expect(input.value).toBe("");
    input.value = "testinvoer";
    page.dispatchEvent(new Event("pageshow"));
    expect(input.value).toBe("");
    input.value = "testinvoer";
    cleanup();
    expect(input.value).toBe("");
    input.value = "losgekoppeld";
    page.dispatchEvent(new Event("pagehide"));
    page.dispatchEvent(new Event("pageshow"));
    expect(input.value).toBe("losgekoppeld");
  });
  it("verwijdert de invoer meteen vóór de aanvraag en bewaart geen formulierwaarde", () => {
    const input = { value: "tijdelijke-testinvoer" } as HTMLInputElement;
    expect(takeOidcSecret(input)).toBe("tijdelijke-testinvoer");
    expect(input.value).toBe("");
    expect(takeOidcSecret(input)).toBe("");
    expect(takeOidcSecret(null)).toBe("");
  });
  it("biedt het veld alleen over HTTPS aan en verklaart de HTTP-grens", () => {
    const http = renderToStaticMarkup(<OidcSecretField https={false} lokaalBeheer ingesteld={false} laatste4={null} />);
    expect(http).not.toContain("<input");
    expect(http).toContain("HTTPS");
    const https = renderToStaticMarkup(<OidcSecretField https lokaalBeheer ingesteld={false} laatste4={null} />);
    expect(https).toContain('type="password"');
  });

  it("toont een SSO-beheerder uitleg in plaats van invoer", () => {
    const html = renderToStaticMarkup(<OidcSecretField https lokaalBeheer={false} ingesteld laatste4={null} />);
    expect(html).not.toContain("<input");
    expect(html).toContain("Meld je aan als lokale beheerder of via de noodlogin");
  });

  it("ontmoedigt aanvullen en opslaan bij browser en wachtwoordmanagers", () => {
    const html = renderToStaticMarkup(<OidcSecretField https lokaalBeheer ingesteld={false} laatste4={null} />);
    expect(html).toContain('autoComplete="off"');
    expect(html).toContain('data-lpignore="true"');
    expect(html).toContain('data-1p-ignore="true"');
    expect(html).toContain('data-bwignore="true"');
    expect(html).not.toContain("new-password");
    expect(html).not.toContain('name=');
  });
});
