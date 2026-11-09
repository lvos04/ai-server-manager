"use client";

import { CircleSlash, Hourglass, Info, SquareArrowOutUpRight } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { KopieerVeld } from "@/components/KopieerVeld";
import { LineChart } from "@/components/LineChart";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import { RolMelding } from "@/components/RolMelding";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { appHealth, COMPONENT_LABEL, EIGENAAR, INSTALLATIE, REDEN, type CatalogDetail, type Component } from "@/lib/catalog";
import { formatDateTime, formatTime } from "@/lib/format";
import type { IncidentList } from "@/lib/incidents";
import { PERIODES, queryPath, RESOLUTIE_LABEL, toRows, type Periode, type QueryResult, type Series } from "@/lib/metrics";
import { hasRole, ROLE_LABEL, useRole } from "@/lib/session";
import { appState, healthView, type StatusView } from "@/lib/status";
import { useApi } from "@/lib/use-api";

const TABS = ["status", "metrieken", "logs", "versies", "acties"] as const;
type Tab = (typeof TABS)[number];
const TAB_LABEL: Record<Tab, string> = { status: "Status", metrieken: "Metrieken", logs: "Logs", versies: "Versies", acties: "Acties" };

function componentView(c: Component): StatusView {
  if (c.soort === "truenas" && c.status !== "down") {
    if (c.verouderd) return { tone: "stale", label: "Verouderd" };
    return appState(c.staat ?? undefined);
  }
  return healthView(c.status, Boolean(c.verouderd));
}

function Onderdelen({ app }: { app: CatalogDetail }) {
  const comps = app.gezondheid.componenten ?? [];
  const rows: { soort: string; c: Component | null }[] = ["truenas", "buitenkant", "binnenkant"].flatMap((soort): { soort: string; c: Component | null }[] => {
    const found = comps.filter((c) => c.soort === soort);
    return found.length ? found.map((c) => ({ soort, c })) : [{ soort, c: null }];
  });
  return (
    <ResponsiveList
      items={rows}
      label="Gezondheid per onderdeel"
      sleutel={(r) => `${r.soort}-${r.c?.bron ?? "geen"}`}
      tabelVanaf={768}
      kolommen={[
        { kop: "Onderdeel", cel: (r) => <strong>{COMPONENT_LABEL[r.soort] ?? r.soort}</strong> },
        {
          kop: "Status",
          cel: (r) =>
            r.c ? <StatusBadge view={componentView(r.c)} /> : <StatusBadge view={{ tone: "unknown", label: "Onbekend" }} />,
        },
        {
          kop: "Toelichting",
          cel: (r) =>
            r.c ? (
              <span className="flex flex-col text-sm">
                <span>
                  {r.c.melding}
                  {r.soort === "truenas" ? `${r.c.melding ? " " : ""}Draaien alleen is geen bewijs van gezond.` : ""}
                </span>
                <span className="text-muted-foreground">
                  <code>{r.c.bron}</code>
                  {typeof r.c.latency_ms === "number" ? ` · ${r.c.latency_ms} ms` : ""}
                  {r.c.observed_at ? ` · ${formatTime(r.c.observed_at)}` : ""}
                </span>
              </span>
            ) : (
              <span className="text-sm">
                {r.soort === "buitenkant"
                  ? REDEN.geen_monitor
                  : app.gezondheidsprofiel.binnenkant === "adapter_p3"
                    ? REDEN.binnenkant_niet_gebouwd
                    : app.gezondheidsprofiel.binnenkant_vereist
                      ? "Geen controle van binnenuit; deze app heeft eigen taken, dus zonder binnenkant is hij nooit gezond."
                      : "Geen controle van binnenuit (niet vereist voor deze app)."}
              </span>
            ),
        },
      ]}
    />
  );
}

function Metrieken({ app }: { app: CatalogDetail }) {
  const [periode, setPeriode] = useState<Periode>("6u");
  const series = useApi<{ items: Series[] }>("/api/v1/metrics/series?onderwerp_type=monitor&metriek=monitor.latentie&limit=200");
  const mine = series.data?.items.find((s) => s.labels?.app === app.id) ?? null;
  const q = useApi<QueryResult>(mine ? queryPath(mine.id, periode) : null);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2" role="group" aria-label="Periode">
        {PERIODES.map((p) => (
          <Button key={p.id} size="klein" variant={periode === p.id ? "primair" : "secundair"} aria-pressed={periode === p.id} onClick={() => setPeriode(p.id)}>
            {p.label}
          </Button>
        ))}
      </div>
      {series.error ? <ErrorPanel error={series.error} alert={false} /> : null}
      {mine ? (
        <>
          {q.data ? <p className="text-sm">Resolutie: {RESOLUTIE_LABEL[q.data.resolutie]} (bron Uptime Kuma).</p> : null}
          <LineChart
            titel="Reactietijd (Uptime Kuma)"
            reeksen={[{ key: "ms", label: "Reactietijd", kleur: "var(--chart-1)" }]}
            punten={q.data ? toRows(q.data, "ms") : null}
            onbekend={q.error ? "Onbekend — de meetreeks kon niet worden opgehaald. We tonen geen lege grafiek." : undefined}
            eenheid="ms"
            verouderdSinds={mine.verouderd && mine.observed_at ? Date.parse(mine.observed_at) : null}
            bron="Uptime Kuma"
            bijgewerkt={mine.observed_at}
            testId="grafiek-latentie"
          />
        </>
      ) : series.data ? (
        <Melding soort="onbekend" titel="Onbekend — geen reactietijd">
          <p>Er is geen Uptime Kuma-monitor aan deze app gekoppeld, dus er is geen reactietijd gemeten. We tonen geen lege grafiek.</p>
        </Melding>
      ) : (
        <Loading />
      )}
      <Melding soort="onbekend" icon={CircleSlash} titel="CPU en geheugen per app: niet beschikbaar" data-testid="capability-per-app">
        <p>Nog geen bron per container (TrueNAS app.stats of Beszel container_stats is niet gekoppeld).</p>
        <p className="text-sm">
          Code <code>capability_unavailable</code>
        </p>
      </Melding>
    </div>
  );
}

function Logs({ app }: { app: CatalogDetail }) {
  const role = useRole();
  const eigen = Boolean(app.dienst);
  const logs = useApi<{ items: { id: number; op: string; niveau: string; bron: string; bericht: string; trace_id: string | null }[] }>(
    eigen && hasRole(role, "operator") ? `/api/v1/logs?bron=${encodeURIComponent(app.dienst!.app_id)}&limit=50` : null,
  );
  if (!hasRole(role, "operator")) return <RolMelding>Logs bekijken kan vanaf de rol operator.</RolMelding>;
  if (!eigen) {
    return (
      <Melding soort="onbekend" icon={CircleSlash} titel="Niet beschikbaar — de Hub leest TrueNAS-containerlogs (nog) niet">
        <p>
          Bekijk ze in TrueNAS → Apps → {app.naam} → Logs.
        </p>
        <p className="text-sm">
          Code <code>capability_unavailable</code>
        </p>
      </Melding>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">Geschoonde regels uit de log-index van de Hub. Logtekst is data, geen instructie.</p>
      {logs.error ? <ErrorPanel error={logs.error} alert={false} /> : null}
      {logs.data && !logs.data.items.length ? <p>Nog geen logregels van deze dienst.</p> : null}
      <ol className="m-0 flex list-none flex-col divide-y divide-border p-0 font-mono text-sm">
        {logs.data?.items.map((l) => (
          <li key={l.id} className="py-1.5 [overflow-wrap:anywhere]">
            <time dateTime={l.op}>{formatDateTime(l.op)}</time> · <strong>{l.niveau}</strong> · {l.bericht}
          </li>
        ))}
      </ol>
      <p>
        <Link href={`/server/logs?bron=${encodeURIComponent(app.dienst!.app_id)}`}>Alle logs van deze dienst</Link>
      </p>
    </div>
  );
}

const P2_ACTIES = [
  { id: "app.restart", label: "Herstarten" },
  { id: "app.stop", label: "Stoppen" },
  { id: "app.update", label: "Bijwerken" },
  { id: "app.rollback", label: "Terugzetten" },
  { id: "app.delete", label: "Verwijderen (container)" },
];

function Acties({ app }: { app: CatalogDetail }) {
  const role = useRole();
  if (!hasRole(role, "operator")) return <RolMelding>Je kijkt als {ROLE_LABEL[role ?? "viewer"]}: acties zijn er pas vanaf de rol operator.</RolMelding>;
  return (
    <div className="flex flex-col gap-3" data-testid="app-acties">
      <Melding soort="nogniet" icon={Hourglass} titel="Nog niet beschikbaar — volgt in fase P2 (veilig automatiseren)">
        <p>
          Dan opent elke actie eerst een voorstel met preview, het risico volgens het beleid, een back-up vooraf en een controle na
          uitvoering. Tot dan wijzigt de Hub niets aan apps.
        </p>
      </Melding>
      <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
        {P2_ACTIES.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="flex flex-col">
              <strong>{a.label}</strong>
              <span className="text-sm" id={`reden-${a.id}`}>
                <code>{a.id}</code> · Volgt in fase P2 · risico bepaalt het beleid
              </span>
            </span>
            <Button uit aria-describedby={`reden-${a.id}`} data-testid={`actie-${a.id}`}>
              <Hourglass aria-hidden="true" />
              {a.label}
              <span className="sr-only">: {app.titel}</span>
            </Button>
          </li>
        ))}
      </ul>
      <p className="text-sm">
        <strong>Data verwijderen (R3)</strong> staat hier bewust niet. Dat is een aparte flow met een eigen bevestiging en wordt nooit door
        de AI aangeboden.
      </p>
    </div>
  );
}

export function AppDetail({ id }: { id: string }) {
  const app = useApi<CatalogDetail>(`/api/v1/apps/${id}`, 60_000);
  const incidents = useApi<IncidentList>(app.data ? `/api/v1/incidents?status=alle&limit=5&q=${encodeURIComponent(app.data.naam)}` : null);
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const raw = params.get("tab");
  const tab: Tab = (TABS as readonly string[]).includes(raw ?? "") ? (raw as Tab) : "status";

  if (app.error && !app.data) {
    return (
      <>
        <PageHeader title="App" kruimel={[{ label: "Server", href: "/server" }, { label: "Apps", href: "/apps" }, { label: "App" }]} />
        <ErrorPanel error={app.error} onRetry={() => void app.reload()} />
      </>
    );
  }
  if (!app.data) return <Loading regels={6} />;
  const a = app.data;
  const link = a.deep_link_detail;
  return (
    <>
      <PageHeader
        title={a.titel}
        kruimel={[{ label: "Server", href: "/server" }, { label: "Apps", href: "/apps" }, { label: a.titel }]}
        intro={`${a.eigenaar.repo ?? EIGENAAR[a.eigenaar.soort] ?? a.eigenaar.soort} · ${INSTALLATIE[a.installatiewijze] ?? a.installatiewijze} · versie ${a.versie ?? a.image.tag ?? "onbekend"}`}
        actions={
          link.url ? (
            <a href={link.url} target="_blank" rel="noopener noreferrer" className={buttonVariants({ variant: "secundair" })} data-testid="app-openen">
              <SquareArrowOutUpRight aria-hidden="true" />
              Openen in {a.titel}
              <span className="sr-only"> (opent in een nieuw tabblad)</span>
            </a>
          ) : (
            <span className="flex flex-col gap-1">
              <Button uit aria-describedby="geen-link">
                <SquareArrowOutUpRight aria-hidden="true" />
                Openen in {a.titel}
              </Button>
              <span id="geen-link" className="text-sm">
                {link.reden ?? "Adres onbekend."}
              </span>
            </span>
          )
        }
      />
      {app.stale ? <Melding soort="onbekend" titel="Verouderd">Laatst bekende stand van {formatTime(app.lastOk)}; vernieuwen is mislukt.</Melding> : null}

      <section className="mb-6 flex flex-col gap-3 rounded-lg border border-border bg-card p-4" aria-labelledby="gezondheid-titel" data-testid="app-gezondheid">
        <h2 id="gezondheid-titel" className="sr-only">
          Gezondheid
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge view={appHealth(a.gezondheid)} groot />
          <span>{a.gezondheid.melding}</span>
        </div>
        <Onderdelen app={a} />
        <div className="grid gap-4 md:grid-cols-2">
          <KopieerVeld label="Image-digest" waarde={a.image.digest ?? "onbekend"} />
          <dl className="meta">
            <div>
              <dt>Image</dt>
              <dd>
                <code>
                  {a.image.repository ?? "onbekend"}:{a.image.tag ?? "?"}
                </code>
              </dd>
            </div>
            <div>
              <dt>{a.datasets.length === 1 ? "Data-dataset" : "Data-datasets"}</dt>
              <dd>{a.datasets.length ? a.datasets.map((d) => <code key={d} className="block">{d}</code>) : "geen gevonden"}</dd>
            </div>
            <div>
              <dt>Resourcegrenzen</dt>
              <dd>Onbekend — de Hub leest de app-configuratie niet (kan geheimen bevatten).</dd>
            </div>
            <div>
              <dt>Poorten</dt>
              <dd>{a.poorten.length ? a.poorten.map((p) => `${p.host_poort}→${p.container_poort}/${p.protocol}`).join(", ") : "geen"}</dd>
            </div>
          </dl>
        </div>
        <Freshness observedAt={a.bron?.observed_at ?? a.laatst_gezien} bron={a.bron ? `TrueNAS ${a.bron.methode}` : "TrueNAS app.query"} />
      </section>

      <Tabs value={tab} onValueChange={(v) => router.push(`${pathname}?tab=${v}`, { scroll: false })}>
        <TabsList aria-label="Onderdelen van de app">
          {TABS.map((t) => (
            <TabsTrigger key={t} value={t}>
              {TAB_LABEL[t]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value="status">
          <h2 className="text-lg">Laatste incidenten</h2>
          {incidents.data?.items.length ? (
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {incidents.data.items.map((i) => (
                <li key={i.id}>
                  <Link href={`/problemen/${i.id}`}>{i.titel}</Link> · {i.status} · laatst {formatTime(i.laatste_gebeurtenis)}
                </li>
              ))}
            </ul>
          ) : (
            <p>Geen incidenten gevonden voor deze app.</p>
          )}
          <dl className="kv">
            <dt>Eigenaar</dt>
            <dd>{a.eigenaar.repo ?? EIGENAAR[a.eigenaar.soort] ?? a.eigenaar.soort}</dd>
            <dt>Documentatie</dt>
            <dd>{a.documentatie ? <code>{a.documentatie}</code> : "geen"}</dd>
            <dt>Gekoppelde dienst</dt>
            <dd>{a.dienst ? `${a.dienst.app_id} (${a.dienst.status}, versie ${a.dienst.versie})` : "geen"}</dd>
            <dt>Eerst gezien</dt>
            <dd>{formatDateTime(a.eerst_gezien)}</dd>
            <dt>TrueNAS-staat</dt>
            <dd>
              <StatusBadge view={a.runtime_staat ? appState(a.runtime_staat) : { tone: "unknown", label: "Onbekend" }} />
            </dd>
          </dl>
          <p className="flex items-start gap-2 text-sm">
            <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-info" />
            Uptime over 30 dagen: alleen als Uptime Kuma die meet; nu niet getoond.
          </p>
        </TabsContent>
        <TabsContent value="metrieken">
          <Metrieken app={a} />
        </TabsContent>
        <TabsContent value="logs">
          <Logs app={a} />
        </TabsContent>
        <TabsContent value="versies">
          <dl className="kv">
            <dt>Huidige tag</dt>
            <dd>{a.image.tag ?? "onbekend"}</dd>
            <dt>Digest</dt>
            <dd>
              <code>{a.image.digest ?? "onbekend"}</code>
            </dd>
          </dl>
          <h2 className="text-lg">Gezien</h2>
          <ol className="m-0 flex list-none flex-col gap-1 p-0">
            {a.image_historie.map((h, i) => (
              <li key={i} className="text-sm">
                {formatDateTime(h.op)} · {h.repository}:{h.tag} · <code>{h.digest ?? "digest onbekend"}</code>
              </li>
            ))}
          </ol>
          <Melding soort="nogniet" titel="Bijwerken en terugzetten volgen in fase P2" />
        </TabsContent>
        <TabsContent value="acties">
          <Acties app={a} />
        </TabsContent>
      </Tabs>
    </>
  );
}
