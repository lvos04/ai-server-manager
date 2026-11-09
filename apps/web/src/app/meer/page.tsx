import type { Metadata } from "next";
import Link from "next/link";
import { Icon } from "@/components/Icon";
import { PageHeader } from "@/components/PageHeader";
import { MORE_LINKS } from "@/lib/nav";

export const metadata: Metadata = { title: "Meer" };

export default function Page() {
  return (
    <>
      <PageHeader title="Meer" />
      <nav aria-label="Alle onderdelen">
        <ul className="plain-list link-list" data-testid="meer-lijst">
          {MORE_LINKS.map((item) => (
            <li key={item.href}>
              <Link href={item.href}>
                <span className="row" style={{ gap: 12 }}>
                  <Icon name={item.icon} />
                  {item.label}
                </span>
                <span aria-hidden="true">→</span>
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
