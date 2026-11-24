"use client";

import { Ban } from "lucide-react";
import { useState } from "react";
import { RisicoBadge } from "@/components/ActiePreview";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { KopieerVeld } from "@/components/KopieerVeld";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import type { Beleid, BeleidsActie } from "@/lib/acties";
import { vasteFout } from "@/lib/acties";
import { formatDuration, formatTime } from "@/lib/format";
import { useBronlijst } from "@/lib/use-meting";
import { cn } from "@/lib/utils";

export const NIET_DOOR_AI = "Het beleid kan niet door de AI worden gewijzigd.";

/** Zoekt in action_id en omschrijving (hoofdletterongevoelig). */
export function filterActies(acties: BeleidsActie[], zoek: string): BeleidsActie[] {
  const z = zoek.trim().toLowerCase();
  return z ? acties.filter((a) => a.action_id.toLowerCase().includes(z) || a.omschrijving.toLowerCase().includes(z)) : acties;
}

/** S-066: het risicobeleid, uitsluitend lezen. */
export function BeleidScreen() {
  const s = useBronlijst<Beleid>("/api/v1/policy");
  const [zoek, setZoek] = useState("");
  const b = s.data;
  const leeg = b && !b.acties.length;
  const acties = b ? filterActies(b.acties, zoek) : [];
  return (
    <>
      <PageHeader
        title="Risicobeleid"
        kruimel={[{ label: "Goedkeuringen", href: "/goedkeuringen" }, { label: "Risicobeleid" }]}
        intro={NIET_DOOR_AI}
      />
      <div className={cn("flex flex-col gap-4", s.stale && "arcering rounded-lg border-2 border-dashed border-stale p-3")} data-testid="beleid">
        {s.data && s.stale ? (
          <Melding soort="onbekend" titel={s.bronTijd ? `Verouderd · stand van ${formatTime(s.bronTijd)}` : "Tijdstip van het beleid onbekend"} data-testid="verouderd">
            <p>De huidige beleidsstand is onbekend.</p>
          </Melding>
        ) : null}
        {s.error && !b ? <ErrorPanel vast={vasteFout} error={s.error} title="Risicobeleid onbekend" onRetry={() => void s.reload()} /> : null}
        {!b && !s.error ? <Loading text="Beleid ophalen…" /> : null}
        {leeg && !s.stale ? (
          <Melding soort="onbekend" titel="Risicobeleid onbekend">
            <p>De beleidsbron bevat geen acties.</p>
          </Melding>
        ) : null}
        {b && !leeg ? (
          <>
            <KopieerVeld label="Beleidsrevisie (policy_hash)" waarde={b.policy_hash} testId="policy-hash" />
            <div className="flex flex-col gap-1">
              <label htmlFor="zoek-actie" className="font-semibold">
                Zoek een actie
              </label>
              <input
                id="zoek-actie"
                type="search"
                className="min-h-touch w-full max-w-md rounded-lg border-2 border-border-strong bg-card px-3"
                value={zoek}
                onChange={(e) => setZoek(e.target.value)}
                autoComplete="off"
              />
            </div>
            {acties.length ? (
              <ResponsiveList
                items={acties}
                label="Acties in het beleid"
                sleutel={(a) => a.action_id}
                testId="beleid-acties"
                tabelVanaf={1280}
                kolommen={[
                  { kop: "Actie", cel: (a) => <><code>{a.action_id}</code><br />{a.omschrijving}</> },
                  { kop: "Uitvoerder", cel: (a) => a.uitvoerder },
                  { kop: "Basisklasse", cel: (a) => <RisicoBadge klasse={a.risk_class} /> },
                  { kop: "Kritieke app", cel: (a) => (a.risk_class_kritiek ? <RisicoBadge klasse={a.risk_class_kritiek} /> : "n.v.t.") },
                  { kop: "Custom App", cel: (a) => (a.risk_class_custom_app ? <RisicoBadge klasse={a.risk_class_custom_app} /> : "n.v.t.") },
                  { kop: "Back-up vereist", cel: (a) => (a.requires_backup ? "ja" : "nee") },
                  { kop: "Wachttijd", cel: (a) => (a.cooldown_seconden ? formatDuration(a.cooldown_seconden) : "geen") },
                ]}
              />
            ) : !s.stale && (
              <p data-testid="geen-regel">Geen regel gevonden voor dit filter.</p>
            )}
            <section className="card" aria-labelledby="verboden-kop">
              <h2 id="verboden-kop" className="text-xl font-bold">
                Verboden en beschermd
              </h2>
              <ul className="plain-list">
                {[...b.verboden, ...b.gereserveerd].map((r) => (
                  <li key={r.id} className="flex flex-col gap-1">
                    <span className="flex items-center gap-2 font-semibold">
                      <Ban aria-hidden="true" className="size-5 text-gate" />
                      <code>{r.code}</code> · Wordt nooit uitgevoerd
                    </span>
                    <span>{r.reden}</span>
                  </li>
                ))}
                {b.beschermd.map((r) => (
                  <li key={r.id} className="flex flex-col gap-1">
                    <span className="flex items-center gap-2 font-semibold">
                      <Ban aria-hidden="true" className="size-5 text-gate" />
                      {r.app} · {r.acties ? r.acties.join(", ") : "alle acties"} · Wordt nooit uitgevoerd
                    </span>
                    <span>{r.reden}</span>
                  </li>
                ))}
              </ul>
            </section>
          </>
        ) : null}
        {b ? <Freshness observedAt={s.bronTijd} bron="Risicobeleid in de Hub" verouderd={s.stale} /> : null}
      </div>
    </>
  );
}
