"use client";

import { useState } from "react";
import { KindSection } from "@/components/KindSection";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { orUnknown } from "@/lib/format";
import { appState } from "@/lib/status";
import type { AppInfo, InventoryKind, RegistryItem } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function AppsScreen() {
  const apps = useApi<InventoryKind<AppInfo>>("/api/v1/inventory/apps");
  const registry = useApi<{ items: RegistryItem[] }>("/api/v1/registry/services");
  const [q, setQ] = useState("");
  const fresh = apps.data?.status === "ok" && !apps.data.verouderd;
  const items = (apps.data?.items ?? []).filter((a) => a.naam.toLowerCase().includes(q.trim().toLowerCase()));
  const urlFor = (naam: string) => registry.data?.items.find((r) => r.app === naam);

  return (
    <>
      <PageHeader
        title="Apps"
        intro="Geïnstalleerde apps zoals TrueNAS ze meldt (alleen-lezen). Beheeracties zoals herstarten of updaten volgen in fase P2 via de executor, altijd met preview en goedkeuring."
      />
      <div className="field" style={{ maxWidth: 420, marginBottom: 16 }}>
        <label htmlFor="zoek-app">Zoek een app</label>
        <input id="zoek-app" type="search" value={q} onChange={(e) => setQ(e.target.value)} autoComplete="off" />
      </div>
      <KindSection id="apps" title="Geïnstalleerde apps" state={apps.data} error={apps.error} loading={apps.loading}>
        {items.length ? (
          <ul className="plain-list" data-testid="app-lijst">
            {items.map((a) => {
              const reg = urlFor(a.naam);
              return (
                <li key={a.naam} className="card stack" style={{ gap: 8 }}>
                  <div className="stat-head">
                    <h3 style={{ margin: 0 }}>{a.naam}</h3>
                    <StatusBadge view={appState(fresh ? a.status : "onbekend")} />
                  </div>
                  <dl className="kv">
                    <dt>Image</dt>
                    <dd>{a.images.length ? a.images.map((i) => <code key={i.image}>{i.image}</code>) : "onbekend"}</dd>
                    <dt>Digest</dt>
                    <dd>{a.images[0]?.digest ? <code>{a.images[0].digest}</code> : "onbekend (TrueNAS gaf geen digest)"}</dd>
                    <dt>Herkend als</dt>
                    <dd>{orUnknown(a.herkend_als)}</dd>
                    <dt>Hostpoorten</dt>
                    <dd>{a.poorten.filter((p) => p.host_poort).map((p) => `${p.host_poort}/${p.protocol}`).join(", ") || "geen"}</dd>
                    <dt>Opslag</dt>
                    <dd>{a.opslag.length ? a.opslag.map((o) => `${orUnknown(o.bron)} → ${orUnknown(o.doel)}`).join("; ") : "onbekend"}</dd>
                    <dt>Gezondheid</dt>
                    <dd>onbekend — {a.gezondheid_toelichting}</dd>
                  </dl>
                  {reg?.basis_url ? (
                    <p style={{ margin: 0 }}>
                      <a className="btn" href={reg.basis_url} target="_blank" rel="noopener noreferrer">
                        Open {a.naam} (eigen web-UI)<span className="sr-only"> in een nieuw tabblad</span>
                      </a>
                    </p>
                  ) : reg?.reden_geen_url ? (
                    <p className="meta" style={{ margin: 0 }}>Geen link: {reg.reden_geen_url}.</p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : apps.data?.status === "ok" ? (
          <p>{q ? "Geen app gevonden met deze zoekterm." : "Geen apps gevonden."}</p>
        ) : null}
      </KindSection>
    </>
  );
}
