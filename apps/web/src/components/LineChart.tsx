"use client";

import { useSyncExternalStore } from "react";
import { CartesianGrid, Line, LineChart as RLineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatDateTime, formatTime } from "@/lib/format";
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

/**
 * Lijngrafiek (C-32) via recharts (O-13): één y-as, lijn 2 px, gat = geen lijn (connectNulls uit) en "Geen meting" in
 * de tabel, nooit 0; verouderd = lijn stopt + arcering "Verouderd sinds …". Altijd "Toon als tabel" erbij. Kleuren
 * alleen uit de Peil-grafiektokens; status blijft gereserveerd.
 */
export function LineChart({
  titel,
  reeksen,
  punten,
  eenheid,
  domein,
  verouderdSinds,
  testId,
}: {
  titel: string;
  reeksen: Reeks[];
  punten: Punt[];
  eenheid: string;
  domein?: [number, number];
  verouderdSinds?: number | null;
  testId?: string;
}) {
  const reduced = useReducedMotion();
  const now = useNow(60_000).getTime();
  const fmt = (v: number | null | undefined) => (typeof v === "number" ? `${num.format(v)}${eenheid === "%" ? "%" : ` ${eenheid}`}` : "Geen meting");
  const last = punten.length ? punten[punten.length - 1]!.t : null;
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
        <div className="h-56 w-full sm:h-64" role="img" aria-label={`${titel}: grafiek met ${punten.length} punten; de tabel hieronder bevat dezelfde gegevens.`}>
          <ResponsiveContainer width="100%" height="100%">
            <RLineChart data={punten} margin={{ top: 8, right: 16, bottom: 4, left: 0 }} accessibilityLayer={false}>
              <defs>
                <pattern id="peil-arcering" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
                  <rect width="2" height="9" fill="var(--stale-hatch)" />
                </pattern>
              </defs>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="t"
                type="number"
                scale="time"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(t: number) => formatTime(new Date(t).toISOString())}
                stroke="var(--chart-axis)"
                tick={{ fill: "var(--chart-label)", fontSize: 14 }}
                minTickGap={48}
              />
              <YAxis
                domain={domein ?? ["auto", "auto"]}
                tickFormatter={(v: number) => num.format(v)}
                stroke="var(--chart-axis)"
                tick={{ fill: "var(--chart-label)", fontSize: 14 }}
                width={48}
              />
              <Tooltip
                isAnimationActive={false}
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <div className="min-w-40 rounded-md border border-border-strong bg-popover p-2 text-sm shadow-md">
                      <p className="font-semibold">{formatDateTime(new Date(Number(label)).toISOString())}</p>
                      {payload.map((p) => (
                        <p key={String(p.dataKey)}>
                          {reeksen.find((r) => r.key === p.dataKey)?.label}: {fmt(p.value as number | null)}
                        </p>
                      ))}
                    </div>
                  ) : null
                }
              />
              {reeksen.map((r) => (
                <Line key={r.key} type="linear" dataKey={r.key} stroke={r.kleur} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={!reduced} />
              ))}
              {verouderdSinds && last ? <ReferenceArea x1={verouderdSinds} x2={Math.max(last, now)} fill="url(#peil-arcering)" ifOverflow="extendDomain" /> : null}
            </RLineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="arcering-gat flex h-24 items-center justify-center rounded-md border-2 border-dashed border-unknown text-unknown-ink">
          Geen meting in deze periode.
        </div>
      )}
      {verouderdSinds ? <p className="text-sm text-unknown-ink">Verouderd sinds {formatTime(new Date(verouderdSinds).toISOString())}: daarna is er geen meting.</p> : null}
      {punten.length ? (
        <details>
          <summary className="flex min-h-touch cursor-pointer items-center font-semibold">Toon als tabel</summary>
          <div className="max-h-72 overflow-y-auto">
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
