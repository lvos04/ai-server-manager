"use client";

import Link from "next/link";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { buttonVariants } from "@/components/ui/button";
import { CATALOGUS_NOG_NIET } from "@/lib/appbeheer";

/**
 * S-046 Appstore-catalogus (ontwerp HUB_P2_ONTWERP.md). De Hub heeft nog geen voor gebruikers leesbare lijst met
 * goedgekeurde, installeerbare versies; tot die bron er is, toont de winkel C-12 en geen enkel product of voorbeeld.
 */
export function CatalogusScreen() {
  return (
    <>
      <PageHeader
        title="Appstore"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Apps", href: "/apps" }, { label: "Appstore" }]}
        intro="Een goedgekeurde app kiezen en installeren als standaard TrueNAS Custom App of officiële catalogusapp."
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      <div className="flex flex-col gap-4">
        <Melding soort="nogniet" titel={CATALOGUS_NOG_NIET} data-testid="catalogus-nog-niet">
          <p>
            <strong>Wat hier komt:</strong> per goedgekeurde versie de validatie, image en digest, poorten, mounts, GPU, netwerk en
            privileges met hun reden, back-updoelen, afhankelijkheden en het installatierisico.
          </p>
          <p>
            <strong>Bron:</strong> een leesroute in de Hub voor de goedgekeurde manifests van de appstore. De bestaande Apps-lijst is de
            inventaris van je NAS en geen winkel; een gevonden app wordt hier nooit als installeerbaar product getoond.
          </p>
        </Melding>
        <p className="flex flex-col gap-2 sm:flex-row">
          <Link href="/apps" className={buttonVariants({ variant: "primair" })}>
            Naar de Apps-lijst
          </Link>
          <Link href="/apps/installeren" className={buttonVariants({ variant: "secundair" })}>
            Installatiewizard bekijken
          </Link>
        </p>
      </div>
    </>
  );
}
