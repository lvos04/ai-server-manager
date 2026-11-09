"use client";

import { ChevronRight, DatabaseBackup, Download, HardDrive, History, Inbox, LayoutGrid, ListChecks, Microchip, RotateCw, Sofa } from "lucide-react";
import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { useNow } from "@/components/Freshness";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { ErnstLabel, SlotLabel, StatusBadge } from "@/components/StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { formatPercent, formatRelative, formatTime } from "@/lib/format";
import {
  auditLabel,
  coverageCounts,
  freshItems,
  gpuLabel,
  homeSummary,
  partCount,
  type CatalogSummary,
  type Channel,
  type IncidentItem,
  type IncidentSummary,
  type MonitorSource,
} from "@/lib/home";
import { hasRole, useRole } from "@/lib/session";
import { gateStatus, type StatusView } from "@/lib/status";
import type { AlertInfo, Coverage, DecisionList, Gate, Gpu, InventoryKind, Pool, TrueNasStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

const REFRESH = 60_000;
const UNKNOWN: StatusView = { tone: "unknown", label: "Onbekend" };
const STALE: StatusView = { tone: "stale", label: "Verouderd" };
const NOT_YET: StatusView = { tone: "not_yet", label: "Nog niet beschikbaar" };

interface AuditList {
  items: { id: number; op: string | null; actor_id: string; actie: string }[];
}

interface Metric {
  waarde: number | null;
  status: string;
  observed_at: string | null;
  bron?: string | null;
  laatst_bekend?: { waarde: number; observed_at: string } | null;
}

interface Observability {
  gpus: { pci_slot: string; beschrijving: string | null; herkend_als: string | null; gebruik: Metric; temperatuur: Metric & { toelichting?: string } }[];
}

const TONE_BORDER: Record<string, string> = {
  down: "border-2 border-down",
  degraded: "border-2 border-degraded",
  unknown: "border-2 border-dashed border-unknown",
  healthy: "border border-border",
};

export function HomeScreen() {
  const role = useRole();
  const op = hasRole(role, "operator");
  const now = useNow(60_000);
  const truenas = useApi<TrueNasStatus>("/api/v1/truenas", REFRESH);
  const pools = useApi<InventoryKind<Pool>>("/api/v1/inventory/pools", REFRESH);
  const gpus = useApi<InventoryKind<Gpu>>("/api/v1/inventory/gpus", REFRESH);
  const obs = useApi<Observability>("/api/v1/observability/nas", REFRESH);
  const alerts = useApi<InventoryKind<AlertInfo>>("/api/v1/inventory/alerts", REFRESH);
  const catalog = useApi<CatalogSummary>("/api/v1/apps?limit=200", REFRESH);
  const incidents = useApi<IncidentSummary>("/api/v1/incidents/samenvatting", REFRESH);
  const activeInc = useApi<{ items: IncidentItem[] }>("/api/v1/incidents?status=actief&limit=20", REFRESH);
  const sources = useApi<{ items: MonitorSource[] }>(op ? "/api/v1/monitoring/sources" : null, REFRESH);
  const channels = useApi<{ items: Channel[] }>(op ? "/api/v1/notifications/channels" : null, REFRESH);
  const decisions = useApi<DecisionList>("/api/v1/decisions", REFRESH);
  const gates = useApi<{ items: Gate[] }>("/api/v1/gates", REFRESH);
  const coverage = useApi<Coverage>("/api/v1/backups/coverage", REFRESH);
  const audit = useApi<AuditList>(hasRole(role, "admin") ? "/api/v1/audit?limit=3" : null, REFRESH);
  const all = [truenas, pools, gpus, obs, alerts, catalog, incidents, activeInc, sources, channels, decisions, gates, coverage, audit];

  // O-03: bij een fout blijven de laatst bekende gegevens staan (verouderd). Een verouderde bron levert geen
  // verse invoer: de samenvatting krijgt hem dan niet, zodat onbekend nooit gezond oogt.
  const fresh = <T,>(s: { data: T | undefined; stale: boolean }) => (s.stale ? undefined : s.data);
  const summary = homeSummary({
    truenas: fresh(truenas),
    pools: pools.data && pools.stale ? { ...pools.data, status: "unknown", verouderd: true } : pools.data,
    alerts: fresh(alerts),
    catalog: fresh(catalog),
    incidents: fresh(incidents),
    activeIncidents: fresh(activeInc)?.items,
    sources: fresh(sources)?.items,
    channels: fresh(channels)?.items,
    decisions: fresh(decisions),
    gates: fresh(gates)?.items,
    coverage: fresh(coverage),
  });
  const firstError = [truenas, pools, catalog, decisions].find((s) => s.error)?.error;
  const lastOk = truenas.lastOk;

  const p = freshItems(pools.data);
  const poolsStale = p.verouderd || pools.stale;
  const g = freshItems(gpus.data);
  const cov = coverageCounts(coverage.data);
  const backupGate = gates.data?.items.find((x) => x.id === "backup_gate");
  const tested = decisions.data?.items.filter((d) => d.status === "Getest").length ?? 0;
  const healthyPools = p.items.filter((x) => x.gezond === true).length;
  const lastAudit = audit.data?.items[0];
  const cat = catalog.data;
  const catFresh = cat && !catalog.stale && cat.inventaris.status === "ok" && !cat.inventaris.verouderd;
  const inc = incidents.data;
  let kritiek = 0;
  for (const per of Object.values(inc?.per_status ?? {})) kritiek += per["kritiek"] ?? 0;

  const poolStatus: StatusView = poolsStale
    ? STALE
    : p.fresh && p.items.length
      ? healthyPools === p.items.length
        ? { tone: "healthy", label: "Gezond" }
        : { tone: "down", label: "Storing" }
      : UNKNOWN;

  return (
    <>
      <PageHeader
        title="Home"
        intro="Overzicht van je platform. Elke waarde toont bron en moment van meten; wat niet (vers) gemeten is, staat als onbekend."
        meta={lastOk ? `Bijgewerkt ${formatTime(lastOk, now)} (${formatRelative(lastOk, now)}) · vernieuwt elke 60 s` : "Nog niet bijgewerkt"}
        actions={
          <Button onClick={() => all.forEach((s) => void s.reload())}>
            <RotateCw aria-hidden="true" />
            Vernieuwen
          </Button>
        }
      />
      {firstError ? <ErrorPanel error={firstError} alert={false} title="Niet alles kon worden opgehaald" /> : null}

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <section
          className={cn("flex min-w-0 flex-col gap-3 rounded-lg bg-card p-4", TONE_BORDER[summary.overall.tone])}
          aria-labelledby="systeemstatus"
          data-testid="systeemstatus"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="systeemstatus">Systeemstatus</h2>
            <span data-testid="totaalstatus">
              <StatusBadge view={summary.overall} groot />
            </span>
          </div>
          <p className="text-sm font-semibold">{partCount(summary.parts)}</p>
          <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
            {summary.parts.map((part) => (
              <li key={part.id} data-testid={`onderdeel-${part.id}`}>
                <Link
                  href={part.href}
                  className="flex min-h-touch flex-wrap items-center gap-x-3 gap-y-1 py-2 text-foreground no-underline hover:bg-accent sm:grid sm:grid-cols-[8rem_auto_minmax(0,1fr)_auto]"
                >
                  <strong>{part.label}</strong>
                  <StatusBadge view={part.view} />
                  <span className="basis-full text-sm sm:basis-auto">{part.detail}</span>
                  <ChevronRight aria-hidden="true" className="hidden size-5 text-muted-foreground sm:block" />
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-card p-4" aria-labelledby="acties-titel">
          <h2 id="acties-titel">Wat actie nodig heeft</h2>
          {summary.actions.length ? (
            <ol className="m-0 flex list-none flex-col gap-3 p-0" data-testid="acties">
              {summary.actions.map((act) => (
                <li key={act.id} className="flex flex-col gap-2 rounded-lg border border-border p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 flex-col gap-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {act.as.soort === "ernst" ? (
                        <ErnstLabel ernst={act.as.ernst} />
                      ) : act.as.soort === "gate" ? (
                        <SlotLabel>Gate dicht</SlotLabel>
                      ) : act.as.soort === "onbekend" ? (
                        <StatusBadge view={UNKNOWN} />
                      ) : (
                        <StatusBadge view={{ tone: "neutral", label: "Onboarding", icon: "open" }} />
                      )}
                      <strong>{act.titel}</strong>
                    </div>
                    <span className="text-sm">{act.uitleg}</span>
                  </div>
                  <Link href={act.href} className={cn(buttonVariants({ variant: "secundair" }), "w-full shrink-0 sm:w-auto")}>
                    {act.knop}
                  </Link>
                </li>
              ))}
            </ol>
          ) : summary.overall.tone === "healthy" ? (
            <p>Er wacht niets op je. Gecontroleerd om {formatTime(lastOk, now)}.</p>
          ) : (
            <p className="text-muted-foreground">Geen openstaande acties in de gemeten gegevens; niet alles is vers gemeten.</p>
          )}
        </section>
      </div>

      <h2 className="mt-8 mb-4">Overzicht</h2>
      <div className="cards">
        <StatCard
          id="opslag"
          title="Opslag"
          icon={HardDrive}
          value={(p.fresh || poolsStale) && p.items.length ? `${healthyPools} van ${p.items.length}` : null}
          unit={p.items.length ? "pools gezond" : undefined}
          kwaliteit={p.fresh && !poolsStale ? "gemeten" : undefined}
          status={poolsStale ? [UNKNOWN, STALE] : poolStatus}
          bron={p.bron ?? "TrueNAS pool.query"}
          observedAt={pools.data?.observed_at ?? null}
          verouderd={poolsStale}
          reden={poolsStale ? pools.data?.melding || pools.error?.message || "De laatste meting is mislukt." : !p.fresh ? p.melding : undefined}
          geprobeerd={poolsStale ? { op: pools.data?.laatste_poging, uitkomst: pools.data?.reason_code ?? pools.error?.code ?? "mislukt" } : null}
          action={{ href: "/server#pools", label: "Pools en datasets bekijken" }}
        />
        <StatCard
          id="apps"
          title="Apps en uptime"
          icon={LayoutGrid}
          value={catFresh ? `${cat.per_status.healthy} van ${cat.totaal}` : cat && catalog.stale ? `${cat.per_status.healthy} van ${cat.totaal}` : null}
          unit={cat ? "apps gezond" : undefined}
          kwaliteit={catFresh ? "gemeten" : undefined}
          status={catFresh ? summary.parts.find((x) => x.id === "apps")!.view : catalog.stale ? [UNKNOWN, STALE] : UNKNOWN}
          bron="Appcatalogus (TrueNAS app.query + Uptime Kuma + binnenkant)"
          observedAt={cat?.inventaris.observed_at ?? null}
          verouderd={catalog.stale || Boolean(cat?.inventaris.verouderd)}
          reden={
            catFresh ? (
              <>Onbekend telt niet als gezond ({cat.per_status.unknown} onbekend). Uptime over 30 dagen volgt zodra Uptime Kuma die levert.</>
            ) : (
              "De inventaris is niet vers; de gezondheid per app is onbekend."
            )
          }
          action={{ href: "/apps", label: "Apps bekijken" }}
        />
        <StatCard
          id="gpu"
          title="GPU en AV1"
          icon={Microchip}
          value={g.fresh ? String(g.items.length) : null}
          unit={g.fresh ? (g.items.length === 1 ? "GPU gevonden" : "GPU's gevonden") : undefined}
          status={g.fresh ? { tone: "unknown", label: "Gebruik onbekend" } : g.verouderd ? [UNKNOWN, STALE] : UNKNOWN}
          bron={g.bron}
          observedAt={gpus.data?.observed_at ?? null}
          verouderd={g.verouderd}
          reden={!g.fresh ? g.melding : undefined}
          action={{ href: "/server/metrieken", label: "GPU-metrieken bekijken" }}
        >
          {obs.data?.gpus.length ? (
            <ul className="m-0 flex list-none flex-col gap-1 p-0 text-sm">
              {obs.data.gpus.map((x) => (
                <li key={x.pci_slot}>
                  <strong>{gpuLabel(x)}</strong> · gebruik{" "}
                  {x.gebruik.status === "ok" && x.gebruik.waarde !== null ? formatPercent(x.gebruik.waarde) : "onbekend"} · temperatuur onbekend (geen bron, nooit 0 °C)
                </li>
              ))}
            </ul>
          ) : null}
          <p className="text-sm">AV1-wachtrij: nog niet beschikbaar — volgt in fase P3 (MediaGuard).</p>
        </StatCard>
        <StatCard
          id="problemen"
          title="Problemen"
          icon={Inbox}
          value={inc && !incidents.stale ? String(inc.actief) : null}
          unit={inc && !incidents.stale ? `actief${kritiek ? ` · ${kritiek} kritiek` : ""}` : undefined}
          status={inc && !incidents.stale ? summary.parts.find((x) => x.id === "problemen")!.view : incidents.stale ? [UNKNOWN, STALE] : UNKNOWN}
          bron="Incidenten-inbox van de Hub"
          observedAt={inc?.bijgewerkt_op ?? null}
          verouderd={incidents.stale}
          action={{ href: "/problemen", label: "Problemen bekijken" }}
        />
        <StatCard
          id="backups"
          title="Veiligheid en back-ups"
          icon={DatabaseBackup}
          value={cov.fresh ? `${cov.volledig} van ${cov.totaal}` : null}
          unit={cov.fresh ? "apps volledig gedekt" : undefined}
          status={backupGate ? { ...gateStatus(backupGate.status), label: `Back-upgate: ${gateStatus(backupGate.status).label.toLowerCase()}` } : UNKNOWN}
          bron="Hub-dekking (TrueNAS-snapshots, cloud-sync, eigen pg_dump)"
          observedAt={cov.observedAt}
          verouderd={!cov.fresh && cov.observedAt !== null}
          reden={!cov.fresh ? "Niet alle bronnen van de dekking zijn vers gemeten." : undefined}
          action={{ href: "/backups", label: "Back-updekking bekijken" }}
        />
        <StatCard
          id="onboarding"
          title="Onboarding"
          icon={ListChecks}
          value={decisions.data ? `${tested} van ${decisions.data.items.length}` : null}
          unit={decisions.data ? "besluiten getest" : undefined}
          status={decisions.data ? { tone: "neutral", label: tested === decisions.data.items.length ? "Compleet" : "Onvolledig", icon: tested === decisions.data.items.length ? "geslaagd" : "open" } : UNKNOWN}
          bron="Besluiten D01–D18 in de Hub"
          observedAt={decisions.data ? latest(decisions.data.items.map((d) => d.updated_at)) : null}
          verouderd={decisions.stale}
          action={{ href: "/onboarding", label: "Onboarding openen" }}
        >
          {decisions.data ? (
            <div
              className="progress"
              role="progressbar"
              aria-label="Besluiten getest"
              aria-valuemin={0}
              aria-valuemax={decisions.data.items.length}
              aria-valuenow={tested}
            >
              <span style={{ width: `${decisions.data.items.length ? Math.round((tested / decisions.data.items.length) * 100) : 0}%` }} />
            </div>
          ) : null}
        </StatCard>
        <StatCard
          id="acties"
          title="Nieuwste acties"
          icon={History}
          value={hasRole(role, "admin") ? (lastAudit ? auditLabel(lastAudit.actie) : "geen") : null}
          status={hasRole(role, "admin") ? { tone: "neutral", label: "Auditspoor", icon: "min" } : { tone: "unknown", label: "Alleen voor beheerders" }}
          bron="Auditspoor van de Hub"
          observedAt={lastAudit?.op ?? null}
          reden={lastAudit ? `Door ${lastAudit.actor_id}. Uitgevoerde beheeracties via de executor volgen in P2.` : !hasRole(role, "admin") ? "Het auditspoor is alleen voor beheerders." : undefined}
          action={{ href: "/instellingen/audit", label: "Auditspoor bekijken" }}
        />
        <StatCard
          id="downloads"
          title="Downloads en bibliotheek"
          icon={Download}
          value={null}
          status={NOT_YET}
          bron="MediaGuard en MSO — nog niet gekoppeld (fase P3)"
          observedAt={null}
          reden="Nog niet beschikbaar — volgt in fase P3 (MediaGuard en MSO)."
          action={{ href: "/media", label: "Wat komt er bij Media?" }}
        />
        <StatCard
          id="huis"
          title="Huiscomfort en energie"
          icon={Sofa}
          value={null}
          status={NOT_YET}
          bron="my_house — nog niet gekoppeld (fase P3)"
          observedAt={null}
          reden="Nog niet beschikbaar — volgt in fase P3 (my_house)."
          action={{ href: "/huis", label: "Wat komt er bij Huis?" }}
        />
      </div>
    </>
  );
}

function latest(values: (string | null)[]): string | null {
  const ts = values.filter((v): v is string => Boolean(v));
  if (!ts.length) return null;
  return ts.reduce((x, y) => (Date.parse(y) > Date.parse(x) ? y : x));
}
