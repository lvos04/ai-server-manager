"use client";

import { KeyRound, LogIn, Plus, ShieldX, Trash2, UserPlus } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Controles } from "@/components/Controles";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { ResponsiveList } from "@/components/ResponsiveList";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { apiRequest } from "@/lib/api";
import { formatDateTime, formatTime } from "@/lib/format";
import { hasRole, ROLE_LABEL, useRole } from "@/lib/session";
import type { Role, User } from "@/lib/types";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";
import { InstellingenKop, asError } from "../delen";

/** RolUitleg (C-61): wat mag elke rol, in dezelfde zinnen als de RolKiezer. */
export const ROL_UITLEG: Record<Role, string> = {
  admin: "Beheerder: alles, ook gebruikers, diensten, SSO en het noodaccount.",
  operator: "Operator: ook meten, vernieuwen, incidenten afhandelen en logs bekijken.",
  viewer: "Kijker: alleen lezen. Kan niets wijzigen.",
  kind: "Kind: alleen Home, Kijken, Zoeken en Ik — met toegestane titels. Nooit beheer.",
};
const ROLES: Role[] = ["viewer", "operator", "admin", "kind"];

function RolKiezer({ name, value, onChange }: { name: string; value: Role | ""; onChange: (r: Role) => void }) {
  return (
    <fieldset className="flex flex-col gap-2 border-0 p-0">
      <legend className="mb-1">Rol</legend>
      {ROLES.map((r) => (
        <label key={r} className="keuze">
          <input type="radio" name={name} value={r} checked={value === r} onChange={() => onChange(r)} />
          <span className="flex flex-col font-semibold">
            {ROLE_LABEL[r].replace(/^./, (c) => c.toUpperCase())}
            <span className="text-sm font-normal">{ROL_UITLEG[r]}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
}

function RolUitleg() {
  return (
    <details>
      <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Wat mag elke rol?</summary>
      <ul className="list-disc pl-6">
        {ROLES.map((r) => (
          <li key={r}>{ROL_UITLEG[r]}</li>
        ))}
      </ul>
      <p className="text-sm">
        Via SSO bepaalt de groep de rol. Hoort iemand bij meerdere groepen, dan wint Kind; anders de hoogste rol. Zonder passende groep:
        geen toegang. De AI kan rollen nooit wijzigen.
      </p>
    </details>
  );
}

function aanmelden(u: User): string {
  if (u.break_glass) return "Noodlogin";
  if (u.auth_bron === "oidc") return "SSO";
  return "Lokaal wachtwoord";
}

function Gebruikers() {
  const users = useApi<{ items: User[] }>("/api/v1/users");
  const [toon, setToon] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role | "">("");
  const [ok, setOk] = useState<string | null>(null);
  const create = useAction();
  const patch = useAction();
  const revoke = useAction();
  const [wijzig, setWijzig] = useState<{ id: string; rol: Role | "" } | null>(null);
  const [uitgeschakeld, setUitgeschakeld] = useState(false);
  const submit = async (ev: FormEvent) => {
    ev.preventDefault();
    setOk(null);
    if (!role) return;
    const r = await create.run("/api/v1/users", { body: { username: username.trim().toLowerCase(), password, role } });
    if (r) {
      setOk(`Gebruiker ${username} aangemaakt.`);
      setUsername("");
      setPassword("");
      setRole("");
      await users.reload();
    }
  };
  const list = (users.data?.items ?? []).filter((u) => uitgeschakeld || !u.disabled);
  const nUit = (users.data?.items ?? []).filter((u) => u.disabled).length;
  return (
    <section className="card" id="gebruikers" aria-labelledby="gebruikers-titel" data-testid="gebruikers">
      <h2 id="gebruikers-titel">Gebruikers en rollen</h2>
      <RolUitleg />
      {users.error ? <ErrorPanel error={users.error} alert={false} /> : null}
      {!users.data && users.loading ? <Loading /> : null}
      {nUit ? (
        <label className="keuze w-fit">
          <input type="checkbox" checked={uitgeschakeld} onChange={(e) => setUitgeschakeld(e.target.checked)} />
          Uitgeschakelde gebruikers tonen ({nUit})
        </label>
      ) : null}
      <ResponsiveList
        items={list}
        label="Gebruikers"
        tabelVanaf={1280}
        sleutel={(u) => u.id}
        rijTestId={(u) => `gebruiker-${u.username}`}
        kolommen={[
          {
            kop: "Gebruiker",
            cel: (u) => (
              <span className="flex flex-col">
                <strong>{u.display_name || u.username}</strong>
                <code className="text-sm">{u.username}</code>
              </span>
            ),
          },
          { kop: "Rol", cel: (u) => <span>{ROLE_LABEL[u.role]}</span> },
          {
            kop: "Aanmelden",
            cel: (u) => (
              <span className="flex flex-col gap-1">
                <span>{aanmelden(u)}</span>
                {u.disabled ? <StatusBadge view={{ tone: "neutral", label: "Uitgeschakeld", icon: "min" }} /> : null}
              </span>
            ),
          },
          {
            kop: "Acties",
            cel: (u) =>
              u.break_glass ? (
                <Link href="/instellingen/noodaccount" className={buttonVariants({ variant: "secundair", size: "klein" })}>
                  Noodaccount beheren
                </Link>
              ) : (
                <span className="flex flex-wrap gap-2">
                  <Button size="klein" onClick={() => setWijzig({ id: u.id, rol: u.role })}>
                    <KeyRound aria-hidden="true" />
                    Rol wijzigen<span className="sr-only">: {u.username}</span>
                  </Button>
                  <Button
                    size="klein"
                    onClick={async () => {
                      const r = await revoke.run(`/api/v1/users/${u.id}/sessions/revoke`, { body: { reden: "ingetrokken door beheerder" } });
                      if (r) setOk(`Sessies van ${u.username} ingetrokken.`);
                    }}
                  >
                    <ShieldX aria-hidden="true" />
                    Sessies intrekken<span className="sr-only">: {u.username}</span>
                  </Button>
                </span>
              ),
          },
        ]}
      />
      {wijzig ? (
        <form
          className="flex flex-col gap-3 rounded-lg border-2 border-border-strong p-3"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!wijzig.rol) return;
            const r = await patch.run(`/api/v1/users/${wijzig.id}`, { method: "PATCH", body: { role: wijzig.rol } });
            if (r) {
              setOk("Rol gewijzigd. Lopende sessies van deze gebruiker zijn ingetrokken.");
              setWijzig(null);
              await users.reload();
            }
          }}
        >
          <RolKiezer name="rol-wijzigen" value={wijzig.rol} onChange={(r) => setWijzig({ ...wijzig, rol: r })} />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="primair" bezig={patch.busy}>
              Rol opslaan
            </Button>
            <Button onClick={() => setWijzig(null)}>Annuleren</Button>
          </div>
        </form>
      ) : null}
      {patch.error ? <ErrorPanel error={patch.error} /> : null}
      {revoke.error ? <ErrorPanel error={revoke.error} /> : null}
      <Button variant="primair" onClick={() => setToon((x) => !x)} aria-expanded={toon} className="w-fit">
        <UserPlus aria-hidden="true" />
        Gebruiker toevoegen
      </Button>
      {toon ? (
        <form className="form" onSubmit={(ev) => void submit(ev)} noValidate>
          <Field id="nieuw-gebruiker" label="Gebruikersnaam" help="Kleine letters, cijfers, punt of streepje (3–64 tekens).">
            {(a) => <input {...a} type="text" autoComplete="off" autoCapitalize="none" value={username} onChange={(e) => setUsername(e.target.value)} />}
          </Field>
          <Field id="nieuw-wachtwoord" label="Eerste wachtwoord" help="Minstens 12 tekens; de gebruiker wijzigt het daarna zelf.">
            {(a) => <input {...a} type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />}
          </Field>
          <RolKiezer name="nieuw-rol" value={role} onChange={setRole} />
          {create.error ? <ErrorPanel error={create.error} title="Aanmaken mislukt" /> : null}
          <div>
            <Button type="submit" bezig={create.busy} uit={!role} aria-describedby={!role ? "rol-nodig" : undefined}>
              Gebruiker aanmaken
            </Button>
            {!role ? (
              <p id="rol-nodig" className="help">
                Kies eerst een rol.
              </p>
            ) : null}
          </div>
        </form>
      ) : null}
      <p role="status" aria-live="polite" className="meta">
        {ok ?? ""}
      </p>
    </section>
  );
}

interface AlleSessie {
  id: string;
  gebruiker: string;
  rol: Role;
  auth_bron: string;
  noodlogin: boolean;
  aangemaakt: string;
  laatst_gezien: string;
  verloopt: string;
  ip: string;
}

function AlleSessies() {
  const s = useApi<{ items: AlleSessie[] }>("/api/v1/sessions", 60_000);
  return (
    <section className="card" aria-labelledby="alle-sessies-titel" data-testid="alle-sessies">
      <h2 id="alle-sessies-titel">Alle sessies</h2>
      {s.error ? <ErrorPanel error={s.error} alert={false} /> : null}
      <ResponsiveList
        items={s.data?.items ?? []}
        label="Alle sessies"
        tabelVanaf={1280}
        sleutel={(x) => x.id}
        kolommen={[
          { kop: "Gebruiker", cel: (x) => `${x.gebruiker} (${ROLE_LABEL[x.rol]})` },
          { kop: "Bron", cel: (x) => (x.noodlogin ? "noodlogin" : x.auth_bron === "oidc" ? "SSO" : "lokaal") },
          { kop: "Laatst actief", cel: (x) => formatDateTime(x.laatst_gezien) },
          { kop: "Bron-IP", cel: (x) => <code>{x.ip}</code> },
        ]}
      />
    </section>
  );
}

interface Oidc {
  ingeschakeld: boolean;
  verplicht: boolean;
  noodaccount_werkend: boolean;
  issuer: string | null;
  client_id: string | null;
  client_secret: { ingesteld: boolean; laatste4: string | null };
  redirect_uri: string | null;
  redirect_uri_https: boolean;
  scopes: string;
  groepen_claim: string;
  rolkoppelingen: { groep: string; rol: Role }[];
  sessie_minuten: number;
  discovery: { status: string; gemeten_op: string | null; endpoints: Record<string, string>; algoritmen: string[] | null };
  jwks: { sleutels: { kid: string; kty: string; alg?: string }[]; gemeten_op: string | null };
  laatste_test: { op: string | null; actueel: boolean; resultaat?: string; reden?: string; uitleg?: string; gebruikersnaam?: string; rol?: string | null; groepen?: string[] };
  gate_authentik: { status: string; redenen: { id: string; tekst: string }[] };
}

interface SsoStatus {
  status: string;
  reden: string | null;
  least_privilege: { waarde: string | null; weergave: string };
  rechten: { status: string | null; weergave: string };
  bijgewerkt_op: string | null;
}

/** S-163 Inloggen via SSO: config, controle van de issuer, groep → rol, testlogin, gate D17, advies home-control-hub. */
function Sso() {
  const cfg = useApi<Oidc>("/api/v1/auth/oidc");
  const advies = useApi<SsoStatus>("/api/v1/sso/status");
  const save = useAction<Oidc>();
  const disc = useAction<{ resultaat: string; reden?: string; uitleg?: string }>();
  const aan = useAction<Oidc>();
  const [form, setForm] = useState<{ issuer: string; client_id: string; client_secret: string; scopes: string; groepen_claim: string; sessie_minuten: number; rolkoppelingen: { groep: string; rol: Role | "" }[] } | null>(null);
  const [testErr, setTestErr] = useState<unknown>(null);
  const c = cfg.data;
  const redirect = typeof window !== "undefined" ? `${window.location.origin}/api/v1/auth/oidc/callback` : "";
  const f =
    form ??
    (c
      ? {
          issuer: c.issuer ?? "",
          client_id: c.client_id ?? "",
          client_secret: "",
          scopes: c.scopes,
          groepen_claim: c.groepen_claim,
          sessie_minuten: c.sessie_minuten,
          rolkoppelingen: c.rolkoppelingen.length ? c.rolkoppelingen : [{ groep: "", rol: "" as const }],
        }
      : null);
  const gateDicht = c?.gate_authentik.status !== "toegestaan";
  const test = c?.laatste_test;
  return (
    <section className="card" id="sso" aria-labelledby="sso-titel" data-testid="sso">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="sso-titel">Inloggen via SSO</h2>
        {c ? <StatusBadge view={{ tone: "neutral", label: c.ingeschakeld ? "Aan" : "Uit", icon: "aan" }} /> : null}
      </div>
      {cfg.error ? <ErrorPanel error={cfg.error} alert={false} /> : null}
      {!c && cfg.loading ? <Loading /> : null}
      {c && gateDicht ? (
        <Melding soort="gate" titel="Inschakelen kan nog niet: geblokkeerd door de HTTPS-voorwaarde" data-testid="sso-gate">
          <p>
            Nodig: besluit D17 (HTTPS) op Getest. {c.gate_authentik.redenen.map((r) => r.tekst).join(" ")}
            {test?.actueel ? " De testlogin hieronder is wel geslaagd." : ""} Dit is geen storing; er wacht een voorwaarde.
          </p>
          <p>
            <Link href="/onboarding/besluit/D17" className={buttonVariants({ variant: "secundair" })}>
              D17 openen
            </Link>
          </p>
        </Melding>
      ) : null}
      {c && f ? (
        <form
          className="form"
          onSubmit={async (e) => {
            e.preventDefault();
            const body = {
              issuer: f.issuer.trim(),
              client_id: f.client_id.trim(),
              ...(f.client_secret ? { client_secret: f.client_secret } : {}),
              redirect_uri: redirect,
              scopes: f.scopes,
              groepen_claim: f.groepen_claim,
              sessie_minuten: f.sessie_minuten,
              rolkoppelingen: f.rolkoppelingen.filter((k) => k.groep && k.rol),
            };
            const r = await save.run("/api/v1/auth/oidc", { method: "PUT", body });
            if (r) {
              setForm(null);
              await cfg.reload();
            }
          }}
        >
          <Field id="sso-issuer" label="Issuer-adres" help="Alleen https. Wijzigen zet SSO uit tot een nieuwe testlogin slaagt.">
            {(a) => <input {...a} type="url" value={f.issuer} onChange={(e) => setForm({ ...f, issuer: e.target.value })} autoComplete="off" />}
          </Field>
          <Field id="sso-client" label="Client-ID">
            {(a) => <input {...a} value={f.client_id} onChange={(e) => setForm({ ...f, client_id: e.target.value })} autoComplete="off" />}
          </Field>
          <Field
            id="sso-geheim"
            label={c.client_secret.ingesteld ? "Clientgeheim vervangen (optioneel)" : "Clientgeheim"}
            help={c.client_secret.ingesteld ? `Ingesteld: ••••${c.client_secret.laatste4 ?? ""}. Leeg laten = niet wijzigen.` : "Wordt versleuteld opgeslagen; je ziet daarna alleen de laatste 4 tekens."}
          >
            {(a) => <input {...a} type="password" value={f.client_secret} onChange={(e) => setForm({ ...f, client_secret: e.target.value })} autoComplete="new-password" />}
          </Field>
          <KopieerVeld label="Terugkeer-adres (zet dit in Authentik)" waarde={redirect} testId="sso-redirect" />
          {redirect.startsWith("http://") ? (
            <Melding soort="info">
              <p>De aanmeldcode is beschermd met PKCE en een browsercookie, maar zet HTTPS aan zodra D17 klaar is.</p>
            </Melding>
          ) : null}
          <div className="grid gap-3 md:grid-cols-3">
            <Field id="sso-scopes" label="Scopes">
              {(a) => <input {...a} value={f.scopes} onChange={(e) => setForm({ ...f, scopes: e.target.value })} />}
            </Field>
            <Field id="sso-claim" label="Groepen-claim">
              {(a) => <input {...a} value={f.groepen_claim} onChange={(e) => setForm({ ...f, groepen_claim: e.target.value })} />}
            </Field>
            <Field id="sso-duur" label="Sessieduur (minuten)" help="15–720.">
              {(a) => <input {...a} type="number" min={15} max={720} value={f.sessie_minuten} onChange={(e) => setForm({ ...f, sessie_minuten: Number(e.target.value) })} />}
            </Field>
          </div>
          <fieldset>
            <legend>Groep → rol</legend>
            <div className="flex flex-col gap-2">
              {f.rolkoppelingen.map((k, i) => (
                <div key={i} className="grid items-end gap-2 sm:grid-cols-[minmax(0,1fr)_12rem_auto]">
                  <div className="field">
                    <label htmlFor={`sso-groep-${i}`}>Groep {i + 1}</label>
                    <input id={`sso-groep-${i}`} value={k.groep} onChange={(e) => setForm({ ...f, rolkoppelingen: f.rolkoppelingen.map((x, j) => (j === i ? { ...x, groep: e.target.value } : x)) })} />
                  </div>
                  <div className="field">
                    <label htmlFor={`sso-rol-${i}`}>Rol {i + 1}</label>
                    <select id={`sso-rol-${i}`} value={k.rol} onChange={(e) => setForm({ ...f, rolkoppelingen: f.rolkoppelingen.map((x, j) => (j === i ? { ...x, rol: e.target.value as Role } : x)) })}>
                      <option value="">Kies een rol</option>
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {ROLE_LABEL[r]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button onClick={() => setForm({ ...f, rolkoppelingen: f.rolkoppelingen.filter((_, j) => j !== i) })}>
                    <Trash2 aria-hidden="true" />
                    Verwijderen<span className="sr-only">: groep {i + 1}</span>
                  </Button>
                </div>
              ))}
              <Button className="w-fit" onClick={() => setForm({ ...f, rolkoppelingen: [...f.rolkoppelingen, { groep: "", rol: "" }] })}>
                <Plus aria-hidden="true" />
                Rij toevoegen
              </Button>
            </div>
          </fieldset>
          {save.error ? <ErrorPanel error={save.error} title="Opslaan mislukt" /> : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="primair" bezig={save.busy} data-testid="sso-opslaan">
              Opslaan
            </Button>
          </div>
        </form>
      ) : null}
      {c?.issuer ? (
        <div className="flex flex-col gap-2">
          <h3>Controle van de issuer</h3>
          <div>
            <Button bezig={disc.busy} onClick={async () => (await disc.run("/api/v1/auth/oidc/discover")) && void cfg.reload()} data-testid="sso-controleren">
              Issuer controleren
            </Button>
          </div>
          {disc.result?.resultaat === "mislukt" ? (
            <Melding soort="fout" titel="Controle mislukt">
              <p>
                {disc.result.uitleg} (<code>{disc.result.reden}</code>)
              </p>
            </Melding>
          ) : null}
          {disc.error ? <ErrorPanel error={disc.error} /> : null}
          <Controles
            testId="sso-controles"
            items={[
              { id: "issuer", naam: "Issuer exact en via https", uitkomst: c.discovery.status === "ok" ? "ok" : "onbekend", detail: c.discovery.gemeten_op ? `Gecontroleerd om ${formatTime(c.discovery.gemeten_op)}.` : "Nog niet gecontroleerd." },
              { id: "oorsprong", naam: "Alle endpoints op dezelfde oorsprong", uitkomst: c.discovery.status === "ok" ? "ok" : "onbekend" },
              {
                id: "sleutels",
                naam: "Sleutels alleen asymmetrisch",
                uitkomst: c.jwks.sleutels.length ? "ok" : "onbekend",
                detail: c.jwks.sleutels.length ? `${c.jwks.sleutels.length} sleutel(s): ${c.jwks.sleutels.map((k) => k.alg ?? k.kty).join(", ")}` : undefined,
              },
            ]}
          />
          <h3>Testlogin</h3>
          <p className="text-sm">Een volledige aanmelding bij de identity provider, zonder dat er een sessie ontstaat.</p>
          <div>
            <Button
              data-testid="sso-testlogin"
              onClick={async () => {
                setTestErr(null);
                try {
                  const { data } = await apiRequest<{ autorisatie_url: string }>("/api/v1/auth/oidc/test", { method: "POST" });
                  window.location.assign(data.autorisatie_url);
                } catch (e) {
                  setTestErr(asError(e));
                }
              }}
            >
              <LogIn aria-hidden="true" />
              Testlogin
            </Button>
          </div>
          {testErr ? <ErrorPanel error={testErr} /> : null}
          {test?.op ? (
            test.resultaat === "geslaagd" ? (
              <p data-testid="sso-testuitkomst">
                <StatusBadge view={{ tone: "neutral", label: "Geslaagd", icon: "geslaagd" }} /> om {formatTime(test.op)}
                {test.gebruikersnaam ? ` als ${test.gebruikersnaam}` : ""}
                {test.rol ? ` · rol ${test.rol}` : ""}. Er is geen sessie gemaakt.{test.actueel ? "" : " (Hoort bij oudere instellingen; test opnieuw.)"}
              </p>
            ) : (
              <Melding soort="fout" titel={`Testlogin ${test.resultaat === "geen_rol" ? "zonder rol" : "mislukt"} om ${formatTime(test.op)}`} data-testid="sso-testuitkomst">
                <p>{test.uitleg ?? (test.resultaat === "geen_rol" ? "De gebruiker hoort bij geen enkele groep met een rol." : "")}</p>
                {test.reden ? <p className="text-sm">Code <code>{test.reden}</code></p> : null}
              </Melding>
            )
          ) : null}
          <h3>Aan- en uitzetten</h3>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primair"
              uit={gateDicht || !test?.actueel || c.ingeschakeld}
              aria-describedby="sso-aan-reden"
              bezig={aan.busy}
              onClick={async () => (await aan.run("/api/v1/auth/oidc/inschakelen", { body: { ingeschakeld: true } })) && void cfg.reload()}
            >
              SSO aanzetten
            </Button>
            {c.ingeschakeld ? (
              <Button onClick={async () => (await aan.run("/api/v1/auth/oidc/inschakelen", { body: { ingeschakeld: false } })) && void cfg.reload()}>SSO uitzetten</Button>
            ) : null}
            <Button uit={!c.ingeschakeld || !c.noodaccount_werkend} aria-describedby="sso-verplicht-reden" data-testid="oidc-verplicht">
              OIDC verplicht maken
            </Button>
          </div>
          <p id="sso-aan-reden" className="help">
            {gateDicht ? "Aanzetten kan pas als D17 (HTTPS) Getest is." : !test?.actueel ? "Aanzetten kan pas na een geslaagde testlogin met de huidige instellingen." : ""}
          </p>
          <p id="sso-verplicht-reden" className="help">
            OIDC verplicht kan pas als SSO aanstaat én het noodaccount werkt
            {!c.noodaccount_werkend ? " (nu niet: het noodaccount werkt niet)" : ""}.
          </p>
          {aan.error ? <ErrorPanel error={aan.error} /> : null}
        </div>
      ) : null}
      <div className="flex flex-col gap-2">
        <h3>Advies van home-control-hub</h3>
        {advies.error ? <ErrorPanel error={advies.error} alert={false} /> : null}
        {advies.data ? (
          advies.data.status === "onbekend" || advies.data.least_privilege.weergave === "deels_gecontroleerd" ? (
            <Melding soort="onbekend" titel={advies.data.least_privilege.weergave === "deels_gecontroleerd" ? "Minste rechten deels gecontroleerd" : "Onbekend"}>
              <p>
                {advies.data.reden === "home_control_hub_niet_gekoppeld" ? "home-control-hub is (nog) niet gekoppeld; er is geen advies." : `Rechten: ${advies.data.rechten.weergave}.`} Het advies
                is nooit de poortwachter: de Hub beslist zelf.
              </p>
            </Melding>
          ) : (
            <p>
              Minste rechten: {advies.data.least_privilege.weergave} · rechten: {advies.data.rechten.weergave}
              {advies.data.rechten.weergave === "verouderd" ? " (verouderd)" : ""}.
            </p>
          )
        ) : null}
      </div>
    </section>
  );
}

export function ToegangScreen() {
  const role = useRole();
  return (
    <>
      <InstellingenKop titel="Gebruikers en toegang" intro="Wie mag wat. De API is altijd de poortwachter; de UI verbergt alleen wat niet mag." />
      {!hasRole(role, "admin") ? (
        <RolMelding>Gebruikers, sessies en SSO beheren kan alleen een beheerder.</RolMelding>
      ) : (
        <div className="stack">
          <Gebruikers />
          <AlleSessies />
          <Sso />
        </div>
      )}
    </>
  );
}
