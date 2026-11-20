"use client";

import { ExternalLink, ShowerHead } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness, useNow } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { aantal, formatDateTime, formatNumber, parseIso } from "@/lib/format";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const ADAPTERS = "/api/v1/adapterkoppelingen";
const SOURCE = "my_house";
const MAX_AGE_MS = 900_000;
const QUALITY = { measured: "Gemeten", estimated: "Geschat", derived: "Afgeleid", missing: "Geen meting" };
const SEVERITY = { info: "Informatie", warn: "Waarschuwing", warning: "Waarschuwing", error: "Fout", critical: "Kritiek" };

interface Sensor {
  value: number | null;
  at: string | null;
  unit: "°C";
  quality: keyof typeof QUALITY;
  stale: boolean;
  max_age_s: number;
}

interface Woning {
  woning: { id: string; name: string | null };
  zones: { id: string; name: string | null; temperature: Sensor; target_c: number | null }[];
  licht: { groups: { id: string; name: string | null; on: boolean; reachable: boolean | null }[] };
  apparaten: { id: string; kind: string; online: boolean; last_seen: string | null }[];
  meldingen: {
    open: number;
    begrensd: boolean;
    observed_at: string | null;
    items: { id: string; severity: keyof typeof SEVERITY; created_at: string | null }[];
  };
}

interface Momentopname {
  woningen: Woning[];
  instellingen: { safe_mode: boolean; link: string | null; observed_at: string | null };
  laatste_backup: { age_h: number; observed_at: string } | null;
}

function isVers(tijd: string | null, now: Date, maxAgeMs: number) {
  const meting = parseIso(tijd);
  if (!meting) return false;
  const age = now.getTime() - meting.getTime();
  return age >= 0 && age <= maxAgeMs;
}

function Koppellink() {
  return <Link className={buttonVariants({ variant: "link" })} href="/instellingen/diensten">Naar instellingen voor diensten</Link>;
}

function Waarde({ tekst, verouderd }: { tekst: string; verouderd: boolean }) {
  return verouderd ? <span className="text-stale-ink">Laatst bekend · {tekst}</span> : <>{tekst}</>;
}

function Temperatuur({ sensor, oud, now }: { sensor: Sensor; oud: boolean; now: Date }) {
  const tijd = parseIso(sensor.at);
  const teOud = sensor.stale || !isVers(sensor.at, now, sensor.max_age_s * 1000);
  const heeftWaarde = sensor.value !== null && !sensor.stale && sensor.quality !== "missing";
  const waarde = heeftWaarde && (oud || !teOud);
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm font-semibold">Temperatuur</p>
      <p className="font-semibold"><Waarde tekst={waarde ? `${formatNumber(sensor.value)} ${sensor.unit}` : "Onbekend"} verouderd={waarde && oud} /></p>
      {tijd && (oud || teOud) ? <StatusBadge view={{ tone: "stale", label: "Verouderd" }} /> : null}
      {waarde ? <p className="text-sm text-muted-foreground">{QUALITY[sensor.quality]}</p> : null}
      <Freshness bron={SOURCE} observedAt={sensor.at} verouderd={!!tijd && (oud || teOud)} />
    </div>
  );
}

function WoningKaarten({ data, oud, now }: { data: Woning; oud: boolean; now: Date }) {
  const groepen = new Map(data.apparaten.filter((apparaat) => apparaat.kind === "light_group").map((groep) => [groep.id, groep]));
  const oudeMeldingen = oud || !isVers(data.meldingen.observed_at, now, MAX_AGE_MS);
  return (
    <section className="flex min-w-0 flex-col gap-3">
      <h2 className="text-xl font-semibold wrap-anywhere">{data.woning.name ?? "Woning zonder naam"}</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <section className="card min-w-0">
          <h3 className="text-lg font-semibold">Zones</h3>
          {data.zones.length === 0 ? <p>Geen zones ontvangen.</p> : (
            <ul className="divide-y divide-border">
              {data.zones.map((zone) => (
                <li key={zone.id} className="flex flex-col gap-2 py-3">
                  <h4 className="font-semibold wrap-anywhere">{zone.name ?? "Zone zonder naam"}</h4>
                  <Temperatuur sensor={zone.temperature} oud={oud} now={now} />
                  <div className="flex flex-col gap-1 text-sm">
                    <p className="font-semibold">Temperatuurdoel</p>
                    {zone.target_c === null ? <p>Onbekend</p> : (
                      <>
                        <p><Waarde tekst={`${formatNumber(zone.target_c)} °C`} verouderd /></p>
                        <Freshness bron={SOURCE} observedAt={null} label="Meettijd" onbekendeTijd="Onbekend" />
                      </>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card min-w-0">
          <h3 className="text-lg font-semibold">Lichtgroepen</h3>
          {data.licht.groups.length === 0 ? <p>Geen lichtgroepen ontvangen.</p> : (
            <dl className="divide-y divide-border">
              {data.licht.groups.map((groep) => {
                const apparaat = groepen.get(groep.id);
                const tijd = apparaat?.last_seen ?? null;
                const verouderd = oud || groep.reachable !== true || apparaat?.online !== true || !isVers(tijd, now, MAX_AGE_MS);
                return (
                  <div key={groep.id} className="flex flex-col gap-1 py-2">
                    <dt className="font-semibold wrap-anywhere">{groep.name ?? "Lichtgroep zonder naam"}</dt>
                    <dd>
                      {groep.reachable === false ? "Onbereikbaar · " : null}
                      <Waarde tekst={groep.on ? "Aan" : "Uit"} verouderd={verouderd} />
                      <Freshness bron={SOURCE} observedAt={tijd} verouderd={!!tijd && verouderd} onbekendeTijd="Onbekend" />
                    </dd>
                  </div>
                );
              })}
            </dl>
          )}
        </section>

        <section className="card min-w-0">
          <h3 className="text-lg font-semibold">Open meldingen</h3>
          <p className="font-semibold">
            <Waarde
              tekst={`${data.meldingen.begrensd ? "Minstens " : ""}${aantal(data.meldingen.open, "open melding", "open meldingen")}`}
              verouderd={oudeMeldingen}
            />
          </p>
          {data.meldingen.items.length > 0 ? (
            <ul className={cn("divide-y divide-border", oudeMeldingen && "text-stale-ink")}>
              {data.meldingen.items.map((melding) => (
                <li key={melding.id} className="flex flex-wrap justify-between gap-x-2 py-2">
                  <span>{SEVERITY[melding.severity]}</span>
                  {melding.created_at ? (
                    <time dateTime={melding.created_at}>{formatDateTime(melding.created_at)}</time>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          <Freshness bron={SOURCE} observedAt={data.meldingen.observed_at} verouderd={oudeMeldingen} />
        </section>

        <section className="card min-w-0">
          <h3 className="flex items-center gap-2 text-lg font-semibold"><ShowerHead aria-hidden="true" className="size-5" />Boiler</h3>
          <p>Alleen meten</p>
          <p className="text-sm text-muted-foreground">Vermogen · Onbekend</p>
          <Freshness bron={null} observedAt={null} />
        </section>
      </div>
    </section>
  );
}

function LaatsteBackup({ backup, oud, now }: { backup: Momentopname["laatste_backup"]; oud: boolean; now: Date }) {
  const bronTijd = parseIso(backup?.observed_at);
  const geschat = backup && bronTijd ? new Date(bronTijd.getTime() - backup.age_h * 3_600_000) : null;
  const datum = geschat && !Number.isNaN(geschat.getTime()) ? geschat.toISOString() : null;
  const verouderd = oud || !isVers(backup?.observed_at ?? null, now, MAX_AGE_MS);
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-semibold">Laatste back-up</h3>
      <p>
        {datum ? (
          <time dateTime={datum}><Waarde tekst={`Ongeveer ${formatDateTime(datum)}`} verouderd={verouderd} /></time>
        ) : "Onbekend"}
      </p>
      <Freshness bron="my_house · systeemstatus" observedAt={backup?.observed_at} verouderd={!!datum && verouderd} />
    </div>
  );
}

function HuisBron({ id, oudeLijst }: { id: string; oudeLijst: boolean }) {
  const { data, error, loading, stale, reload } = useApi<Momentopname>(`${ADAPTERS}/${encodeURIComponent(id)}/huis`, 60_000);
  const now = useNow(1000);
  const verlopen = error?.code === "bron_token_verlopen" || error?.code === "bron_token_ingetrokken";
  const oud = oudeLijst || stale;
  const oudeInstellingen = oud || !isVers(data?.instellingen.observed_at ?? null, now, MAX_AGE_MS);
  // Een geweigerde of verwijderde koppeling mag geen eerdere meting blijven tonen.
  const toonMeting = data && (!error || error.status === 0 || error.status === 503);
  return (
    <div className="flex min-w-0 flex-col gap-4">
      {error ? (
        <div>
          <ErrorPanel
            error={error}
            title={verlopen ? "my_house · koppeling verlopen" : "Gegevens van my_house ontbreken"}
            onRetry={verlopen ? undefined : reload}
          />
          {verlopen ? <Koppellink /> : null}
        </div>
      ) : null}
      {loading && !toonMeting ? <Loading text="Woningen ophalen…" /> : null}
      {toonMeting ? (
        <>
          <section className="card min-w-0">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h2 className="text-lg font-semibold">my_house</h2>
              {!oudeInstellingen && data.instellingen.link ? (
                <a className={buttonVariants({ variant: "link" })} href={data.instellingen.link} rel="noreferrer">
                  <ExternalLink aria-hidden="true" /> Open in my_house
                </a>
              ) : null}
            </div>
            {oud ? <StatusBadge view={{ tone: "stale", label: "Verouderde woninggegevens" }} /> : null}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1">
                <h3 className="font-semibold">Veilige modus</h3>
                <p><Waarde tekst={data.instellingen.safe_mode ? "Actief" : "Uit"} verouderd={oudeInstellingen} /></p>
                <Freshness bron={SOURCE} observedAt={data.instellingen.observed_at} verouderd={oudeInstellingen} />
              </div>
              <LaatsteBackup backup={data.laatste_backup} oud={oud} now={now} />
            </div>
          </section>
          {data.woningen.length === 0 ? <p className="card">my_house heeft geen woningen doorgegeven.</p> : null}
          {data.woningen.map((woning) => (
            <WoningKaarten key={woning.woning.id} data={woning} oud={oud} now={now} />
          ))}
        </>
      ) : null}
    </div>
  );
}

function HuisLijst({ cursors, vorige, volgende }: {
  cursors: string[];
  vorige: () => void;
  volgende: (cursor: string) => void;
}) {
  const cursor = cursors.at(-1);
  const query = new URLSearchParams({ limit: "5", ...(cursor ? { cursor } : {}) });
  const { data, error, loading, stale, reload } = useApi<{ items: string[]; next_cursor: string | null }>(
    `${ADAPTERS}/my-house?${query}`, 60_000,
  );
  const next = data?.next_cursor;
  return (
    <div className="flex flex-col gap-6">
      {error ? <ErrorPanel error={error} onRetry={reload} /> : null}
      {loading && !data ? <Loading text="Koppelingen ophalen…" /> : null}
      {!stale && data?.items.length === 0 ? (
        cursor ? <p className="card">Geen verdere my_house-koppelingen gevonden.</p> : (
          <section className="card">
            <h2 className="text-lg font-semibold">my_house is nog niet gekoppeld</h2>
            <p>Een beheerder kan de leesverbinding instellen.</p>
            <div><Koppellink /></div>
          </section>
        )
      ) : null}
      {data?.items.map((id) => <HuisBron key={id} id={id} oudeLijst={stale} />)}
      {cursor || next ? (
        <nav className="flex flex-wrap gap-2" aria-label="Pagina’s met my_house-koppelingen">
          {cursor ? <Button onClick={vorige}>Vorige koppelingen</Button> : null}
          {next && !stale ? <Button onClick={() => volgende(next)}>Volgende koppelingen</Button> : null}
        </nav>
      ) : null}
    </div>
  );
}

export function HuisScreen() {
  const [cursors, setCursors] = useState<string[]>([]);
  return (
    <>
      <PageHeader title="Huis" intro="Bekijk de gegevens van je woning uit my_house." />
      <HuisLijst
        key={cursors.at(-1) ?? "begin"}
        cursors={cursors}
        vorige={() => setCursors((oud) => oud.slice(0, -1))}
        volgende={(cursor) => setCursors((oud) => [...oud, cursor])}
      />
    </>
  );
}
