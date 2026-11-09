"use client";

import { Fingerprint, KeyRound, Link2, RotateCw, ShieldX, SquareArrowOutUpRight, Unlink } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Aftellen } from "@/components/Aftellen";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { BevestigDialoog } from "@/components/ui/alert-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { apiRequest, HubApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatRelative, formatTime } from "@/lib/format";
import { hasRole, ROLE_LABEL, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";
import { InstellingenKop } from "../delen";

const EXECUTOR = "ai-server-manager-executor";
const EIGEN_DIENSTEN = [
  { id: "home-control-hub", label: "Home Control Hub (home-control-hub)" },
  { id: "appstore-en-fork", label: "Appstore (appstore-en-fork)" },
  { id: "jelly-leon-platform", label: "Jelly Leon-platform (jelly-leon-platform)" },
  { id: "zoeken-en-persoonlijke-ai", label: "Zoeken en persoonlijke AI (zoeken-en-persoonlijke-ai)" },
];

interface Token {
  id: string;
  laatste4: string;
  aangemaakt: string;
  verloopt: string | null;
  ingetrokken: string | null;
  laatst_gebruikt: string | null;
  geldig: boolean;
}

export interface Dienst {
  id: string;
  app_id: string;
  status: "active" | "revoked" | string;
  version: string | null;
  enrolled_via: string;
  enrolled_at: string;
  updated_at: string;
  truenas_app: { naam: string | null; bevestigd: boolean; bevestigd_op: string | null; gemeten_kandidaten: string[] | null };
  rotatie: { aangevraagd_op: string | null; aangevraagd_door: string | null; aanbevolen: boolean; token_leeftijd_dagen: number | null };
  tokens: Token[];
}

interface Keyset {
  jwks: unknown;
  policy_public_key: unknown;
  keyset_fingerprint: string;
}

export interface RegistryItem {
  app: string;
  basis_url: string | null;
  reden_geen_url: string | null;
  verouderd: boolean;
}

export interface Koppelcode {
  grant_id: string;
  app_id: string;
  koppelcode: string;
  verloopt_op: string;
  keyset_fingerprint: string;
}

interface Enrollment {
  grant_id: string;
  app_id: string;
  enrollment_token: string;
  verloopt_op: string;
  keyset_fingerprint: string;
}

/** C-57: vingerafdruk van deze Hub + publieke sleutelset (geen geheim). */

/** "van vandaag" / "1 dag oud" / "12 dagen oud"; onbekend blijft onbekend (nooit "0 dagen"). */
function tokenLeeftijd(dagen: number | null | undefined): string {
  if (typeof dagen !== "number") return "leeftijd onbekend";
  if (dagen < 1) return "van vandaag";
  return dagen === 1 ? "1 dag oud" : `${dagen} dagen oud`;
}

function Vingerafdruk({ ks }: { ks: Keyset }) {
  return (
    <section className="card" aria-labelledby="vingerafdruk-titel" data-testid="vingerafdruk-hub">
      <h2 id="vingerafdruk-titel" className="flex items-center gap-2">
        <Fingerprint aria-hidden="true" className="size-5 text-muted-foreground" />
        Vingerafdruk van deze Hub
      </h2>
      <KopieerVeld label="Vingerafdruk (16 tekens in groepen van 4)" waarde={ks.keyset_fingerprint} />
      <p>Een dienst toont bij het koppelen deze vingerafdruk. Komt die niet overeen, koppel dan niet en trek de dienst in.</p>
      <details>
        <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Publieke sleutelset (voor MediaGuard, MSO en my_house)</summary>
        <p className="text-sm">Alleen publieke sleutels (geen geheim). Bestaande apps plakken deze set in hun eigen beheer-UI en vergelijken de vingerafdruk.</p>
        <KopieerVeld label="Publieke sleutelset (JSON)" waarde={JSON.stringify({ jwks: ks.jwks, policy_public_key: ks.policy_public_key })} />
      </details>
    </section>
  );
}

/** C-40a KoppelcodeKaart: code + vingerafdruk samen, aftellen, gemeten adres van de statuspagina, wachten op de dienst. */
export function KoppelcodeKaart({ code, adres, onVerlopen, gekoppeld }: { code: Koppelcode; adres: RegistryItem | undefined; onVerlopen: () => void; gekoppeld: boolean }) {
  const [verlopen, setVerlopen] = useState(() => Date.parse(code.verloopt_op) <= Date.now());
  const exec = code.app_id === EXECUTOR;
  const duur = exec ? 30 : 60;
  const verloop = useCallback(() => {
    setVerlopen(true);
    onVerlopen();
  }, [onVerlopen]);
  if (verlopen && !gekoppeld) {
    return (
      <Melding soort="onbekend" titel="Verlopen — maak een nieuwe code." data-testid="koppelcode-verlopen">
        <p>Deze koppelcode werkt niet meer.</p>
      </Melding>
    );
  }
  return (
    <div className="flex flex-col gap-3 rounded-lg border-2 border-border-strong p-4" data-testid="koppelcode">
      <p className="font-mono text-2xl leading-9 font-semibold tracking-wider" aria-hidden="true">
        {code.koppelcode}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <KopieerVeld label="Koppelcode" waarde={code.koppelcode} testId="koppelcode-waarde" />
        <KopieerVeld label="Vingerafdruk van de Hub" waarde={code.keyset_fingerprint} testId="koppelcode-vingerafdruk" />
      </div>
      <p className="flex flex-wrap items-center gap-2">
        Verloopt over <Aftellen tot={code.verloopt_op} onVerlopen={verloop} testId="aftellen" />
      </p>
      <p className="text-sm">
        Deze code zie je maar één keer. Hij werkt één keer en verloopt na {duur} minuten. Een nieuwe code maakt deze niet ongeldig.
      </p>
      <ol data-genummerd="" className="flex flex-col gap-1">
        <li>
          Open de statuspagina van {code.app_id}:{" "}
          {adres?.basis_url ? (
            <a href={adres.basis_url} target="_blank" rel="noopener noreferrer">
              {adres.basis_url}
              <span className="sr-only"> (opent in een nieuw tabblad)</span>
            </a>
          ) : (
            <strong>Adres onbekend — vernieuw de inventaris</strong>
          )}
        </li>
        <li>Vul de koppelcode in en controleer dat de vingerafdruk hetzelfde is.</li>
        <li>Klik daar op koppelen.</li>
      </ol>
      {gekoppeld ? (
        <p role="status" data-testid="koppeling-gemeld">
          <StatusBadge view={{ tone: "neutral", label: "Gekoppeld", icon: "gekoppeld" }} /> {code.app_id} heeft zich gemeld.
        </p>
      ) : (
        <p role="status" className="text-sm">
          Wacht op de dienst — deze pagina toont de koppeling zodra {code.app_id} zich meldt.
        </p>
      )}
    </div>
  );
}

function Koppelen({ onNieuw, diensten, registry }: { onNieuw: () => void; diensten: Dienst[]; registry: RegistryItem[] }) {
  const [app, setApp] = useState("");
  const [wijze, setWijze] = useState<"" | "token" | "code">("");
  const [code, setCode] = useState<Koppelcode | null>(null);
  const [token, setToken] = useState<Enrollment | null>(null);
  const [err, setErr] = useState<HubApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [start, setStart] = useState(0);
  const hubUrl = typeof window !== "undefined" ? window.location.origin : "";
  const localhost = /\/\/(localhost|127\.0\.0\.1|\[::1\])/.test(hubUrl);
  const gekoppeld = Boolean(code && diensten.some((d) => d.app_id === code.app_id && d.status === "active" && Date.parse(d.enrolled_at) >= start - 5000));

  // Zolang een koppelcode open staat: elke 5 s het register verversen (tot de dienst zich meldt).
  useEffect(() => {
    if (!code || gekoppeld) return;
    const t = setInterval(onNieuw, 5000);
    return () => clearInterval(t);
  }, [code, gekoppeld, onNieuw]);

  const maak = async () => {
    setErr(null);
    setBusy(true);
    setCode(null);
    setToken(null);
    try {
      setStart(Date.now());
      if (wijze === "code") setCode((await apiRequest<Koppelcode>("/api/v1/services/pairing-codes", { method: "POST", body: { app_id: app } })).data);
      else setToken((await apiRequest<Enrollment>("/api/v1/services/enrollment-tokens", { method: "POST", body: { app_id: app } })).data);
    } catch (e) {
      setErr(e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" id="dienst-koppelen" aria-labelledby="koppelen-titel" data-testid="dienst-koppelen">
      <h2 id="koppelen-titel">Dienst koppelen</h2>
      <Field id="dienst-app" label="Welke dienst?" help="De executor koppel je via Onboarding → Executor, met een koppelcode op zijn eigen statuspagina.">
        {(a) => (
          <select {...a} value={app} onChange={(e) => setApp(e.target.value)}>
            <option value="">Kies een dienst</option>
            {EIGEN_DIENSTEN.map((d) => (
              <option key={d.id} value={d.id}>
                {d.label}
              </option>
            ))}
          </select>
        )}
      </Field>
      <fieldset className="flex flex-col gap-2 border-0 p-0">
        <legend className="mb-1">Hoe koppel je?</legend>
        <label className="keuze">
          <input type="radio" name="koppelwijze" value="token" checked={wijze === "token"} onChange={() => setWijze("token")} />
          <span className="flex flex-col font-semibold">
            Enrollment-token in het Custom App-formulier (aanbevolen)
            <span className="text-sm font-normal">Je vult drie omgevingsvariabelen in bij de app in TrueNAS.</span>
          </span>
        </label>
        <label className="keuze">
          <input type="radio" name="koppelwijze" value="code" checked={wijze === "code"} onChange={() => setWijze("code")} />
          <span className="flex flex-col font-semibold">
            Koppelcode op de statuspagina
            <span className="text-sm font-normal">Voor een app die al draait: je typt de code op zijn statuspagina.</span>
          </span>
        </label>
      </fieldset>
      <div>
        <Button variant="primair" uit={!app || !wijze} aria-describedby={!app || !wijze ? "koppel-nodig" : undefined} bezig={busy} onClick={() => void maak()} data-testid="koppel-maken">
          <Link2 aria-hidden="true" />
          {wijze === "code" ? "Koppelcode maken" : "Enrollment-token maken"}
        </Button>
        {!app || !wijze ? (
          <p id="koppel-nodig" className="help">
            Kies eerst een dienst en een manier van koppelen.
          </p>
        ) : null}
      </div>
      {err ? <ErrorPanel error={err} /> : null}
      {code ? <KoppelcodeKaart code={code} adres={registry.find((r) => r.app === code.app_id)} onVerlopen={() => undefined} gekoppeld={gekoppeld} /> : null}
      {token ? (
        <div className="flex flex-col gap-3 rounded-lg border-2 border-border-strong p-4" data-testid="enrollment-token">
          <p>
            Vul deze drie omgevingsvariabelen in bij de app: <strong>TrueNAS → Apps → {token.app_id} → Bewerken → Omgevingsvariabelen</strong>, en
            klik op Opslaan. Geen YAML, geen terminal.
          </p>
          <KopieerVeld label="HUB_URL" waarde={hubUrl} testId="env-hub-url" />
          {localhost ? (
            <Melding soort="info">
              <p>Dit adres is localhost: dat werkt niet vanuit een andere container. Open de Hub via het NAS-adres en maak dan een nieuw token.</p>
            </Melding>
          ) : null}
          <KopieerVeld label="HUB_ENROLLMENT_TOKEN" waarde={token.enrollment_token} testId="env-token" />
          <KopieerVeld label="HUB_KEY_FINGERPRINT" waarde={token.keyset_fingerprint} testId="env-fingerprint" />
          <p className="text-sm">
            Dit token zie je maar één keer. Het werkt één keer en verloopt om {formatTime(token.verloopt_op)} (60 minuten).
          </p>
        </div>
      ) : null}
    </section>
  );
}

function laatsteContact(d: Dienst): string | null {
  const used = d.tokens.filter((t) => t.geldig && t.laatst_gebruikt).map((t) => t.laatst_gebruikt!).sort();
  return used.length ? used[used.length - 1]! : null;
}

/** C-41a DienstKaart: neutraal "Gekoppeld" (nooit groen), rotatie, ontkoppelen, intrekken met getypte app-id. */
function DienstKaart({ d, admin, onWijziging, statusUrl }: { d: Dienst; admin: boolean; onWijziging: () => void; statusUrl: string | null }) {
  const exec = d.app_id === EXECUTOR;
  const actief = d.status === "active";
  const [rotOpen, setRotOpen] = useState(false);
  const [ontkoppel, setOntkoppel] = useState(false);
  const [intrek, setIntrek] = useState(false);
  const [typed, setTyped] = useState("");
  const rot = useAction();
  const unlink = useAction();
  const revoke = useAction();
  const confirm = useAction();
  const token = d.tokens.filter((t) => t.geldig).sort((a, b) => Date.parse(b.aangemaakt) - Date.parse(a.aangemaakt))[0];
  const contact = laatsteContact(d);
  const kandidaat = d.truenas_app.gemeten_kandidaten?.[0];
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-card p-4" data-testid={`dienst-${d.app_id}`} aria-labelledby={`dienst-${d.id}-titel`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`dienst-${d.id}-titel`} className="[overflow-wrap:anywhere]">
          {d.app_id}
        </h3>
        <div className="flex flex-wrap gap-2">
          {actief ? <StatusBadge view={{ tone: "neutral", label: "Gekoppeld", icon: "gekoppeld" }} /> : <StatusBadge view={{ tone: "neutral", label: "Ingetrokken", icon: "ingetrokken" }} />}
          {actief && d.rotatie.aangevraagd_op ? <StatusBadge view={{ tone: "info", label: "Rotatie aangevraagd" }} testId="rotatie-aangevraagd" /> : null}
        </div>
      </div>
      {actief ? <p className="text-sm">‘Gekoppeld’ zegt alleen dat de dienst een geldige sleutel heeft. Of hij gezond is, zie je bij Apps.</p> : null}
      <dl className="kv">
        <dt>App-id</dt>
        <dd>
          <code>{d.app_id}</code>
        </dd>
        <dt>Versie</dt>
        <dd>{d.version ?? "onbekend"}</dd>
        <dt>Gekoppeld</dt>
        <dd>
          {formatDate(d.enrolled_at)} via {d.enrolled_via === "token" ? "enrollment-token" : d.enrolled_via === "koppelcode" ? "koppelcode" : d.enrolled_via}
        </dd>
        <dt>Laatste contact</dt>
        <dd>{contact ? `${formatDateTime(contact)} (${formatRelative(contact)})` : "nog geen"}</dd>
        <dt>Token</dt>
        <dd>
          {token ? (
            <>
              <code>••••{token.laatste4}</code> · {tokenLeeftijd(d.rotatie.token_leeftijd_dagen)}
            </>
          ) : (
            "geen geldig token"
          )}
        </dd>
        <dt>TrueNAS-app</dt>
        <dd>
          {d.truenas_app.bevestigd ? (
            <>
              <code>{d.truenas_app.naam}</code> (bevestigd)
            </>
          ) : kandidaat ? (
            <span className="flex flex-wrap items-center gap-2">
              gemeten: <code>{kandidaat}</code>
              {admin && actief ? (
                <Button size="klein" bezig={confirm.busy} onClick={async () => (await confirm.run(`/api/v1/services/${d.id}/truenas-app`, { method: "PUT", body: { app_name: kandidaat } })) && onWijziging()}>
                  Bevestigen<span className="sr-only">: {kandidaat}</span>
                </Button>
              ) : null}
            </span>
          ) : (
            "niet gemeten"
          )}
        </dd>
      </dl>
      {confirm.error ? <ErrorPanel error={confirm.error} /> : null}
      {exec ? (
        <p className="text-sm">
          Schrijfsleutel: alleen op de executorpagina; de Hub ziet hem nooit.{" "}
          {statusUrl ? (
            <a href={statusUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1">
              Executorpagina openen <SquareArrowOutUpRight aria-hidden="true" className="size-4" />
              <span className="sr-only">(opent in een nieuw tabblad)</span>
            </a>
          ) : null}
        </p>
      ) : null}
      {actief && d.rotatie.aanbevolen && !d.rotatie.aangevraagd_op ? (
        <Melding soort="info">
          <p>Token ouder dan 180 dagen. We raden aan rotatie aan te vragen. De Hub roteert nooit zelf en de AI kan het niet aanvragen.</p>
        </Melding>
      ) : null}
      {admin && actief ? (
        <div className="flex flex-wrap gap-2">
          {!exec ? (
            <Button onClick={() => setRotOpen(true)} uit={Boolean(d.rotatie.aangevraagd_op)} aria-describedby={d.rotatie.aangevraagd_op ? `rot-${d.id}` : undefined}>
              <KeyRound aria-hidden="true" />
              Rotatie aanvragen<span className="sr-only">: {d.app_id}</span>
            </Button>
          ) : null}
          {!exec ? (
            <Button onClick={() => setOntkoppel((x) => !x)} aria-expanded={ontkoppel}>
              <Unlink aria-hidden="true" />
              Ontkoppelen…<span className="sr-only">: {d.app_id}</span>
            </Button>
          ) : null}
          <Button variant="gevaar" onClick={() => setIntrek((x) => !x)} aria-expanded={intrek}>
            <ShieldX aria-hidden="true" />
            Intrekken…<span className="sr-only">: {d.app_id}</span>
          </Button>
        </div>
      ) : null}
      {d.rotatie.aangevraagd_op ? (
        <p id={`rot-${d.id}`} className="text-sm">
          Rotatie aangevraagd om {formatDateTime(d.rotatie.aangevraagd_op)}; de dienst roteert bij zijn volgende aanroep.
        </p>
      ) : null}
      <BevestigDialoog
        open={rotOpen}
        onOpenChange={setRotOpen}
        titel={`Rotatie aanvragen voor ${d.app_id}?`}
        bevestig="Rotatie aanvragen"
        onBevestig={async () => (await rot.run(`/api/v1/services/${d.id}/rotate`)) && onWijziging()}
      >
        <p>De dienst krijgt bij zijn volgende aanroep het verzoek om zelf een nieuw token te maken. Er is geen onderbreking. Je ziet geen token.</p>
      </BevestigDialoog>
      {rot.error ? <ErrorPanel error={rot.error} /> : null}
      {ontkoppel ? (
        <div className="flex flex-col gap-3 rounded-lg border-2 border-border-strong p-3" data-testid="ontkoppel-blok">
          <p>
            <strong>Ontkoppelen {d.app_id}?</strong> De Hub vraagt de dienst om de koppeling te wissen en trekt daarna de registratie in. De dienst
            houdt zijn eigen data. Opnieuw koppelen kan daarna alleen via deze pagina.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="gevaar" bezig={unlink.busy} onClick={async () => (await unlink.run(`/api/v1/services/${d.id}/unlink`)) && onWijziging()} data-testid="ontkoppelen-bevestigen">
              {d.app_id} ontkoppelen
            </Button>
            <Button onClick={() => setOntkoppel(false)}>Annuleren</Button>
          </div>
          {unlink.error?.code === "service_address_unknown" ? (
            <Melding soort="onbekend" titel="Ontkoppelen kan niet">
              <p>Het adres van deze dienst is niet gemeten. Vernieuw de inventaris of trek de registratie alleen in.</p>
            </Melding>
          ) : unlink.error ? (
            <ErrorPanel
              error={unlink.error}
              title="Ontkoppelen is mislukt"
              onRetry={() => void unlink.run(`/api/v1/services/${d.id}/unlink`).then((r) => r && onWijziging())}
            />
          ) : null}
          {unlink.error && unlink.error.status === 502 ? <p className="text-sm">De dienst is niet bereikbaar of weigerde; er is niets ontkoppeld en niets ingetrokken.</p> : null}
        </div>
      ) : null}
      {intrek ? (
        <form
          className="flex flex-col gap-3 rounded-lg border-2 border-down p-3"
          onSubmit={async (e) => {
            e.preventDefault();
            if (typed !== d.app_id) return;
            if (await revoke.run(`/api/v1/services/${d.id}/revoke`)) {
              setIntrek(false);
              onWijziging();
            }
          }}
          data-testid="intrek-blok"
        >
          <p>
            <strong>Registratie intrekken?</strong> Alle tokens van {d.app_id} worden direct ongeldig. Dit is onomkeerbaar zonder opnieuw te koppelen.
          </p>
          <Field id={`intrek-${d.id}`} label={`Typ ${d.app_id} om te bevestigen.`}>
            {(a) => <input {...a} value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" autoCapitalize="none" />}
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="gevaar" uit={typed !== d.app_id} aria-describedby={`intrek-reden-${d.id}`} bezig={revoke.busy} data-testid="intrekken-bevestigen">
              Registratie intrekken
            </Button>
            <Button onClick={() => setIntrek(false)}>Annuleren</Button>
          </div>
          <p id={`intrek-reden-${d.id}`} className="help">
            {typed !== d.app_id ? "Typ eerst de app-id om te bevestigen." : ""}
          </p>
          {revoke.error ? <ErrorPanel error={revoke.error} /> : null}
        </form>
      ) : null}
      {!actief && admin ? (
        <p>
          <a href="#dienst-koppelen" className={buttonVariants({ variant: "secundair" })}>
            <RotateCw aria-hidden="true" />
            Opnieuw koppelen
          </a>
        </p>
      ) : null}
    </article>
  );
}

export function DienstenScreen() {
  const role = useRole();
  const admin = hasRole(role, "admin");
  const op = hasRole(role, "operator");
  const services = useApi<{ items: Dienst[]; inventaris: { status: string; observed_at: string | null } }>(op ? "/api/v1/services" : null);
  const keyset = useApi<Keyset>("/api/v1/auth/keyset");
  const registry = useApi<{ items: RegistryItem[] }>("/api/v1/registry/services");
  const [toonIngetrokken, setToonIngetrokken] = useState(false);
  const reload = services.reload;
  const items = services.data?.items ?? [];
  const actief = items.filter((d) => d.status === "active");
  const ingetrokken = items.filter((d) => d.status !== "active");
  const zichtbaar = toonIngetrokken ? items : actief;
  return (
    <>
      <InstellingenKop
        titel="Diensten"
        intro="Eigen diensten koppelen aan de Hub: elke dienst krijgt een eigen sleutel. Het register toont alleen de laatste 4 tekens van een token."
        actions={
          admin ? (
            <a href="#dienst-koppelen" className={buttonVariants({ variant: "primair" })}>
              <Link2 aria-hidden="true" />
              Dienst koppelen
            </a>
          ) : null
        }
      />
      <div className="stack">
        {keyset.data ? <Vingerafdruk ks={keyset.data} /> : keyset.error ? <ErrorPanel error={keyset.error} alert={false} /> : <Loading />}
        {!admin ? <RolMelding>Je kijkt als {ROLE_LABEL[role ?? "viewer"]}: koppelen, rotatie, ontkoppelen en intrekken kan alleen een beheerder.</RolMelding> : null}
        {admin ? <Koppelen onNieuw={reload} diensten={items} registry={registry.data?.items ?? []} /> : null}
        <section aria-labelledby="register-titel" className="flex flex-col gap-3" data-testid="dienstenregister">
          <h2 id="register-titel">Gekoppelde diensten</h2>
          {services.error ? <ErrorPanel error={services.error} onRetry={() => void services.reload()} alert={false} /> : null}
          {op && !services.data && services.loading ? <Loading regels={4} /> : null}
          {!op ? <p>Het register is zichtbaar vanaf de rol operator.</p> : null}
          {services.data && !actief.length ? (
            <p>
              Nog geen diensten gekoppeld. Een dienst koppelen geeft hem een eigen sleutel voor de Hub.{" "}
              {admin ? <a href="#dienst-koppelen">Dienst koppelen</a> : null}
            </p>
          ) : null}
          {ingetrokken.length ? (
            <label className="keuze w-fit">
              <input type="checkbox" checked={toonIngetrokken} onChange={(e) => setToonIngetrokken(e.target.checked)} />
              Ingetrokken diensten tonen ({ingetrokken.length})
            </label>
          ) : null}
          <div className="grid items-start gap-4 xl:grid-cols-2">
            {zichtbaar.map((d) => (
              <DienstKaart key={d.id} d={d} admin={admin} onWijziging={() => void reload()} statusUrl={registry.data?.items.find((r) => r.app === d.app_id)?.basis_url ?? null} />
            ))}
          </div>
          {services.data?.inventaris.status !== "ok" && services.data ? (
            <p className="text-sm">
              De inventaris is niet actueel: adressen van statuspagina&apos;s en TrueNAS-appnamen zijn onbekend. <Link href="/server">Vernieuw de inventaris.</Link>
            </p>
          ) : null}
        </section>
      </div>
    </>
  );
}
