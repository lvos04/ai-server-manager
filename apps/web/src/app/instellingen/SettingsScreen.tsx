"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { TableWrap } from "@/components/TableWrap";
import { apiRequest, HubApiError } from "@/lib/api";
import { formatDateTime, orUnknown } from "@/lib/format";
import { auditLabel } from "@/lib/home";
import { PWA_LABEL, usePwaState } from "@/lib/pwa";
import { hasRole, ROLE_LABEL, useSession } from "@/lib/session";
import { applyTheme, readTheme, subscribeTheme, type ThemeChoice } from "@/lib/theme";
import type { Role, Session, User } from "@/lib/types";
import { useApi } from "@/lib/use-api";

function asError(e: unknown): HubApiError {
  return e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e));
}

const THEMES: { value: ThemeChoice; label: string }[] = [
  { value: "systeem", label: "Zoals het apparaat (licht of donker)" },
  { value: "licht", label: "Licht" },
  { value: "donker", label: "Donker" },
];

export function SettingsScreen() {
  const { state, logout } = useSession();
  const router = useRouter();
  const me = state.status === "auth" ? state.me.user : undefined;
  const isAdmin = hasRole(me?.role, "admin");
  const health = useApi<{ status: string; version: string }>("/healthz");
  const pwa = usePwaState();

  return (
    <>
      <PageHeader title="Instellingen" />
      <nav className="toc" aria-label="Onderdelen van instellingen">
        <a href="#account">Account</a>
        <a href="#weergave">Weergave</a>
        <a href="#sessies">Sessies</a>
        {isAdmin ? <a href="#gebruikers">Gebruikers</a> : null}
        {isAdmin ? <a href="#audit">Auditspoor</a> : null}
        <a href="#over">Over de Hub</a>
      </nav>
      <div className="stack">
        <section className="card stack" id="account" aria-labelledby="account-titel">
          <h2 id="account-titel">Account</h2>
          {me ? (
            <dl className="kv">
              <dt>Gebruikersnaam</dt>
              <dd>{me.username}</dd>
              <dt>Weergavenaam</dt>
              <dd>{me.display_name || "—"}</dd>
              <dt>Rol</dt>
              <dd>{ROLE_LABEL[me.role]}</dd>
            </dl>
          ) : null}
          <PasswordForm />
          <div className="row">
            <button
              type="button"
              className="btn"
              onClick={() => void logout().then(() => router.replace("/inloggen"))}
              data-testid="uitloggen-instellingen"
            >
              Uitloggen
            </button>
          </div>
        </section>

        <ThemeSection />
        <SessionsSection />
        {isAdmin ? <UsersSection /> : null}
        {isAdmin ? <AuditSection /> : null}

        <section className="card stack" id="over" aria-labelledby="over-titel" data-testid="over-de-hub">
          <h2 id="over-titel">Over de Hub</h2>
          <dl className="kv">
            <dt>Versie web-UI</dt>
            <dd>{process.env.NEXT_PUBLIC_HUB_VERSION ?? "onbekend"}</dd>
            <dt>Versie API</dt>
            <dd>{health.data ? health.data.version : health.error ? "niet bereikbaar" : "laden…"}</dd>
            <dt>Offline-schil (PWA)</dt>
            <dd data-testid="pwa-status" data-state={pwa}>
              {PWA_LABEL[pwa]}
            </dd>
          </dl>
          <ul className="plain-list link-list">
            <li>
              <Link href="/onboarding">
                <span>Onboarding (D01–D18)</span>
                <span aria-hidden="true">→</span>
              </Link>
            </li>
            <li>
              <Link href="/onboarding/truenas">
                <span>TrueNAS-koppeling (alleen-lezen)</span>
                <span aria-hidden="true">→</span>
              </Link>
            </li>
            <li>
              <Link href="/onboarding/executor">
                <span>Executor (koppelen volgt in P2)</span>
                <span aria-hidden="true">→</span>
              </Link>
            </li>
            <li>
              <a href="/api/docs">
                <span>API-documentatie (OpenAPI)</span>
                <span aria-hidden="true">→</span>
              </a>
            </li>
          </ul>
        </section>
      </div>
    </>
  );
}

function ThemeSection() {
  const theme = useSyncExternalStore<ThemeChoice>(subscribeTheme, readTheme, () => "systeem");
  return (
    <section className="card stack" id="weergave" aria-labelledby="weergave-titel">
      <h2 id="weergave-titel">Weergave</h2>
      <fieldset>
        <legend>Thema</legend>
        {THEMES.map((t) => (
          <label key={t.value} className="choice">
            <input
              type="radio"
              name="thema"
              value={t.value}
              checked={theme === t.value}
              onChange={() => applyTheme(t.value)}
              data-testid={`thema-${t.value}`}
            />
            {t.label}
          </label>
        ))}
      </fieldset>
      <p className="meta">Wordt alleen op dit apparaat onthouden.</p>
    </section>
  );
}

function PasswordForm() {
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
      <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 600 }}>Wachtwoord wijzigen</summary>
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
          <button type="submit" className="btn" disabled={busy}>
            {busy ? "Bezig…" : "Wachtwoord wijzigen"}
          </button>
        </div>
      </form>
    </details>
  );
}

function SessionsSection() {
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
    <section className="card stack" id="sessies" aria-labelledby="sessies-titel" data-testid="sessies">
      <h2 id="sessies-titel">Actieve sessies</h2>
      {sessions.error ? <ErrorPanel error={sessions.error} /> : null}
      {error ? <ErrorPanel error={error} /> : null}
      <ul className="plain-list">
        {(sessions.data?.items ?? []).map((s) => (
          <li key={s.id} className="row" style={{ justifyContent: "space-between" }}>
            <span>
              {s.huidige ? <strong>Deze sessie</strong> : "Andere sessie"} · IP <code>{s.ip}</code>
              <br />
              <span className="meta">
                Gestart {formatDateTime(s.aangemaakt)} · laatst gezien {formatDateTime(s.laatst_gezien)} · verloopt {formatDateTime(s.verloopt)}
              </span>
            </span>
            {!s.huidige ? (
              <button type="button" className="btn btn-danger" onClick={() => void revoke(s.id)}>
                Intrekken
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

const ROLES: Role[] = ["viewer", "operator", "admin", "kind"];

function UsersSection() {
  const users = useApi<{ items: User[] }>("/api/v1/users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role | "">("");
  const [error, setError] = useState<HubApiError | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setOk(null);
    if (!role) {
      setError(new HubApiError(422, "invoer_onvolledig", "Kies een rol."));
      return;
    }
    setBusy(true);
    try {
      await apiRequest("/api/v1/users", { method: "POST", body: { username: username.trim().toLowerCase(), password, role } });
      setOk(`Gebruiker ${username} aangemaakt.`);
      setUsername("");
      setPassword("");
      setRole("");
      await users.reload();
    } catch (e) {
      setError(asError(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card stack" id="gebruikers" aria-labelledby="gebruikers-titel" data-testid="gebruikers">
      <h2 id="gebruikers-titel">Gebruikers</h2>
      {users.error ? <ErrorPanel error={users.error} /> : null}
      <TableWrap label="Gebruikers">
        <table>
          <caption className="sr-only">Gebruikers</caption>
          <thead>
            <tr>
              <th scope="col">Gebruiker</th>
              <th scope="col">Rol</th>
              <th scope="col">Status</th>
              <th scope="col">Aangemaakt</th>
            </tr>
          </thead>
          <tbody>
            {(users.data?.items ?? []).map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{ROLE_LABEL[u.role]}</td>
                <td>{u.disabled ? <StatusBadge view={{ tone: "neutral", label: "Uitgeschakeld" }} /> : <StatusBadge view={{ tone: "info", label: "Actief" }} />}</td>
                <td>{formatDateTime(u.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
      <details>
        <summary style={{ minHeight: 44, display: "flex", alignItems: "center", cursor: "pointer", fontWeight: 600 }}>Gebruiker toevoegen</summary>
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
          <Field id="nieuw-gebruiker" label="Gebruikersnaam" help="Kleine letters, cijfers, punt of streepje (3–64 tekens).">
            {(a) => <input {...a} type="text" autoComplete="off" autoCapitalize="none" value={username} onChange={(e) => setUsername(e.target.value)} />}
          </Field>
          <Field id="nieuw-wachtwoord" label="Eerste wachtwoord" help="Minstens 12 tekens; de gebruiker wijzigt het daarna zelf.">
            {(a) => <input {...a} type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />}
          </Field>
          <Field id="nieuw-rol" label="Rol" help="Kijker: alleen lezen. Operator: ook meten en vernieuwen. Beheerder: alles. Kinderprofiel: alleen eigen profiel.">
            {(a) => (
              <select {...a} value={role} onChange={(e) => setRole(e.target.value as Role | "")}>
                <option value="">— maak een keuze —</option>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABEL[r]}
                  </option>
                ))}
              </select>
            )}
          </Field>
          {error ? <ErrorPanel error={error} title="Aanmaken mislukt" /> : null}
          <p role="status" aria-live="polite" className="meta">
            {ok ?? ""}
          </p>
          <div className="row">
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Bezig…" : "Gebruiker aanmaken"}
            </button>
          </div>
        </form>
      </details>
    </section>
  );
}

interface AuditRow {
  id: number;
  op: string | null;
  actor_type: string;
  actor_id: string;
  actie: string;
  doel_type: string | null;
  doel_id: string | null;
}

function AuditSection() {
  const audit = useApi<{ items: AuditRow[]; next_cursor: string | null }>("/api/v1/audit?limit=20");
  return (
    <section className="card stack" id="audit" aria-labelledby="audit-titel" data-testid="audit">
      <h2 id="audit-titel">Auditspoor (laatste 20)</h2>
      {audit.error ? <ErrorPanel error={audit.error} /> : null}
      <TableWrap label="Auditspoor">
        <table>
          <caption className="sr-only">Auditspoor</caption>
          <thead>
            <tr>
              <th scope="col">Wanneer</th>
              <th scope="col">Wie</th>
              <th scope="col">Actie</th>
              <th scope="col">Doel</th>
            </tr>
          </thead>
          <tbody>
            {(audit.data?.items ?? []).map((r) => (
              <tr key={r.id}>
                <td>{formatDateTime(r.op)}</td>
                <td>{r.actor_id}</td>
                <td>
                  {auditLabel(r.actie)}
                  <div className="meta">
                    <code>{r.actie}</code>
                  </div>
                </td>
                <td>{r.doel_type ? `${r.doel_type}: ${orUnknown(r.doel_id)}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </TableWrap>
    </section>
  );
}
