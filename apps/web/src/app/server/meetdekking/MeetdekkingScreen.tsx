"use client";

import { Check, CircleHelp, Minus, X } from "lucide-react";
import Link from "next/link";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { ResponsiveList } from "@/components/ResponsiveList";
import { SERVER_SUBNAV, Subnav } from "@/components/Subnav";
import { formatTime } from "@/lib/format";
import { useApi } from "@/lib/use-api";

interface BronCel {
  bron: string;
  kan_leveren: "ja" | "nee" | "afhankelijk" | string;
  toelichting: string;
  zekerheid: string;
  gekoppeld: boolean | null;
  levert: boolean | null;
  laatst: string | null;
  reden: string | null;
}

interface Metriek {
  metriek: string;
  titel: string;
  eenheid: string;
  onderwerp: string;
  onderwerp_id: string;
  gedekt: boolean;
  hiaat: string | null;
  bronnen: BronCel[];
}

interface Coverage {
  metrieken: Metriek[];
  hiaten: string[];
  apps: {
    totaal: number;
    met_buitenkant: number;
    met_binnenkant: number;
    hiaten: { id: string; naam: string; buitenkant: boolean; binnenkant: boolean; binnenkant_vereist: boolean; hiaat: string; truenas: string }[];
  };
  zekerheid: string;
  observed_at: string;
}

const BRON: Record<string, string> = { truenas_realtime: "TrueNAS (realtime)", truenas: "TrueNAS", beszel: "Beszel", uptime_kuma: "Uptime Kuma" };
const REDEN: Record<string, string> = {
  bron_niet_gekoppeld: "bron niet gekoppeld",
  nog_niet_gemeten: "nog niet gemeten",
  verouderd: "verouderd",
  niet_geleverd: "niet geleverd",
};

/** Cel van de DekkingsMatrix (C-33): symbool + woord, geen kleurvlakken. */
function Cel({ c }: { c: BronCel }) {
  const levert = c.levert === true ? { I: Check, w: "Levert" } : c.levert === false ? { I: X, w: "Levert nu niet" } : { I: CircleHelp, w: "Onbekend" };
  const kan = c.kan_leveren === "ja" ? "kan" : c.kan_leveren === "afhankelijk" ? "kan (afhankelijk)" : c.kan_leveren === "nee" ? "kan niet" : c.kan_leveren;
  const K = c.kan_leveren === "nee" ? Minus : null;
  return (
    <span className="flex flex-col gap-0.5 text-sm" data-bron={c.bron} data-levert={String(c.levert)}>
      <span className="flex items-center gap-1.5 font-semibold">
        {K ? <K aria-hidden="true" className="size-4" /> : <levert.I aria-hidden="true" className="size-4" />}
        {c.kan_leveren === "nee" ? "N.v.t." : levert.w}
      </span>
      <span>
        {BRON[c.bron] ?? c.bron}: {kan}
        {c.reden ? ` · ${REDEN[c.reden] ?? c.reden}` : ""}
        {c.laatst ? ` · ${formatTime(c.laatst)}` : ""}
      </span>
    </span>
  );
}

export function MeetdekkingScreen() {
  const cov = useApi<Coverage>("/api/v1/monitoring/coverage", 60_000);
  const c = cov.data;
  return (
    <>
      <PageHeader
        title="Meetdekking"
        kruimel={[{ label: "Server", href: "/server" }, { label: "Meetdekking" }]}
        intro="Per metriek: welke bron het kan leveren en wat er nu echt geleverd wordt. ‘Kan leveren’ komt uit de broncode (NIET GEVALIDEERD op de NAS); ‘levert’ is gemeten."
      />
      <Subnav items={SERVER_SUBNAV} label="Server" />
      {cov.error ? <ErrorPanel error={cov.error} onRetry={() => void cov.reload()} alert={false} /> : null}
      {!c && cov.loading ? <Loading regels={6} /> : null}
      {c ? (
        <div className="flex flex-col gap-6">
          <p data-testid="dekking-samenvatting">
            {c.metrieken.filter((m) => m.gedekt).length} van {c.metrieken.length} metrieken hebben nu een verse bron.
          </p>
          <ResponsiveList
            items={c.metrieken}
            label="Meetdekking per metriek"
            testId="dekkingsmatrix"
            sleutel={(m) => `${m.metriek}-${m.onderwerp_id}`}
            kolommen={[
              {
                kop: "Metriek",
                cel: (m) => (
                  <span className="flex flex-col">
                    <strong>{m.titel}</strong>
                    <span className="text-sm text-muted-foreground">
                      {m.onderwerp === "nas" ? "NAS" : `${m.onderwerp} ${m.onderwerp_id}`} · {m.eenheid}
                    </span>
                  </span>
                ),
              },
              {
                kop: "Nu gedekt",
                cel: (m) => (
                  <span className="flex flex-col text-sm">
                    <span className="flex items-center gap-1.5 font-semibold">
                      {m.gedekt ? <Check aria-hidden="true" className="size-4" /> : <X aria-hidden="true" className="size-4" />}
                      {m.gedekt ? "Ja" : "Nee"}
                    </span>
                    {m.hiaat ? <span>{m.hiaat}</span> : null}
                  </span>
                ),
              },
              {
                kop: "Bronnen",
                cel: (m) => (
                  <span className="flex flex-col gap-2">
                    {m.bronnen.map((b) => (
                      <Cel key={b.bron} c={b} />
                    ))}
                  </span>
                ),
              },
            ]}
          />
          <section className="card" aria-labelledby="apps-dekking">
            <h2 id="apps-dekking">Apps</h2>
            <p>
              {c.apps.totaal} apps · {c.apps.met_buitenkant} met een buitenkant (Uptime Kuma) · {c.apps.met_binnenkant} met een controle van
              binnenuit.
            </p>
            {c.apps.hiaten.length ? (
              <ul className="m-0 flex list-none flex-col gap-1 p-0">
                {c.apps.hiaten.map((a) => (
                  <li key={a.id}>
                    <Link href={`/apps/${a.id}`}>{a.naam}</Link>: {a.buitenkant ? "buitenkant ja" : "geen buitenkant"} ·{" "}
                    {a.binnenkant ? "binnenkant ja" : a.binnenkant_vereist ? "binnenkant vereist maar ontbreekt" : "geen binnenkant"} · <code>{a.hiaat}</code>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
          <p className="text-sm">{c.zekerheid}</p>
          <Freshness observedAt={c.observed_at} bron="Hub (monitoring/coverage)" />
        </div>
      ) : null}
    </>
  );
}
