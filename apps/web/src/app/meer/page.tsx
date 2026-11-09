import { ChevronRight } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { NAV_ICON } from "@/components/nav-icons";
import { MORE_LINKS } from "@/lib/nav";

export const metadata: Metadata = { title: "Meer" };

export default function Page() {
  return (
    <>
      <PageHeader title="Meer" />
      <nav aria-label="Alle onderdelen">
        <ul className="plain-list link-list" data-testid="meer-lijst">
          {MORE_LINKS.map((item) => {
            const Icon = NAV_ICON[item.icon];
            return (
              <li key={item.href}>
                <Link href={item.href}>
                  <span className="flex items-center gap-3">
                    <Icon aria-hidden="true" className="size-5 text-muted-foreground" />
                    {item.label}
                  </span>
                  <ChevronRight aria-hidden="true" className="size-5" />
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
