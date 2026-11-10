"use client";

import { RotateCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { useMinWidth } from "@/components/ResponsiveList";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { ErnstLabel, StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatRelative, formatTime } from "@/lib/format";
import type { IncidentSummary, MonitorSource } from "@/lib/home";
import { incidentStatusView, sortIncidents, type Incident, type IncidentList } from "@/lib/incidents";
import { hasRole, useRole } from "@/lib/session";
import { ernstVan } from "@/lib/status";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { IncidentDetail } from "./IncidentDetail";

const REFRESH = 30_000;
type StatusFilter = "actief" | "opgelost" | "alle";
type ErnstFilter = "" | "kritiek" | "waarschuwing" | "info";

/** IncidentRij (C-27): één link — ernst · titel · bron · eerste–laatste · ×n · status. */
function IncidentRij({ inc, actief }: { inc: Incident; actief: boolean }) {
  const now = new Date();
  return (
    <Link
      href={`/problemen/${inc.id}`}
      className={cn(
        "flex min-h-touch flex-col gap-1.5 rounded-lg border border-border bg-card p-3 text-foreground no-underline hover:bg-accent",
        actief && "border-2 border-primary bg-accent",
      )}
      aria-current={actief ? "page" : undefined}
      data-testid={`incident-${inc.id}`}
    >
      <span className="flex flex-wrap items-center gap-2">
        <ErnstLabel ernst={ernstVan(inc.ernst, inc.ernst_bron)} />
        <StatusBadge view={incidentStatusView(inc, (x) => formatTime(x, now))} />
        {inc.heropend ? <span className="rounded-sm border border-border-strong px-1.5 text-sm font-semibold">Heropend</span> : null}
        <span className="ml-auto font-mono text-sm font-semibold" aria-label={`${inc.aantal_gebeurtenissen} keer gezien`}>
          ×{inc.aantal_gebeurtenissen}
        </span>
      </span>
      <strong className="[overflow-wrap:anywhere]">{inc.titel}</strong>
      <span className="text-sm text-muted-foreground">
        {inc.bron} · eerst {formatTime(inc.eerste_gebeurtenis, now)} · laatst {formatTime(inc.laatste_gebeurtenis, now)} ({formatRelative(inc.laatste_gebeurtenis, now)})
      </span>
    </Link>
  );
}

export function ProblemenScreen({ selectedId }: { selectedId?: string }) {
  const role = useRole();
  const [status, setStatus] = useState<StatusFilter>("actief");
  const [ernst, setErnst] = useState<ErnstFilter>("");
  const [oorzaak, setOorzaak] = useState("");
  const qs = new URLSearchParams({ status, limit: "100" });
  if (ernst) qs.set("ernst", ernst);
  if (oorzaak) qs.set("oorzaak", oorzaak);
  const list = useApi<IncidentList>(`/api/v1/incidents?${qs.toString()}`, REFRESH);
  const sum = useApi<IncidentSummary>("/api/v1/incidents/samenvatting", REFRESH);
  const sources = useApi<{ items: MonitorSource[] }>(hasRole(role, "operator") ? "/api/v1/monitoring/sources" : null, REFRESH);
  const wide = useMinWidth(1280);
  const items = sortIncidents(list.data?.items ?? []);
  const now = new Date();

  // "Geen problemen" alleen als de monitoring vers is; anders Onbekend (nooit geruststellend zonder meting).
  const src = sources.data?.items.filter((s) => s.ingeschakeld) ?? [];
  const monitoringFresh = src.length > 0 && src.every((s) => s.status.status === "ok" && !s.status.verouderd);
  const lastOk = src.map((s) => s.status.laatste_ok).filter(Boolean).sort()[0] ?? null;

  const inbox = (
    <section aria-labelledby="inbox-titel" className="flex min-w-0 flex-col gap-3" data-testid="incidenten-inbox">
      <h2 id="inbox-titel" className="sr-only">
        Inbox
      </h2>
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3" data-testid="incident-filter">
        <fieldset className="border-0 p-0">
          <legend className="mb-1 text-sm">Status</legend>
          <div className="flex flex-wrap gap-2">
            {(["actief", "opgelost", "alle"] as const).map((s) => (
              <Button key={s} size="klein" variant={status === s ? "primair" : "secundair"} aria-pressed={status === s} onClick={() => setStatus(s)}>
                {s === "actief" ? "Actief" : s === "opgelost" ? "Opgelost" : "Alle"}
              </Button>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="field">
            <label htmlFor="filter-ernst">Ernst</label>
            <select id="filter-ernst" value={ernst} onChange={(e) => setErnst(e.target.value as ErnstFilter)}>
              <option value="">Alle</option>
              <option value="kritiek">Kritiek</option>
              <option value="waarschuwing">Middel</option>
              <option value="info">Info</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-oorzaak">Groeperen op oorzaak</label>
            <select id="filter-oorzaak" value={oorzaak} onChange={(e) => setOorzaak(e.target.value)}>
              <option value="">Geen groepering</option>
              {sum.data?.groepen.map((g) => (
                <option key={g.oorzaak} value={g.oorzaak}>
                  {g.oorzaak} ({g.aantal})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
      <p className="text-sm" aria-live="polite">
        {list.data ? `${items.length} ${items.length === 1 ? "incident" : "incidenten"} · actief eerst, dan ernst · filter: ${status}${ernst ? `, ${ernst === "waarschuwing" ? "middel" : ernst}` : ""}` : ""}
      </p>
      {list.error ? <ErrorPanel error={list.error} onRetry={() => void list.reload()} alert={false} /> : null}
      {list.stale ? <Melding soort="onbekend" titel="Verouderd">De lijst toont de stand van {formatTime(list.lastOk, now)}; vernieuwen is mislukt.</Melding> : null}
      {!list.data && list.loading ? <Loading regels={4} /> : null}
      {list.data && items.length === 0 ? (
        status === "actief" && !ernst && !oorzaak ? (
          monitoringFresh ? (
            <p data-testid="geen-problemen">Geen open problemen. Gecontroleerd om {formatTime(lastOk, now)}.</p>
          ) : (
            <Melding soort="onbekend" titel="Onbekend" data-testid="geen-problemen">
              <p>
                We weten niet of er problemen zijn: de monitoring is niet vers
                {lastOk ? ` (laatst ${formatTime(lastOk, now)})` : src.length ? "" : " of er is nog geen monitoringbron ingesteld"}. Er staan geen
                actieve incidenten in de inbox.
              </p>
            </Melding>
          )
        ) : (
          <p>Geen incidenten met dit filter.</p>
        )
      ) : null}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {items.map((inc) => (
          <li key={inc.id}>
            <IncidentRij inc={inc} actief={inc.id === selectedId} />
          </li>
        ))}
      </ul>
      {list.data?.next_cursor ? <p className="text-sm">Er zijn meer incidenten; verfijn het filter.</p> : null}
    </section>
  );

  if (selectedId && !wide) return <IncidentDetail id={selectedId} />;

  return (
    <>
      <PageHeader
        title="Problemen"
        intro="Eén inbox met incidenten uit monitoring, diensten en de Hub zelf. De hypothese komt uit vaste regels (geen AI); ‘Toon bewijs’ laat zien waarop hij rust."
        meta={list.lastOk ? `Bijgewerkt ${formatTime(list.lastOk, now)} · vernieuwt elke 30 s` : undefined}
        actions={
          <Button onClick={() => [list, sum, sources].forEach((s) => void s.reload())}>
            <RotateCw aria-hidden="true" />
            Vernieuwen
          </Button>
        }
      />
      {selectedId ? (
        <div className="grid grid-cols-[24rem_minmax(0,1fr)] items-start gap-6">
          {inbox}
          <IncidentDetail id={selectedId} embedded />
        </div>
      ) : wide && list.data?.items.length ? (
        // Master-detail (Peil §9) ook zonder keuze: dezelfde indeling als met een gekozen incident, zonder sprong.
        <div className="grid grid-cols-[24rem_minmax(0,1fr)] items-start gap-6">
          {inbox}
          <section className="rounded-lg border border-border bg-card p-6" aria-label="Details van een incident" data-testid="geen-incident-gekozen">
            <p className="max-w-prose">Kies links een incident. Hier zie je dan de feiten, de hypothese met bewijs, het stappenplan en de tijdlijn.</p>
          </section>
        </div>
      ) : (
        inbox
      )}
    </>
  );
}
