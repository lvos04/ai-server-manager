import { ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export interface Kruimel {
  label: string;
  href?: string;
}

/** Kruimelpad (C-02): nav > ol, elk deel ≥ 44 px, laatste deel aria-current zonder link. */
export function Kruimelpad({ items }: { items: Kruimel[] }) {
  return (
    <nav aria-label="Kruimelpad" className="mb-1">
      <ol className="flex flex-wrap items-center gap-x-1 text-sm">
        {items.map((k, i) => (
          <li key={`${k.label}-${i}`} className="flex items-center gap-1">
            {i > 0 ? <ChevronRight aria-hidden="true" className="size-4 text-muted-foreground" /> : null}
            {k.href && i < items.length - 1 ? (
              <Link href={k.href} className="inline-flex min-h-touch min-w-touch items-center font-semibold">
                {k.label}
              </Link>
            ) : (
              <span aria-current="page" className="inline-flex min-h-touch items-center text-muted-foreground">
                {k.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** PageHeader (C-02): kruimelpad, h1, omschrijving, meta-regel ("Bijgewerkt …"), acties rechts (md+) of eronder. */
export function PageHeader({
  title,
  intro,
  actions,
  kruimel,
  meta,
}: {
  title: string;
  intro?: ReactNode;
  actions?: ReactNode;
  kruimel?: Kruimel[];
  meta?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-2">
      {kruimel ? <Kruimelpad items={kruimel} /> : null}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-2xl leading-8 font-bold">{title}</h1>
          {intro ? <p className="max-w-prose text-muted-foreground">{intro}</p> : null}
          {meta ? <p className="text-sm text-muted-foreground">{meta}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </div>
  );
}
