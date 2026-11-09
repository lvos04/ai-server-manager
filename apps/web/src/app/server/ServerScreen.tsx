"use client";

import Link from "next/link";
import { KindSection } from "@/components/KindSection";
import { PageHeader } from "@/components/PageHeader";
import { RefreshInventory } from "@/components/RefreshInventory";
import { ErnstLabel, StatusBadge } from "@/components/StatusBadge";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { TableWrap } from "@/components/TableWrap";
import { formatBytes, formatDateTime, formatDuration, formatPercent, orUnknown } from "@/lib/format";
import { alertErnst, gpuLabel } from "@/lib/home";
import { appState, kindStatus, poolHealth } from "@/lib/status";
import type {
  AlertInfo,
  AppInfo,
  Dataset,
  Disk,
  Gpu,
  InventoryKind,
  InventorySummary,
  Pool,
  SmartResult,
  SystemInfo,
} from "@/lib/types";
import { useApi } from "@/lib/use-api";

const KIND_LABEL: Record<string, string> = {
  apps: "Apps",
  images: "Images",
  pools: "Pools",
  datasets: "Datasets",
  gpus: "GPU's",
  disks: "Schijven",
  smart: "SMART-tests",
  snapshot_tasks: "Snapshot-taken",
  cloudsync: "Cloud-sync-taken",
  replication: "Replicatie",
  alerts: "Meldingen",
  network: "Netwerk",
  system: "Systeem",
};

interface SnapshotTask {
  id: number;
  dataset: string;
  recursief: boolean;
  ingeschakeld: boolean;
  laatste_staat: string | null;
  laatste_run: string | null;
  bewaartermijn: { waarde: number; eenheid: string } | null;
}

interface Network {
  adressen: { adres: string; familie: string; interface: string }[];
  standaardroutes: string[];
}

export function ServerScreen() {
  const summary = useApi<InventorySummary>("/api/v1/inventory");
  const system = useApi<InventoryKind<SystemInfo>>("/api/v1/inventory/systeem");
  const pools = useApi<InventoryKind<Pool>>("/api/v1/inventory/pools");
  const datasets = useApi<InventoryKind<Dataset>>("/api/v1/inventory/datasets?limit=200");
  const apps = useApi<InventoryKind<AppInfo>>("/api/v1/inventory/apps");
  const gpus = useApi<InventoryKind<Gpu>>("/api/v1/inventory/gpus");
  const disks = useApi<InventoryKind<Disk>>("/api/v1/inventory/disks");
  const smart = useApi<InventoryKind<SmartResult>>("/api/v1/inventory/smart");
  const snaps = useApi<InventoryKind<SnapshotTask>>("/api/v1/inventory/snapshot-taken");
  const alerts = useApi<InventoryKind<AlertInfo>>("/api/v1/inventory/alerts");
  const network = useApi<InventoryKind<Network>>("/api/v1/inventory/netwerk");
  const all = [summary, system, pools, datasets, apps, gpus, disks, smart, snaps, alerts, network];
  const reloadAll = () => all.forEach((s) => void s.reload());

  const s = summary.data;
  const sysData = system.data?.data;
  const fresh = (k: { status: string; verouderd: boolean } | undefined) => k?.status === "ok" && !k.verouderd;

  return (
    <>
      <PageHeader
        title="Server"
        intro="Inventaris van je TrueNAS, alleen-lezen: de Hub wijzigt hier niets op de NAS. Onbekend of verouderd staat er ook zo."
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      <nav className="toc mb-4" aria-label="Onderdelen van de inventaris">
        <a href="#overzicht">Overzicht</a>
        <a href="#systeem">Systeem</a>
        <a href="#pools">Pools</a>
        <a href="#datasets">Datasets</a>
        <a href="#apps">Apps</a>
        <a href="#gpus">GPU&apos;s</a>
        <a href="#schijven">Schijven</a>
        <a href="#snapshots">Snapshot-taken</a>
        <a href="#meldingen">Meldingen</a>
        <a href="#netwerk">Netwerk</a>
      </nav>

      <div className="stack">
        <section className="card stack" id="overzicht" aria-labelledby="overzicht-titel" data-testid="sectie-overzicht">
          <h2 id="overzicht-titel">Overzicht</h2>
          {s ? (
            <>
              <dl className="kv">
                <dt>NAS-adres</dt>
                <dd>{s.nas_url ? <code>{s.nas_url}</code> : "nog niet ingesteld (D03)"}</dd>
                <dt>Laatste ophaalronde</dt>
                <dd>{s.laatste_run ? `${formatDateTime(s.laatste_run.klaar)} — ${s.laatste_run.status}` : "nog nooit"}</dd>
                <dt>TrueNAS-versie</dt>
                <dd>{orUnknown(s.laatste_run?.nas_versie)}</dd>
                <dt>Rechten van de key</dt>
                <dd>{s.laatste_run?.key_scope === "alleen_lezen" ? "alleen-lezen" : orUnknown(s.laatste_run?.key_scope)}</dd>
                <dt>Methoden bepaald via</dt>
                <dd>{orUnknown(s.laatste_run?.capability_bron)}</dd>
                <dt>Verloopt na</dt>
                <dd>{Math.round(s.ttl_seconden / 60)} minuten zonder nieuwe meting (dan onbekend)</dd>
              </dl>
              {!s.nas_url ? (
                <p>
                  <Link href="/onboarding/truenas">Koppel eerst TrueNAS (alleen-lezen)</Link>.
                </p>
              ) : (
                <RefreshInventory onDone={reloadAll} />
              )}
              <TableWrap label="Status per onderdeel van de inventaris">
                <table>
                  <caption className="sr-only">Status per onderdeel van de inventaris</caption>
                  <thead>
                    <tr>
                      <th scope="col">Onderdeel</th>
                      <th scope="col">Status</th>
                      <th scope="col">Aantal</th>
                      <th scope="col">Laatst bijgewerkt</th>
                      <th scope="col">Bron</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.soorten.map((k) => (
                      <tr key={k.kind}>
                        <td>{KIND_LABEL[k.kind] ?? k.kind}</td>
                        <td>
                          {kindStatus(k.status, k.verouderd) ? <StatusBadge view={kindStatus(k.status, k.verouderd)!} /> : <span className="text-sm">Vers</span>}
                          {k.status !== "ok" && k.reason_code ? <div className="meta">{k.reason_code}</div> : null}
                        </td>
                        <td>{k.aantal ?? "—"}</td>
                        <td>{k.observed_at ? formatDateTime(k.observed_at) : "nooit"}</td>
                        <td>{k.bron?.methode ? <code>{k.bron.methode}</code> : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </>
          ) : null}
        </section>

        <KindSection id="systeem" title="Systeem" state={system.data} error={system.error} loading={system.loading}>
          {sysData ? (
            <dl className="kv">
              <dt>Versie</dt>
              <dd>{orUnknown(sysData.versie)}</dd>
              <dt>Hostnaam</dt>
              <dd>{orUnknown(sysData.info?.hostnaam)}</dd>
              <dt>Processor</dt>
              <dd>
                {orUnknown(sysData.info?.cpu)}
                {sysData.info?.cores ? ` (${sysData.info.cores} threads)` : ""}
              </dd>
              <dt>Geheugen</dt>
              <dd>{formatBytes(sysData.info?.geheugen_bytes)}</dd>
              <dt>Uptime (bij meting)</dt>
              <dd>{formatDuration(sysData.info?.uptime_seconden)}</dd>
              <dt>Tijdzone</dt>
              <dd>{orUnknown(sysData.info?.tijdzone)}</dd>
            </dl>
          ) : null}
        </KindSection>

        <KindSection id="pools" title="Pools" state={pools.data} error={pools.error} loading={pools.loading}>
          {pools.data?.items?.length ? (
            <TableWrap label="Pools">
              <table>
                <caption className="sr-only">Pools</caption>
                <thead>
                  <tr>
                    <th scope="col">Pool</th>
                    <th scope="col">Gezondheid</th>
                    <th scope="col">TrueNAS-status</th>
                    <th scope="col">Gebruik</th>
                    <th scope="col">Vrij</th>
                    <th scope="col">Laatste scrub</th>
                  </tr>
                </thead>
                <tbody>
                  {pools.data.items.map((p) => (
                    <tr key={p.naam}>
                      <td>{p.naam}</td>
                      <td>
                        <StatusBadge view={poolHealth(p.gezond, fresh(pools.data))} />
                      </td>
                      <td>{orUnknown(p.status)}</td>
                      <td>{formatPercent(p.gebruik_pct)}</td>
                      <td>
                        {formatBytes(p.vrij_bytes)} van {formatBytes(p.grootte_bytes)}
                      </td>
                      <td>
                        {p.scrub.laatst_beeindigd ? formatDateTime(p.scrub.laatst_beeindigd) : "onbekend"}
                        {typeof p.scrub.fouten === "number" ? ` · ${p.scrub.fouten} fouten` : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : pools.data?.status === "ok" ? (
            <p>Geen pools gevonden.</p>
          ) : null}
        </KindSection>

        <KindSection id="datasets" title="Datasets" state={datasets.data} error={datasets.error} loading={datasets.loading}>
          {datasets.data?.items?.length ? (
            <>
              <TableWrap label="Datasets">
                <table>
                  <caption className="sr-only">Datasets</caption>
                  <thead>
                    <tr>
                      <th scope="col">Dataset</th>
                      <th scope="col">Type</th>
                      <th scope="col">Gebruikt</th>
                      <th scope="col">Beschikbaar</th>
                      <th scope="col">Versleuteld</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datasets.data.items.map((d) => (
                      <tr key={d.naam}>
                        <td>
                          <code>{d.naam}</code>
                        </td>
                        <td>{orUnknown(d.type)}</td>
                        <td>{formatBytes(d.gebruikt_bytes)}</td>
                        <td>{formatBytes(d.beschikbaar_bytes)}</td>
                        <td>{d.versleuteld === null ? "onbekend" : d.versleuteld ? "ja" : "nee"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
              {datasets.data.totaal !== undefined && datasets.data.totaal > (datasets.data.items?.length ?? 0) ? (
                <p className="meta">
                  {datasets.data.items.length} van {datasets.data.totaal} getoond.
                </p>
              ) : null}
            </>
          ) : null}
        </KindSection>

        <KindSection id="apps" title="Apps" state={apps.data} error={apps.error} loading={apps.loading}>
          {apps.data?.items?.length ? (
            <>
              <ul className="plain-list">
                {apps.data.items.map((a) => (
                  <li key={a.naam} className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      <strong>{a.naam}</strong>{" "}
                      <span className="meta">{a.images[0] ? <code>{a.images[0].image}</code> : "image onbekend"}</span>
                    </span>
                    <StatusBadge view={appState(fresh(apps.data) ? a.status : "onbekend")} />
                  </li>
                ))}
              </ul>
              <p>
                <Link href="/apps">Alle details per app</Link>
              </p>
            </>
          ) : null}
        </KindSection>

        <KindSection id="gpus" title="GPU's" state={gpus.data} error={gpus.error} loading={gpus.loading}>
          {gpus.data?.items?.length ? (
            <TableWrap label="GPU's">
              <table>
                <caption className="sr-only">GPU&apos;s</caption>
                <thead>
                  <tr>
                    <th scope="col">GPU</th>
                    <th scope="col">Herkend als</th>
                    <th scope="col">PCI-slot</th>
                    <th scope="col">Render-node</th>
                  </tr>
                </thead>
                <tbody>
                  {gpus.data.items.map((g) => (
                    <tr key={g.pci_slot ?? g.beschrijving ?? "gpu"}>
                      <td>{orUnknown(g.beschrijving)}</td>
                      <td>{g.herkend_als ? gpuLabel(g) : "onbekend"}</td>
                      <td>
                        <code>{orUnknown(g.pci_slot)}</code>
                      </td>
                      <td>{g.render_node ? <code>{g.render_node}</code> : "onbekend (niet meetbaar via deze methode; zie D08)"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          ) : null}
        </KindSection>

        <KindSection id="schijven" title="Schijven en SMART" state={disks.data} error={disks.error} loading={disks.loading}>
          {disks.data?.items?.length ? (
            <TableWrap label="Schijven">
              <table>
                <caption className="sr-only">Schijven</caption>
                <thead>
                  <tr>
                    <th scope="col">Schijf</th>
                    <th scope="col">Pool</th>
                    <th scope="col">Model</th>
                    <th scope="col">Grootte</th>
                    <th scope="col">Laatste SMART-test</th>
                  </tr>
                </thead>
                <tbody>
                  {disks.data.items.map((d) => {
                    const sm = fresh(smart.data) ? smart.data?.items?.find((x) => x.disk === d.naam) : undefined;
                    return (
                      <tr key={d.naam}>
                        <td>{d.naam}</td>
                        <td>{orUnknown(d.pool)}</td>
                        <td>{orUnknown(d.model)}</td>
                        <td>{formatBytes(d.grootte_bytes)}</td>
                        <td>{sm?.laatste_test ? `${orUnknown(sm.laatste_test.omschrijving)}: ${orUnknown(sm.laatste_test.status_tekst ?? sm.laatste_test.status)}` : "onbekend"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </TableWrap>
          ) : null}
        </KindSection>

        <KindSection id="snapshots" title="Snapshot-taken" state={snaps.data} error={snaps.error} loading={snaps.loading}>
          {snaps.data?.items?.length ? (
            <ul className="plain-list">
              {snaps.data.items.map((t) => (
                <li key={t.id}>
                  <code>{t.dataset}</code>
                  {t.recursief ? " (recursief)" : ""} — {t.ingeschakeld ? "ingeschakeld" : "uitgeschakeld"}, laatste run{" "}
                  {t.laatste_run ? formatDateTime(t.laatste_run) : "onbekend"} ({orUnknown(t.laatste_staat)})
                  {t.bewaartermijn ? `, bewaren ${t.bewaartermijn.waarde} ${t.bewaartermijn.eenheid.toLowerCase()}` : ""}
                </li>
              ))}
            </ul>
          ) : snaps.data?.status === "ok" ? (
            <p>Geen snapshot-taken gevonden.</p>
          ) : null}
        </KindSection>

        <KindSection id="meldingen" title="Meldingen van TrueNAS" state={alerts.data} error={alerts.error} loading={alerts.loading}>
          {alerts.data?.items?.length ? (
            <ul className="plain-list">
              {alerts.data.items.map((al) => (
                <li key={al.uuid} className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    {al.tekst}
                    <br />
                    <span className="meta">
                      {orUnknown(al.klasse)} · {al.tijd ? formatDateTime(al.tijd) : "tijd onbekend"}
                      {al.genegeerd ? " · genegeerd in TrueNAS" : ""}
                    </span>
                  </span>
                  <ErnstLabel ernst={alertErnst(al.niveau)} />
                </li>
              ))}
            </ul>
          ) : alerts.data?.status === "ok" ? (
            <p>Geen meldingen.</p>
          ) : null}
        </KindSection>

        <KindSection id="netwerk" title="Netwerk" state={network.data} error={network.error} loading={network.loading}>
          {network.data?.data?.adressen?.length ? (
            <ul className="plain-list">
              {network.data.data.adressen.map((ad) => (
                <li key={`${ad.interface}-${ad.adres}`}>
                  <code>{ad.adres}</code> op {ad.interface} ({ad.familie})
                </li>
              ))}
            </ul>
          ) : null}
        </KindSection>
      </div>
    </>
  );
}
