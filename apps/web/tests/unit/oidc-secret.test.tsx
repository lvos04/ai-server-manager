import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { OidcSecretField } from "@/components/OidcSecretField";

describe("OIDC-clientgeheim", () => {
  it("biedt het veld alleen over HTTPS aan en verklaart de HTTP-grens", () => {
    const http = renderToStaticMarkup(<OidcSecretField https={false} ingesteld={false} laatste4={null} />);
    expect(http).not.toContain("<input");
    expect(http).toContain("HTTPS");
    const https = renderToStaticMarkup(<OidcSecretField https ingesteld={false} laatste4={null} />);
    expect(https).toContain('type="password"');
  });
});
