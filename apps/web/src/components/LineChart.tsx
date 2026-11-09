"use client";

import { useId, useState, useSyncExternalStore, type KeyboardEvent } from "react";
import {
  CartesianGrid,
  Line,
  LineChart as RLineChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { aantal, formatDateTime, formatTime } from "@/lib/format";
import { useNow } from "./Freshness";

export interface Reeks {
  key: string;
  label: string;
  /** Alleen Peil-grafiektokens: var(--chart-1) … var(--chart-5). */
  kleur: string;
}

export interface Punt {
  /** Tijd in ms sinds epoch. */
  t: number;
  [reeks: string]: number | null;
}

function subscribeMotion(cb: () => void) {
  const m = window.matchMedia("(prefers-reduced-motion: reduce)");
  m.addEventListener("change", cb);
  return () => m.removeEventListener("change", cb);
}

function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeMotion, () => window.matchMedia("(prefers-reduced-motion: reduce)").matches, () => true);
}

const num = new Intl.NumberFormat("nl-NL", { maximumFractionDigits: 1 });
const klein = new Intl.NumberFormat("nl-NL", { maximumSignificantDigits: 2 });
/** Getal op een as of in een label: kleine waarden houden hun cijfers (anders leest een as "0, 0, 0, 0"). */
const getal = (v: number) => (v !== 0 && Math.abs(v) < 10 ? klein.format(v) : num.format(v));

const leeg = (p: Punt, reeksen: Reeks[]) => reeksen.every((r) => typeof p[r.key] !== "number");

/** Aaneengesloten stukken zonder meting (alle reeksen leeg): van het laatste punt ervóór tot het eerste erna. */
export function gaten(punten: Punt[], reeksen: Reeks[]): { x1: number; x2: number }[] {
  const uit: { x1: number; x2: number }[] = [];
  for (let i = 0; i < punten.length; i++) {
    if (!leeg(punten[i]!, reeksen)) continue;
    let j = i;
    while (j + 1 < punten.length && leeg(punten[j + 1]!, reeksen)) j++;
    const x1 = i > 0 ? punten[i - 1]!.t : punten[i]!.t;
    const x2 = j < punten.length - 1 ? punten[j + 1]!.t : punten[j]!.t;
    if (x2 > x1) uit.push({ x1, x2 });
    i = j;
  }
  return uit;
}

/**
 * Lijngrafiek (C-32) via recharts (O-13): één y-as, lijn 2 px, gat = geen lijn (connectNulls uit) + arcering "Geen
 * meting", nooit 0; verouderd = lijn stopt + arcering "Verouderd sinds …"; eindpunt met ring en (bij één reeks) een
 * direct label. Bediening met aanwijzer én toetsenbord (plotvak tabindex=0: pijltjes, Home, End, Esc) met draadkruis,
 * zichtbare uitlezing en voorlezen via aria-live. Altijd "Toon als tabel" erbij. Kleuren alleen uit de
 * Peil-grafiektokens; status blijft gereserveerd. Tekst in teksttokens, nooit in de reekskleur.
 */
export function LineChart({
  titel,
  reeksen,
  punten: puntenOfNull,
  eenheid,
  domein,
  verouderdSinds,
  onbekend,
  bron,
  bijgewerkt,
  testId,
}: {
  titel: string;
  reeksen: Reeks[];
  /** null = nog aan het ophalen (dan nooit "Geen meting": dat zou een onware uitspraak zijn). */
  punten: Punt[] | null;
  eenheid: string;
  domein?: [number, number];
  verouderdSinds?: number | null;
  /** Ophalen mislukt zonder eerdere gegevens: eerlijke reden i.p.v. een lege grafiek. */
  onbekend?: string;
  /** Bron en tijd voor het onderschrift (Peil: elk getal heeft bron en tijd). */
  bron?: string | null;
  bijgewerkt?: string | null;
  testId?: string;
}) {
  const reduced = useReducedMotion();
  const laden = puntenOfNull === null;
  const punten = puntenOfNull ?? [];
  const now = useNow(60_000).getTime();
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const [k, setK] = useState<number | null>(null);
  const fmt = (v: number | null | undefined) => (typeof v === "number" ? `${getal(v)}${eenheid === "%" ? "%" : ` ${eenheid}`}` : "Geen meting");
  const last = punten.length ? punten[punten.length - 1]!.t : null;
  const first = punten.length ? punten[0]!.t : null;
  const span = first !== null && last !== null ? Math.max(1, last - first) : 1;
  // Een gat aan het eind valt bij "verouderd" al onder de verouderd-arcering.
  const gat = gaten(punten, reeksen).filter((g) => !(verouderdSinds && last !== null && g.x2 >= last && g.x1 >= verouderdSinds - 1));
  const eindpunten = reeksen
    .map((r) => {
      for (let i = punten.length - 1; i >= 0; i--) {
        const v = punten[i]![r.key];
        if (typeof v === "number") return { r, t: punten[i]!.t, v };
      }
      return null;
    })
    .filter((e): e is { r: Reeks; t: number; v: number } => e !== null);
  const kp = k !== null ? (punten[k] ?? null) : null;
  const tijdVan = (t: number) => formatTime(new Date(t).toISOString());
  const uitlezing = kp ? `${tijdVan(kp.t)}: ${reeksen.map((r) => (reeksen.length > 1 ? `${r.label} ${fmt(kp[r.key])}` : fmt(kp[r.key]))).join(", ")}` : "";
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const n = punten.length;
    if (!n) return;
    let next: number | null = k;
    if (e.key === "ArrowRight") next = k === null ? n - 1 : Math.min(n - 1, k + 1);
    else if (e.key === "ArrowLeft") next = k === null ? n - 1 : Math.max(0, k - 1);
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = n - 1;
    else if (e.key === "Escape") next = null;
    else return;
    e.preventDefault();
    setK(next);
  };
  const samenvatting =
    first !== null && last !== null
      ? `${titel}: ${aantal(punten.length, "meetpunt", "meetpunten")} van ${tijdVan(first)} tot ${tijdVan(last)}${gat.length ? `; ${aantal(gat.length, "periode", "perioden")} zonder meting` : ""}${verouderdSinds ? `; verouderd sinds ${tijdVan(verouderdSinds)}` : ""}. Gebruik de pijltjestoetsen om per meetpunt te lezen; de tabel hieronder bevat dezelfde gegevens.`
      : titel;
  return (
    <figure className="m-0 flex flex-col gap-2" data-testid={testId}>
      <figcaption className="font-semibold">{titel}</figcaption>
      {reeksen.length > 1 ? (
        <ul className="m-0 flex list-none flex-wrap gap-4 p-0 text-sm" aria-label="Legenda">
          {reeksen.map((r) => (
            <li key={r.key} className="flex items-center gap-2">
              <span className="inline-block h-0.5 w-4 rounded-full" style={{ background: r.kleur }} aria-hidden="true" />
              {r.label}
            </li>
          ))}
        </ul>
      ) : null}
      {punten.length ? (
        <div className="relative">
          {/* Peil C-32: plotvak role=img + tabindex=0 met pijltjestoetsen (de samenvatting staat in aria-label, de waarde
              per punt in de aria-live-regel eronder). */}
          {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-noninteractive-tabindex -- zie hierboven */}
          <div role="img" tabIndex={0} onKeyDown={onKey} onBlur={() => setK(null)} aria-label={samenvatting} className="h-56 w-full rounded-sm sm:h-64" data-testid={testId ? `${testId}-plot` : undefined}>
            <ResponsiveContainer width="100%" height="100%">
              <RLineChart data={punten} margin={{ top: 24, right: 16, bottom: 4, left: 0 }} accessibilityLayer={false}>
                <defs>
                  <pattern id={`${uid}-verouderd`} width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
                    <rect width="2" height="9" fill="var(--stale-hatch)" />
                  </pattern>
                  <pattern id={`${uid}-gat`} width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
                    <rect width="1.5" height="7" fill="var(--chart-gap)" />
                  </pattern>
                </defs>
                <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
                <XAxis
                  dataKey="t"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(t: number) => tijdVan(t)}
                  stroke="var(--chart-axis)"
                  tick={{ fill: "var(--chart-label)", fontSize: 14 }}
                  minTickGap={48}
                />
                <YAxis
                  domain={domein ?? ["auto", "auto"]}
                  tickFormatter={(v: number) => getal(v)}
                  stroke="var(--chart-axis)"
                  tick={{ fill: "var(--chart-label)", fontSize: 14 }}
                  width={48}
                />
                <Tooltip
                  isAnimationActive={false}
                  cursor={{ stroke: "var(--foreground)", strokeWidth: 1 }}
                  content={({ active, payload, label }) =>
                    active && payload?.length ? (
                      <div className="min-w-40 rounded-md border border-border-strong bg-popover p-2 text-sm shadow-md">
                        {payload.map((p) => (
                          <p key={String(p.dataKey)} className="font-semibold">
                            {reeksen.length > 1 ? `${reeksen.find((r) => r.key === p.dataKey)?.label}: ` : ""}
                            {fmt(p.value as number | null)}
                          </p>
                        ))}
                        <p className="text-muted-foreground">{formatDateTime(new Date(Number(label)).toISOString())}</p>
                      </div>
                    ) : null
                  }
                />
                {gat.map((g) => (
                  <ReferenceArea
                    key={`gat-${g.x1}`}
                    x1={g.x1}
                    x2={g.x2}
                    fill={`url(#${uid}-gat)`}
                    fillOpacity={1}
                    label={(g.x2 - g.x1) / span >= 0.15 ? { value: "Geen meting", position: "insideBottom", fill: "var(--chart-label)", fontSize: 14, fontWeight: 600 } : undefined}
                  />
                ))}
                {verouderdSinds && last ? <ReferenceArea x1={verouderdSinds} x2={Math.max(last, now)} fill={`url(#${uid}-verouderd)`} fillOpacity={1} ifOverflow="extendDomain" /> : null}
                {reeksen.map((r) => (
                  <Line key={r.key} type="linear" dataKey={r.key} stroke={r.kleur} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={!reduced} />
                ))}
                {eindpunten.map((e) => (
                  <ReferenceDot
                    key={`eind-${e.r.key}`}
                    x={e.t}
                    y={e.v}
                    r={5}
                    fill={e.r.kleur}
                    stroke="var(--card)"
                    strokeWidth={2}
                    // Direct label rechts uitgelijnd boven het eindpunt (Peil C-32): valt zo nooit buiten het plotvak.
                    label={
                      reeksen.length === 1
                        ? ({ viewBox }: { viewBox?: { x?: number; y?: number; width?: number } }) => (
                            <text x={(viewBox?.x ?? 0) + (viewBox?.width ?? 0)} y={(viewBox?.y ?? 0) - 8} textAnchor="end" fill="var(--foreground)" fontSize={14} fontWeight={600}>
                              {fmt(e.v)}
                            </text>
                          )
                        : undefined
                    }
                  />
                ))}
                {kp ? <ReferenceLine x={kp.t} stroke="var(--foreground)" strokeWidth={1} /> : null}
                {kp
                  ? reeksen.map((r) =>
                      typeof kp[r.key] === "number" ? <ReferenceDot key={`k-${r.key}`} x={kp.t} y={kp[r.key] as number} r={6} fill={r.kleur} stroke="var(--card)" strokeWidth={2} /> : null,
                    )
                  : null}
              </RLineChart>
            </ResponsiveContainer>
          </div>
          {kp ? (
            // Zichtbare uitlezing bij toetsenbordbediening (zelfde inhoud als de tooltip van de aanwijzer).
            <div className="pointer-events-none absolute top-0 right-2 z-sticky min-w-40 rounded-md border border-border-strong bg-popover p-2 text-sm shadow-md" aria-hidden="true">
              {reeksen.map((r) => (
                <p key={r.key} className="font-semibold">
                  {reeksen.length > 1 ? `${r.label}: ` : ""}
                  {fmt(kp[r.key])}
                </p>
              ))}
              <p className="text-muted-foreground">{formatDateTime(new Date(kp.t).toISOString())}</p>
            </div>
          ) : null}
          <p className="sr-only" aria-live="polite">
            {uitlezing}
          </p>
        </div>
      ) : laden && onbekend ? (
        <div className="flex min-h-24 items-center justify-center rounded-md border-2 border-dashed border-unknown bg-unknown-bg px-3 py-2 text-center text-unknown-ink">{onbekend}</div>
      ) : laden ? (
        <div className="flex h-56 items-center justify-center rounded-md border border-border px-3 py-2 text-center text-muted-foreground sm:h-64">Meetreeks ophalen…</div>
      ) : (
        <div className="arcering-gat flex min-h-24 items-center justify-center rounded-md border-2 border-dashed border-unknown px-3 py-2 text-center text-unknown-ink">
          Geen meting in deze periode.
        </div>
      )}
      {verouderdSinds ? <p className="text-sm text-unknown-ink">Verouderd sinds {tijdVan(verouderdSinds)}: daarna is er geen meting.</p> : null}
      {punten.length ? (
        <p className="text-sm text-muted-foreground">
          {bron ? `Bron: ${bron}` : null}
          {bron && bijgewerkt ? ` · bijgewerkt ${formatTime(bijgewerkt)}` : null}
          {bron ? " · " : null}
          een gat betekent dat er geen meting was (nooit 0).
        </p>
      ) : null}
      {punten.length ? (
        <details>
          <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Toon als tabel</summary>
          {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scrollbaar kader moet focusbaar zijn (axe: scrollable-region-focusable) */}
          <div className="max-h-72 overflow-y-auto" tabIndex={0} role="region" aria-label={`Tabel: ${titel}`}>
            <table>
              <caption className="sr-only">{titel}</caption>
              <thead>
                <tr>
                  <th scope="col">Tijd</th>
                  {reeksen.map((r) => (
                    <th key={r.key} scope="col">
                      {r.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {punten.map((p) => (
                  <tr key={p.t}>
                    <td>{formatDateTime(new Date(p.t).toISOString())}</td>
                    {reeksen.map((r) => (
                      <td key={r.key}>{fmt(p[r.key])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </figure>
  );
}
