"use client";

import { RefreshCw, SquareArrowOutUpRight } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { shortDigest } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import { StatusBadge } from "@/components/StatusBadge";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { Button, buttonVariants } from "@/components/ui/button";
import { appHealth, EIGENAAR, INSTALLATIE, sortApps, type CatalogApp, type CatalogList } from "@/lib/catalog";
import { formatDate, formatTime } from "@/lib/format";
import { hasRole, useRole } from "@/lib/session";
import { useAction } from "@/lib/use-action";
import { useApi } from "@/lib/use-api";

type Filter = "alle" | "down" | "degraded" | "unknown" | "healthy";
const CHIPS: { id: Filter; label: string }[] = [
  { id: "alle", label: "Alle" },
  { id: "down", label: "Storing" },
  { id: "degraded", label: "Beperkt" },
  { id: "unknown", label: "Onbekend" },
  { id: "healthy", label: "Gezond" },
];

function DeepLink({ app }: { app: CatalogApp }) {
  if (!app.deep_link) {
    return (
      <span className="flex flex-col gap-1">
        <Button size="klein" uit aria-describedby={`geen-link-${app.id}`}>
          <SquareArrowOutUpRight aria-hidden="true" />
          Openen<span className="sr-only">: {app.titel}</span>
        </Button>
        <span id={`geen-link-${app.id}`} className="text-sm">
          Geen adres bekend (NAS-adres D03 of poort ontbreekt).
        </span>
      </span>
    );
  }
  return (
    <a href={app.deep_link} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "secundair", size: "klein" })}>
      <SquareArrowOutUpRight aria-hidden="true" />
      Openen<span className="sr-only">: {app.titel} (opent in een nieuw tabblad)</span>
    </a>
  );
}

function Versie({ app }: { app: CatalogApp }) {
  return (
    <span className="flex flex-col">
      <span>{app.image.tag ?? app.versie ?? "onbekend"}</span>
      <code className="text-sm" title={app.image.digest ?? undefined}>
        {shortDigest(app.image.digest)}
      </code>
    </span>
  );
}

function Gezondheid({ app }: { app: CatalogApp }) {
  return (
    <span className="flex flex-col gap-1">
      <StatusBadge view={appHealth(app.gezondheid)} />
      <span className="text-sm">{app.gezondheid.melding}</span>
      {!app.aanwezig && app.verdwenen_sinds ? (
        <span className="w-fit rounded-sm border border-border-strong px-1.5 text-sm font-semibold">Verdwenen sinds {formatDate(app.verdwenen_sinds)}</span>
      ) : null}
    </span>
  );
}

export function AppsScreen() {
  const role = useRole();
  const [verdwenen, setVerdwenen] = useState(false);
  const list = useApi<CatalogList>(`/api/v1/apps?limit=200${verdwenen ? "&alleen_aanwezig=false" : ""}`, 60_000);
  const discover = useAction<{ toelichting: string; nieuw: number; bijgewerkt: number; verdwenen: number }>();
  const [filter, setFilter] = useState<Filter>("alle");
  const [q, setQ] = useState("");
  const d = list.data;
  const meer = Boolean(d?.next_cursor);
  const needle = q.trim().toLowerCase();
  const items = sortApps(d?.items ?? [], meer).filter(
    (a) =>
      (filter === "alle" || a.gezondheid.status === filter) &&
      (!needle || [a.titel, a.naam, a.app_id, a.runtime_id, a.image.repository].some((v) => (v ?? "").toLowerCase().includes(needle))),
  );
  const invStale = d && (d.inventaris.verouderd || d.inventaris.status !== "ok");
  const now = new Date();

  return (
    <>
      <PageHeader
        title="Apps"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Apps" }]}
        intro="Alle apps op je NAS met gezondheid, versie, herkomst en eigenaar. Alleen lezen: beheeracties volgen in fase P2."
        meta={
          d
            ? `Catalogus bijgewerkt ${formatTime(d.observed_at, now)} · inventaris van ${d.inventaris.observed_at ? formatTime(d.inventaris.observed_at, now) : "onbekend"} (TrueNAS app.query)`
            : undefined
        }
        actions={
          hasRole(role, "operator") ? (
            <Button bezig={discover.busy} onClick={async () => (await discover.run("/api/v1/apps/discover")) && void list.reload()} data-testid="catalogus-bijwerken">
              <RefreshCw aria-hidden="true" />
              Catalogus bijwerken
            </Button>
          ) : null
        }
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      <div className="flex flex-col gap-4">
        {discover.result ? (
          <p role="status" className="text-sm" data-testid="catalogus-status">
            {discover.result.toelichting}
          </p>
        ) : null}
        {discover.error ? <ErrorPanel error={discover.error} /> : null}
        <p className="max-w-prose text-sm">
          Gezond betekent: bereikbaar én (voor apps met eigen taken) een verse controle van binnenuit. ‘Draait’ volgens TrueNAS alleen
          is nooit gezond.
        </p>

        <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3" data-testid="app-filter">
          <div className="field max-w-md">
            <label htmlFor="zoek-app">Zoek een app</label>
            <input id="zoek-app" type="search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" />
            <p className="help">Naam, app-id of image.</p>
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter op gezondheid">
            {CHIPS.map((c) => {
              const n = c.id === "alle" ? (d?.totaal ?? 0) : (d?.per_status[c.id] ?? 0);
              return (
                <Button key={c.id} size="klein" variant={filter === c.id ? "primair" : "secundair"} aria-pressed={filter === c.id} onClick={() => setFilter(c.id)}>
                  {c.label} <span className="font-mono">({n})</span>
                </Button>
              );
            })}
          </div>
          <label className="keuze w-fit">
            <input type="checkbox" checked={verdwenen} onChange={(e) => setVerdwenen(e.target.checked)} />
            Ook verdwenen apps tonen
          </label>
        </div>

        <p className="text-sm" aria-live="polite" data-testid="app-teller">
          {d ? `${items.length} ${items.length === 1 ? "app" : "apps"} · ${meer ? "op naam" : "slechtste status eerst"} · filter: ${CHIPS.find((c) => c.id === filter)?.label.toLowerCase()}` : ""}
        </p>
        {meer ? <Melding soort="info">Meer dan 200 apps: gesorteerd op naam.</Melding> : null}
        {invStale ? (
          <Melding soort="onbekend" titel={`Inventaris verouderd (laatst ${formatTime(d?.inventaris.observed_at, now)})`}>
            <p>
              Elke app staat daarom op Onbekend of Verouderd met de laatst bekende TrueNAS-staat. <Link href="/server">Vernieuw de inventaris.</Link>
            </p>
          </Melding>
        ) : null}
        {list.error ? <ErrorPanel error={list.error} onRetry={() => void list.reload()} alert={false} /> : null}
        {!d && list.loading ? <Loading regels={5} /> : null}
        {d && d.totaal === 0 && !verdwenen ? (
          <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4">
            <p>Nog geen apps in de catalogus. De catalogus vult zich na een geslaagde inventaris.</p>
            <p>
              <Link href="/server" className={buttonVariants({ variant: "primair" })}>
                Inventaris vernieuwen
              </Link>
            </p>
          </div>
        ) : null}
        {d && items.length ? (
          <ResponsiveList
            items={items}
            label="Apps in de catalogus"
            testId="app-lijst"
            sleutel={(a) => a.id}
            rijTestId={(a) => `app-${a.runtime_id}`}
            kolommen={[
              {
                kop: "App",
                cel: (a) => (
                  <span className="flex flex-col">
                    <Link href={`/apps/${a.id}`} className="losse-link font-semibold">
                      {a.titel}
                    </Link>
                    <code className="text-sm">{a.runtime_id}</code>
                  </span>
                ),
              },
              { kop: "Gezondheid", cel: (a) => <Gezondheid app={a} /> },
              { kop: "Versie", cel: (a) => <Versie app={a} /> },
              {
                kop: "Installatie en eigenaar",
                cel: (a) => (
                  <span className="flex flex-col text-sm">
                    <span>{INSTALLATIE[a.installatiewijze] ?? a.installatiewijze}</span>
                    <span>{a.eigenaar.repo ?? EIGENAAR[a.eigenaar.soort] ?? a.eigenaar.soort}</span>
                  </span>
                ),
              },
              { kop: "Openen", cel: (a) => <DeepLink app={a} /> },
            ]}
            kaart={(a) => (
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <span className="flex min-w-0 flex-col">
                    <Link href={`/apps/${a.id}`} className="losse-link font-semibold">
                      {a.titel}
                    </Link>
                    <code className="text-sm">{a.runtime_id}</code>
                  </span>
                  <DeepLink app={a} />
                </div>
                <Gezondheid app={a} />
                <dl className="meta">
                  <div>
                    <dt>Versie</dt>
                    <dd>
                      {a.image.tag ?? "onbekend"} · <code>{shortDigest(a.image.digest)}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Installatie</dt>
                    <dd>{INSTALLATIE[a.installatiewijze] ?? a.installatiewijze}</dd>
                  </div>
                  <div>
                    <dt>Eigenaar</dt>
                    <dd>{a.eigenaar.repo ?? EIGENAAR[a.eigenaar.soort] ?? a.eigenaar.soort}</dd>
                  </div>
                </dl>
              </div>
            )}
          />
        ) : d && d.totaal > 0 ? (
          <p>Geen apps met dit filter.</p>
        ) : null}
      </div>
    </>
  );
}
