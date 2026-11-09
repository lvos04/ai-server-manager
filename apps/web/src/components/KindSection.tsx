"use client";

import type { ReactNode } from "react";
import { kindStatus } from "@/lib/status";
import type { KindState } from "@/lib/types";
import { ErrorPanel } from "./ErrorPanel";
import { Freshness } from "./Freshness";
import { Loading } from "./Loading";
import { Melding } from "./Melding";
import { StatusBadge } from "./StatusBadge";

/**
 * Eén soort uit de inventaris: Versheid (bron + bijgewerkt + geprobeerd) en — bij onbekend/verouderd — de reden en
 * het advies. Vers = geen badge (de tijd zegt genoeg). Verouderd (O-03): de laatst bekende meting blijft zichtbaar,
 * gemarkeerd als verouderd; de inhoud zelf is dan gedempt.
 */
export function KindSection({
  id,
  title,
  state,
  error,
  loading,
  children,
}: {
  id: string;
  title: string;
  state: KindState | undefined;
  error?: unknown;
  loading?: boolean;
  children?: ReactNode;
}) {
  const badge = state ? kindStatus(state.status, state.verouderd) : null;
  return (
    <section
      className={state?.verouderd ? "card stack border-2 border-dashed border-stale" : "card stack"}
      id={id}
      aria-labelledby={`${id}-titel`}
      data-testid={`sectie-${id}`}
    >
      <div className="stat-head">
        <h2 id={`${id}-titel`}>{title}</h2>
        {badge ? <StatusBadge view={badge} /> : null}
      </div>
      {error ? <ErrorPanel error={error} alert={false} /> : null}
      {!state && loading ? <Loading /> : null}
      {state ? (
        <>
          <Freshness
            observedAt={state.observed_at}
            bron={state.bron?.methode ? `TrueNAS ${state.bron.methode}` : null}
            verouderd={state.verouderd}
            geprobeerd={state.status !== "ok" && state.laatste_poging ? { op: state.laatste_poging, uitkomst: state.reason_code ?? "mislukt" } : null}
          />
          {state.status !== "ok" ? (
            <Melding
              soort="onbekend"
              data-testid={`onbekend-${id}`}
              titel={state.verouderd ? "Verouderd — hieronder de laatst bekende meting, status Onbekend." : "Onbekend."}
            >
              <p>{state.melding}</p>
              {state.advies ? <p>{state.advies}</p> : null}
              {state.reason_code ? (
                <p className="text-sm">
                  Reden: <code>{state.reason_code}</code>
                </p>
              ) : null}
            </Melding>
          ) : null}
          {state.verouderd ? <div className="flex flex-col gap-3 text-stale-ink">{children}</div> : children}
        </>
      ) : null}
    </section>
  );
}
