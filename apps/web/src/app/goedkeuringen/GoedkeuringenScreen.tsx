"use client";

import Link from "next/link";
import { useState } from "react";
import { RisicoBadge } from "@/components/ActiePreview";
import { Aftellen } from "@/components/Aftellen";
import { ErrorPanel } from "@/components/ErrorPanel";
import { Freshness } from "@/components/Freshness";
import { Loading } from "@/components/Loading";
import { Melding } from "@/components/Melding";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { doelNaam, statusView, weigerReden, type ActieVerzoek, vasteFout } from "@/lib/acties";
import { formatDateTime, formatTime } from "@/lib/format";
import { usePaginaLijst } from "@/lib/use-meting";
import { cn } from "@/lib/utils";

type Filter = "wacht_op_goedkeuring" | "open" | "alle";
const FILTER: Record<Filter, string> = {
  wacht_op_goedkeuring: "Wacht op goedkeuring",
  open: "Open (ook goedgekeurd en klaar)",
  alle: "Alle, met historie",
};

const sleutel = (v: ActieVerzoek) => v.request_id;

function Rij({ v, verouderd }: { v: ActieVerzoek; verouderd: boolean }) {
  const doel = doelNaam(v.target) ?? "onbekend doel";
  const wacht = v.status === "wacht_op_goedkeuring";
  return (
    <Link
      href={`/goedkeuringen/${v.request_id}`}
      className={cn("flex min-h-touch flex-col gap-1.5 rounded-lg border border-border bg-card p-3 text-foreground no-underline hover:bg-accent", verouderd && "arcering border-2 border-dashed border-stale")}
      data-testid={`verzoek-${v.request_id}`}
    >
      <span className="flex flex-wrap items-center gap-2">
        <RisicoBadge klasse={v.risk_class} />
        <StatusBadge view={verouderd ? { tone: "stale", label: `Verouderd · ${statusView(v.status).label}` } : statusView(v.status)} />
      </span>
      <strong className="[overflow-wrap:anywhere]">
        <code>{v.action_id}</code> · {doel}
      </strong>
      <span className="text-sm text-muted-foreground">
        Aangevraagd {formatDateTime(v.aangemaakt_op)} door {v.actor.type === "user" ? "gebruiker" : v.actor.type === "ai" ? "AI" : "dienst of flow"}
        {wacht && v.geldig_tot ? (
          <>
            {" "}
            · verloopt over <Aftellen tot={v.geldig_tot} />
          </>
        ) : null}
      </span>
      {v.status === "afgewezen" ? <span className="text-sm">{weigerReden(v.resultaat)}</span> : null}
    </Link>
  );
}

/** S-062: de lijst met openstaande goedkeuringen; de teller in de kopbalk gebruikt dezelfde wachtlijst. */
export function GoedkeuringenScreen() {
  const [filter, setFilter] = useState<Filter>("wacht_op_goedkeuring");
  const pad = `/api/v1/actions?status=${filter}&limit=50`;
  const s = usePaginaLijst(pad, sleutel);
  const items = s.data?.items ?? [];
  const cursor = s.data?.next_cursor;
  return (
    <>
      <PageHeader
        title="Goedkeuringen"
        intro="Voorstellen die op een beslissing wachten. Een beheerder keurt precies de getoonde wijziging goed."
        actions={
          <Link href="/goedkeuringen/beleid" className="losse-link font-semibold">
            Risicobeleid bekijken
          </Link>
        }
      />
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="filter" className="font-semibold">
            Toon
          </label>
          <select
            id="filter"
            className="min-h-touch w-fit max-w-full rounded-lg border-2 border-border-strong bg-card px-3"
            value={filter}
            onChange={(e) => setFilter(e.target.value as Filter)}
            data-testid="filter"
          >
            {Object.entries(FILTER).map(([k, label]) => (
              <option key={k} value={k}>
                {label}
              </option>
            ))}
          </select>
        </div>
        {s.data && s.stale ? (
          <Melding soort="onbekend" titel={s.bronTijd ? `Verouderd · stand van ${formatTime(s.bronTijd)}` : "Tijdstip van de wachtlijst onbekend"} className="arcering border-dashed border-stale" data-testid="verouderd">
            <p>De huidige stand van de wachtlijst is onbekend. Open een verzoek voor de actuele stand.</p>
          </Melding>
        ) : null}
        {s.error && !s.data ? <ErrorPanel vast={vasteFout} error={s.error} title="Goedkeuringen ophalen mislukt" onRetry={() => void s.reload()} /> : null}
        {!s.data && !s.error ? <Loading text="Goedkeuringen ophalen…" /> : null}
        {s.data && !items.length && !cursor && !s.stale ? (
          <p data-testid="leeg">{filter === "wacht_op_goedkeuring" ? "Geen openstaande goedkeuringen." : "Geen voorstellen voor dit filter."}</p>
        ) : null}
        {items.length ? (
          <ul className="m-0 flex list-none flex-col gap-3 p-0" aria-label="Voorstellen" data-testid="goedkeuringen-lijst">
            {items.map((v) => (
              <li key={v.request_id}>
                <Rij v={v} verouderd={s.stale} />
              </li>
            ))}
          </ul>
        ) : null}
        {s.data && s.error ? <ErrorPanel vast={vasteFout} error={s.error} title="Goedkeuringen ophalen mislukt" onRetry={() => void s.reload()} /> : null}
        {cursor ? (
          <div>
            <Button onClick={s.meer} bezig={s.loading}>Meer laden</Button>
          </div>
        ) : null}
        {s.data ? <Freshness observedAt={s.bronTijd} bron="Hub-acties" verouderd={s.stale} /> : null}
      </div>
    </>
  );
}
