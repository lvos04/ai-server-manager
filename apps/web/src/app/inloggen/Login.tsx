"use client";

import { LifeBuoy, LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { apiRequest, HubApiError } from "@/lib/api";
import { safeReturnPath } from "@/lib/nav";
import { useSession } from "@/lib/session";
import type { LoginResult } from "@/lib/types";
import { Melding } from "@/components/Melding";
import { Button, buttonVariants } from "@/components/ui/button";
import { useApi } from "@/lib/use-api";

/** Meldingen bij `/inloggen?sso_fout=…` (HUB_PEIL_ONTWERP §4.8.6). */
export const SSO_FOUT: Record<string, string> = {
  sso_uit: "Inloggen via SSO staat uit. Log in met je eigen account.",
  sso_gewijzigd: "De SSO-instellingen zijn net gewijzigd. Probeer opnieuw.",
  geen_rol: "Je account hoort bij geen enkele groep die toegang heeft. Vraag een beheerder om je groep te koppelen.",
  account_uitgeschakeld: "Dit account is uitgeschakeld. Vraag een beheerder.",
  issuer_onbereikbaar: "Authentik is niet bereikbaar. Gebruik je eigen account of de noodlogin.",
  netwerk: "Authentik is niet bereikbaar. Gebruik je eigen account of de noodlogin.",
};

export function ssoFoutTekst(code: string): string {
  return SSO_FOUT[code] ?? "Inloggen via SSO is mislukt.";
}

export function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const { state, refresh } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const back = safeReturnPath(params.get("terug"));
  const ssoFout = params.get("sso_fout");
  const sso = useApi<{ ingeschakeld: boolean; login_url: string | null }>("/api/v1/auth/oidc/beschikbaar");

  useEffect(() => {
    if (state.status === "auth") router.replace(back);
    if (state.status === "setup") router.replace("/eerste-start");
  }, [state.status, router, back]);

  if (state.status === "loading") return <Loading text="Aanmelding controleren…" />;

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError(new HubApiError(0, "invoer_ontbreekt", "Vul je gebruikersnaam en wachtwoord in."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest<LoginResult>("/api/v1/auth/login", { method: "POST", body: { username: username.trim(), password } });
      setPassword("");
      await refresh();
    } catch (err) {
      setError(err instanceof HubApiError ? err : new HubApiError(0, "onbekend", String(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <section className="card auth-card stack" aria-labelledby="titel">
        <div>
          <h1 id="titel">Inloggen</h1>
          <p>Log in op de Hub van je TrueNAS Home Platform.</p>
        </div>
        {state.status === "error" ? <ErrorPanel error={state.error} onRetry={() => void refresh()} /> : null}
        {ssoFout ? (
          <Melding soort="fout" titel="Inloggen via SSO is niet gelukt" role="alert" data-testid="sso-fout" data-code={ssoFout}>
            <p>{ssoFoutTekst(ssoFout)}</p>
            <p className="text-sm">
              Code <code>{ssoFout}</code>
            </p>
          </Melding>
        ) : null}
        {sso.data?.ingeschakeld && sso.data.login_url ? (
          <a href={`${sso.data.login_url}${sso.data.login_url.includes("?") ? "&" : "?"}terug=${encodeURIComponent(back)}`} className={buttonVariants({ variant: "secundair", blok: true })} data-testid="sso-inloggen">
            Inloggen met SSO
            <LogIn aria-hidden="true" />
          </a>
        ) : null}
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
          <Field id="gebruikersnaam" label="Gebruikersnaam">
            {(a) => (
              <input {...a} type="text" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={(e) => setUsername(e.target.value)} required />
            )}
          </Field>
          <Field id="wachtwoord" label="Wachtwoord">
            {(a) => (
              <input {...a} type="password" name="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            )}
          </Field>
          {error ? <ErrorPanel error={error} title="Inloggen mislukt" /> : null}
          <div className="row">
            <Button type="submit" variant="primair" bezig={busy}>
              {busy ? "Bezig…" : "Inloggen"}
            </Button>
          </div>
        </form>
        <p className="flex items-center gap-2 text-sm">
          <LifeBuoy aria-hidden="true" className="size-4" />
          <Link href="/inloggen/nood" className="inline-flex min-h-touch items-center">
            Noodlogin (alleen vanaf je eigen netwerk)
          </Link>
        </p>
      </section>
    </div>
  );
}
