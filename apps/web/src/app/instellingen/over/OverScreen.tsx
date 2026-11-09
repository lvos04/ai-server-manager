"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { Validatielabel } from "@/components/StatusBadge";
import { PRODUCT } from "@/lib/nav";
import { useApi } from "@/lib/use-api";
import { InstellingenKop } from "../delen";

/** Validatiestatus per onderdeel (O-12, C-09): exacte strings uit contract §11; nooit "Gereed" of "Geslaagd". */
const VALIDATIE: { onderdeel: string; labels: string[] }[] = [
  { onderdeel: "Web-UI (Peil)", labels: ["Sim-getest"] },
  { onderdeel: "Inventaris en TrueNAS-koppeling", labels: ["Sim-getest", "NIET GEVALIDEERD (echte NAS)"] },
  { onderdeel: "Appcatalogus en gezondheid", labels: ["Sim-getest", "NIET GEVALIDEERD (echte NAS)"] },
  { onderdeel: "Monitoring (Uptime Kuma, Beszel, Gotify)", labels: ["Sim-getest", "NIET GEVALIDEERD (echte NAS)"] },
  { onderdeel: "GPU-metingen (A310, UHD 770)", labels: ["NIET GEVALIDEERD (hardware)"] },
  { onderdeel: "Inloggen via SSO (Authentik)", labels: ["Sim-getest", "NIET GEVALIDEERD (account)"] },
  { onderdeel: "Noodlogin", labels: ["Sim-getest", "NIET GEVALIDEERD (echte NAS)"] },
  { onderdeel: "Diensten koppelen", labels: ["Sim-getest"] },
];

export function OverScreen() {
  const health = useApi<{ status: string; version: string }>("/healthz");
  return (
    <>
      <InstellingenKop titel="Over deze Hub" />
      <div className="stack">
        <section className="card" id="over" aria-labelledby="over-titel" data-testid="over-de-hub">
          <h2 id="over-titel">{PRODUCT}</h2>
          <dl className="kv">
            <dt>Centrale app</dt>
            <dd>Hub</dd>
            <dt>Versie web-UI</dt>
            <dd>{process.env.NEXT_PUBLIC_HUB_VERSION ?? "onbekend"}</dd>
            <dt>Versie API</dt>
            <dd>{health.data ? health.data.version : health.error ? "niet bereikbaar" : "laden…"}</dd>
            <dt>Ontwerptaal</dt>
            <dd>Peil 1.1.0 (Tailwind 4, shadcn/ui, lucide)</dd>
          </dl>
        </section>
        <section className="card" aria-labelledby="validatie-titel" data-testid="validatie">
          <h2 id="validatie-titel">Validatie per onderdeel</h2>
          <p className="meta">Sim-getest = getest tegen simulators. NIET GEVALIDEERD = nog niet op een echte NAS, hardware of account geprobeerd.</p>
          <ul className="m-0 flex list-none flex-col divide-y divide-border p-0">
            {VALIDATIE.map((v) => (
              <li key={v.onderdeel} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{v.onderdeel}</span>
                <span className="flex flex-wrap gap-2">
                  {v.labels.map((l) => (
                    <Validatielabel key={l}>{l}</Validatielabel>
                  ))}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card" aria-labelledby="links-titel">
          <h2 id="links-titel">Verder</h2>
          <ul className="plain-list link-list">
            {[
              ["/onboarding", "Onboarding (D01–D18)"],
              ["/onboarding/truenas", "TrueNAS-koppeling (alleen-lezen)"],
              ["/onboarding/executor", "Executor"],
            ].map(([href, label]) => (
              <li key={href}>
                <Link href={href!}>
                  <span>{label}</span>
                  <ChevronRight aria-hidden="true" className="size-5" />
                </Link>
              </li>
            ))}
            <li>
              <a href="/api/docs">
                <span>API-documentatie (OpenAPI)</span>
                <ChevronRight aria-hidden="true" className="size-5" />
              </a>
            </li>
          </ul>
          <p className="meta">Licentie: zie LICENSE in de repository. Lettertype: systeemfont (geen externe bronnen).</p>
        </section>
      </div>
    </>
  );
}
