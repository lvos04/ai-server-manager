import type { ReactNode } from "react";

/**
 * Tabel in een eigen scrollkader voor 2D-inhoud die niet als kaartenlijst past (datasets, schijven, auditregels,
 * gates). Kerninformatie (apps, diensten, incidenten) gebruikt ResponsieveLijst (C-34, K1). Het kader is met het
 * toetsenbord bereikbaar en heeft een naam (WCAG 2.1.1).
 */
export function TableWrap({ label, children }: { label: string; children: ReactNode }) {
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scrollbaar kader moet focusbaar zijn (axe: scrollable-region-focusable)
    <div className="table-wrap min-h-touch max-w-full overflow-x-auto rounded-lg border border-border bg-card" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}
