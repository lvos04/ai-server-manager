"use client";

import { useEffect, useState } from "react";
import { formatDateTime, formatRelative } from "@/lib/format";

/** "Laatst bijgewerkt" + bron: verplicht op elke kaart (contract §1). */
export function Freshness({
  observedAt,
  bron,
  verouderd,
  label = "Laatst bijgewerkt",
}: {
  observedAt: string | null | undefined;
  bron?: string | null;
  verouderd?: boolean;
  label?: string;
}) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, []);
  return (
    <dl className="meta" data-testid="freshness">
      <div>
        <dt>{label}: </dt>
        <dd>
          {observedAt ? (
            <time dateTime={observedAt} title={formatDateTime(observedAt)}>
              {formatDateTime(observedAt)} ({formatRelative(observedAt, now)})
            </time>
          ) : (
            "nog nooit gemeten"
          )}
          {verouderd ? " — verouderd" : ""}
        </dd>
      </div>
      <div>
        <dt>Bron: </dt>
        <dd>{bron || "onbekend"}</dd>
      </div>
    </dl>
  );
}
