"use client";

import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness, useNow } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { TableWrap } from "@/components/TableWrap";
import { formatDateTime, formatNumber } from "@/lib/format";
import { coverageCounts } from "@/lib/home";
import { coverageStatus, gateStatus, kindStatus, testResult } from "@/lib/status";
import type { AppBackup, Coverage, Gate, SelfBackupList } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const BRON_LABEL: Record<string, string> = {
  apps: "Apps (app.query)",
  datasets: "Datasets",
  snapshot_tasks: "Snapshot-taken",
  latest_snapshots: "Laatste snapshots",
  cloudsync: "Cloud-sync (OneDrive)",
  replication: "Replicatie",
};

function actueel(rij: AppBackup, nu: number, verouderd: boolean) {
  return !verouderd && !!rij.observed_at && Date.parse(rij.observed_at) <= nu
    && !!rij.geldig_tot && Date.parse(rij.geldig_tot) >= nu;
}

export function BackupsScreen() {
  const nu = useNow(1000).getTime();
  const coverage = useApi<Coverage>("/api/v1/backups/coverage", 30_000);
  const gate = useApi<Gate>("/api/v1/gates/backup_gate", 30_000);
  const r2 = useApi<Gate>("/api/v1/gates/r2_r3_acties", 30_000);
  const self = useApi<SelfBackupList>("/api/v1/backups/self");
  const c = coverage.data;
  const meldingen = Object.entries(c?.app_backups ?? {});
  const vereistGedekt = (id: string) => {
    const rij = c?.app_backups?.[id];
    return rij?.status === "gedekt" && actueel(rij, nu, coverage.stale);
  };
  const mgGedekt = vereistGedekt("mediaguard");
  const dekkingBevestigd = mgGedekt && vereistGedekt("emby_exportarchief") && meldingen.every(([, rij]) =>
    !rij.vereist || (rij.status === "gedekt" && actueel(rij, nu, coverage.stale))
  );
  const apps = (c?.apps ?? []).map((app) =>
    app.db_export.bron === "MediaGuard-herstelrapport" && !mgGedekt
      ? { ...app, volledige_appbackup: false, db_export: { ...app.db_export, status: "unknown" } }
      : app
  );
  const counts = coverageCounts(c && { ...c, apps });

  return (
    <>
      <PageHeader
        title="Backups"
        intro="Dekking per app en dataset: lokale snapshots, externe kopie (OneDrive), app-consistente database-export en de laatste hersteltest. Alleen-lezen."
      />
      <div className="stack">
        <section className="card stack" aria-labelledby="gate-titel" data-testid="sectie-backupgate">
          <div className="stat-head">
            <h2 id="gate-titel">Back-upgate</h2>
            {gate.data ? <StatusBadge view={gateStatus(gate.stale || (gate.data.toegestaan && !dekkingBevestigd) ? "unknown" : gate.data.status)} /> : null}
          </div>
          {gate.error ? <ErrorPanel error={gate.error} /> : null}
          {gate.data ? (
            <>
              <p>
                Een geslaagde synchronisatie is geen herstelgarantie. Zolang deze gate dicht is, zijn R2/R3-acties niet
                beschikbaar
                {r2.data ? (
                  <>
                    {" "}
                    (R2/R3-acties: <StatusBadge view={gateStatus(r2.stale || (r2.data.toegestaan && !dekkingBevestigd) ? "unknown" : r2.data.status)} />)
                  </>
                ) : null}
                .
              </p>
              {gate.data.redenen.length ? (
                <ul>
                  {gate.data.redenen.map((r) => (
                    <li key={`${r.soort}-${r.id}`}>{r.tekst}</li>
                  ))}
                </ul>
              ) : null}
              <p className="meta">Afgeleid op {formatDateTime(gate.data.afgeleid_op)}. Een gate kan niet worden weggeklikt.</p>
            </>
          ) : null}
        </section>

        {coverage.error ? <ErrorPanel error={coverage.error} /> : null}
        {!c && coverage.loading ? <Loading /> : null}
        {c ? (
          <>
            <section className="card stack" aria-labelledby="bronnen-titel">
              <h2 id="bronnen-titel">Bronnen van de dekking</h2>
              <p>
                {counts.fresh
                  ? `${counts.volledig} van ${counts.totaal} apps hebben een volledige app-back-up.`
                  : "Niet alle bronnen zijn actueel: de dekking is daarom deels onbekend."}
              </p>
              <ul className="plain-list">
                {Object.entries(c.bronnen).map(([k, b]) => (
                  <li key={k} className="row" style={{ justifyContent: "space-between" }}>
                    <span>
                      {BRON_LABEL[k] ?? k}
                      <br />
                      <span className="meta">{b.observed_at ? `gemeten ${formatDateTime(b.observed_at)}` : "nooit gemeten"}</span>
                    </span>
                    {kindStatus(b.status, b.verouderd) ? <StatusBadge view={kindStatus(b.status, b.verouderd)!} /> : <span className="text-sm">Vers</span>}
                  </li>
                ))}
              </ul>
              <p className="meta">{c.opmerking}</p>
              {meldingen.length ? <>
                <h3>Back-upmeldingen</h3>
                <ul className="plain-list" aria-label="Back-upmeldingen">
                  {meldingen.map(([id, rij]) => {
                    const verlopen = rij.status !== "unknown" && !actueel(rij, nu, coverage.stale);
                    return (
                      <li key={id} className="row" style={{ justifyContent: "space-between" }}>
                        <span>
                          {rij.naam}
                          <br />
                          <span className="meta">
                            {verlopen ? "Geen actuele meting." : rij.reden}
                            {rij.aanwezig === true && !verlopen ? " Archief aanwezig." : null}
                            {rij.leeftijd_uren != null && !verlopen ? ` Bij controle ${formatNumber(rij.leeftijd_uren)} uur oud.` : null}
                            {rij.plaats && !verlopen ? ` Kopie in ${rij.plaats}.` : null}
                            {rij.observed_at ? ` Gemeten ${formatDateTime(rij.observed_at)}.` : null}
                          </span>
                        </span>
                        <StatusBadge view={coverageStatus(verlopen ? "unknown" : rij.status)} />
                      </li>
                    );
                  })}
                </ul>
              </> : null}
            </section>

            <section className="card stack" aria-labelledby="apps-titel" data-testid="dekking-apps">
              <h2 id="apps-titel">Per app</h2>
              <TableWrap label="Back-updekking per app">
                <table>
                  <caption className="sr-only">Back-updekking per app</caption>
                  <thead>
                    <tr>
                      <th scope="col">App</th>
                      <th scope="col">Lokaal snapshot</th>
                      <th scope="col">Extern</th>
                      <th scope="col">DB-export</th>
                      <th scope="col">Hersteltest</th>
                      <th scope="col">Volledig</th>
                      <th scope="col">RPO / RTO (D16)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {apps.map((a) => (
                      <tr key={a.app}>
                        <th scope="row">
                          {a.app}
                          {a.redenen.length ? <div className="meta" style={{ fontWeight: 400 }}>{a.redenen.join(" ")}</div> : null}
                        </th>
                        <td>
                          <StatusBadge view={coverageStatus(a.lokaal_snapshot)} />
                        </td>
                        <td>
                          <StatusBadge view={coverageStatus(a.extern)} />
                          {a.extern === "gedekt" && !a.extern_herstelgarantie ? <div className="meta">geen herstelgarantie</div> : null}
                        </td>
                        <td>
                          <StatusBadge view={coverageStatus(a.db_export.status)} />
                          {a.db_export.reason_code ? <div className="meta">{a.db_export.reason_code}</div> : null}
                        </td>
                        <td>
                          <StatusBadge view={testResult(a.laatste_hersteltest?.resultaat)} />
                          {a.laatste_hersteltest ? <div className="meta">{formatDateTime(a.laatste_hersteltest.uitgevoerd_op)}</div> : null}
                        </td>
                        <td>{a.volledige_appbackup ? <StatusBadge view={{ tone: "neutral", label: "Ja", icon: "geslaagd" }} /> : <StatusBadge view={{ tone: "neutral", label: "Nee", icon: "min" }} />}</td>
                        <td>
                          {a.rpo_rto.bron ? (
                            <>
                              RPO {formatNumber(a.rpo_rto.rpo_uren)} u: <StatusBadge view={coverageStatus(a.rpo_rto.rpo_status)} />
                              <br />
                              RTO {formatNumber(a.rpo_rto.rto_uren)} u: <StatusBadge view={coverageStatus(a.rpo_rto.rto_status)} />
                            </>
                          ) : (
                            <>
                              <StatusBadge view={{ tone: "unknown", label: "Geen doel" }} />
                              <div className="meta">
                                <Link href="/onboarding/besluit/D16" className="losse-link">
                                  Leg RPO/RTO vast in D16
                                </Link>
                              </div>
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </section>

            <section className="card stack" aria-labelledby="datasets-titel" data-testid="dekking-datasets">
              <h2 id="datasets-titel">Per dataset</h2>
              <TableWrap label="Back-updekking per dataset">
                <table>
                  <caption className="sr-only">Back-updekking per dataset</caption>
                  <thead>
                    <tr>
                      <th scope="col">Dataset</th>
                      <th scope="col">Apps</th>
                      <th scope="col">Lokaal snapshot</th>
                      <th scope="col">Extern (OneDrive e.d.)</th>
                      <th scope="col">Hersteltest</th>
                    </tr>
                  </thead>
                  <tbody>
                    {c.datasets.map((d) => (
                      <tr key={d.dataset}>
                        <th scope="row">
                          <code>{d.dataset}</code>
                        </th>
                        <td>{d.apps.join(", ") || "—"}</td>
                        <td>
                          <StatusBadge view={coverageStatus(d.lokaal_snapshot.status)} />
                          {d.lokaal_snapshot.laatste_snapshot ? <div className="meta">laatste {formatDateTime(d.lokaal_snapshot.laatste_snapshot)}</div> : null}
                        </td>
                        <td>
                          <StatusBadge view={coverageStatus(d.extern.status)} />
                          {d.extern.cloud_sync.map((cs) => (
                            <div className="meta" key={`${cs.omschrijving}`}>
                              {cs.omschrijving ?? "taak"} ({cs.provider ?? "?"}): {cs.laatste_job_staat ?? "onbekend"}
                              {cs.laatste_job_beeindigd ? `, ${formatDateTime(cs.laatste_job_beeindigd)}` : ""}
                            </div>
                          ))}
                        </td>
                        <td>
                          <StatusBadge view={testResult(d.laatste_hersteltest?.resultaat)} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
              <Freshness observedAt={counts.observedAt} bron="TrueNAS-inventaris (snapshot-taken, snapshots, cloud-sync, replicatie)" verouderd={!counts.fresh && counts.observedAt !== null} label="Oudste bron gemeten" />
            </section>
          </>
        ) : null}

        <section className="card stack" aria-labelledby="eigen-titel" data-testid="sectie-eigen-backup">
          <h2 id="eigen-titel">Database van de Hub zelf</h2>
          {self.error ? <ErrorPanel error={self.error} /> : null}
          {self.data ? (
            self.data.laatste_geverifieerd ? (
              <p>
                <StatusBadge view={{ tone: "neutral", label: "Geverifieerd", icon: "geslaagd" }} /> Laatste geverifieerde export (pg_dump + SHA-256 + pg_restore --list):{" "}
                {formatDateTime(self.data.laatste_geverifieerd.beeindigd_op)}
                {self.data.laatste_geverifieerd.inhoudsopgave_items ? ` (${self.data.laatste_geverifieerd.inhoudsopgave_items} items)` : ""}.
              </p>
            ) : (
              <p>
                <StatusBadge view={{ tone: "unknown", label: "Ontbreekt" }} /> Er is nog geen geverifieerde export van de Hub-database. De worker maakt die
                dagelijks; een export telt pas als geslaagd na controle van checksum en inhoudsopgave.
              </p>
            )
          ) : null}
        </section>
      </div>
    </>
  );
}
