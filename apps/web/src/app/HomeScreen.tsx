"use client";

import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDateTime } from "@/lib/format";
import { auditLabel, coverageCounts, freshItems, gpuSummary, homeSummary } from "@/lib/home";
import { hasRole, useRole } from "@/lib/session";
import { gateStatus, type StatusView } from "@/lib/status";
import type { AlertInfo, AppInfo, Coverage, DecisionList, Gate, Gpu, InventoryKind, Pool, TrueNasStatus } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const REFRESH = 60_000;
const UNKNOWN: StatusView = { tone: "unknown", label: "Onbekend" };
const NOT_YET: StatusView = { tone: "neutral", label: "Nog niet beschikbaar" };

interface AuditList {
  items: { id: number; op: string | null; actor_id: string; actie: string }[];
}

export function HomeScreen() {
  const role = useRole();
  const truenas = useApi<TrueNasStatus>("/api/v1/truenas", REFRESH);
  const pools = useApi<InventoryKind<Pool>>("/api/v1/inventory/pools", REFRESH);
  const apps = useApi<InventoryKind<AppInfo>>("/api/v1/inventory/apps", REFRESH);
  const gpus = useApi<InventoryKind<Gpu>>("/api/v1/inventory/gpus", REFRESH);
  const alerts = useApi<InventoryKind<AlertInfo>>("/api/v1/inventory/alerts", REFRESH);
  const decisions = useApi<DecisionList>("/api/v1/decisions", REFRESH);
  const gates = useApi<{ items: Gate[] }>("/api/v1/gates", REFRESH);
  const coverage = useApi<Coverage>("/api/v1/backups/coverage", REFRESH);
  const audit = useApi<AuditList>(hasRole(role, "admin") ? "/api/v1/audit?limit=3" : null, REFRESH);

  const firstError = [truenas, pools, decisions].find((s) => s.error)?.error;
  const summary = homeSummary({
    truenas: truenas.data,
    pools: pools.data,
    apps: apps.data,
    alerts: alerts.data,
    decisions: decisions.data,
    gates: gates.data?.items,
    coverage: coverage.data,
  });

  const p = freshItems(pools.data);
  const a = freshItems(apps.data);
  const g = freshItems(gpus.data);
  const cov = coverageCounts(coverage.data);
  const backupGate = gates.data?.items.find((x) => x.id === "backup_gate");
  const tested = decisions.data?.items.filter((d) => d.status === "Getest").length;
  const healthyPools = p.items.filter((x) => x.gezond === true).length;
  const running = a.items.filter((x) => x.staat === "RUNNING").length;
  const lastAudit = audit.data?.items[0];

  return (
    <>
      <PageHeader
        title="Home"
        intro="Overzicht van je platform. Elke waarde toont bron en moment van meten; wat niet (vers) gemeten is, staat als onbekend."
        actions={
          <button type="button" className="btn" onClick={() => [truenas, pools, apps, gpus, alerts, decisions, gates, coverage, audit].forEach((s) => void s.reload())}>
            Vernieuwen
          </button>
        }
      />
      {firstError ? <ErrorPanel error={firstError} /> : null}

      <section className="card stack" aria-labelledby="systeemstatus" data-testid="systeemstatus">
        <div className="stat-head">
          <h2 id="systeemstatus">Systeemstatus</h2>
          <span data-testid="totaalstatus">
            <StatusBadge view={summary.overall} />
          </span>
        </div>
        <ul className="plain-list">
          {summary.parts.map((part) => (
            <li key={part.id} className="row" style={{ justifyContent: "space-between" }}>
              <span>
                <strong>{part.label}</strong>
                <br />
                <span className="meta">{part.detail}</span>
              </span>
              <StatusBadge view={part.view} />
            </li>
          ))}
        </ul>
        <h3>Wat actie nodig heeft</h3>
        {summary.actions.length ? (
          <ul className="plain-list link-list" data-testid="acties">
            {summary.actions.map((act) => (
              <li key={act.id}>
                <Link href={act.href}>
                  <span>{act.tekst}</span>
                  <span aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Geen openstaande acties gevonden in de gemeten gegevens.</p>
        )}
      </section>

      <h2 style={{ marginTop: 24 }}>Overzicht</h2>
      <div className="cards">
        <StatCard
          id="opslag"
          title="Opslag"
          value={p.fresh && p.items.length ? `${healthyPools} van ${p.items.length}` : "onbekend"}
          unit={p.fresh && p.items.length ? "pools gezond" : undefined}
          status={p.fresh && p.items.length ? (healthyPools === p.items.length ? { tone: "ok", label: "Gezond" } : { tone: "bad", label: "Niet gezond" }) : UNKNOWN}
          bron={p.bron}
          observedAt={pools.data?.observed_at ?? null}
          verouderd={p.verouderd}
          action={{ href: "/server#pools", label: "Bekijk pools en datasets" }}
        />
        <StatCard
          id="apps"
          title="Apps en uptime"
          value={a.fresh ? String(a.items.length) : "onbekend"}
          unit={a.fresh ? `apps · ${running} draaien volgens TrueNAS` : undefined}
          status={a.fresh ? { tone: "unknown", label: "Uptime onbekend" } : UNKNOWN}
          bron={a.bron}
          observedAt={apps.data?.observed_at ?? null}
          verouderd={a.verouderd}
          action={{ href: "/apps", label: "Bekijk apps" }}
        >
          <p className="meta" style={{ margin: 0 }}>
            Uptime en gezondheid per app volgen in fase P1 (monitoring) en P3 (connectors).
          </p>
        </StatCard>
        <StatCard
          id="gpu"
          title="GPU / AV1"
          value={g.fresh ? String(g.items.length) : "onbekend"}
          unit={g.fresh ? (g.items.length === 1 ? "GPU gevonden" : "GPU's gevonden") : undefined}
          status={g.fresh ? { tone: "unknown", label: "Gebruik onbekend" } : UNKNOWN}
          bron={g.bron}
          observedAt={gpus.data?.observed_at ?? null}
          verouderd={g.verouderd}
          action={{ href: "/server#gpus", label: "Bekijk GPU's" }}
        >
          {g.fresh && g.items.length ? <p className="meta" style={{ margin: 0 }}>{gpuSummary(g)}. AV1-gebruik volgt in P1.</p> : null}
        </StatCard>
        <StatCard
          id="backups"
          title="Veiligheid en back-ups"
          value={cov.fresh ? `${cov.volledig} van ${cov.totaal}` : "onbekend"}
          unit={cov.fresh ? "apps volledig gedekt" : undefined}
          status={backupGate ? { ...gateStatus(backupGate.status), label: `Back-upgate: ${gateStatus(backupGate.status).label.toLowerCase()}` } : UNKNOWN}
          bron="Hub-dekking (TrueNAS-snapshots, cloud-sync, eigen pg_dump)"
          observedAt={cov.observedAt}
          verouderd={!cov.fresh && cov.observedAt !== null}
          action={{ href: "/backups", label: "Bekijk back-updekking" }}
        />
        <StatCard
          id="onboarding"
          title="Onboarding"
          value={decisions.data ? `${tested ?? 0} van ${decisions.data.items.length}` : "onbekend"}
          unit={decisions.data ? "besluiten getest" : undefined}
          status={decisions.data ? (tested === decisions.data.items.length ? { tone: "ok", label: "Compleet" } : { tone: "warn", label: "Onvolledig" }) : UNKNOWN}
          bron="Besluiten D01–D18 in de Hub"
          observedAt={decisions.data ? latest(decisions.data.items.map((d) => d.updated_at)) : null}
          action={{ href: "/onboarding", label: "Naar de onboarding" }}
        />
        <StatCard
          id="acties"
          title="Nieuwste acties"
          value={hasRole(role, "admin") ? (lastAudit ? auditLabel(lastAudit.actie) : "geen") : "alleen voor beheerders"}
          status={hasRole(role, "admin") ? { tone: "info", label: "Auditspoor" } : UNKNOWN}
          bron="Auditspoor van de Hub"
          observedAt={lastAudit?.op ?? null}
          action={{ href: "/instellingen#audit", label: "Bekijk auditspoor" }}
        >
          {lastAudit ? (
            <p className="meta" style={{ margin: 0 }}>
              Door {lastAudit.actor_id} op {formatDateTime(lastAudit.op)}. Uitgevoerde beheeracties (via de executor) volgen in P2.
            </p>
          ) : null}
        </StatCard>
        <StatCard
          id="downloads"
          title="Downloads en bibliotheek"
          value="onbekend"
          status={NOT_YET}
          bron="MediaGuard en MSO — nog niet gekoppeld (fase P3)"
          observedAt={null}
          action={{ href: "/media", label: "Wat komt er bij Media?" }}
        />
        <StatCard
          id="huis"
          title="Huiscomfort en energie"
          value="onbekend"
          status={NOT_YET}
          bron="my_house — nog niet gekoppeld (fase P3)"
          observedAt={null}
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
