"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { PageHeader } from "@/components/PageHeader";
import { INSTELLINGEN_SUBNAV } from "@/components/Subnav";

/** Oude ankers van de P0-pagina → subpagina (links op Home en in oude bladwijzers blijven werken). */
const ANKER: Record<string, string> = {
  account: "/instellingen/account",
  weergave: "/instellingen/account",
  sessies: "/instellingen/account",
  gebruikers: "/instellingen/toegang",
  audit: "/instellingen/audit",
  over: "/instellingen/over",
};

const UITLEG: Record<string, string> = {
  "/instellingen/account": "Naam, wachtwoord, thema en je eigen sessies.",
  "/instellingen/toegang": "Gebruikers en rollen (ook kind), alle sessies en inloggen via SSO.",
  "/instellingen/noodaccount": "Noodlogin met wachtwoord en TOTP, voor als SSO niet werkt.",
  "/instellingen/diensten": "Diensten koppelen met een koppelcode of enrollment-token, rotatie en intrekken.",
  "/instellingen/monitoring": "Uptime Kuma, Beszel, alertregels, Gotify en melden als de Hub uitvalt.",
  "/instellingen/apparaat": "Offline-schil (PWA) op dit apparaat.",
  "/instellingen/audit": "Wie wat deed, en de controle van de auditketting.",
  "/instellingen/over": "Versies, validatiestatus en links.",
};

export function InstellingenIndex() {
  const router = useRouter();
  useEffect(() => {
    const hash = window.location.hash.replace(/^#/, "");
    if (hash && ANKER[hash]) router.replace(ANKER[hash]);
  }, [router]);
  return (
    <>
      <PageHeader title="Instellingen" />
      <nav aria-label="Onderdelen van instellingen">
        <ul className="plain-list link-list" data-testid="instellingen-index">
          {INSTELLINGEN_SUBNAV.map((i) => (
            <li key={i.href}>
              <Link href={i.href}>
                <span className="flex flex-col">
                  <span>{i.label}</span>
                  <span className="text-sm font-normal text-muted-foreground">{UITLEG[i.href]}</span>
                </span>
                <ChevronRight aria-hidden="true" className="size-5 shrink-0" />
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}
