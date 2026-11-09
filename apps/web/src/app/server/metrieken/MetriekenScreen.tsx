"use client";

import { Cpu, Gauge, HardDrive, MemoryStick, Network, Thermometer, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { LineChart } from "@/components/LineChart";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { Button } from "@/components/ui/button";
import { formatBytes, formatPercent, formatTime } from "@/lib/format";
import { gpuLabel } from "@/lib/home";
import { bronLabel, mergeRows, PERIODES, queryPath, RESOLUTIE_LABEL, toRows, type Periode, type QueryResult, type Series } from "@/lib/metrics";
import type { StatusView } from "@/lib/status";
import { useApi } from "@/lib/use-api";
import { cn } from "@/lib/utils";

interface Metric {
  waarde: number | null;
  eenheid: string;
  bron: string | null;
  observed_at: string | null;
  status: "ok" | "unknown" | string;
  reden: string | null;
  reeks_id?: number;
  laatst_bekend?: { waarde: number | null; observed_at: string; bron?: string } | null;
  toelichting?: string;
}

interface Obs {
  nas: { hostnaam: string | null; versie: string | null };
  cpu: { gebruik: Metric; temperatuur: Metric };
  geheugen: { totaal: Metric; gebruikt: Metric; beschikbaar_pct: Metric; zfs_arc: Metric; zfs_arc_treffers: Metric };
  pools: { naam: string; status: string | null; gezond: boolean | null; gebruik: Metric; vrij: Metric }[];
  netwerk: { totaal: { ontvangen: Metric; verzonden: Metric; toelichting: string } };
  gpus: { pci_slot: string; beschrijving: string | null; herkend_als: string | null; gebruik: Metric; vermogen: Metric; temperatuur: Metric }[];
  uitgesloten_systemen: { naam: string; reden?: string }[];
  realtime: { laatste_poging: string | null; meting: string; reden: string | null };
  ttl_seconden: number;
  observed_at: string;
}

interface Coverage {
  metrieken: { metriek: string; titel: string; gedekt: boolean }[];
  hiaten: string[];
}

const REDEN: Record<string, string> = {
  geen_bron: "geen bron levert deze meting",
  verouderd: "de laatste meting is ouder dan de TTL",
  niet_geleverd: "geen bron levert dit",
};

const UNKNOWN: StatusView = { tone: "unknown", label: "Onbekend" };
const STALE: StatusView = { tone: "stale", label: "Verouderd" };

/** Mbit/s; kleine gemeten waarden houden hun cijfers ("0,03"), zodat een meting nooit als 0 leest. */
function mbit(bps: number | null | undefined): string {
  if (typeof bps !== "number") return "";
  const v = (bps * 8) / 1_000_000;
  return new Intl.NumberFormat("nl-NL", v !== 0 && Math.abs(v) < 10 ? { maximumSignificantDigits: 2 } : { maximumFractionDigits: 1 }).format(v);
}

/** Tegel voor één meting: vers = waarde; verouderd = laatst bekend (O-03); geen bron = Onbekend zonder getal. */
function Tegel({ id, titel, icon, m, fmt, unit, status, extra }: { id: string; titel: string; icon: typeof Cpu; m: Metric; fmt: (v: number) => string; unit?: string; status?: StatusView; extra?: ReactNode }) {
  const ok = m.status === "ok" && m.waarde !== null;
  const stale = !ok && Boolean(m.laatst_bekend);
  return (
    <StatCard
      id={id}
      title={titel}
      icon={icon}
      value={ok ? fmt(m.waarde!) : stale && m.laatst_bekend?.waarde != null ? fmt(m.laatst_bekend.waarde) : null}
      unit={unit}
      kwaliteit={ok ? "gemeten" : undefined}
      // Peil §4.4 / K3: een verse waarde krijgt géén badge (de tijd en "· gemeten" zeggen genoeg); alleen afwijkingen.
      status={ok ? (status ?? []) : stale ? [UNKNOWN, STALE] : UNKNOWN}
      bron={m.bron ?? m.laatst_bekend?.bron ?? "geen bron"}
      observedAt={ok ? m.observed_at : (m.laatst_bekend?.observed_at ?? null)}
      verouderd={stale}
      reden={!ok ? `Onbekend — ${REDEN[m.reden ?? ""] ?? m.reden ?? "niet gemeten"}. We tonen geen schatting.` : undefined}
      action={{ href: "/server/meetdekking", label: "Meetdekking bekijken" }}
    >
      {extra}
    </StatCard>
  );
}

function useReeks(type: string, oid: string, metriek: string, periode: Periode) {
  const list = useApi<{ items: Series[] }>(`/api/v1/metrics/series?onderwerp_type=${type}&onderwerp_id=${encodeURIComponent(oid)}&metriek=${metriek}&limit=10`);
  const s = list.data?.items.sort((a, b) => (a.bron.startsWith("truenas") ? -1 : 0) - (b.bron.startsWith("truenas") ? -1 : 0))[0] ?? null;
  const q = useApi<QueryResult>(s ? queryPath(s.id, periode) : null);
  return { s, q, loaded: Boolean(list.data) };
}

function Grafiek({ type, oid, metriek, titel, eenheid, domein, periode, testId }: { type: string; oid: string; metriek: string; titel: string; eenheid: string; domein?: [number, number]; periode: Periode; testId?: string }) {
  const { s, q, loaded } = useReeks(type, oid, metriek, periode);
  if (!loaded) return <Loading regels={2} />;
  if (!s) {
    return (
      <div className="flex flex-col gap-2" data-testid={testId}>
        <p className="font-semibold">{titel}</p>
        <div className="arcering-gat flex min-h-24 items-center justify-center rounded-md border-2 border-dashed border-unknown px-3 py-2 text-center text-unknown-ink">Geen meting — er is nog geen reeks.</div>
      </div>
    );
  }
  return (
    <LineChart
      titel={titel}
      reeksen={[{ key: "v", label: titel, kleur: "var(--chart-1)" }]}
      punten={q.data ? toRows(q.data, "v") : null}
      onbekend={q.error ? "Onbekend — de meetreeks kon niet worden opgehaald. We tonen geen lege grafiek." : undefined}
      eenheid={eenheid}
      domein={domein}
      verouderdSinds={s.verouderd && s.observed_at ? Date.parse(s.observed_at) : null}
      bron={bronLabel(s.bron)}
      bijgewerkt={s.observed_at}
      testId={testId}
    />
  );
}

function NetwerkGrafiek({ periode }: { periode: Periode }) {
  const rx = useReeks("nas", "nas", "netwerk.ontvangen", periode);
  const tx = useReeks("nas", "nas", "netwerk.verzonden", periode);
  if (!rx.loaded || !tx.loaded) return <Loading regels={2} />;
  if (!rx.s && !tx.s) {
    return <div className="arcering-gat flex min-h-24 items-center justify-center rounded-md border-2 border-dashed border-unknown px-3 py-2 text-center text-unknown-ink">Geen meting — er is nog geen reeks voor netwerkverkeer.</div>;
  }
  const toMbit = (rows: ReturnType<typeof toRows>, key: string) => rows.map((r) => ({ ...r, [key]: typeof r[key] === "number" ? ((r[key] as number) * 8) / 1_000_000 : null }));
  return (
    <LineChart
      titel="Netwerkverkeer (Mbit/s)"
      reeksen={[
        { key: "rx", label: "Ontvangen", kleur: "var(--chart-1)" },
        { key: "tx", label: "Verzonden", kleur: "var(--chart-2)" },
      ]}
      punten={(!rx.s || rx.q.data) && (!tx.s || tx.q.data) ? mergeRows(toMbit(toRows(rx.q.data, "rx"), "rx"), toMbit(toRows(tx.q.data, "tx"), "tx")) : null}
      onbekend={rx.q.error || tx.q.error ? "Onbekend — de meetreeks kon niet worden opgehaald. We tonen geen lege grafiek." : undefined}
      eenheid="Mbit/s"
      bron={bronLabel(rx.s?.bron ?? tx.s?.bron)}
      bijgewerkt={rx.s?.observed_at ?? tx.s?.observed_at ?? null}
      testId="grafiek-netwerk"
    />
  );
}

export function MetriekenScreen() {
  const [periode, setPeriode] = useState<Periode>("6u");
  const obs = useApi<Obs>("/api/v1/observability/nas", 30_000);
  const cov = useApi<Coverage>("/api/v1/monitoring/coverage", 60_000);
  const o = obs.data;
  const gedekt = cov.data?.metrieken.filter((m) => m.gedekt).length ?? 0;
  const res = PERIODES.find((p) => p.id === periode)!;
  const resolutie = res.ms <= 6 * 3_600_000 ? "ruw" : res.ms <= 7 * 86_400_000 ? "5m" : "1u";
  return (
    <>
      <PageHeader
        title="Metrieken"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Metrieken" }]}
        intro="Live metingen van je NAS met bron en tijd. TrueNAS (reporting.realtime) gaat voor Beszel; ouder dan de TTL is onbekend, nooit 0."
        meta={o ? `Bijgewerkt ${formatTime(o.observed_at)} · verouderd na ${o.ttl_seconden} s · live-meting (reporting.realtime): ${o.realtime.meting === "ok" ? "werkt" : "onbekend"}${o.realtime.reden ? ` (${o.realtime.reden})` : ""}` : undefined}
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Periode">
          {PERIODES.map((p) => (
            <Button key={p.id} size="klein" variant={periode === p.id ? "primair" : "secundair"} aria-pressed={periode === p.id} onClick={() => setPeriode(p.id)}>
              {p.label}
            </Button>
          ))}
        </div>
        <p className="text-sm">Alle grafieken volgen deze periode; resolutie: {RESOLUTIE_LABEL[resolutie]}.</p>
      </div>
      {obs.error ? <ErrorPanel error={obs.error} onRetry={() => void obs.reload()} alert={false} /> : null}
      {!o && obs.loading ? <Loading regels={6} /> : null}
      {o ? (
        <div className="flex flex-col gap-6">
          <section aria-labelledby="nu-titel">
            <h2 id="nu-titel" className="mb-3">
              Nu
            </h2>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Tegel id="cpu" titel="CPU-gebruik" icon={Cpu} m={o.cpu.gebruik} fmt={(v) => formatPercent(v)} />
              <Tegel id="cpu-temp" titel="CPU-temperatuur" icon={Thermometer} m={o.cpu.temperatuur} fmt={(v) => `${Math.round(v)}`} unit="°C" />
              <Tegel
                id="geheugen"
                titel="Geheugen"
                icon={MemoryStick}
                m={o.geheugen.gebruikt}
                fmt={(v) => formatBytes(v)}
                unit={o.geheugen.totaal.waarde ? `van ${formatBytes(o.geheugen.totaal.waarde)}` : undefined}
                extra={
                  o.geheugen.gebruikt.waarde !== null && o.geheugen.totaal.waarde ? (
                    <div className="h-3 w-full overflow-hidden rounded-full bg-chart-meter-track" role="meter" aria-label="Geheugengebruik" aria-valuemin={0} aria-valuemax={o.geheugen.totaal.waarde} aria-valuenow={o.geheugen.gebruikt.waarde}>
                      <span className="block h-full bg-chart-1" style={{ width: `${Math.min(100, (o.geheugen.gebruikt.waarde / o.geheugen.totaal.waarde) * 100)}%` }} />
                    </div>
                  ) : null
                }
              />
              <Tegel id="arc" titel="ZFS-cache (ARC)" icon={Gauge} m={o.geheugen.zfs_arc} fmt={(v) => formatBytes(v)} extra={<p className="text-sm">Trefkans: {o.geheugen.zfs_arc_treffers.status === "ok" ? formatPercent(o.geheugen.zfs_arc_treffers.waarde) : "onbekend"}</p>} />
            </div>
          </section>

          <section className="card" aria-labelledby="cpu-titel">
            <h2 id="cpu-titel">CPU</h2>
            <Grafiek type="nas" oid="nas" metriek="cpu.gebruik" titel="CPU-gebruik (%)" eenheid="%" domein={[0, 100]} periode={periode} testId="grafiek-cpu" />
          </section>

          <section aria-labelledby="gpu-titel" data-testid="gpus">
            <h2 id="gpu-titel" className="mb-3">
              GPU&apos;s
            </h2>
            {o.gpus.length ? (
              <div className="grid gap-4 xl:grid-cols-2">
                {o.gpus.map((g) => {
                  const ok = g.gebruik.status === "ok" && g.gebruik.waarde !== null;
                  return (
                    <article key={g.pci_slot} className={cn("flex min-w-0 flex-col gap-3 rounded-lg border bg-card p-4", ok ? "border-border" : "border-2 border-dashed border-unknown")} data-testid={`gpu-${g.pci_slot}`} aria-labelledby={`gpu-${g.pci_slot}-titel`}>
                      <h3 id={`gpu-${g.pci_slot}-titel`} className="flex flex-col">
                        {gpuLabel(g)}
                        <code className="text-sm font-normal">{g.pci_slot}</code>
                      </h3>
                      <dl className="meta">
                        <div>
                          <dt>Gebruik</dt>
                          <dd>{ok ? formatPercent(g.gebruik.waarde) : `Onbekend — ${REDEN[g.gebruik.reden ?? ""] ?? g.gebruik.reden}`}</dd>
                        </div>
                        <div>
                          <dt>Vermogen</dt>
                          <dd>{g.vermogen.status === "ok" && g.vermogen.waarde !== null ? `${g.vermogen.waarde} W` : "Niet beschikbaar — capability_unavailable"}</dd>
                        </div>
                        <div>
                          <dt>Temperatuur</dt>
                          <dd data-testid="gpu-temperatuur">Onbekend — geen bron levert de GPU-temperatuur. Nooit 0 °C.</dd>
                        </div>
                        <div>
                          <dt>Bron</dt>
                          <dd>{g.gebruik.bron ?? g.gebruik.laatst_bekend?.bron ?? "geen bron"}</dd>
                        </div>
                      </dl>
                      <Grafiek type="gpu" oid={g.pci_slot} metriek="gpu.gebruik" titel={`Gebruik ${gpuLabel(g)} (%)`} eenheid="%" domein={[0, 100]} periode={periode} />
                    </article>
                  );
                })}
              </div>
            ) : (
              <p>Geen GPU&apos;s in de inventaris.</p>
            )}
          </section>

          <section className="card" aria-labelledby="opslag-titel" data-testid="opslag-meters">
            <h2 id="opslag-titel" className="flex items-center gap-2">
              <HardDrive aria-hidden="true" className="size-5 text-muted-foreground" />
              Opslag
            </h2>
            <ul className="m-0 flex list-none flex-col gap-3 p-0">
              {o.pools.map((p) => {
                const pct = p.gebruik.status === "ok" ? p.gebruik.waarde : null;
                const over = pct !== null && pct >= 90;
                return (
                  <li key={p.naam} className="flex flex-col gap-1">
                    <span className="flex flex-wrap justify-between gap-2">
                      <strong>{p.naam}</strong>
                      {pct === null ? (
                        <StatusBadge view={{ tone: "unknown", label: "Onbekend" }} />
                      ) : over ? (
                        // Meter boven de drempel (Peil §10): icoon + woord + tekst, nooit alleen de kleur van de vulling.
                        <span className="inline-flex items-center gap-1.5 font-semibold text-degraded-ink">
                          <TriangleAlert aria-hidden="true" className="size-4 text-degraded" />
                          {formatPercent(pct)} gebruikt — boven de drempel van 90%
                        </span>
                      ) : (
                        <span>{formatPercent(pct)} gebruikt</span>
                      )}
                    </span>
                    {pct !== null ? (
                      <div className="h-3 w-full overflow-hidden rounded-full bg-chart-meter-track" role="meter" aria-label={`Gebruik pool ${p.naam}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
                        <span className={cn("block h-full", over ? "bg-degraded" : "bg-chart-1")} style={{ width: `${Math.min(100, pct)}%` }} />
                      </div>
                    ) : null}
                    <span className="text-sm text-muted-foreground">
                      {p.gebruik.bron ?? "geen bron"} · {p.gebruik.observed_at ? formatTime(p.gebruik.observed_at) : "nooit gemeten"}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="card" aria-labelledby="netwerk-titel">
            <h2 id="netwerk-titel" className="flex items-center gap-2">
              <Network aria-hidden="true" className="size-5 text-muted-foreground" />
              Netwerk
            </h2>
            <dl className="meta">
              <div>
                <dt>Ontvangen</dt>
                <dd>{o.netwerk.totaal.ontvangen.status === "ok" ? `${mbit(o.netwerk.totaal.ontvangen.waarde)} Mbit/s` : "Onbekend"}</dd>
              </div>
              <div>
                <dt>Verzonden</dt>
                <dd>{o.netwerk.totaal.verzonden.status === "ok" ? `${mbit(o.netwerk.totaal.verzonden.waarde)} Mbit/s` : "Onbekend"}</dd>
              </div>
            </dl>
            <p className="text-sm">{o.netwerk.totaal.toelichting}</p>
            <NetwerkGrafiek periode={periode} />
          </section>

          <section className="card" aria-labelledby="dekking-titel">
            <h2 id="dekking-titel">Meetdekking</h2>
            {cov.data ? (
              <p>
                {gedekt} van {cov.data.metrieken.length} metrieken hebben nu een verse bron.
                {cov.data.hiaten.length ? ` Hiaten: ${cov.data.hiaten.slice(0, 6).join(", ")}${cov.data.hiaten.length > 6 ? ", …" : ""}.` : ""}
              </p>
            ) : null}
            {o.uitgesloten_systemen.length ? (
              <p className="text-sm">
                Niet meegeteld (D10): {o.uitgesloten_systemen.map((s) => s.naam).join(", ")}.
              </p>
            ) : (
              <p className="text-sm">Het Beszel-systeem van de mini-pc telt nooit mee (D10).</p>
            )}
            <p>
              <Link href="/server/meetdekking" className="losse-link">
                Meetdekking per metriek en bron
              </Link>
            </p>
          </section>
          {o.realtime.meting !== "ok" ? (
            <Melding soort="onbekend" titel="Live metingen van TrueNAS zijn onbekend">
              <p>
                reporting.realtime: {o.realtime.reden ?? "nog niet gemeten"}
                {o.realtime.laatste_poging ? ` (laatste poging ${formatTime(o.realtime.laatste_poging)})` : ""}. NIET GEVALIDEERD op een echte NAS.
              </p>
            </Melding>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
