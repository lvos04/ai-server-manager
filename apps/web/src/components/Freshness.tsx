"use client";

import { useEffect, useState } from "react";
import { formatDateTime, formatRelative, formatTime } from "@/lib/format";

/**
 * Versheid (C-06): `dl` met Bron / Bijgewerkt (/ Geprobeerd). Geen badge en nooit groen. Relatieve tijd ververst elke
 * minuut zonder live-aankondiging. "Nog nooit gemeten" als er geen waarneming is.
 */
export function Freshness({
  observedAt,
  bron,
  verouderd,
  geprobeerd,
  label = "Bijgewerkt",
  extra,
}: {
  observedAt: string | null | undefined;
  bron?: string | null;
  verouderd?: boolean;
  geprobeerd?: { op: string | null | undefined; uitkomst: string } | null;
  label?: string;
  extra?: [string, string][];
}) {
  const now = useNow(60_000);
  return (
    <dl className="meta" data-testid="freshness">
      <div>
        <dt>Bron</dt>
        <dd>{bron || "onbekend"}</dd>
      </div>
      <div>
        <dt>{label}</dt>
        <dd>
          {observedAt ? (
            <time dateTime={observedAt} title={formatDateTime(observedAt)}>
              {formatTime(observedAt, now)} ({formatRelative(observedAt, now)})
            </time>
          ) : (
            "Nog nooit gemeten"
          )}
          {verouderd ? " · verouderd" : ""}
        </dd>
      </div>
      {geprobeerd ? (
        <div>
          <dt>Geprobeerd</dt>
          <dd>
            {geprobeerd.op ? <time dateTime={geprobeerd.op}>{formatTime(geprobeerd.op, now)}</time> : "onbekend"} · {geprobeerd.uitkomst}
          </dd>
        </div>
      ) : null}
      {extra?.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Huidige tijd die elke `ms` ververst (voor relatieve tijden en aftellen). */
export function useNow(ms: number): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}
