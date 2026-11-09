"use client";

import { LifeBuoy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Melding } from "@/components/Melding";
import { Button } from "@/components/ui/button";
import { apiRequest, HubApiError } from "@/lib/api";
import { useSession } from "@/lib/session";

/** Noodlogin (S-003, contract 1.2 §4.1): publieke pagina, wachtwoord + TOTP, alleen vanaf privé-adressen. */
export function Noodlogin() {
  const router = useRouter();
  const { state, refresh } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (state.status === "auth") router.replace("/");
  }, [state.status, router]);

  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiRequest("/api/v1/auth/break-glass/login", { method: "POST", body: { username: username.trim(), password, totp: totp.replace(/\s/g, "") } });
      setPassword("");
      setTotp("");
      await refresh();
    } catch (e) {
      setError(e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e)));
    } finally {
      setBusy(false);
    }
  };

  let melding: string | null = null;
  if (error?.code === "source_not_private") melding = "Noodlogin kan alleen vanaf je eigen netwerk. Dit apparaat komt binnen via een adres buiten het netwerk.";
  else if (error?.status === 401) melding = "Gebruikersnaam, wachtwoord of code klopt niet.";
  else if (error?.status === 429) melding = "Te veel pogingen vanaf dit apparaat. Probeer het over een paar minuten opnieuw.";

  return (
    <div className="center-screen">
      <section className="card auth-card stack" aria-labelledby="titel">
        <h1 id="titel" className="flex items-center gap-2">
          <LifeBuoy aria-hidden="true" className="size-6" />
          Noodlogin
        </h1>
        <Melding soort="info">
          <p>
            Alleen voor als inloggen via SSO niet werkt. Werkt alleen vanaf je eigen netwerk (LAN of VPN). Elke noodlogin wordt vastgelegd en
            gemeld; daarna moet je wachtwoord en TOTP vernieuwen.
          </p>
        </Melding>
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
          <Field id="nood-gebruikersnaam" label="Gebruikersnaam">
            {(a) => <input {...a} autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={(e) => setUsername(e.target.value)} required />}
          </Field>
          <Field id="nood-wachtwoord" label="Wachtwoord">
            {(a) => <input {...a} type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />}
          </Field>
          <Field id="nood-totp" label="Code uit de authenticator-app" help="6 cijfers.">
            {(a) => <input {...a} inputMode="numeric" autoComplete="one-time-code" value={totp} onChange={(e) => setTotp(e.target.value)} required />}
          </Field>
          {error ? (
            melding ? (
              <div className="flex flex-col gap-2 rounded-lg border-2 border-down bg-down-bg p-4 text-down-ink" role="alert" data-testid="error-panel" data-code={error.code}>
                <p className="font-bold">Noodlogin mislukt</p>
                <p>{melding}</p>
                <p className="text-sm">
                  Code <code>{error.code}</code>
                  {error.traceId ? (
                    <>
                      {" "}
                      · Trace-ID <code>{error.traceId}</code>
                    </>
                  ) : null}
                </p>
              </div>
            ) : (
              <ErrorPanel error={error} title="Noodlogin mislukt" />
            )
          ) : null}
          <div>
            <Button type="submit" variant="primair" bezig={busy}>
              Noodlogin
            </Button>
          </div>
        </form>
        <p>
          <Link href="/inloggen" className="inline-flex min-h-touch items-center">
            Terug naar gewoon inloggen
          </Link>
        </p>
      </section>
    </div>
  );
}
