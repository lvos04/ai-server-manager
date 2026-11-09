import type { ReactNode } from "react";
import { INSTELLINGEN_SUBNAV, Subnav } from "@/components/Subnav";

/** Instellingen (OB-12): index + subpagina's; ≥ 1024 een vaste subnavigatie links (14 rem). */
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="lg:grid lg:grid-cols-[14rem_minmax(0,1fr)] lg:items-start lg:gap-8">
      <div className="hidden lg:block">
        <Subnav items={INSTELLINGEN_SUBNAV} label="Instellingen" vertical />
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
