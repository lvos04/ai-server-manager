import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OidcSecretField, takeOidcSecret } from "@/components/OidcSecretField";

describe("OIDC-clientgeheim", () => {
  it("verwijdert de invoer meteen vóór de aanvraag en bewaart geen formulierwaarde", () => {
    const input = { value: "tijdelijke-testinvoer" } as HTMLInputElement;
    expect(takeOidcSecret(input)).toBe("tijdelijke-testinvoer");
    expect(input.value).toBe("");
    expect(takeOidcSecret(input)).toBe("");
    expect(takeOidcSecret(null)).toBe("");
  });
  it("biedt het veld alleen over HTTPS aan en verklaart de HTTP-grens", () => {
    const http = renderToStaticMarkup(<OidcSecretField https={false} ingesteld={false} laatste4={null} />);
    expect(http).not.toContain("<input");
    expect(http).toContain("HTTPS");
    const https = renderToStaticMarkup(<OidcSecretField https ingesteld={false} laatste4={null} />);
    expect(https).toContain('type="password"');
  });

  it("ontmoedigt aanvullen en opslaan bij browser en wachtwoordmanagers", () => {
    const html = renderToStaticMarkup(<OidcSecretField https ingesteld={false} laatste4={null} />);
    expect(html).toContain('autoComplete="off"');
    expect(html).toContain('data-lpignore="true"');
    expect(html).toContain('data-1p-ignore="true"');
    expect(html).toContain('data-bwignore="true"');
    expect(html).not.toContain("new-password");
    expect(html).not.toContain('name=');
  });
});
