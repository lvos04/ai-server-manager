"use client";

import { CirclePause, ExternalLink } from "lucide-react";
import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness, useNow } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { buttonVariants } from "@/components/ui/button";
import { ADAPTERS, allePaginas, type Koppeling, type Pagina } from "@/app/instellingen/diensten/adapterweergave";
import type { HubApiError } from "@/lib/api";
import { formatDateTime, formatNumber, formatTime } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import {
  KETEN, KOPPELSCHERM, MSO_ONBEKEND, ketenLink, mediaguardWeergave, msoWeergave,
  type Cijfer, type MediaGuardOverzicht, type MediaGuardWeergave, type MsoWeergave,
} from "./mediaweergave";

const EIGENAAR = { mediaguard: "MediaGuard", "media-source-optimizer": "MSO" };

function verbindingsuitval(error: HubApiError) {
  return error.status === 0 || [502, 503, 504].includes(error.status);
}

function Koppellink({ children = "Naar instellingen voor diensten" }: { children?: string }) {
  return <Link className={buttonVariants({ variant: "link" })} href={KOPPELSCHERM}>{children}</Link>;
}

/** Een getal met meetkwaliteit (Peil C-07). Verouderd: grijs met "Laatst gemeten …", nooit als actueel. */
export function CijferTegel({ cijfer, bron }: { cijfer: Cijfer; bron: string }) {
  const { waarde, zekerheid, verouderd } = cijfer;
  const getal = waarde === null || zekerheid === "onbekend" ? null : (zekerheid === "geschat" ? "≈ " : "") + formatNumber(waarde);
  return (
    <div className="flex min-w-0 flex-col gap-1 rounded-lg border border-border p-3" data-testid={"cijfer-" + cijfer.id}>
      <h4 className="font-semibold">{cijfer.titel}</h4>
      {getal === null ? (
        <p className="text-2xl font-semibold">
          Onbekend
          {cijfer.observedAt ? <span className="block text-sm font-semibold text-stale-ink">Laatst gemeten · {formatTime(cijfer.observedAt)}</span> : null}
        </p>
      ) : verouderd ? (
        <p className="text-2xl text-stale-ink">
          {getal}
          <span className="block text-sm font-semibold">Laatst gemeten{cijfer.observedAt ? " · " + formatTime(cijfer.observedAt) : ""} · {zekerheid}</span>
        </p>
      ) : (
        <p className="text-2xl font-semibold">{getal} <span className="text-sm text-muted-foreground">· {zekerheid}</span></p>
      )}
      {getal !== null && verouderd ? <StatusBadge view={{ tone: "stale", label: "Verouderd" }} /> : null}
      {cijfer.reden ? <p className="text-sm">{getal === null ? "Onbekend: " : ""}{cijfer.reden}</p> : null}
      <Freshness bron={bron} label="Gemeten" observedAt={cijfer.observedAt} verouderd={cijfer.observedAt !== null && verouderd} />
    </div>
  );
}

function janee(v: boolean | null) {
  return v === null ? "onbekend" : v ? "ja" : "nee";
}

/** Balk "gepauzeerd": alleen een melding. De noodstop opheffen kan op dit scherm niet (geen actieknoppen). */
export function Pauzebalk({ sinds }: { sinds: string | null }) {
  return (
    <div role="status" data-testid="pauzebalk"
      className="flex gap-3 rounded-lg border-2 border-paused bg-paused-bg p-4 text-paused-ink [&>svg]:mt-0.5 [&>svg]:size-5 [&>svg]:shrink-0 [&>svg]:text-paused">
      <CirclePause aria-hidden="true" />
      <div className="flex flex-col gap-1">
        <p className="font-bold">MediaGuard is gepauzeerd (noodstop)</p>
        <p>Sinds {sinds ? <time dateTime={sinds}>{formatDateTime(sinds)}</time> : "onbekend"}. MediaGuard zoekt, importeert en encodeert niet zolang de noodstop aan staat.</p>
      </div>
    </div>
  );
}

export function MediaGuardKaart({ mg }: { mg: MediaGuardWeergave }) {
  const titel = "mediaguard-" + mg.id;
  return (
    <article className="card min-w-0" aria-labelledby={titel}>
      <h3 id={titel} className="text-lg font-semibold">MediaGuard</h3>
      <p className="text-sm break-all text-muted-foreground">Installatie · {mg.installatie}</p>
      {mg.noodstop.actief ? <Pauzebalk sinds={mg.noodstop.sinds} /> : null}
      <section aria-label="Mediaservers" className="flex flex-col gap-1">
        <h4 className="font-semibold">Mediaservers</h4>
        {mg.servers === null ? (
          <p>Onbekend: {mg.serversReden}</p>
        ) : mg.servers.length === 0 ? <p>MediaGuard volgt geen mediaserver.</p> : (
          <ul className="divide-y divide-border">
            {mg.servers.map((s, i) => (
              <li key={i} className="flex flex-wrap gap-x-4 py-2">
                <span className="font-semibold wrap-anywhere">{s.label}</span>
                <span>Verbonden · {janee(s.verbonden)}</span>
                <span>Kijkpauze actief · {janee(s.kijkpauze)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {mg.noodstop.actief === null ? (
        <p>
          Noodstop · onbekend: {mg.noodstop.reden}
          {mg.noodstop.observedAt ? <span className="text-stale-ink"> · laatst gemeten <time dateTime={mg.noodstop.observedAt}>{formatTime(mg.noodstop.observedAt)}</time></span> : null}
        </p>
      ) : null}
      {mg.noodstop.actief === false ? <p data-testid="noodstop-uit">Noodstop · uit · gemeten</p> : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {mg.cijfers.map((c) => <CijferTegel key={c.id} cijfer={c} bron="MediaGuard" />)}
      </div>
    </article>
  );
}

export function MsoKaart({ mso }: { mso: MsoWeergave }) {
  const titel = "mso-" + mso.id;
  const g = mso.gezondheid;
  return (
    <article className="card min-w-0" aria-labelledby={titel}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 id={titel} className="text-lg font-semibold">Media Source Optimizer (MSO)</h3>
        {mso.adres ? (
          <a className={buttonVariants({ variant: "link" })} href={mso.adres} rel="noreferrer"><ExternalLink aria-hidden="true" /> Open in MSO</a>
        ) : null}
      </div>
      <p className="text-sm break-all text-muted-foreground">Installatie · {mso.installatie}</p>
      <div className="flex flex-col gap-1" data-testid="mso-gezondheid">
        <h4 className="font-semibold">Gezondheid (openbare verbindingstest)</h4>
        {g.zekerheid === "onbekend" ? <p className="font-semibold">Onbekend</p> : g.verouderd ? (
          <p className="text-stale-ink">{g.tekst}<span className="block text-sm font-semibold">Laatst gemeten{g.observedAt ? " · " + formatTime(g.observedAt) : ""} · gemeten</span></p>
        ) : <p className="font-semibold">{g.tekst} <span className="text-sm text-muted-foreground">· gemeten</span></p>}
        {g.zekerheid !== "onbekend" && g.verouderd ? <StatusBadge view={{ tone: "stale", label: "Verouderd" }} /> : null}
        {g.reden ? <p className="text-sm">{g.reden}</p> : null}
        <Freshness bron="MSO · openbare verbindingstest" label="Gemeten" observedAt={g.observedAt} verouderd={g.verouderd} />
      </div>
      <dl className="flex flex-col gap-2">
        <div>
          <dt className="font-semibold">Open wijzigingen</dt>
          <dd>{MSO_ONBEKEND}{mso.adres ? <> · <a href={mso.adres} rel="noreferrer">bekijk ze in MSO</a></> : null}</dd>
        </div>
        <div>
          <dt className="font-semibold">Kosten</dt>
          <dd>{MSO_ONBEKEND} · herkomst: MSO</dd>
        </div>
      </dl>
    </article>
  );
}

/** Leest het alleen-lezen overzicht van één MediaGuard-installatie; een fout of twijfel blijft zichtbaar onbekend. */
export function MediaGuardBron({ koppeling, oudeLijst, nu }: { koppeling: Koppeling; oudeLijst: boolean; nu: number }) {
  const { data, error, loading, stale } = useApi<MediaGuardOverzicht>(
    `${ADAPTERS}/${encodeURIComponent(koppeling.id)}/mediaguard`, 60_000, verbindingsuitval,
  );
  // Een weigering mag geen eerdere meting blijven tonen; bij verbindingsuitval blijft die grijs staan.
  const overzicht = data && (!error || verbindingsuitval(error)) ? data : null;
  const fout = loading && !data ? "wordt opgehaald" : error ? error.message : "geen bevestigde meting";
  return <MediaGuardKaart mg={mediaguardWeergave(koppeling, overzicht, nu, oudeLijst || stale, fout)} />;
}

function NietGekoppeld({ app }: { app: string }) {
  return (
    <section className="card">
      <h3 className="text-lg font-semibold">{app} is niet gekoppeld</h3>
      <p>Een beheerder kan de leesverbinding instellen.</p>
      <div><Koppellink /></div>
    </section>
  );
}

export function MediaInhoud({ koppelingen, verouderd, nu }: { koppelingen: Koppeling[]; verouderd: boolean; nu: number }) {
  const mg = koppelingen.filter((k) => k.app_id === "mediaguard");
  const mso = koppelingen.filter((k) => k.app_id === "media-source-optimizer").map((k) => msoWeergave(k, nu, verouderd));
  if (!mg.length && !mso.length) {
    return (
      <section className="card" data-testid="media-leeg">
        <h2 className="text-lg font-semibold">MediaGuard en MSO zijn nog niet gekoppeld</h2>
        <p>Zonder koppeling heeft de Hub geen mediagegevens. Een beheerder koppelt de apps onder Instellingen → Diensten.</p>
        <div><Koppellink /></div>
      </section>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      {verouderd ? <StatusBadge view={{ tone: "stale", label: "Verouderde mediagegevens" }} /> : null}
      <section aria-labelledby="media-mediaguard" className="flex flex-col gap-3">
        <h2 id="media-mediaguard" className="text-xl font-semibold">MediaGuard</h2>
        {mg.length ? mg.map((k) => <MediaGuardBron key={k.id} koppeling={k} oudeLijst={verouderd} nu={nu} />) : <NietGekoppeld app="MediaGuard" />}
      </section>
      <section aria-labelledby="media-mso" className="flex flex-col gap-3">
        <h2 id="media-mso" className="text-xl font-semibold">Media Source Optimizer</h2>
        {mso.length ? mso.map((m) => <MsoKaart key={m.id} mso={m} />) : <NietGekoppeld app="MSO" />}
      </section>
      <section aria-labelledby="media-keten" className="card min-w-0">
        <h2 id="media-keten" className="text-xl font-semibold">Waarom ontbreekt dit?</h2>
        <p>Een ontbrekende film of aflevering loopt door deze schakels. Elke eigenaar toont de oorzaak in het eigen scherm.</p>
        <ol className="flex list-decimal flex-col gap-2 pl-6">
          {KETEN.map((s) => {
            const href = ketenLink(koppelingen, s.eigenaar, s.scherm);
            return (
              <li key={s.onderdeel}>
                <span className="font-semibold">{s.onderdeel}</span> · eigenaar {EIGENAAR[s.eigenaar]} ·{" "}
                {href === KOPPELSCHERM ? <Link href={href}>eerst koppelen</Link> : <a href={href} rel="noreferrer">open in {EIGENAAR[s.eigenaar]}</a>}
              </li>
            );
          })}
        </ol>
      </section>
      <section aria-labelledby="media-jelly" className="card">
        <h2 id="media-jelly" className="text-xl font-semibold">Jelly Leon</h2>
        <StatusBadge view={{ tone: "not_yet", label: "Gepland in fase P4" }} />
        <p>Emby blijft de mediaserver. Dit scherm toont nog geen gegevens van Jelly Leon.</p>
      </section>
    </div>
  );
}

export function MediaScreen() {
  const { data, error, loading, stale, reload } = useApi<Pagina<Koppeling>>(ADAPTERS + "?limit=200", 60_000, verbindingsuitval, allePaginas);
  const nu = useNow(1000).getTime();
  return (
    <>
      <PageHeader title="Media" intro="Bekijk wat MediaGuard en MSO over je media melden. Acties doe je in de app zelf." />
      {error ? <ErrorPanel error={error} title="Mediagegevens ontbreken" onRetry={reload} /> : null}
      {loading && !data ? <Loading text="Koppelingen ophalen…" /> : null}
      {data && (!error || verbindingsuitval(error)) ? <MediaInhoud koppelingen={data.items} verouderd={stale} nu={nu} /> : null}
    </>
  );
}
