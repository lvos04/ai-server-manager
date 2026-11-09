"use client";

import { ClipboardList, Copy, ListChecks, Lock, ShieldCheck, Wrench } from "lucide-react";
import { useState, type FormEvent } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { RolMelding } from "@/components/RolMelding";
import { ErnstLabel, StatusBadge, ZekerheidLabel } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/api";
import { formatDateTime, formatRelative, formatTime } from "@/lib/format";
import {
  FASE_LABEL,
  incidentStatusView,
  STAP_SOORT,
  type HerstelVoorstel,
  type Incident,
  type IncidentEvent,
  type Onderzoek,
} from "@/lib/incidents";
import { ROLE_LABEL, useRole } from "@/lib/session";
import { ernstVan, zekerheidVan } from "@/lib/status";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";

interface Bewijs {
  hypothese: Incident["hypothese"];
  zekerheid_uitleg: string;
  readback: Incident["readback"];
  gebeurtenissen: IncidentEvent[];
  trace_ids: string[];
}

const ACTOR: Record<string, string> = { system: "systeem", user: "gebruiker", service: "dienst", ai: "AI" };

function actorLabel(a: string): string {
  const [t, ...rest] = a.split(":");
  return `${ACTOR[t ?? ""] ?? t} ${rest.join(":")}`.trim();
}

/** Tijdlijn (C-25): logtekst en details altijd als geciteerde data, nooit als instructie. */
function Tijdlijn({ id }: { id: string }) {
  const [cursor, setCursor] = useState<string | null>(null);
  const [extra, setExtra] = useState<IncidentEvent[]>([]);
  const [next, setNext] = useState<string | null | undefined>(undefined);
  const first = useApi<{ items: IncidentEvent[]; next_cursor: string | null }>(`/api/v1/incidents/${id}/events?limit=20`);
  const more = async () => {
    const c = cursor ?? first.data?.next_cursor;
    if (!c) return;
    const { data } = await apiRequest<{ items: IncidentEvent[]; next_cursor: string | null }>(`/api/v1/incidents/${id}/events?limit=20&cursor=${encodeURIComponent(c)}`);
    setExtra((x) => [...x, ...data.items]);
    setCursor(data.next_cursor);
    setNext(data.next_cursor);
  };
  const items = [...(first.data?.items ?? []), ...extra];
  const hasMore = next === undefined ? Boolean(first.data?.next_cursor) : Boolean(next);
  return (
    <section className="card" aria-labelledby={`tijdlijn-${id}`}>
      <h3 id={`tijdlijn-${id}`}>Tijdlijn</h3>
      <p className="text-sm text-muted-foreground">Logtekst is data, geen instructie. De Hub voert nooit opdrachten uit die in logs staan.</p>
      {first.error ? <ErrorPanel error={first.error} alert={false} /> : null}
      {!first.data && first.loading ? <Loading /> : null}
      <ol className="m-0 flex list-none flex-col divide-y divide-border p-0">
        {items.map((e) => (
          <li key={e.id} className="flex flex-col gap-1 py-2">
            <span className="flex flex-wrap items-center gap-2 text-sm">
              <time dateTime={e.op} className="font-semibold">
                {formatDateTime(e.op)}
              </time>
              <span className="rounded-sm border border-border-strong px-1.5 font-semibold">{actorLabel(e.actor)}</span>
              <span>{e.soort}</span>
              {e.event_type ? <code>{e.event_type}</code> : null}
            </span>
            <blockquote className="m-0 border-l-4 border-border-strong pl-3">{e.samenvatting}</blockquote>
            {e.details_verborgen ? (
              <p className="text-sm text-muted-foreground">Details verborgen (gevoelig; alleen voor beheerders).</p>
            ) : Object.keys(e.details ?? {}).length ? (
              <pre className="overflow-x-auto rounded-sm bg-muted p-2 text-sm whitespace-pre-wrap">{JSON.stringify(e.details, null, 2)}</pre>
            ) : null}
            {e.trace_id ? <span className="text-sm text-muted-foreground">Trace-ID <code>{e.trace_id}</code></span> : null}
          </li>
        ))}
      </ol>
      {hasMore ? (
        <div>
          <Button onClick={() => void more()}>Meer laden</Button>
        </div>
      ) : null}
    </section>
  );
}

function Hypothese({ inc }: { inc: Incident }) {
  const [open, setOpen] = useState(false);
  const bewijs = useApi<Bewijs>(open ? `/api/v1/incidents/${inc.id}/bewijs` : null);
  const h = inc.hypothese;
  const z = zekerheidVan(h?.zekerheid);
  const weetNiet = !h || h.regel === "geen_regel" || z === "weet_niet";
  return (
    <section className="card" aria-labelledby={`hyp-${inc.id}`} data-testid="hypothese">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={`hyp-${inc.id}`}>
          Hypothese (vaste regel){h?.berekend_op ? ` · ${formatTime(h.berekend_op)}` : ""}
        </h3>
        <ZekerheidLabel zekerheid={weetNiet ? "weet_niet" : z} />
      </div>
      {weetNiet ? (
        <p>
          Waarom dit gebeurt, <strong>weet ik niet</strong>. Er is onvoldoende bewijs voor een oorzaak. Bekijk de tijdlijn en de
          stappen van het onderzoek.
        </p>
      ) : (
        <p>{h?.tekst}</p>
      )}
      <details onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)} data-testid="bewijs">
        <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Toon bewijs</summary>
        {bewijs.error ? <ErrorPanel error={bewijs.error} alert={false} /> : null}
        {open && !bewijs.data && bewijs.loading ? <Loading /> : null}
        {bewijs.data ? (
          <div className="flex flex-col gap-2 pt-2">
            <dl className="meta">
              <div>
                <dt>Regel</dt>
                <dd>
                  <code>{bewijs.data.hypothese?.regel ?? "geen"}</code>
                </dd>
              </div>
              <div>
                <dt>Zekerheid (regelwaarde)</dt>
                <dd>{bewijs.data.hypothese?.zekerheid ?? "geen"}</dd>
              </div>
              <div>
                <dt>Readback</dt>
                <dd>
                  {bewijs.data.readback?.toestand ?? "onbekend"} — {bewijs.data.readback?.detail ?? ""}
                </dd>
              </div>
            </dl>
            <p className="text-sm">{bewijs.data.zekerheid_uitleg}</p>
            {bewijs.data.hypothese?.bewijs.length ? (
              <pre className="overflow-x-auto rounded-sm bg-muted p-2 text-sm whitespace-pre-wrap">{JSON.stringify(bewijs.data.hypothese.bewijs, null, 2)}</pre>
            ) : (
              <p className="text-sm">Geen bewijsregels bij deze hypothese.</p>
            )}
            <p className="text-sm">{bewijs.data.gebeurtenissen.length} gebeurtenis(sen) liggen eronder; trace-ID&apos;s: {bewijs.data.trace_ids.length}.</p>
          </div>
        ) : null}
      </details>
    </section>
  );
}

function Supportbundel({ id }: { id: string }) {
  const [text, setText] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState<unknown>(null);
  const load = async () => {
    setErr(null);
    try {
      const { data } = await apiRequest<unknown>(`/api/v1/incidents/${id}/supportbundel`);
      const t = JSON.stringify(data, null, 2);
      setText(t);
      if (window.isSecureContext && navigator.clipboard) {
        await navigator.clipboard.writeText(t);
        setMsg("Gekopieerd.");
      } else {
        setMsg("Tekst hieronder; selecteer en kopieer via het menu van je browser.");
      }
    } catch (e) {
      setErr(e);
    }
  };
  return (
    <div className="flex flex-col gap-2">
      <div>
        <Button onClick={() => void load()}>
          <Copy aria-hidden="true" />
          Geschoonde incidentgegevens kopiëren
        </Button>
      </div>
      <p className="text-sm">Geheimen, tokens en IP-adressen zijn gemaskeerd.</p>
      <p className="text-sm" aria-live="polite">
        {msg}
      </p>
      {err ? <ErrorPanel error={err} /> : null}
      {text ? <pre className="max-h-64 overflow-auto rounded-sm border-2 border-dashed border-border-strong bg-card p-2 text-sm select-all" data-testid="supportbundel">{text}</pre> : null}
    </div>
  );
}

function Stappenplan({ data }: { data: Onderzoek }) {
  if (!data.runbook) return <p>Geen stappenplan voor dit soort incident.</p>;
  return (
    <div className="flex flex-col gap-3" data-testid="stappenplan">
      <p>
        <strong>{data.runbook.titel}.</strong> {data.runbook.scenario}
      </p>
      {Object.entries(data.runbook.fasen).map(([fase, stappen]) => (
        <div key={fase}>
          <h4 className="font-semibold">{FASE_LABEL[fase] ?? fase}</h4>
          <ol data-genummerd="" className="flex flex-col gap-1">
            {stappen.map((s, i) => (
              <li key={i}>
                <span className="mr-1 rounded-sm border border-border-strong px-1 text-sm font-semibold">{STAP_SOORT[s.soort] ?? s.soort}</span>
                {s.tekst}
                {s.action_id ? (
                  <span className="text-sm text-muted-foreground">
                    {" "}
                    (<code>{s.action_id}</code>, voorstel — uitvoeren volgt in fase P2)
                  </span>
                ) : null}
              </li>
            ))}
          </ol>
        </div>
      ))}
      {data.runbook.test_na_herstel?.length ? (
        <div>
          <h4 className="font-semibold">Controle na herstel</h4>
          <ul className="list-disc pl-6">
            {data.runbook.test_na_herstel.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function Voorstel({ v }: { v: HerstelVoorstel }) {
  if (!v.voorstel) {
    return (
      <Melding soort="onbekend" titel="Geen herstelvoorstel" data-testid="herstelvoorstel">
        <p>{v.advies}</p>
        <p className="text-sm">
          Reden: <code>{v.reden}</code>
        </p>
      </Melding>
    );
  }
  return (
    <div className="flex flex-col gap-3 rounded-lg border-2 border-border-strong p-4" data-testid="herstelvoorstel">
      <h4 className="font-semibold">Voorstel (alleen lezen)</h4>
      <dl className="kv">
        <dt>Actie</dt>
        <dd>
          <code>{v.voorstel.action_id}</code>
        </dd>
        <dt>Doel</dt>
        <dd>
          <code>{JSON.stringify(v.voorstel.target)}</code>
        </dd>
        <dt>Parameters</dt>
        <dd>
          <code>{JSON.stringify(v.voorstel.parameters)}</code>
        </dd>
        <dt>Vervalt na</dt>
        <dd>{Math.round(v.voorstel.expires_in_seconds / 60)} min</dd>
        <dt>Risico</dt>
        <dd>Bepaalt het beleid (P2). Voorgestelde klasse {v.voorstel.risk_claim} is een claim en telt niet.</dd>
      </dl>
      <Melding soort="nogniet" titel="Uitvoeren volgt in fase P2">
        <p>Tot dan voer je dit zelf uit in TrueNAS → Apps. De Hub wijzigt nu niets.</p>
      </Melding>
    </div>
  );
}

export function IncidentDetail({ id, embedded }: { id: string; embedded?: boolean }) {
  const role = useRole();
  const inc = useApi<Incident>(`/api/v1/incidents/${id}`, 30_000);
  const actions = inc.data?.acties ?? [];
  const can = (a: string) => actions.includes(a);
  const act = useAction<Incident>();
  const [ozBusy, setOzBusy] = useState(false);
  const [ozError, setOzError] = useState<unknown>(null);
  const [onderzoekData, setOnderzoekData] = useState<Onderzoek | null>(null);
  const herstel = useAction<HerstelVoorstel>();
  const [minuten, setMinuten] = useState("240");
  const [uitstel, setUitstel] = useState("60");
  const [reden, setReden] = useState("");
  const [vmReden, setVmReden] = useState("");
  const [notitie, setNotitie] = useState("");
  const [msg, setMsg] = useState("");
  const now = new Date();

  if (inc.error && !inc.data) {
    return (
      <div className="flex flex-col gap-4" data-testid="incident-detail">
        {embedded ? <h2>Incident</h2> : <PageHeader title="Incident" kruimel={[{ label: "Problemen", href: "/problemen" }, { label: "Incident" }]} />}
        <ErrorPanel error={inc.error} onRetry={() => void inc.reload()} />
      </div>
    );
  }
  if (!inc.data) return <Loading />;
  const i = inc.data;
  const kritiek = i.ernst === "kritiek";
  const doe = async (path: string, body: unknown, ok: string) => {
    setMsg("");
    const r = await act.run(`/api/v1/incidents/${id}/${path}`, { body, ifMatch: inc.etag });
    if (r) {
      setMsg(ok);
      await inc.reload();
    }
  };
  const nogActief = act.error?.code === "nog_actief";
  const rb = (act.error?.details?.readback as { bron?: string; gemeten_op?: string } | undefined) ?? undefined;

  return (
    <article className="flex min-w-0 flex-col gap-4" data-testid="incident-detail" aria-labelledby={`inc-titel-${id}`}>
      {embedded ? (
        <h2 id={`inc-titel-${id}`} className="[overflow-wrap:anywhere]">
          {i.titel}
        </h2>
      ) : (
        <div id={`inc-titel-${id}`}>
          <PageHeader title={i.titel} kruimel={[{ label: "Problemen", href: "/problemen" }, { label: "Incident" }]} />
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <ErnstLabel ernst={ernstVan(i.ernst)} />
        <StatusBadge view={incidentStatusView(i, (x) => formatTime(x, now))} />
        {i.heropend ? <span className="rounded-sm border border-border-strong px-1.5 text-sm font-semibold">Heropend ({i.heropend}×)</span> : null}
      </div>
      <dl className="meta">
        <div>
          <dt>Bron</dt>
          <dd>{i.bron}</dd>
        </div>
        <div>
          <dt>Onderwerp</dt>
          <dd>
            {i.onderwerp.naam ?? i.onderwerp.id} ({i.onderwerp.type})
          </dd>
        </div>
        <div>
          <dt>Eerst gezien</dt>
          <dd>{formatDateTime(i.eerste_gebeurtenis)}</dd>
        </div>
        <div>
          <dt>Laatst gezien</dt>
          <dd>
            {formatDateTime(i.laatste_gebeurtenis)} ({formatRelative(i.laatste_gebeurtenis, now)}) · ×{i.aantal_gebeurtenissen}
          </dd>
        </div>
        <div>
          <dt>Readback</dt>
          <dd>
            {i.readback ? `${i.readback.toestand} — ${i.readback.detail}${i.readback.gemeten_op ? ` (${formatTime(i.readback.gemeten_op, now)})` : ""}` : "onbekend"}
          </dd>
        </div>
        {i.opgelost ? (
          <div>
            <dt>Opgelost</dt>
            <dd>
              {formatDateTime(i.opgelost.op)} door {i.opgelost.door}: {i.opgelost.reden}
            </dd>
          </div>
        ) : null}
      </dl>
      {inc.stale ? <Melding soort="onbekend" titel="Verouderd">Dit is de laatst bekende stand ({formatTime(inc.lastOk, now)}); vernieuwen is mislukt.</Melding> : null}

      {i.veilige_modus.actief ? (
        <Melding soort="gate" icon={Lock} titel={`Veilige modus sinds ${formatTime(i.veilige_modus.sinds, now)}`} data-testid="veilige-modus">
          <p>De Hub stelt geen herstart meer voor (2× opnieuw mislukt binnen een uur).</p>
          {can("onderzoek") ? (
            <form
              className="flex flex-col gap-2"
              onSubmit={(e: FormEvent) => {
                e.preventDefault();
                void doe("veilige-modus", { actief: false, reden: vmReden }, "Veilige modus opgeheven.");
              }}
            >
              <div className="field">
                <label htmlFor={`vm-reden-${id}`}>Reden (verplicht, komt in het auditspoor)</label>
                <input id={`vm-reden-${id}`} value={vmReden} onChange={(e) => setVmReden(e.target.value)} minLength={3} required />
              </div>
              <div>
                <Button type="submit" bezig={act.busy}>
                  <ShieldCheck aria-hidden="true" />
                  Veilige modus opheffen…
                </Button>
              </div>
            </form>
          ) : null}
        </Melding>
      ) : (
        <p className="text-sm" data-testid="veilige-modus">
          Veilige modus: uit. Na 2× opnieuw mislukken binnen een uur stelt de Hub geen herstart meer voor.
        </p>
      )}

      <Hypothese inc={i} />

      {role === "viewer" ? <RolMelding>Je kijkt als {ROLE_LABEL.viewer}: je kunt hier niets wijzigen.</RolMelding> : null}

      {i.actief && (can("erkennen") || can("snoozen") || can("oplossen")) ? (
        <section className="card" aria-labelledby={`acties-${id}`}>
          <h3 id={`acties-${id}`}>Afhandelen</h3>
          <div className="grid gap-4 md:grid-cols-2">
            {can("erkennen") ? (
              <form
                className="flex flex-col gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void doe("erkennen", { minuten: Number(minuten) }, "Erkend.");
                }}
              >
                <div className="field">
                  <label htmlFor={`erken-${id}`}>Erkennen voor</label>
                  <select id={`erken-${id}`} value={minuten} onChange={(e) => setMinuten(e.target.value)}>
                    <option value="60">1 uur</option>
                    <option value="240">4 uur</option>
                    <option value="1440">24 uur</option>
                  </select>
                  <p className="help">Daarna escaleert het opnieuw als het probleem er nog is.</p>
                </div>
                <div>
                  <Button type="submit" bezig={act.busy}>
                    Erkennen
                  </Button>
                </div>
              </form>
            ) : null}
            {can("snoozen") ? (
              <form
                className="flex flex-col gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void doe("snooze", { minuten: Number(uitstel) }, "Uitgesteld.");
                }}
              >
                <div className="field">
                  <label htmlFor={`uitstel-${id}`}>Uitstellen</label>
                  <select id={`uitstel-${id}`} value={uitstel} onChange={(e) => setUitstel(e.target.value)}>
                    <option value="60">1 uur</option>
                    <option value="480">8 uur</option>
                    <option value="1440">24 uur</option>
                    {!kritiek ? <option value="4320">3 dagen</option> : null}
                    <option value="0">Uitstel opheffen</option>
                  </select>
                  <p className="help">Meldingen worden zolang onderdrukt{kritiek ? "; kritiek hooguit 24 uur" : ""}.</p>
                </div>
                <div>
                  <Button type="submit" bezig={act.busy}>
                    Uitstellen…
                  </Button>
                </div>
              </form>
            ) : null}
            {can("oplossen") ? (
              <form
                className="flex flex-col gap-2 md:col-span-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void doe("oplossen", { reden }, "Opgelost.");
                }}
              >
                <div className="field">
                  <label htmlFor={`oplos-${id}`}>Reden van oplossen</label>
                  <input id={`oplos-${id}`} value={reden} onChange={(e) => setReden(e.target.value)} minLength={3} required />
                  <p className="help">Kan alleen als de bron het probleem niet meer meldt (readback is leidend).</p>
                </div>
                <div>
                  <Button type="submit" variant="primair" bezig={act.busy} data-testid="oplossen">
                    Oplossen
                  </Button>
                </div>
              </form>
            ) : null}
          </div>
          {nogActief ? (
            <Melding soort="info" icon={Lock} data-testid="nog-actief">
              <p>
                Oplossen kan niet: {rb?.bron ?? i.bron} meldt het probleem nog
                {rb?.gemeten_op ? ` (readback ${formatTime(rb.gemeten_op, now)})` : ""}. Erken of stel het uit.
              </p>
            </Melding>
          ) : act.error ? (
            <ErrorPanel error={act.error} />
          ) : null}
          <p role="status" className="text-sm">
            {msg}
          </p>
        </section>
      ) : null}

      {can("onderzoek") || can("herstel_voorstellen") ? (
        <section className="card" aria-labelledby={`onderzoek-${id}`}>
          <h3 id={`onderzoek-${id}`}>Onderzoek en herstel</h3>
          <div className="flex flex-wrap gap-2">
            {can("onderzoek") ? (
              <Button
                bezig={ozBusy}
                onClick={async () => {
                  setOzBusy(true);
                  setOzError(null);
                  try {
                    const { data } = await apiRequest<Onderzoek>(`/api/v1/incidents/${id}/onderzoek`);
                    setOnderzoekData(data);
                  } catch (e) {
                    setOnderzoekData(null);
                    setOzError(e);
                  } finally {
                    setOzBusy(false);
                  }
                }}
              >
                <ListChecks aria-hidden="true" />
                Onderzoek
              </Button>
            ) : null}
            {can("herstel_voorstellen") && i.actief ? (
              <Button bezig={herstel.busy} onClick={() => void herstel.run(`/api/v1/incidents/${id}/herstel-voorstellen`, { body: {} })}>
                <Wrench aria-hidden="true" />
                Herstel voorstellen
              </Button>
            ) : null}
          </div>
          {ozError ? <ErrorPanel error={ozError} /> : null}
          {onderzoekData ? <Stappenplan data={onderzoekData} /> : null}
          {herstel.error ? <ErrorPanel error={herstel.error} /> : null}
          {herstel.result ? <Voorstel v={herstel.result} /> : null}
        </section>
      ) : null}

      {can("notitie") && i.actief ? (
        <section className="card" aria-labelledby={`notitie-${id}`}>
          <h3 id={`notitie-${id}`}>Notitie</h3>
          <form
            className="flex flex-col gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              await doe("notities", { tekst: notitie }, "Notitie opgeslagen (geschoond).");
              setNotitie("");
            }}
          >
            <div className="field">
              <label htmlFor={`notitie-tekst-${id}`}>Notitie bij dit incident</label>
              <textarea id={`notitie-tekst-${id}`} value={notitie} onChange={(e) => setNotitie(e.target.value)} required maxLength={2000} />
              <p className="help">Wordt geschoond opgeslagen (geheimen en IP-adressen gemaskeerd).</p>
            </div>
            <div>
              <Button type="submit" bezig={act.busy}>
                <ClipboardList aria-hidden="true" />
                Notitie opslaan
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {can("supportbundel") ? (
        <section className="card" aria-labelledby={`bundel-${id}`}>
          <h3 id={`bundel-${id}`}>Supportbundel</h3>
          <Supportbundel id={id} />
        </section>
      ) : null}

      <Tijdlijn id={id} />
    </article>
  );
}
