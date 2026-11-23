"use client";

import Link from "next/link";
import { Freshness, useNow } from "@/components/Freshness";
import { Leesstand } from "@/components/Leesstand";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import { StatusBadge } from "@/components/StatusBadge";
import { appNaam, backupGate, BRONNAMEN, datasetNaam, gateVoorwaarde, meettijd, meldreden, uren, verseApp } from "@/lib/backups";
import { formatDateTime, formatNumber } from "@/lib/format";
import { coverageCounts } from "@/lib/home";
import { coverageStatus, gateStatus, testResult } from "@/lib/status";
import type { Coverage, CoverageApp, Gate, SelfBackupList } from "@/lib/types";
import { useMeting } from "@/lib/use-meting";
import { BackupNav } from "./BackupNav";

const BRON_LABEL: Record<string, string> = {
  apps: "App-inventaris", datasets: "Datasets", snapshot_tasks: "Snapshot-taken",
  latest_snapshots: "Laatste snapshots", cloudsync: "Cloud-sync", replication: "Replicatie",
};

export function BackupsScreen() {
  const nu = useNow(1000).getTime();
  const coverage = useMeting<Coverage>("/api/v1/backups/coverage");
  const gate = useMeting<Gate>("/api/v1/gates/backup_gate");
  const r2 = useMeting<Gate>("/api/v1/gates/r2_r3_acties");
  const self = useMeting<SelfBackupList>("/api/v1/backups/self");
  const c = coverage.data;
  const oud = coverage.stale;
  const vers = (...ids: string[]) => !oud && ids.every(id => {
    const b = c?.bronnen[id];
    return b?.status === "ok" && !b.verouderd && !!meettijd(b.observed_at, nu) && nu - Date.parse(b.observed_at!) <= 900_000;
  });
  const lokaal = vers("snapshot_tasks", "latest_snapshots", "datasets");
  const extern = vers("cloudsync", "replication", "datasets");
  const counts = coverageCounts(c);
  const status = backupGate(gate.data, c, gate.stale || (gate.data?.toegestaan === true && oud), nu);
  const dbVers = (a: CoverageApp) => vers("apps") && (a.db_export.bron !== "MediaGuard-herstelrapport"
    || (verseApp(c, "mediaguard", nu) && c?.app_backups?.mediaguard?.status === "gedekt"));
  const volledig = (a: CoverageApp) => a.volledige_appbackup && dbVers(a) && a.db_export.status === "geverifieerd"
    && ((lokaal && a.lokaal_snapshot === "gedekt") || (extern && a.extern === "gedekt"));
  const badge = (waarde: string, actueel: boolean) => <StatusBadge view={coverageStatus(actueel ? waarde : "unknown")} />;
  const test = (t: { resultaat: string; uitgevoerd_op: string } | null) => t && (oud || !meettijd(t.uitgevoerd_op, nu) || !["mislukt", "geslaagd"].includes(t.resultaat))
    ? badge("unknown", false) : <StatusBadge view={testResult(t?.resultaat)} />;
  return <>
    <PageHeader title="Backups" intro="Dekking per app en dataset, herstelpunten en hersteltests." />
    <BackupNav />
    <div className="stack">
      <section className="card stack" aria-labelledby="gate-titel" data-testid="sectie-backupgate">
        <div className="stat-head"><h2 id="gate-titel">Back-upgate</h2><StatusBadge view={gateStatus(status)} /></div>
        <Leesstand bron={gate} naam="Back-upgate" />
        {status === "geblokkeerd" && <p>Gate dicht. Bijwerken wacht op de volgende voorwaarden.</p>}
        {status === "unknown" && <p>De voorwaarden zijn niet aantoonbaar vervuld. Bijwerken blijft geblokkeerd.</p>}
        {gate.data?.redenen.map((r, i) => {
          const [tekst, href] = gateVoorwaarde(r);
          return <p key={i}><Link className="losse-link" href={href}>{tekst}</Link></p>;
        })}
        {gate.data?.vereist && !gate.stale && <ul aria-label="Overige gatevoorwaarden">
          {[
            ...gate.data.vereist.besluiten.map(b => b.id), ...gate.data.vereist.metingen,
          ].filter(id => !gate.data!.redenen.some(r => r.id === id)).map(id => {
            const naam = ({ D04: "Externe back-up (D04)", D05: "Snapshotbeleid (D05)", D16: "Hersteldoelen (D16)", eigen_backup: "Eigen Hub-export", extern_backup: "Externe upload", ...BRONNAMEN } as Record<string, string>)[id];
            if (!naam) return null;
            const meting = c?.app_backups?.[id];
            const uitleg = Object.hasOwn(BRONNAMEN, id)
              ? meting?.vereist === false ? "Niet vereist" : !oud && meting?.status === "gedekt" && verseApp(c, id, nu) ? "Bevestigd" : "Onbekend"
              : status === "unknown" ? "Geen afzonderlijke blokkade gemeld" : "Voldoet volgens de gate";
            return <li key={id}>{naam} · {uitleg}</li>;
          })}
        </ul>}
        {r2.data && <p>R2/R3-acties · <StatusBadge view={gateStatus(backupGate(r2.data, c, r2.stale || (r2.data.toegestaan && (oud || status !== "toegestaan")), nu))} /></p>}
        <Freshness bron="Hub · back-upgate" observedAt={meettijd(gate.data?.afgeleid_op, nu)} verouderd={gate.stale} />
      </section>
      <Leesstand bron={coverage} naam="Back-updekking" />
      {c && <>
        <section className="card stack" aria-labelledby="bronnen-titel">
          <h2 id="bronnen-titel">Bronnen van de dekking</h2>
          <p>{counts.fresh && vers(...Object.keys(BRON_LABEL))
            ? `${c.apps.filter(volledig).length} van ${counts.totaal} apps hebben een volledige app-back-up.`
            : "Niet alle bronnen zijn actueel. De dekking is deels onbekend."}</p>
          <ul className="plain-list">{Object.entries(BRON_LABEL).map(([id, naam]) => <li key={id}>
            {naam} · {vers(id) ? "Vers" : "Onbekend"} · gemeten {formatDateTime(meettijd(c.bronnen[id]?.observed_at, nu))}
          </li>)}</ul>
          <p>Synchronisatie is geen herstelgarantie.</p>
          <h3 id="appmeldingen">Back-upmeldingen</h3>
          <ul className="plain-list" aria-label="Back-upmeldingen">
            {Object.entries(BRONNAMEN).map(([id, naam]) => {
              const rij = c.app_backups?.[id];
              const verlopen = !!rij && rij.status !== "unknown" && !verseApp(c, id, nu);
              const stand = verlopen || oud || id === "media-source-optimizer" ? "unknown" : rij?.status;
              return <li key={id} className="row justify-between">
                <span>{naam}<br /><span className="meta">
                  {verlopen || oud ? "Geen actuele meting." : stand !== "gedekt" ? meldreden(rij?.reden) : null}
                  {stand === "degraded" && " Niet gedekt."}
                  {stand === "gedekt" && rij?.leeftijd_uren != null && ` Bij controle ${formatNumber(rij.leeftijd_uren)} uur oud.`}
                  {id === "emby_exportarchief" && stand === "gedekt" && rij?.aanwezig && " Archief aanwezig."}
                  {rij?.vereist === false && " Niet vereist voor de gate."}
                  {rij?.observed_at && ` Gemeten ${formatDateTime(meettijd(rij.observed_at, nu))}.`}
                </span></span>
                <StatusBadge view={stand === "degraded" ? { tone: "degraded", label: "Beperkt" } : coverageStatus(stand)} />
              </li>;
            })}
          </ul>
        </section>
        <section className="card stack" aria-labelledby="apps-titel" data-testid="dekking-apps">
          <h2 id="apps-titel">Per app</h2>
          <ResponsiveList items={c.apps} label="Back-updekking per app" sleutel={a => a.app} tabelVanaf={768} kolommen={[
            { kop: "App", cel: a => <><Link className="losse-link break-all" href={`/backups/herstelpunten?app=${encodeURIComponent(appNaam(a.app))}`}>{appNaam(a.app)}</Link>
              <p>{oud ? "Volledigheid onbekend" : volledig(a) ? "Volledige appback-up" : "Geen volledige appback-up aangetoond"}</p></> },
            { kop: "Back-updekking", cel: a => <>
              <p>Lokaal snapshot · {badge(a.lokaal_snapshot, lokaal && vers("apps"))}</p>
              <p>Extern · {badge(a.extern, extern && vers("apps"))}</p>
              <p>DB-export · {badge(a.db_export.status, dbVers(a))}</p>
              {a.db_export.reason_code === "capability_unavailable" && <span className="meta block break-all">Niet beschikbaar (capability_unavailable)</span>}
            </> },
            { kop: "Laatste hersteltest", cel: a => <>{test(a.laatste_hersteltest)} {formatDateTime(meettijd(a.laatste_hersteltest?.uitgevoerd_op, nu))}</> },
            { kop: "Hersteldoelen", cel: a => a.rpo_rto?.bron ? <>RPO {uren(a.rpo_rto.rpo_uren)} · {badge(a.rpo_rto.rpo_status, !oud)}<br />RTO {uren(a.rpo_rto.rto_uren)} · {badge(a.rpo_rto.rto_status, !oud)}</> : <Link className="losse-link" href="/onboarding/besluit/D16">Leg RPO/RTO vast in D16</Link> },
          ]} />
        </section>
        <section className="card stack" aria-labelledby="datasets-titel" data-testid="dekking-datasets">
          <h2 id="datasets-titel">Per dataset</h2>
          {!c.datasets.length && <p>{vers("datasets") ? "Geen datasets voor deze selectie." : "Datasets onbekend."}</p>}
          <ResponsiveList items={c.datasets} label="Back-updekking per dataset" sleutel={d => d.dataset} tabelVanaf={768} kolommen={[
            { kop: "Dataset", cel: d => <span className="break-all">{datasetNaam(d.dataset) ?? "Onbekend"}</span> },
            { kop: "Apps", className: "break-all", cel: d => d.apps.map(appNaam).join(", ") || "Onbekend" },
            { kop: "Lokaal snapshot", cel: d => <>{badge(d.lokaal_snapshot.status, lokaal)} {formatDateTime(meettijd(d.lokaal_snapshot.laatste_snapshot, nu))}</> },
            { kop: "Extern", cel: d => badge(d.extern.status, extern) },
            { kop: "Hersteltest", cel: d => test(d.laatste_hersteltest) },
          ]} />
          <Freshness observedAt={meettijd(counts.observedAt, nu)} bron="TrueNAS-inventaris" verouderd={oud || !counts.fresh} label="Oudste bron gemeten" />
        </section>
      </>}
      <section className="card stack" aria-labelledby="eigen-titel" data-testid="sectie-eigen-backup">
        <h2 id="eigen-titel">Database van de Hub zelf</h2>
        <Leesstand bron={self} naam="Eigen back-up" />
        {self.data && <p>{self.stale ? "Laatste export onbekend." : self.data.laatste_geverifieerd
          ? `Geverifieerde export · checksum en inhoudsopgave gecontroleerd op ${formatDateTime(self.data.laatste_geverifieerd.beeindigd_op)}.`
          : "Er is nog geen geverifieerde export van de Hub-database."}</p>}
      </section>
    </div>
  </>;
}
