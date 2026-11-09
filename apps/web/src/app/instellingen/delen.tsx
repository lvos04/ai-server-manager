"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { apiRequest, HubApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useSession } from "@/lib/session";
import { applyTheme, readTheme, subscribeTheme, type ThemeChoice } from "@/lib/theme";
import type { Session } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import type { ReactNode } from "react";

export function asError(e: unknown): HubApiError {
  return e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e));
}

/** Kop van een instellingen-subpagina met kruimelpad Instellingen › <titel>. */
export function InstellingenKop({ titel, intro, actions }: { titel: string; intro?: ReactNode; actions?: ReactNode }) {
  return <PageHeader title={titel} intro={intro} actions={actions} kruimel={[{ label: "Instellingen", href: "/instellingen" }, { label: titel }]} />;
}

const THEMES: { value: ThemeChoice; label: string }[] = [
  { value: "systeem", label: "Systeem" },
  { value: "licht", label: "Licht" },
  { value: "donker", label: "Donker" },
];

/** ThemaKeuze (C-50): Systeem / Licht / Donker als knoppengroep; alleen op dit apparaat. */
export function ThemeSection() {
  const theme = useSyncExternalStore<ThemeChoice>(subscribeTheme, readTheme, () => "systeem");
  return (
    <section className="card" id="weergave" aria-labelledby="weergave-titel">
      <h2 id="weergave-titel">Thema</h2>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Thema">
        {THEMES.map((t) => (
          <Button key={t.value} variant={theme === t.value ? "primair" : "secundair"} aria-pressed={theme === t.value} onClick={() => applyTheme(t.value)} data-testid={`thema-${t.value}`}>
            {t.label}
          </Button>
        ))}
      </div>
      <p className="meta">Systeem volgt het apparaat (licht of donker). Wordt alleen op dit apparaat onthouden.</p>
    </section>
  );
}

export function PasswordForm() {
  const [cur, setCur] = useState("");
  const [nw, setNw] = useState("");
  const [nw2, setNw2] = useState("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setOk(null);
    if (nw !== nw2) {
      setError(new HubApiError(422, "invoer_onvolledig", "De nieuwe wachtwoorden zijn niet gelijk."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest("/api/v1/auth/password", { method: "POST", body: { huidig_wachtwoord: cur, nieuw_wachtwoord: nw } });
      setOk("Wachtwoord gewijzigd. Je andere sessies zijn ingetrokken.");
      setCur("");
      setNw("");
      setNw2("");
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <details>
      <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Wachtwoord wijzigen</summary>
      <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
        <Field id="pw-huidig" label="Huidig wachtwoord">
          {(a) => <input {...a} type="password" autoComplete="current-password" value={cur} onChange={(e) => setCur(e.target.value)} />}
        </Field>
        <Field id="pw-nieuw" label="Nieuw wachtwoord" help="Minstens 12 tekens.">
          {(a) => <input {...a} type="password" autoComplete="new-password" value={nw} onChange={(e) => setNw(e.target.value)} />}
        </Field>
        <Field id="pw-nieuw2" label="Nieuw wachtwoord herhalen">
          {(a) => <input {...a} type="password" autoComplete="new-password" value={nw2} onChange={(e) => setNw2(e.target.value)} />}
        </Field>
        {error ? <ErrorPanel error={error} title="Wijzigen mislukt" /> : null}
        <p role="status" aria-live="polite" className="meta">
          {ok ?? ""}
        </p>
        <div className="row">
          <Button type="submit" bezig={busy}>
            {busy ? "Bezig…" : "Wachtwoord wijzigen"}
          </Button>
        </div>
      </form>
    </details>
  );
}

/**
 * Eigen sessies (testid `sessies`). Intrekken is geen gevaar (opnieuw inloggen kan altijd): een gewone knop, geen rode.
 * Kindvariant (O-05): kindertaal, geen IP-adres of codes in beeld — die staan achter "Details voor een volwassene".
 */
export function SessionsSection({ kind }: { kind?: boolean } = {}) {
  const sessions = useApi<{ items: Session[] }>("/api/v1/auth/sessions");
  const [error, setError] = useState<HubApiError | null>(null);
  const revoke = async (id: string) => {
    setError(null);
    try {
      await apiRequest(`/api/v1/auth/sessions/${id}/revoke`, { method: "POST" });
      await sessions.reload();
    } catch (e) {
      setError(asError(e));
    }
  };
  return (
    <section className="card" id="sessies" aria-labelledby="sessies-titel" data-testid="sessies">
      <h2 id="sessies-titel">{kind ? "Waar je bent ingelogd" : "Mijn sessies"}</h2>
      {sessions.error ? <ErrorPanel error={sessions.error} alert={false} /> : null}
      {error ? <ErrorPanel error={error} /> : null}
      <ul className="plain-list">
        {(sessions.data?.items ?? []).map((s) => (
          <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
            {kind ? (
              <span className="flex flex-col">
                {s.huidige ? <strong>Dit apparaat</strong> : "Een ander apparaat"}
                <span className="meta">Laatst gebruikt {formatDateTime(s.laatst_gezien)}</span>
                <details>
                  <summary className="min-h-touch cursor-pointer py-2 text-sm font-semibold">Details voor een volwassene</summary>
                  <p className="text-sm">
                    IP <code>{s.ip}</code> · gestart {formatDateTime(s.aangemaakt)} · verloopt {formatDateTime(s.verloopt)}
                  </p>
                </details>
              </span>
            ) : (
              <span>
                {s.huidige ? <strong>Deze sessie</strong> : "Andere sessie"} · IP <code>{s.ip}</code>
                <br />
                <span className="meta">
                  Gestart {formatDateTime(s.aangemaakt)} · laatst gezien {formatDateTime(s.laatst_gezien)} · verloopt {formatDateTime(s.verloopt)}
                </span>
              </span>
            )}
            {!s.huidige ? (
              <Button onClick={() => void revoke(s.id)}>
                <LogOut aria-hidden="true" />
                {kind ? "Uitloggen op dat apparaat" : "Intrekken"}
                {kind ? null : <span className="sr-only">: sessie vanaf {s.ip}</span>}
              </Button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function LogoutButton() {
  const { logout } = useSession();
  const router = useRouter();
  return (
    <Button onClick={() => void logout().then(() => router.replace("/inloggen"))} data-testid="uitloggen-instellingen">
      <LogOut aria-hidden="true" />
      Uitloggen
    </Button>
  );
}
