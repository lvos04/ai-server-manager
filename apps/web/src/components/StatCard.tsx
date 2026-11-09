import Link from "next/link";
import type { ReactNode } from "react";
import type { StatusView } from "@/lib/status";
import { Freshness } from "./Freshness";
import { StatusBadge } from "./StatusBadge";

/** Home-kaart: getal + eenheid + bron + laatst bijgewerkt + duidelijke vervolghandeling (08_UI). */
export function StatCard({
  id,
  title,
  value,
  unit,
  status,
  bron,
  observedAt,
  verouderd,
  action,
  children,
}: {
  id: string;
  title: string;
  value: string;
  unit?: string;
  status: StatusView;
  bron: string | null;
  observedAt: string | null;
  verouderd?: boolean;
  action: { href: string; label: string };
  children?: ReactNode;
}) {
  return (
    <section className="card stat" aria-labelledby={`kaart-${id}`} data-testid={`kaart-${id}`}>
      <div className="stat-head">
        <h2 id={`kaart-${id}`} style={{ fontSize: "1rem" }}>
          {title}
        </h2>
        <StatusBadge view={status} />
      </div>
      <p className="stat-value" data-testid={`waarde-${id}`}>
        {value}
        {unit ? <span className="unit">{unit}</span> : null}
      </p>
      {children}
      <Freshness observedAt={observedAt} bron={bron} verouderd={verouderd} />
      <p style={{ margin: 0 }}>
        <Link href={action.href}>{action.label}</Link>
      </p>
    </section>
  );
}
