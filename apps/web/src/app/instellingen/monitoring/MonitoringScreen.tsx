"use client";

import { BellOff, CircleSlash, PlugZap, Plus, Send } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Controles, type Controle } from "@/components/Controles";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Field } from "@/components/Field";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { ResponsiveList } from "@/components/ResponsiveList";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatDateTime, formatTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";
import { InstellingenKop } from "../delen";

interface Bron {
  id: string;
  soort: "uptime_kuma" | "beszel";
  naam: string;
  basis_url: string;
  geheim: { soort: string; ingesteld: boolean; laatste4: string | null; gewijzigd_op: string | null };
  identiteit: string | null;
  ingeschakeld: boolean;
  status: { status: "ok" | "fout" | "unknown"; reden: string | null; melding: string; laatste_poging: string | null; laatste_ok: string | null; verouderd: boolean; versie: string | null };
  detail: { monitors?: number; gekoppeld?: number; fouten?: unknown[]; versie?: string } | null;
}

interface Kanaal {
  id: string;
  naam: string;
  basis_url: string;
  token: { ingesteld: boolean; laatste4: string | null };
  min_ernst: string;
  stille_uren: { van: string; tot: string } | null;
  max_per_venster: number;
  venster_s: number;
  ingeschakeld: boolean;
  status: { laatste_status: string; laatste_reden: string | null; melding: string; laatste_op: string | null; gotify_versie: string | null };
  onderdrukt: { aantal: number; sinds: string | null };
}

interface Regel {
  id: string;
  standaard: boolean;
  naam: string;
  metriek: string;
  operator: string;
  drempel: number;
  herstel_drempel: number | null;
  duur_s: number;
  herstel_duur_s: number;
  ernst: string;
  ingeschakeld: boolean;
  gedempt_tot: string | null;
}

interface Melding_ {
  id: string;
  titel: string;
  ernst: string;
  status: string;
  reden: string | null;
  aangemaakt_op: string;
  verzonden_op: string | null;
  bron: string;
}

interface OutOfBand {
  hub_in_meldpad: boolean;
  uitleg: string;
  uptime_kuma: { id: string; naam: string; status: string; laatst_ok: string | null; locatie: string }[];
  hub_uitval: { status: string; tekst: string; bewaakt: Record<string, boolean> };
  apps_zonder_kuma_monitor: string[];
  kuma_meldt_via_gotify: string;
  volledige_nas_uitval: { status: string; gedekt: boolean; tekst: string };
  laatste_bevestiging: { getest_op: string; door?: string; externe_host?: boolean } | null;
}

const SOORT: Record<string, string> = { uptime_kuma: "Uptime Kuma", beszel: "Beszel" };
const ERNST: Record<string, string> = { info: "Info", waarschuwing: "Middel", kritiek: "Kritiek" };
const MELDING_STATUS: Record<string, string> = {
  wachtrij: "In de wachtrij",
  uitgesteld: "Uitgesteld",
  verzonden: "Door Gotify aangenomen",
  onderdrukt: "Onderdrukt (rate-limit)",
  mislukt: "Mislukt",
  dead_letter: "Opgegeven (dead-letter)",
};

/** C-60 BronKaart: soort + versie, adres, sleutel ••••4, uitgelezen-pil (neutraal) of Storing met reden. */
function BronKaart({ b, admin, onWijziging }: { b: Bron; admin: boolean; onWijziging: () => void }) {
  const test = useAction<{ resultaat: Record<string, unknown> }>();
  const [nieuw, setNieuw] = useState("");
  const patch = useAction();
  const fout = b.status.status === "fout";
  return (
    <article className={`flex min-w-0 flex-col gap-3 rounded-lg bg-card p-4 ${fout ? "border-2 border-down" : "border border-border"}`} data-testid={`bron-${b.naam}`} aria-labelledby={`bron-${b.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`bron-${b.id}`}>
          {b.naam} <span className="text-base font-normal">({SOORT[b.soort]}{b.status.versie ? ` ${b.status.versie}` : ""})</span>
        </h3>
        {fout ? (
          <StatusBadge view={{ tone: "down", label: "Uitlezen mislukt" }} />
        ) : b.status.status === "ok" && !b.status.verouderd ? (
          <StatusBadge view={{ tone: "neutral", label: `Uitgelezen om ${formatTime(b.status.laatste_ok)}`, icon: "geslaagd" }} />
        ) : (
          <StatusBadge view={{ tone: b.status.laatste_ok ? "stale" : "unknown", label: b.status.laatste_ok ? "Verouderd" : "Nog niet uitgelezen" }} />
        )}
      </div>
      {fout ? (
        <p className="text-sm" data-testid="bron-reden">
          {b.status.melding || b.status.reden} {b.status.laatste_ok ? `Laatst gelukt om ${formatDateTime(b.status.laatste_ok)}.` : "Nog nooit gelukt."} Metingen uit deze bron zijn nu onbekend.
        </p>
      ) : null}
      <dl className="kv">
        <dt>Adres</dt>
        <dd>
          <code>{b.basis_url}</code>
        </dd>
        <dt>{b.soort === "beszel" ? "Readonly-gebruiker" : "API-sleutel"}</dt>
        <dd>
          {b.soort === "beszel" ? `${b.identiteit ?? "?"} · wachtwoord ` : ""}
          {b.geheim.ingesteld ? <code>••••{b.geheim.laatste4}</code> : "niet ingesteld"}
        </dd>
        {b.soort === "uptime_kuma" && b.detail?.monitors !== undefined ? (
          <>
            <dt>Monitors</dt>
            <dd>
              {b.detail.monitors} monitors · {b.detail.gekoppeld ?? 0} gekoppeld aan een app · {(b.detail.monitors ?? 0) - (b.detail.gekoppeld ?? 0)} niet gekoppeld
            </dd>
          </>
        ) : null}
      </dl>
      {admin ? (
        <div className="flex flex-wrap gap-2">
          <Button bezig={test.busy} onClick={async () => (await test.run(`/api/v1/monitoring/sources/${b.id}/test`)) && onWijziging()}>
            <PlugZap aria-hidden="true" />
            Nu uitlezen<span className="sr-only">: {b.naam}</span>
          </Button>
        </div>
      ) : null}
      {test.error ? <ErrorPanel error={test.error} /> : null}
      {admin && fout && (b.status.reden ?? "").includes("credential") ? (
        <form
          className="flex flex-col gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            const body = b.soort === "beszel" ? { wachtwoord: nieuw } : { api_key: nieuw };
            if (await patch.run(`/api/v1/monitoring/sources/${b.id}`, { method: "PATCH", body })) {
              setNieuw("");
              onWijziging();
            }
          }}
        >
          <Field id={`vervang-${b.id}`} label={b.soort === "beszel" ? "Nieuw wachtwoord" : "Nieuwe API-sleutel"}>
            {(a) => <input {...a} type="password" autoComplete="new-password" value={nieuw} onChange={(e) => setNieuw(e.target.value)} />}
          </Field>
          <div>
            <Button type="submit" variant="primair" bezig={patch.busy}>
              {b.soort === "beszel" ? "Wachtwoord vervangen" : "Sleutel vervangen"}
            </Button>
          </div>
          {patch.error ? <ErrorPanel error={patch.error} /> : null}
        </form>
      ) : null}
    </article>
  );
}

function BronToevoegen({ onKlaar }: { onKlaar: () => void }) {
  const [soort, setSoort] = useState<"" | "uptime_kuma" | "beszel">("");
  const [f, setF] = useState({ naam: "", basis_url: "", api_key: "", status_paginas: "", identiteit: "", wachtwoord: "", nas_systeem: "" });
  const create = useAction<{ id: string }>();
  const test = useAction<{ resultaat: { status?: string; reden?: string } ; bron: Bron }>();
  const [uitkomst, setUitkomst] = useState<Bron | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!soort) return;
    const body =
      soort === "uptime_kuma"
        ? { soort, naam: f.naam, basis_url: f.basis_url.trim(), ...(f.api_key ? { api_key: f.api_key } : {}), status_paginas: f.status_paginas.split(",").map((s) => s.trim()).filter(Boolean) }
        : { soort, naam: f.naam, basis_url: f.basis_url.trim(), identiteit: f.identiteit, wachtwoord: f.wachtwoord, ...(f.nas_systeem ? { nas_systeem: f.nas_systeem } : {}) };
    const src = await create.run("/api/v1/monitoring/sources", { body });
    if (!src) return;
    // Opslaan en testen: de bron blijft opgeslagen, ook als de test mislukt (de reden staat in de bronkaart).
    const t = await test.run(`/api/v1/monitoring/sources/${src.id}/test`);
    setUitkomst(t?.bron ?? null);
    setF({ naam: "", basis_url: "", api_key: "", status_paginas: "", identiteit: "", wachtwoord: "", nas_systeem: "" });
    onKlaar();
  };
  return (
    <form className="form" onSubmit={(e) => void submit(e)} data-testid="bron-toevoegen">
      <fieldset className="flex flex-col gap-2 border-0 p-0">
        <legend className="mb-1">Soort bron</legend>
        {(["uptime_kuma", "beszel"] as const).map((s) => (
          <label key={s} className="keuze">
            <input type="radio" name="bron-soort" value={s} checked={soort === s} onChange={() => setSoort(s)} />
            {SOORT[s]}
          </label>
        ))}
      </fieldset>
      {soort ? (
        <>
          <Field id="bron-naam" label="Naam">
            {(a) => <input {...a} value={f.naam} onChange={(e) => setF({ ...f, naam: e.target.value })} required />}
          </Field>
          <Field id="bron-adres" label="Adres" help="Vorm: http(s)://<adres>:<poort>. Geen localhost; de Hub draait in een eigen container.">
            {(a) => <input {...a} type="url" value={f.basis_url} onChange={(e) => setF({ ...f, basis_url: e.target.value })} required />}
          </Field>
          {soort === "uptime_kuma" ? (
            <>
              <Field id="bron-key" label="API-sleutel (voor /metrics)" help="Maak in Uptime Kuma onder Instellingen → API-sleutels. Je ziet hem daarna alleen nog als ••••4.">
                {(a) => <input {...a} type="password" autoComplete="new-password" value={f.api_key} onChange={(e) => setF({ ...f, api_key: e.target.value })} />}
              </Field>
              <Field id="bron-paginas" label="Statuspagina's (optioneel)" help="Slugs gescheiden door komma's.">
                {(a) => <input {...a} value={f.status_paginas} onChange={(e) => setF({ ...f, status_paginas: e.target.value })} />}
              </Field>
            </>
          ) : (
            <>
              <Field id="bron-gebruiker" label="Readonly-gebruiker (e-mailadres)">
                {(a) => <input {...a} autoComplete="off" value={f.identiteit} onChange={(e) => setF({ ...f, identiteit: e.target.value })} required />}
              </Field>
              <Field id="bron-wachtwoord" label="Wachtwoord">
                {(a) => <input {...a} type="password" autoComplete="new-password" value={f.wachtwoord} onChange={(e) => setF({ ...f, wachtwoord: e.target.value })} required />}
              </Field>
              <Field id="bron-systeem" label="NAS-systeem (optioneel)" help="Het Beszel-systeem van de NAS; de mini-pc telt nooit mee (D10).">
                {(a) => <input {...a} value={f.nas_systeem} onChange={(e) => setF({ ...f, nas_systeem: e.target.value })} />}
              </Field>
            </>
          )}
        </>
      ) : null}
      {create.error ? <ErrorPanel error={create.error} title="Opslaan mislukt" /> : null}
      <div>
        <Button type="submit" variant="primair" uit={!soort} aria-describedby="bron-uitleg" bezig={create.busy || test.busy} data-testid="opslaan-en-testen">
          <PlugZap aria-hidden="true" />
          Opslaan en testen
        </Button>
        <p id="bron-uitleg" className="help">
          De Hub slaat eerst op en test daarna. Mislukt de test, dan blijft de bron opgeslagen met de reden.
        </p>
      </div>
      {uitkomst ? (
        <p role="status" data-testid="bron-testuitkomst">
          {uitkomst.status.status === "ok" ? `Opgeslagen en uitgelezen om ${formatTime(uitkomst.status.laatste_ok)}.` : `Opgeslagen; uitlezen mislukt: ${uitkomst.status.melding || uitkomst.status.reden || "onbekend"}.`}
        </p>
      ) : null}
    </form>
  );
}

function KanaalKaart({ k, admin, onWijziging }: { k: Kanaal; admin: boolean; onWijziging: () => void }) {
  const test = useAction<{ verzonden: boolean; reden: string | null; melding: string }>();
  const [token, setToken] = useState("");
  const patch = useAction();
  const gestopt = k.status.laatste_reden === "token_geweigerd";
  return (
    <article className={`flex min-w-0 flex-col gap-3 rounded-lg bg-card p-4 ${gestopt ? "border-2 border-down" : "border border-border"}`} data-testid={`kanaal-${k.naam}`} aria-labelledby={`kanaal-${k.id}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`kanaal-${k.id}`}>
          {k.naam} <span className="text-base font-normal">(Gotify{k.status.gotify_versie ? ` ${k.status.gotify_versie}` : ""})</span>
        </h3>
        {gestopt ? <StatusBadge view={{ tone: "down", label: "Kanaal gestopt" }} /> : <StatusBadge view={{ tone: "neutral", label: k.ingeschakeld ? "Aan" : "Uit", icon: "aan" }} />}
      </div>
      {gestopt ? <p className="text-sm">Kanaal gestopt: Gotify weigerde het token. Vul een nieuw token in.</p> : null}
      <dl className="kv">
        <dt>Adres</dt>
        <dd>
          <code>{k.basis_url}</code>
        </dd>
        <dt>App-token</dt>
        <dd>{k.token.ingesteld ? <code>••••{k.token.laatste4}</code> : "niet ingesteld"}</dd>
        <dt>Vanaf ernst</dt>
        <dd>{ERNST[k.min_ernst] ?? k.min_ernst}</dd>
        <dt>Stille uren</dt>
        <dd>{k.stille_uren ? `${k.stille_uren.van}–${k.stille_uren.tot} (kritiek gaat altijd door)` : "geen"}</dd>
        <dt>Hoogstens</dt>
        <dd>
          {k.max_per_venster} per {Math.round(k.venster_s / 60)} min, daarna één samenvatting
          {k.onderdrukt.aantal ? ` · nu ${k.onderdrukt.aantal} onderdrukt` : ""}
        </dd>
      </dl>
      {admin ? (
        <div>
          <Button bezig={test.busy} onClick={async () => (await test.run(`/api/v1/notifications/channels/${k.id}/test`)) && onWijziging()} data-testid="testmelding">
            <Send aria-hidden="true" />
            Testmelding versturen<span className="sr-only">: {k.naam}</span>
          </Button>
        </div>
      ) : null}
      {test.result ? (
        <p role="status" data-testid="testmelding-uitkomst">
          {test.result.verzonden
            ? `Om ${formatTime(new Date().toISOString())} door Gotify aangenomen. Of hij op je telefoon aankwam, kan de Hub niet zien.`
            : `Niet aangenomen: ${test.result.melding || test.result.reden}.`}
        </p>
      ) : null}
      {test.error ? <ErrorPanel error={test.error} /> : null}
      {admin && gestopt ? (
        <form
          className="flex flex-col gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            if (await patch.run(`/api/v1/notifications/channels/${k.id}`, { method: "PATCH", body: { token } })) {
              setToken("");
              onWijziging();
            }
          }}
        >
          <Field id={`token-${k.id}`} label="Nieuw applicatietoken">
            {(a) => <input {...a} type="password" autoComplete="new-password" value={token} onChange={(e) => setToken(e.target.value)} />}
          </Field>
          <div>
            <Button type="submit" variant="primair" bezig={patch.busy}>
              Token vervangen
            </Button>
          </div>
          {patch.error ? <ErrorPanel error={patch.error} /> : null}
        </form>
      ) : null}
    </article>
  );
}

function KanaalToevoegen({ onKlaar }: { onKlaar: () => void }) {
  const [f, setF] = useState({ naam: "", basis_url: "", token: "", min_ernst: "info" });
  const create = useAction();
  return (
    <form
      className="form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (await create.run("/api/v1/notifications/channels", { body: { naam: f.naam, basis_url: f.basis_url.trim(), token: f.token, min_ernst: f.min_ernst } })) {
          setF({ naam: "", basis_url: "", token: "", min_ernst: "info" });
          onKlaar();
        }
      }}
      data-testid="kanaal-toevoegen"
    >
      <Field id="kanaal-naam" label="Naam">
        {(a) => <input {...a} value={f.naam} onChange={(e) => setF({ ...f, naam: e.target.value })} required />}
      </Field>
      <Field id="kanaal-adres" label="Adres van Gotify" help="Vorm: http(s)://<adres>:<poort>.">
        {(a) => <input {...a} type="url" value={f.basis_url} onChange={(e) => setF({ ...f, basis_url: e.target.value })} required />}
      </Field>
      <Field id="kanaal-token" label="Applicatietoken" help="Een applicatietoken uit Gotify (nooit een client-token).">
        {(a) => <input {...a} type="password" autoComplete="new-password" value={f.token} onChange={(e) => setF({ ...f, token: e.target.value })} required />}
      </Field>
      <Field id="kanaal-ernst" label="Vanaf ernst">
        {(a) => (
          <select {...a} value={f.min_ernst} onChange={(e) => setF({ ...f, min_ernst: e.target.value })}>
            <option value="info">Info</option>
            <option value="waarschuwing">Middel</option>
            <option value="kritiek">Kritiek</option>
          </select>
        )}
      </Field>
      {create.error ? <ErrorPanel error={create.error} title="Opslaan mislukt" /> : null}
      <div>
        <Button type="submit" variant="primair" bezig={create.busy}>
          <Plus aria-hidden="true" />
          Kanaal toevoegen
        </Button>
      </div>
    </form>
  );
}

function OutOfBandKaart({ o, admin, onWijziging }: { o: OutOfBand; admin: boolean; onWijziging: () => void }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ kuma_meldt_hub_uitval: false, kuma_gotify_test_ontvangen: false, externe_host: false, notitie: "" });
  const save = useAction();
  const bewaakt = o.hub_uitval.status === "kuma_bewaakt_hub" ? "ja" : o.hub_uitval.status === "hiaat" ? "nee" : "onbekend";
  const items: Controle[] = [
    { id: "meldpad", naam: "De Hub zit niet in het meldpad van Uptime Kuma", uitkomst: o.hub_in_meldpad ? "fout" : "ok", detail: o.uitleg },
    { id: "bewaakt", naam: "Uptime Kuma bewaakt de Hub", uitkomst: bewaakt === "ja" ? "ok" : bewaakt === "nee" ? "fout" : "onbekend", detail: o.hub_uitval.tekst },
    {
      id: "gotify",
      naam: "Uptime Kuma meldt via Gotify",
      uitkomst: "onbekend",
      detail:
        o.kuma_meldt_via_gotify === "handmatig_bevestigd" && o.laatste_bevestiging
          ? `Handmatig bevestigd op ${formatDateTime(o.laatste_bevestiging.getest_op)}; niet door de Hub gevalideerd.`
          : "Niet te lezen via /metrics; leg een handmatige test vast.",
    },
    {
      id: "nas",
      naam: "Als de hele NAS uitvalt",
      uitkomst: "onbekend",
      detail:
        o.volledige_nas_uitval.status === "niet_gedekt" && o.uptime_kuma.length
          ? "Dan meldt niemand iets: Uptime Kuma en Gotify draaien op dezelfde NAS. " + o.volledige_nas_uitval.tekst
          : o.volledige_nas_uitval.tekst,
    },
  ];
  return (
    <section className="card" aria-labelledby="oob-titel" data-testid="out-of-band">
      <h2 id="oob-titel">Meldt er nog iets als de Hub uitvalt?</h2>
      <Controles items={items} />
      {o.apps_zonder_kuma_monitor.length ? <p className="text-sm">Apps zonder Uptime Kuma-monitor: {o.apps_zonder_kuma_monitor.join(", ")}.</p> : null}
      {admin ? (
        <>
          <Button className="w-fit" onClick={() => setOpen((x) => !x)} aria-expanded={open}>
            Handmatige test vastleggen
          </Button>
          {open ? (
            <form
              className="form"
              onSubmit={async (e) => {
                e.preventDefault();
                if (await save.run("/api/v1/monitoring/out-of-band/bevestiging", { body: { ...f, getest_op: new Date().toISOString() } })) {
                  setOpen(false);
                  onWijziging();
                }
              }}
            >
              {(
                [
                  ["kuma_meldt_hub_uitval", "In Uptime Kuma gezien: een monitor op de Hub gaf een melding"],
                  ["kuma_gotify_test_ontvangen", "De testmelding van Uptime Kuma via Gotify kwam aan op de telefoon"],
                  ["externe_host", "Uptime Kuma en Gotify draaien op een host buiten deze NAS"],
                ] as const
              ).map(([k, l]) => (
                <label key={k} className="keuze">
                  <input type="checkbox" checked={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.checked })} />
                  {l}
                </label>
              ))}
              <Field id="oob-notitie" label="Notitie (optioneel)">
                {(a) => <input {...a} value={f.notitie} onChange={(e) => setF({ ...f, notitie: e.target.value })} maxLength={500} />}
              </Field>
              {save.error ? <ErrorPanel error={save.error} /> : null}
              <div>
                <Button type="submit" variant="primair" bezig={save.busy}>
                  Vastleggen
                </Button>
              </div>
              <p className="help">Dit wordt een auditrecord met status ‘handmatig bevestigd’, nooit ‘gevalideerd’.</p>
            </form>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

export function MonitoringScreen() {
  const role = useRole();
  const op = hasRole(role, "operator");
  const admin = hasRole(role, "admin");
  const bronnen = useApi<{ items: Bron[] }>(op ? "/api/v1/monitoring/sources" : null, 60_000);
  const regels = useApi<{ items: Regel[] }>("/api/v1/alerts/rules");
  const kanalen = useApi<{ items: Kanaal[] }>(op ? "/api/v1/notifications/channels" : null, 60_000);
  const oob = useApi<OutOfBand>("/api/v1/monitoring/out-of-band", 60_000);
  const log = useApi<{ items: Melding_[] }>(op ? "/api/v1/notifications?limit=20" : null, 60_000);
  const demp = useAction();
  const [bronOpen, setBronOpen] = useState(false);
  const [kanaalOpen, setKanaalOpen] = useState(false);
  return (
    <>
      <InstellingenKop titel="Monitoring en meldingen" intro="Bronnen die de Hub alleen leest (Uptime Kuma, Beszel), alertregels en meldingskanalen (Gotify)." />
      {!op ? <RolMelding>Bronnen en kanalen zijn zichtbaar vanaf de rol operator; wijzigen kan alleen een beheerder.</RolMelding> : null}
      <div className="stack">
        {op ? (
          <section aria-labelledby="bronnen-titel" className="flex flex-col gap-3" data-testid="monitoringbronnen">
            <h2 id="bronnen-titel">Monitoringbronnen</h2>
            {bronnen.error ? <ErrorPanel error={bronnen.error} alert={false} /> : null}
            {!bronnen.data && bronnen.loading ? <Loading /> : null}
            {bronnen.data && !bronnen.data.items.length ? <p>Nog geen monitoringbron. Zonder bron is de gezondheid van apps van buitenaf onbekend.</p> : null}
            <div className="grid items-start gap-4 xl:grid-cols-2">
              {bronnen.data?.items.map((b) => (
                <BronKaart key={b.id} b={b} admin={admin} onWijziging={() => void bronnen.reload()} />
              ))}
            </div>
            {admin ? (
              <div className="card">
                <Button className="w-fit" onClick={() => setBronOpen((x) => !x)} aria-expanded={bronOpen}>
                  <Plus aria-hidden="true" />
                  Bron toevoegen
                </Button>
                {bronOpen ? <BronToevoegen onKlaar={() => void bronnen.reload()} /> : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <section className="card" aria-labelledby="regels-titel" data-testid="alertregels">
          <h2 id="regels-titel">Alertregels</h2>
          {regels.error ? <ErrorPanel error={regels.error} alert={false} /> : null}
          {regels.data && !regels.data.items.length ? <p>Nog geen alertregels.</p> : null}
          {regels.data?.items.length ? (
            <ResponsiveList
              items={regels.data.items}
              label="Alertregels"
              // Vijf kolommen passen naast de subnavigatie van Instellingen pas vanaf 1280 (op 1024: 42 px overloop).
              tabelVanaf={1280}
              sleutel={(r) => r.id}
              kolommen={[
                {
                  kop: "Regel",
                  cel: (r) => (
                    <span className="flex flex-col">
                      <strong>{r.naam}</strong>
                      <span className="text-sm">
                        <code>{r.metriek}</code>
                        {r.standaard ? " · standaardregel" : ""}
                      </span>
                    </span>
                  ),
                },
                { kop: "Drempel", cel: (r) => `${r.operator} ${r.drempel}${r.herstel_drempel !== null ? ` (herstel ${r.herstel_drempel})` : ""}` },
                { kop: "Duur", cel: (r) => `${Math.round(r.duur_s / 60)} min · herstel ${Math.round(r.herstel_duur_s / 60)} min` },
                { kop: "Ernst", cel: (r) => ERNST[r.ernst] ?? r.ernst },
                {
                  kop: "Dempen",
                  cel: (r) =>
                    r.gedempt_tot ? (
                      `Gedempt tot ${formatDateTime(r.gedempt_tot)}`
                    ) : op ? (
                      <Button size="klein" bezig={demp.busy} onClick={async () => (await demp.run(`/api/v1/alerts/rules/${r.id}/snooze`, { body: { minuten: 60 } })) && void regels.reload()}>
                        <BellOff aria-hidden="true" />
                        1 uur dempen<span className="sr-only">: {r.naam}</span>
                      </Button>
                    ) : (
                      "—"
                    ),
                },
              ]}
            />
          ) : null}
          {demp.error ? <ErrorPanel error={demp.error} /> : null}
          <p className="text-sm">Regels bewerken kan alleen een beheerder; dat volgt in deze UI later (de API kan het al).</p>
        </section>

        {op ? (
          <section aria-labelledby="kanalen-titel" className="flex flex-col gap-3" id="meldingen" data-testid="meldingskanalen">
            <h2 id="kanalen-titel">Meldingskanalen</h2>
            {kanalen.error ? <ErrorPanel error={kanalen.error} alert={false} /> : null}
            {kanalen.data && !kanalen.data.items.length ? <p>Nog geen meldingskanaal. Zonder kanaal verstuurt de Hub geen meldingen.</p> : null}
            <div className="grid items-start gap-4 xl:grid-cols-2">
              {kanalen.data?.items.map((k) => (
                <KanaalKaart key={k.id} k={k} admin={admin} onWijziging={() => void kanalen.reload()} />
              ))}
            </div>
            {admin ? (
              <div className="card">
                <Button className="w-fit" onClick={() => setKanaalOpen((x) => !x)} aria-expanded={kanaalOpen}>
                  <Plus aria-hidden="true" />
                  Kanaal toevoegen
                </Button>
                {kanaalOpen ? <KanaalToevoegen onKlaar={() => void kanalen.reload()} /> : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {oob.data ? <OutOfBandKaart o={oob.data} admin={admin} onWijziging={() => void oob.reload()} /> : oob.error ? <ErrorPanel error={oob.error} alert={false} /> : null}

        {op ? (
          <section className="card" aria-labelledby="log-titel" data-testid="meldingenlog">
            <h2 id="log-titel">Meldingenlogboek</h2>
            {log.error ? <ErrorPanel error={log.error} alert={false} /> : null}
            {log.data && !log.data.items.length ? <p>Nog geen meldingen verstuurd.</p> : null}
            {log.data?.items.length ? (
              <ResponsiveList
                items={log.data.items}
                label="Meldingenlogboek"
                // Vier kolommen naast de subnavigatie: op 1024 met een breder systeemlettertype (DejaVu in CI) 9 px te breed.
                tabelVanaf={1280}
                sleutel={(m) => m.id}
                kolommen={[
                  { kop: "Wanneer", cel: (m) => formatDateTime(m.aangemaakt_op) },
                  { kop: "Melding", cel: (m) => m.titel },
                  { kop: "Ernst", cel: (m) => ERNST[m.ernst] ?? m.ernst },
                  { kop: "Status", cel: (m) => `${MELDING_STATUS[m.status] ?? m.status}${m.reden ? ` (${m.reden})` : ""}` },
                ]}
              />
            ) : null}
            <p className="flex items-start gap-2 text-sm">
              <CircleSlash aria-hidden="true" className="mt-0.5 size-4" />
              ‘Door Gotify aangenomen’ betekent niet dat hij op je telefoon aankwam: dat kan de Hub niet zien.
            </p>
          </section>
        ) : null}
        {!op ? <Melding soort="info"><p>De out-of-band-kaart hierboven is voor iedereen zichtbaar.</p></Melding> : null}
      </div>
    </>
  );
}
