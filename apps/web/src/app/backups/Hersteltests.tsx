"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Leesstand } from "@/components/Leesstand";
import { ResponsiveList } from "@/components/ResponsiveList";
import { Button } from "@/components/ui/button";
import { type ActieVerzoek, toonbareFout, vasteFout } from "@/lib/acties";
import { appNaam, datasetNaam, KLOON, puntDatasets, UUID, type Herstelpunt, type TestRecord } from "@/lib/backups";
import { brontijd, formatDateTime } from "@/lib/format";
import { lijstIsVers } from "@/lib/lijstversheid";
import { useRole } from "@/lib/session";
import { testResult } from "@/lib/status";
import { useAction } from "@/lib/use-action";
import { useBronlijst, useBronstand, useMeting, usePaginaLijst } from "@/lib/use-meting";

const sleutel = (v: ActieVerzoek) => v.request_id;
const SOORT: Record<string, string> = { foto: "Foto", database: "Database", dataset: "Dataset", config: "Configuratie" };
const uitkomst = (s?: string) => s === "geslaagd" || s === "mislukt" ? testResult(s).label : "Onbekend";
const object = (v: unknown): Record<string, unknown> => v && typeof v === "object" && !Array.isArray(v) ? v as Record<string, unknown> : {};

export function kloonDoelen(p: Herstelpunt, snapshot?: ActieVerzoek) {
  const w = object(snapshot?.preview?.wijziging);
  const rb = object(snapshot?.resultaat?.readback);
  const leden = object(rb.leden);
  const ds = puntDatasets(p);
  if (!UUID.test(p.id) || snapshot?.request_id !== p.checkpoint_id || snapshot.action_id !== "zfs.snapshot.create"
    || snapshot.status !== "uitgevoerd" || rb.aanwezig !== true || w.soort !== "snapshot_maken" || typeof w.snapshot !== "string"
    || !ds.length || ds.length > 32 || !ds.every(d => Object.hasOwn(leden, d) && /^[0-9]+$/.test(String(leden[d])))) return [];
  const delen = w.snapshot.split("@");
  if (delen.length !== 2 || !datasetNaam(delen[0]) || delen[0] !== snapshot.target.dataset || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$/.test(delen[1]!)) return [];
  return ds.map((d, i) => ({ snapshot: `${d}@${delen[1]}`, doel: `${d.split("/")[0]}/asm-sandbox/proef-${p.id}-${i + 1}` }));
}

interface RobotRapport {
  herstelpunt: string; restore_test: string; resultaat: string; reden: string | null;
  kloon?: { resultaat: string }; database?: { resultaat: string }; productie?: { resultaat: string };
}

function Proef({ punt, verouderd, ververs }: { punt: Herstelpunt; verouderd: boolean; ververs: () => Promise<void> }) {
  const router = useRouter();
  const snapshot = useMeting<ActieVerzoek>(UUID.test(punt.checkpoint_id) ? `/api/v1/actions/${punt.checkpoint_id}` : null);
  const klonen = usePaginaLijst<ActieVerzoek>(`/api/v1/actions?action_id=${KLOON}&status=uitgevoerd&limit=50`, sleutel);
  const voorstel = useAction<{ request_id: string }>();
  const robot = useAction<RobotRapport>();
  const [herlezen, setHerlezen] = useState(false);
  const doelen = kloonDoelen(punt, snapshot.data);
  const passendeKlonen = doelen.map(d => klonen.data?.items.find(v => {
    const rb = object(v.resultaat?.readback);
    return v.action_id === KLOON && v.status === "uitgevoerd" && v.risk_class === "R1" && UUID.test(v.request_id)
      && v.target.snapshot === d.snapshot && rb.aanwezig === true && rb.dataset === d.doel
      && brontijd(v.uitgevoerd_op) > brontijd(punt.gemaakt_op);
  }));
  const volgende = doelen.find((_, i) => !passendeKlonen[i]);
  const bevestigd = passendeKlonen.filter((v): v is ActieVerzoek => v !== undefined);
  const compleet = doelen.length > 0 && bevestigd.length === doelen.length;
  const tijden = bevestigd.flatMap(v => {
    // Bij later opgehaald executorbewijs kan de Hub het verzoek pas na de eigenlijke readback hebben afgesloten.
    const meettijden = [v.bijgewerkt_op, v.uitgevoerd_op];
    const readbackTijd = v.resultaat?.uitgevoerd_op;
    if (readbackTijd !== undefined) meettijden.push(typeof readbackTijd === "string" ? readbackTijd : null);
    return meettijden;
  });
  const stand = useBronstand(klonen, klonen.bronTijd, ...tijden);
  const oud = verouderd || snapshot.stale || klonen.stale || !klonen.data || (compleet && stand.stale);
  const openPreview = async () => {
    if (!volgende || oud || voorstel.busy) return;
    const res = await voorstel.run("/api/v1/actions", { body: {
      action_id: KLOON, target: { host_id: "nas-primary", snapshot: volgende.snapshot },
      parameters: { doel_dataset: volgende.doel }, reason: "Zandbakkloon voor een hersteltest.",
    } });
    if (res && UUID.test(res.request_id)) router.push(`/goedkeuringen/${res.request_id}`);
  };
  const toets = async () => {
    if (!compleet || oud || herlezen || robot.busy || !lijstIsVers(stand.bronTijd, Date.now())) return;
    setHerlezen(true);
    await robot.run(`/api/v1/backups/herstelpunten/${punt.id}/hersteltest`, { body: { klonen: bevestigd.map(v => v.request_id) } });
    await ververs();
  };
  const r = robot.result?.herstelpunt === punt.id ? robot.result : null;
  return <>
    <Leesstand naam="Snapshotbewijs" bron={snapshot} />
    <Leesstand naam="Zandbakklonen" bron={klonen} />
    {klonen.data?.next_cursor && <Button onClick={klonen.meer}>Oudere klonen laden</Button>}
    {!compleet && <>
      <p id="kloonreden">Start geblokkeerd — er ontbreekt een bevestigde zandbakkloon.
        {volgende ? " Bekijk de R1-preview en voer de kloon afzonderlijk uit. Keer daarna terug naar dit herstelpunt." : " Het bronbewijs voor de preview is niet beschikbaar."}</p>
      <Button uit={oud || !volgende} bezig={voorstel.busy} aria-describedby="kloonreden" onClick={() => void openPreview()}>Nieuwe hersteltest</Button>
    </>}
    {compleet && <><p id="robotreden" className={oud ? "arcering rounded-lg border border-dashed border-stale p-3" : undefined}>
      {oud ? <>{stand.bronTijd ? <>Laatst bekend · stand van <time dateTime={stand.bronTijd}>{formatDateTime(stand.bronTijd)}</time></> : "Tijdstip van de kloonbevestiging onbekend"}.
        {" "}Zandbakklonen · {bevestigd.length}. Starten wacht op een actuele bevestiging.</>
        : <>Bevestigde zandbakklonen · {bevestigd.length}. De robot toetst deze klonen en de proefdatabase bij dit herstelpunt.</>}</p>
      <Button uit={oud || herlezen} bezig={robot.busy} aria-describedby="robotreden" onClick={() => void toets()}>Hersteltest in zandbak starten</Button></>}
    {voorstel.error && <ErrorPanel vast={vasteFout} error={toonbareFout(voorstel.error)} title="Kloonvoorstel onbekend" />}
    {robot.error && <><ErrorPanel vast={vasteFout} error={toonbareFout(robot.error)} title="Resultaat onbekend" /><p>De stand is opnieuw opgevraagd. Controleer de bewijsrecords voordat je opnieuw start.</p></>}
    {r && <div aria-live="polite"><h3>Robotrapport</h3>
      <p>{r.resultaat === "geslaagd" && [r.kloon, r.database, r.productie].every(d => d?.resultaat === "geslaagd") && !oud ? "Hersteltest geslaagd" :
        r.resultaat === "mislukt" ? "Hersteltest mislukt" : "Resultaat onbekend"}</p>
      {r.reden === "checksum_afwijkend" && <p>De controlesom wijkt af. Het herstelpunt is ongezond.</p>}
      <dl className="kv">{([["Kloon", r.kloon], ["Database", r.database], ["Productie ongewijzigd", r.productie]] as const).map(([naam, deel]) =>
        <div key={naam}><dt>{naam}</dt><dd>{oud && deel?.resultaat === "geslaagd" ? "Onbekend" : uitkomst(deel?.resultaat)}</dd></div>)}</dl>
    </div>}
  </>;
}

function NieuweTest({ initPunt, ververs }: { initPunt?: string; ververs: () => Promise<void> }) {
  const punten = useBronlijst<{ items: Herstelpunt[] }>("/api/v1/backups/herstelpunten");
  const opties = punten.data?.items.filter(p => UUID.test(p.id) && UUID.test(p.checkpoint_id)) ?? [];
  const [keuze, kies] = useState(initPunt);
  const punt = keuze ? opties.find(p => p.id === keuze) : opties[0];
  return <section className="card stack"><h2>Zandbakproef</h2>
    <Leesstand naam="Herstelpunten" bron={punten} />
    {opties.length > 0 && <><label htmlFor="test-punt">Herstelpunt voor de proef</label>
      <select id="test-punt" value={punt?.id ?? ""} onChange={e => {
        kies(e.target.value);
        window.history.replaceState(null, "", `?punt=${encodeURIComponent(e.target.value)}`);
      }}>{!punt && <option value="">Kies een herstelpunt</option>}{opties.map(p => <option key={p.id} value={p.id}>{appNaam(p.app)} · {formatDateTime(p.gemaakt_op)} · {p.id.slice(0, 8)}</option>)}</select></>}
    {punt ? <Proef key={punt.id} punt={punt} verouderd={punten.stale} ververs={ververs} />
      : <><p id="geen-punt">{punten.stale || !punten.data ? "De actuele herstelpunten zijn onbekend." : "Een bevestigd herstelpunt voor de zandbakkloon is niet beschikbaar."}</p><Button uit aria-describedby="geen-punt">Nieuwe hersteltest</Button></>}
  </section>;
}

export function Hersteltests({ initPunt }: { initPunt?: string }) {
  const bron = useBronlijst<{ items: TestRecord[] }>("/api/v1/backups/restore-tests");
  const rol = useRole();
  return <div className="stack">
    {rol === "admin" && <NieuweTest initPunt={initPunt} ververs={bron.reload} />}
    <section className="card stack"><h2>Vastgelegde hersteltests</h2>
      <Leesstand naam="Hersteltests" bron={bron} />
      {bron.data && !bron.data.items.length && !bron.stale && <p>Nog geen hersteltests.</p>}
      {bron.data && <ResponsiveList items={bron.data.items} label="Bewijsrecords" sleutel={r => r.id} tabelVanaf={768} kolommen={[
        { kop: "Doel", cel: t => t.app_id ? appNaam(t.app_id) : datasetNaam(t.dataset) ?? "Onbekend" },
        { kop: "Soort", cel: t => Object.hasOwn(SOORT, t.soort) ? SOORT[t.soort] : "Onbekend" },
        { kop: "Vastgelegd resultaat", cel: t => bron.stale && t.resultaat === "geslaagd" ? "Onbekend" : uitkomst(t.resultaat) },
        { kop: "Uitgevoerd", cel: t => formatDateTime(t.uitgevoerd_op) },
        { kop: "Duur", cel: t => Number.isSafeInteger(t.duur_minuten) && t.duur_minuten! >= 0 ? `${t.duur_minuten} min` : "Onbekend" },
      ]} />}
      <p className="meta">Het afzonderlijke robotrapport is alleen direct na de proef beschikbaar. Een bewijsrecord bevat geen controle van de drie deelresultaten.</p>
    </section>
  </div>;
}
