import type { ReactNode } from "react";

/**
 * Tabel in een eigen scrollkader (geen horizontaal scrollen van de hele pagina op mobiel). Het kader is met het
 * toetsenbord bereikbaar en heeft een naam, zodat ook toetsenbordgebruikers kunnen scrollen (WCAG 2.1.1).
 */
export function TableWrap({ label, children }: { label: string; children: ReactNode }) {
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scrollbaar kader moet focusbaar zijn (axe: scrollable-region-focusable)
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}
