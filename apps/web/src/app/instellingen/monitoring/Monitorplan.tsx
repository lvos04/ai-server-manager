"use client";

import { useState } from "react";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { Leesstand } from "@/components/Leesstand";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { toonbareFout, vasteFout } from "@/lib/acties";
import { appNaam, UUID } from "@/lib/backups";
import type { StatusView } from "@/lib/status";
import { useAction } from "@/lib/use-action";
import { useMeting } from "@/lib/use-meting";

interface Regel {
  app: { id: string; naam: string }; stand: string; reden: string | null; bewaakt: boolean;
  plan_sha256: string | null; bevestiging: { plan_sha256: string } | null; bevestiging_verouderd: boolean;
  controle: { soort: string; adres: string; verwachte_status: number; timeout_s: number; interval_s: number } | null;
}

const HASH = /^sha256:[0-9a-f]{64}$/;
const REDEN: Record<string, string> = {
  hostpoort_onbekend: "De hostpoort ontbreekt.", nas_adres_onbekend: "Het controleadres is onbekend.",
  monitor_ontbreekt: "Het manifest bevat geen monitorregel.", monitor_ongeldig: "De monitorregel is onvolledig.",
  manifest_onbereikbaar: "Het manifest is onbereikbaar.", versie_onbekend: "De manifestversie is onbekend.",
};

export function monitorStand(r: Regel, oud: boolean): StatusView {
  if (oud) return { tone: "unknown", label: "Bewaking onbekend" };
  if (r.stand === "handmatig bevestigd" && r.bewaakt === true && !r.bevestiging_verouderd && HASH.test(r.plan_sha256 ?? "")
    && r.bevestiging?.plan_sha256 === r.plan_sha256) return { tone: "neutral", label: "Handmatig bevestigd", icon: "ingesteld" };
  return { tone: "gate", label: "Niet bewaakt" };
}

function juisteControle(c: Regel["controle"]) {
  if (!c || c.soort !== "http" || !/^http:\/\/(?:\[[a-fA-F0-9:]+\]|[A-Za-z0-9.-]+):\d{1,5}\/(?!\/)[A-Za-z0-9._~/-]{0,254}$/.test(c.adres)) return false;
  return Number.isInteger(c.verwachte_status) && c.verwachte_status >= 100 && c.verwachte_status <= 599
    && Number.isInteger(c.timeout_s) && c.timeout_s >= 1 && c.timeout_s <= 300
    && Number.isInteger(c.interval_s) && c.interval_s >= 10 && c.interval_s <= 86400;
}

function Planregel({ r, oud, admin, opnieuw }: { r: Regel; oud: boolean; admin: boolean; opnieuw: () => Promise<void> }) {
  const a = useAction();
  const [gewijzigd, setGewijzigd] = useState(false);
  const c = juisteControle(r.controle) ? r.controle : null;
  const stand = monitorStand(r, oud || gewijzigd);
  const mag = !oud && !gewijzigd && r.stand === "voorgesteld" && !!c && HASH.test(r.plan_sha256 ?? "") && UUID.test(r.app.id);
  const bevestig = async () => {
    if (!mag || !admin || a.busy) return;
    const antwoord = await a.run(`/api/v1/monitoring/monitorplan/${r.app.id}/bevestiging`, { body: { bevestigd: true, plan_sha256: r.plan_sha256 } });
    if (!antwoord) setGewijzigd(true);
    await opnieuw();
  };
  const uitleg = gewijzigd || r.bevestiging_verouderd ? "Lees het actuele plan en neem de nieuwe regel over."
    : c ? "Neem deze regel over in Uptime Kuma." : r.reden && Object.hasOwn(REDEN, r.reden) ? REDEN[r.reden] : "Er is geen volledige monitorregel.";
  return <li className="card stack"><h3>{appNaam(r.app.naam)}</h3><StatusBadge view={stand} />
    {c && <dl className="kv"><dt>HTTP-controle</dt><dd className="break-all">{c.adres}</dd><dt>Verwachte HTTP-status</dt><dd>{c.verwachte_status}</dd>
      <dt>Time-out</dt><dd>{c.timeout_s} s</dd><dt>Interval</dt><dd>{c.interval_s} s</dd></dl>}
    {stand.tone !== "neutral" && <p id={`reden-${r.app.id}`}>{uitleg}</p>}
    {admin && stand.tone !== "neutral" && <Button uit={!mag} bezig={a.busy} onClick={() => void bevestig()} aria-describedby={`reden-${r.app.id}`}>Handmatig bevestigen</Button>}
    {a.error && <ErrorPanel error={toonbareFout(a.error)} vast={vasteFout} title="Bevestiging onbekend" onRetry={() => { void opnieuw().then(() => setGewijzigd(false)); }} />}
  </li>;
}

export function Monitorplan({ admin }: { admin: boolean }) {
  const bron = useMeting<{ items: Regel[]; observed_at: string }>("/api/v1/monitoring/monitorplan");
  return <section id="monitorplan" className="stack" aria-labelledby="monitorplan-titel">
    <h2 id="monitorplan-titel">Monitorplan per app</h2>
    <p>De bevestiging legt vast welke regel de beheerder heeft overgenomen in Uptime Kuma. De appstatus komt uit de eigen meting.</p>
    <Leesstand bron={bron} naam="Monitorplan" />
    {bron.data && <>
      {!bron.data.items.length && !bron.stale && <p>Geen apps voor dit monitorplan.</p>}
      <ul className="plain-list stack">{bron.data.items.filter(r => UUID.test(r.app.id)).map(r =>
        <Planregel key={`${r.app.id}-${r.plan_sha256}`} r={r} oud={bron.stale} admin={admin} opnieuw={bron.reload} />)}</ul>
      <Freshness bron="Hub · monitorplan" observedAt={bron.data.observed_at} verouderd={bron.stale} />
    </>}
  </section>;
}
