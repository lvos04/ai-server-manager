"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { normalizePath } from "@/lib/nav";
import { cn } from "@/lib/utils";

export interface SubnavItem {
  href: string;
  label: string;
}

/** Subnavigatie (C-62) binnen Server en Instellingen: links (geen tabs), actief = aria-current. */
export function Subnav({ items, label, vertical }: { items: SubnavItem[]; label: string; vertical?: boolean }) {
  const p = normalizePath(usePathname() || "/");
  return (
    <nav aria-label={label} className={cn("mb-4", vertical && "lg:mb-0")}>
      <ul className={cn("m-0 flex list-none flex-wrap gap-2 p-0", vertical && "lg:flex-col lg:gap-1")}>
        {items.map((i) => {
          const active = p === i.href;
          return (
            <li key={i.href}>
              <Link
                href={i.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex min-h-touch items-center gap-2 rounded-lg border border-border-strong bg-card px-3.5 font-semibold text-foreground no-underline hover:bg-accent aria-[current=page]:border-2 aria-[current=page]:border-primary aria-[current=page]:bg-accent",
                  vertical &&
                    "lg:flex lg:w-full lg:border-0 lg:bg-transparent lg:aria-[current=page]:border-0 lg:aria-[current=page]:shadow-[inset_4px_0_0_var(--primary)]",
                )}
              >
                {i.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export const SERVER_SUBNAV: SubnavItem[] = [
  { href: "/server", label: "Overzicht" },
  { href: "/apps", label: "Apps" },
  { href: "/server/metrieken", label: "Metrieken" },
  { href: "/server/meetdekking", label: "Meetdekking" },
  { href: "/server/logs", label: "Logs" },
];

export const INSTELLINGEN_SUBNAV: SubnavItem[] = [
  { href: "/instellingen/account", label: "Account" },
  { href: "/instellingen/toegang", label: "Gebruikers en toegang" },
  { href: "/instellingen/noodaccount", label: "Noodaccount" },
  { href: "/instellingen/diensten", label: "Diensten" },
  { href: "/instellingen/monitoring", label: "Monitoring en meldingen" },
  { href: "/instellingen/apparaat", label: "Apparaat en app" },
  { href: "/instellingen/audit", label: "Auditspoor" },
  { href: "/instellingen/over", label: "Over deze Hub" },
];
