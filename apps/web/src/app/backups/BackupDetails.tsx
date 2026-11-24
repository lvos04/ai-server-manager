"use client";

import Link from "next/link";
import { useState } from "react";
import { useNow } from "@/components/Freshness";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Leesstand } from "@/components/Leesstand";
import { Melding } from "@/components/Melding";
import { ResponsiveList } from "@/components/ResponsiveList";
import { StatusBadge } from "@/components/StatusBadge";
import { APP_ID, appNaam, databaseAanwezig, meettijd, puntDatasets, puntenReden, uploadStand, uren, UUID, type Herstelpunt, type TestRecord, type UploadTaak } from "@/lib/backups";
import { formatDateTime, formatDuration, formatRelative } from "@/lib/format";
import { coverageStatus, testResult } from "@/lib/status";
import type { Coverage } from "@/lib/types";
import { useBronlijst, useMeting } from "@/lib/use-meting";

export function Herstelpunten({ initApp }: { initApp?: string }) {
  const [app, kies] = useState(initApp && APP_ID.test(initApp) ? initApp : "");
  const punten = useBronlijst<{ items: Herstelpunt[] }>(`/api/v1/backups/herstelpunten${app ? `?app=${encodeURIComponent(app)}` : ""}`);
  const dekking = useMeting<Coverage>("/api/v1/backups/coverage");
  const nu = useNow(1000).getTime();
  const opties = new Set([app, ...(dekking.data?.apps.map(a => a.app) ?? []), ...(punten.data?.items.map(p => p.app) ?? [])].filter(a => APP_ID.test(a)));
  return <section className="card stack">
    <label htmlFor="punt-app">Herstelpunten per app</label>
    <select id="punt-app" className="w-full sm:max-w-sm" value={app} onChange={e => kies(e.target.value)}>
      <option value="">Alle apps</option>{Array.from(opties).sort().map(a => <option key={a}>{a}</option>)}
    </select>
    <Leesstand bron={punten} naam="Herstelpunten" />
    <Leesstand bron={dekking} naam="Hersteldoelen" />
    {punten.data && !punten.data.items.length && !punten.stale && <p>Geen herstelpunten gevonden{app && " voor deze app"}.</p>}
    {punten.data && <ResponsiveList label="Herstelpunten per app" items={punten.data.items} sleutel={p => p.id} kolommen={[
      { kop: "App en soort", cel: p => <>{appNaam(p.app)} · {puntDatasets(p).length ? "Snapshot" : "Soort onbekend"}{databaseAanwezig(p) && " en database-export"}</> },
      { kop: "Gemaakt", cel: p => <>{formatDateTime(meettijd(p.gemaakt_op, nu))}<br />{formatRelative(meettijd(p.gemaakt_op, nu), new Date(nu))}</> },
      { kop: "Checkpoint", cel: p => UUID.test(p.checkpoint_id) ? <KopieerVeld label="Checkpoint-ID" waarde={p.checkpoint_id} /> : "Niet beschikbaar" },
      { kop: "Status en bewijs", cel: p => {
        const a = dekking.data?.apps.find(a => a.app === p.app);
        const reden = puntenReden(p, a?.herkend_als ?? null, a?.rpo_rto.rpo_uren, nu);
        const oud = punten.stale || dekking.stale;
        return <>
          <StatusBadge view={p.status === "ongezond" ? testResult("mislukt") : coverageStatus(!oud && p.status === "geverifieerd" ? "geverifieerd" : "unknown")} />
          <p>{oud ? "Telt niet mee. De lezing is verouderd." : reden ? `Telt niet mee. ${reden}` : "Telt mee binnen de RPO."}</p>
          <p>Maximale leeftijd (RPO) · {uren(a?.rpo_rto.rpo_uren)}<br />Beoogde hersteltijd (RTO) · {uren(a?.rpo_rto.rto_uren)}</p>
        </>;
      } },
    ]} />}
  </section>;
}

const UPLOAD: Record<string, string> = {
  aanmelding_verlopen: "Aanmelding verlopen. Controleer de externe back-up.", verouderd: "Laatste upload te oud",
  mislukt: "Upload mislukt", ontbreekt: "Geen passende uploadtaak", ok: "Upload bevestigd",
};

export function Extern() {
  const bron = useBronlijst<{ status: string; taken: UploadTaak[]; max_leeftijd_s: number }>("/api/v1/backups/extern", "afgeleid_op");
  const nu = useNow(1000).getTime();
  const data = bron.data;
  const taken = data?.taken ?? [];
  const stand = (t: UploadTaak) => uploadStand(t, data?.max_leeftijd_s ?? 0, nu);
  const status = data?.status === "ok" ? (taken.length ? taken.map(stand).find(s => s !== "ok") ?? "ok" : "unknown") : data?.status;
  const label = (s: string | undefined) => s && Object.hasOwn(UPLOAD, s) && !(bron.stale && (s === "ok" || s === "ontbreekt")) ? UPLOAD[s] : "Externe back-up onbekend";
  return <section className="card stack">
    <Leesstand bron={bron} naam="Externe back-up" />
    {data && <>
      <Melding soort={status === "ok" && !bron.stale ? "info" : status === "unknown" || bron.stale ? "onbekend" : "gate"} titel={label(status)}>
        {status !== "ok" && <p>De externe voorwaarde van de back-upgate blijft dicht. <Link className="losse-link" href="/problemen">Bekijk problemen</Link></p>}
        {status === "ok" && <p>Een bevestigde upload bewijst alleen de synchronisatie.</p>}
      </Melding>
      <p>Gerapporteerde taken · {bron.stale || (data.status === "unknown" && !taken.length) ? "Onbekend" : taken.length}. Maximale uploadleeftijd · {formatDuration(data.max_leeftijd_s)}.</p>
      <ResponsiveList label="Uploadtaken uit D04" items={taken} sleutel={t => String(t.id)} tabelVanaf={768} kolommen={[
        { kop: "D04-uploadtaak", cel: t => Number.isSafeInteger(t.id) ? `Taak ${t.id}` : "Taak-ID onbekend" },
        { kop: "Bron", cel: () => "TrueNAS Cloud Sync · OneDrive" },
        { kop: "Stand", cel: t => label(stand(t)) },
        { kop: "Eindtijd upload", cel: t => formatDateTime(meettijd(t.beeindigd, nu)) },
      ]} />
      <p className="meta">Aantal bestanden en bewijs van versleuteling zijn niet beschikbaar.</p>
    </>}
  </section>;
}

const SCENARIOS: Record<string, { titel: string; stappen: string[] }> = {
  poolverlies: { titel: "Pool verloren of defect", stappen: [
    "Zet de noodstop van de Hub aan en bewaar de oorspronkelijke schijven als terugval.",
    "Controleer in de TrueNAS-webinterface het afzonderlijke hersteldoel, de externe appkopie en de geverifieerde Hub-export.",
    "Stop en verifieer eerst de back-up en het afzonderlijke hersteldoel.",
    "Zet de kopie op het afzonderlijke doel terug en controleer per app het herstel in de zandbak.",
  ] },
  credential_lek: { titel: "Toegang uitgelekt", stappen: [
    "Zet de noodstop van de Hub aan.", "Vervang de betrokken sleutel in de TrueNAS-webinterface en trek de oude toegang in.",
    "Werk de koppeling en de Hub-kluis bij. Controleer de toegang en lees het auditspoor over de betrokken periode.",
  ] },
  foutieve_appmigratie: { titel: "Foutieve appmigratie", stappen: [
    "Behoud de installatie en zoek het herstelpunt van vóór de migratie.",
    "Laat de hersteltest in de zandbak zowel de gegevens als de database toetsen.",
    "Controleer de versie en de tellingen met de app-eigenaar voordat je beslist over terugkeer.",
  ] },
  mediaguard_terugzetten: { titel: "MediaGuard terugzetten", stappen: [
    "Laat MediaGuard en de mediaserver draaien en bewaar de oude installatie als terugval.",
    "Kies een herstelpunt met database-export en controleer in de zandbak de tellingen van de voortgang en de kijkgeschiedenis.",
    "Leg de vergelijking en het terugvalpad vast. Terugzetten via de eigenaar vereist menselijk akkoord.",
  ] },
  verhuizing: { titel: "Verhuizen naar andere hardware", stappen: [
    "Verifieer de nieuwste Hub-export en bewaar de vereiste kluis- en ondertekeningssleutels afzonderlijk en beveiligd.",
    "Oefen de verhuizing op de afzonderlijke teststack. Houd de oude installatie beschikbaar.",
    "Controleer de checksum, de kluis en iedere dienstkoppeling. Koppel de executor gecontroleerd opnieuw.",
  ] },
};

export function Rampenscenarios({ scenario }: { scenario?: string }) {
  const bron = useBronlijst<{ scenarios: { id: string }[]; laatste_hersteltests: TestRecord[] }>("/api/v1/backups/rampenscenario");
  const ids = [...new Set(bron.data?.scenarios.map(s => s.id).filter(id => Object.hasOwn(SCENARIOS, id)))];
  const keuze = scenario ?? ids[0];
  const actief = keuze && ids.includes(keuze) ? SCENARIOS[keuze] : null;
  return <section className="card stack">
    <Leesstand bron={bron} naam="Scenario’s" />
    {bron.data && <>
      <nav aria-label="Rampenscenario kiezen"><ul>{ids.map(id => <li key={id}><Link className="losse-link" aria-current={id === keuze ? "page" : undefined} href={`/backups/rampenscenarios?scenario=${id}`}>{SCENARIOS[id]!.titel}</Link></li>)}</ul></nav>
      {actief ? <><h2>{actief.titel}</h2><p>Laatste oefening onbekend. Er is geen oefendatum aan dit scenario gekoppeld.</p>
        <ol data-genummerd="" className="list-decimal space-y-2 pl-6">{actief.stappen.map(stap => <li key={stap}>{stap}</li>)}</ol></>
        : <p>Stappen voor dit scenario niet beschikbaar.</p>}
      <h2>Recente hersteltests per app</h2>
      {bron.data.laatste_hersteltests.length ? <ul>{bron.data.laatste_hersteltests.map((t, i) => <li key={i}>
        {appNaam(t.app_id)} · {bron.stale || !["geslaagd", "mislukt"].includes(t.resultaat) ? "Onbekend" : testResult(t.resultaat).label} · {formatDateTime(t.uitgevoerd_op)}
      </li>)}</ul> : !bron.stale && <p>Nog geen hersteltests vastgelegd.</p>}
    </>}
  </section>;
}
