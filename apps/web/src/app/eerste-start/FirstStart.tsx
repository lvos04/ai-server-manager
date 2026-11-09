"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { apiRequest, HubApiError } from "@/lib/api";
import { useSession } from "@/lib/session";
import { uuidv4 } from "@/lib/uuid";
import type { LoginResult } from "@/lib/types";

const USERNAME_RE = /^[a-z0-9][a-z0-9._-]{2,63}$/;
const MIN_PASSWORD = 12;

export function FirstStart() {
  const router = useRouter();
  const { state, refresh } = useSession();
  const [code, setCode] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const attempt = useRef(uuidv4());

  useEffect(() => {
    if (state.status === "auth") router.replace("/onboarding");
  }, [state.status, router]);

  if (state.status === "loading") return <Loading text="Status van de Hub controleren…" />;
  if (state.status === "error") return <ErrorPanel error={state.error} onRetry={() => void refresh()} />;
  if (state.status === "anon") {
    return (
      <div className="center-screen">
        <section className="card auth-card stack" aria-labelledby="klaar">
          <h1 id="klaar">Eerste start is al afgerond</h1>
          <p>Er is al een beheerder. Log in met je account.</p>
          <p>
            <Link className="btn btn-primary" href="/inloggen">
              Naar inloggen
            </Link>
          </p>
        </section>
      </div>
    );
  }

  const validate = (): Record<string, string> => {
    const e: Record<string, string> = {};
    if (!code.trim()) e.code = "Vul de setupcode uit de app-log in.";
    if (!USERNAME_RE.test(username)) e.username = "3–64 tekens: kleine letters, cijfers, punt, streepje of liggend streepje; begin met een letter of cijfer.";
    if (password.length < MIN_PASSWORD) e.password = `Minstens ${MIN_PASSWORD} tekens.`;
    else if (password.toLowerCase() === username.toLowerCase()) e.password = "Mag niet gelijk zijn aan de gebruikersnaam.";
    if (password2 !== password) e.password2 = "De wachtwoorden zijn niet gelijk.";
    return e;
  };

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setApiError(null);
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      await apiRequest<LoginResult>("/api/v1/setup/admin", {
        method: "POST",
        idempotencyKey: attempt.current,
        body: { setup_code: code.trim().toUpperCase(), username, password, display_name: displayName.trim() },
      });
      await refresh();
    } catch (err) {
      attempt.current = uuidv4();
      setApiError(err instanceof HubApiError ? err : new HubApiError(0, "onbekend", String(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <section className="card auth-card stack" aria-labelledby="titel">
        <div>
          <h1 id="titel">Eerste start</h1>
          <p>Welkom. Maak het eerste beheerdersaccount aan met de eenmalige setupcode.</p>
        </div>
        <div className="notice tone-info" data-testid="setupcode-uitleg">
          <p>
            <strong>Waar vind ik de setupcode?</strong>
          </p>
          <ol className="howto">
            <li>Open de TrueNAS-web-UI.</li>
            <li>
              Ga naar <strong>Apps</strong> en kies <strong>ai-server-manager</strong>.
            </li>
            <li>
              Open de <strong>Logs</strong> van de app.
            </li>
            <li>
              Zoek de regel <code>SETUPCODE (eenmalig, voor het eerste beheerdersaccount)</code>. Staat hij er meer dan
              eens, dan geldt de onderste.
            </li>
          </ol>
          <p className="meta">
            Code kwijt of verlopen (na 24 uur)? Herstart de app in TrueNAS: er verschijnt een nieuwe code en de oude
            vervalt. De code staat nergens anders dan in die log.
          </p>
        </div>
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate aria-describedby={apiError ? "setup-fout" : undefined}>
          <Field id="setupcode" label="Setupcode" error={errors.code}>
            {(a) => (
              <input
                {...a}
                type="text"
                name="setupcode"
                autoComplete="one-time-code"
                autoCapitalize="characters"
                spellCheck={false}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
            )}
          </Field>
          <Field id="gebruikersnaam" label="Gebruikersnaam" help="Kleine letters, cijfers, punt of streepje (3–64 tekens)." error={errors.username}>
            {(a) => (
              <input
                {...a}
                type="text"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                value={username}
                onChange={(e) => setUsername(e.target.value.toLowerCase())}
                required
              />
            )}
          </Field>
          <Field id="weergavenaam" label="Weergavenaam (optioneel)">
            {(a) => (
              <input {...a} type="text" name="display_name" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            )}
          </Field>
          <Field id="wachtwoord" label="Wachtwoord" help={`Minstens ${MIN_PASSWORD} tekens. Wordt alleen als argon2id-hash bewaard.`} error={errors.password}>
            {(a) => (
              <input {...a} type="password" name="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            )}
          </Field>
          <Field id="wachtwoord2" label="Wachtwoord herhalen" error={errors.password2}>
            {(a) => (
              <input {...a} type="password" name="password2" autoComplete="new-password" value={password2} onChange={(e) => setPassword2(e.target.value)} required />
            )}
          </Field>
          {apiError ? (
            <div id="setup-fout">
              <ErrorPanel error={apiError} title="Beheerder aanmaken mislukt" />
            </div>
          ) : null}
          <div className="row">
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Bezig…" : "Beheerder aanmaken"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
