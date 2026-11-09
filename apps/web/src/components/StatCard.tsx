import { ChevronRight, type LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { formatTime } from "@/lib/format";
import type { StatusView } from "@/lib/status";
import { cn } from "@/lib/utils";
import { Freshness } from "./Freshness";
import { StatusBadge } from "./StatusBadge";
import { buttonVariants } from "./ui/button";

/**
 * StatKaart (C-05): titel → badge(s) → waarde + eenheid (+ kwaliteit) → reden/extra → Versheid → precies één
 * vervolglink. Verouderd (O-03): de laatst bekende waarde blijft staan in een gearceerd waardevak met "Laatst bekend ·
 * 10:12" en de status Onbekend/Verouderd — nooit gewist en nooit als actueel. Geen waarde = geen getal (nooit 0).
 */
export function StatCard({
  id,
  title,
  icon: Icon,
  value,
  unit,
  kwaliteit,
  status,
  bron,
  observedAt,
  verouderd,
  reden,
  action,
  children,
  geprobeerd,
}: {
  id: string;
  title: string;
  icon?: LucideIcon;
  value: string | null;
  unit?: string;
  kwaliteit?: "gemeten" | "afgeleid";
  status: StatusView | StatusView[];
  bron: string | null;
  observedAt: string | null;
  verouderd?: boolean;
  reden?: ReactNode;
  action: { href: string; label: string };
  children?: ReactNode;
  geprobeerd?: { op: string | null | undefined; uitkomst: string } | null;
}) {
  const badges = Array.isArray(status) ? status : [status];
  const unknownish = badges.some((b) => b.tone === "unknown" || b.tone === "stale" || b.tone === "unlinked");
  return (
    <article
      className={cn(
        "flex min-w-0 flex-col gap-3 rounded-lg border border-border bg-card p-4",
        verouderd ? "border-2 border-dashed border-stale" : unknownish && value === null && "border-2 border-dashed border-unknown",
      )}
      aria-labelledby={`kaart-${id}-titel`}
      data-testid={`kaart-${id}`}
    >
      <h3 id={`kaart-${id}-titel`} className="flex items-center gap-2 text-lg leading-7 font-semibold">
        {Icon ? <Icon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" /> : null}
        {title}
      </h3>
      <div className="flex flex-wrap gap-2">
        {badges.map((b, i) => (
          <StatusBadge key={i} view={b} />
        ))}
      </div>
      {value !== null && verouderd ? (
        <div className="arcering rounded-md border-2 border-dashed border-stale px-3 py-2">
          <p className="text-sm font-semibold text-unknown-ink">Laatst bekend{observedAt ? ` · ${formatTime(observedAt)}` : ""}</p>
          <p className="text-3xl leading-9 text-stale-ink" data-testid={`waarde-${id}`}>
            {value}
            {unit ? <span className="ml-1.5 text-lg text-stale-ink">{unit}</span> : null}
            <span className="sr-only"> (laatst bekende waarde, verouderd)</span>
          </p>
        </div>
      ) : value !== null ? (
        <p className="text-3xl leading-9 font-semibold" data-testid={`waarde-${id}`}>
          {value}
          {unit ? <span className="ml-1.5 text-lg font-semibold text-muted-foreground">{unit}</span> : null}
          {kwaliteit ? <span className="ml-1.5 text-sm font-semibold text-muted-foreground">· {kwaliteit}</span> : null}
        </p>
      ) : (
        <p className="sr-only" data-testid={`waarde-${id}`}>
          onbekend
        </p>
      )}
      {reden ? <div className="text-sm text-foreground">{reden}</div> : null}
      {children}
      <Freshness observedAt={observedAt} bron={bron} verouderd={verouderd} geprobeerd={geprobeerd} />
      <Link href={action.href} className={cn(buttonVariants({ variant: "secundair", blok: true }), "mt-auto")}>
        {action.label}
        <ChevronRight aria-hidden="true" />
      </Link>
    </article>
  );
}
