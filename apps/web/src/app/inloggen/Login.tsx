"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { apiRequest, HubApiError } from "@/lib/api";
import { safeReturnPath } from "@/lib/nav";
import { useSession } from "@/lib/session";
import type { LoginResult } from "@/lib/types";

export function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const { state, refresh } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const back = safeReturnPath(params.get("terug"));

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
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Bezig…" : "Inloggen"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
