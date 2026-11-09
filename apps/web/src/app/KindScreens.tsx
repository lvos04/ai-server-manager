"use client";

import { MonitorPlay, Search, Smile } from "lucide-react";
import Link from "next/link";
import { useSession } from "@/lib/session";
import { LogoutButton, SessionsSection, ThemeSection } from "./instellingen/delen";

/** Kindschil (O-05): kindertaal, geen systeemstatus, geen incidenten, geen beheertermen of codes in beeld. */
function KindKaart({ titel, tekst, href, icon: Icon, fase }: { titel: string; tekst: string; href: string; icon: typeof Search; fase: string }) {
  return (
    <article className="flex flex-col gap-2 rounded-lg border-2 border-border-strong bg-card p-4">
      <h2 className="flex items-center gap-2">
        <Icon aria-hidden="true" className="size-6" />
        {titel}
      </h2>
      <p>{tekst}</p>
      <details>
        <summary className="min-h-touch cursor-pointer py-2 font-semibold">Details voor een volwassene</summary>
        <p className="text-sm">Volgt in fase {fase}.</p>
      </details>
      <p>
        <Link href={href} className="inline-flex min-h-touch items-center font-semibold">
          Naar {titel}
        </Link>
      </p>
    </article>
  );
}

export function KindHome() {
  const { state } = useSession();
  const naam = state.status === "auth" ? state.me.user.display_name || state.me.user.username : "";
  return (
    <div className="flex flex-col gap-6" data-testid="kind-home">
      <h1 className="text-3xl font-bold">Hoi {naam}</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <KindKaart titel="Kijken" icon={MonitorPlay} href="/kijken" fase="P4" tekst="Kijken komt later. Tot dan kijk je in Jelly Leon." />
        <KindKaart titel="Zoeken" icon={Search} href="/zoeken" fase="P5" tekst="Zoeken komt later." />
      </div>
    </div>
  );
}

export function KindKijken() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl font-bold">Kijken</h1>
      <p>Kijken komt later. Tot dan kijk je in Jelly Leon.</p>
      <p>Weet je niet hoe? Vraag het aan een volwassene.</p>
      <details>
        <summary className="min-h-touch cursor-pointer py-2 font-semibold">Details voor een volwassene</summary>
        <p className="text-sm">Volgt in fase P4 (Jelly Leon met toegestane titels per kind).</p>
      </details>
    </div>
  );
}

export function KindZoeken() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-3xl font-bold">Zoeken</h1>
      <p>Zoeken komt later.</p>
      <details>
        <summary className="min-h-touch cursor-pointer py-2 font-semibold">Details voor een volwassene</summary>
        <p className="text-sm">Volgt in fase P5 (zoeken met alleen toegestane titels).</p>
      </details>
    </div>
  );
}

export function KindIk() {
  const { state } = useSession();
  const naam = state.status === "auth" ? state.me.user.display_name || state.me.user.username : "";
  return (
    <div className="flex flex-col gap-4">
      <h1 className="flex items-center gap-2 text-3xl font-bold">
        <Smile aria-hidden="true" className="size-8" />
        Ik
      </h1>
      <p>Je bent ingelogd als {naam}.</p>
      <ThemeSection />
      <SessionsSection />
      <div>
        <LogoutButton />
      </div>
    </div>
  );
}
