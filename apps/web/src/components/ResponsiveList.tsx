"use client";

import { useSyncExternalStore, type ReactNode } from "react";
import { cn } from "@/lib/utils";

function subscribe(query: string) {
  return (cb: () => void) => {
    const m = window.matchMedia(query);
    m.addEventListener("change", cb);
    return () => m.removeEventListener("change", cb);
  };
}

/** Breekpunt-hook (min-width in px); server-render: smal. */
export function useMinWidth(px: number): boolean {
  const q = `(min-width: ${px}px)`;
  return useSyncExternalStore(subscribe(q), () => window.matchMedia(q).matches, () => false);
}

export interface Kolom<T> {
  kop: string;
  cel: (item: T) => ReactNode;
  className?: string;
}

/**
 * ResponsieveLijst (C-34): vanaf `tabelVanaf` (standaard 1024) een echte tabel, kleiner een kaartenlijst met dezelfde
 * velden — geen horizontaal scrollkader voor kerninformatie (K1). Precies één weergave in de DOM.
 */
export function ResponsiveList<T>({
  items,
  kolommen,
  sleutel,
  label,
  kaart,
  tabelVanaf = 1024,
  testId,
  rijTestId,
}: {
  items: T[];
  kolommen: Kolom<T>[];
  sleutel: (item: T) => string;
  label: string;
  kaart?: (item: T) => ReactNode;
  tabelVanaf?: number;
  testId?: string;
  rijTestId?: (item: T) => string;
}) {
  const breed = useMinWidth(tabelVanaf);
  if (breed) {
    return (
      <table aria-label={label} data-testid={testId}>
        <thead>
          <tr>
            {kolommen.map((k) => (
              <th key={k.kop} scope="col" className={k.className}>
                {k.kop}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={sleutel(it)} data-testid={rijTestId?.(it)}>
              {kolommen.map((k) => (
                <td key={k.kop} className={k.className}>
                  {k.cel(it)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  return (
    <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label={label} data-testid={testId}>
      {items.map((it) => (
        <li key={sleutel(it)} className="flex min-w-0 flex-col gap-2 rounded-lg border border-border bg-card p-3" data-testid={rijTestId?.(it)}>
          {kaart ? (
            kaart(it)
          ) : (
            <dl className="grid grid-cols-1 gap-1">
              {kolommen.map((k) => (
                <div key={k.kop} className={cn("flex min-w-0 flex-col")}>
                  <dt className="text-sm font-semibold text-muted-foreground">{k.kop}</dt>
                  <dd className="min-w-0 [overflow-wrap:anywhere]">{k.cel(it)}</dd>
                </div>
              ))}
            </dl>
          )}
        </li>
      ))}
    </ul>
  );
}
