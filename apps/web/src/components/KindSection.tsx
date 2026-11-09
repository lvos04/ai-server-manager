"use client";

import type { ReactNode } from "react";
import { kindStatus } from "@/lib/status";
import type { KindState } from "@/lib/types";
import { ErrorPanel } from "./ErrorPanel";
import { Freshness } from "./Freshness";
import { Loading } from "./Loading";
import { StatusBadge } from "./StatusBadge";

/** Eén soort uit de inventaris: status, laatst bijgewerkt, bron en — bij onbekend/verouderd — de reden en het advies. */
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
  return (
    <section className="card stack" id={id} aria-labelledby={`${id}-titel`} data-testid={`sectie-${id}`}>
      <div className="stat-head">
        <h2 id={`${id}-titel`}>{title}</h2>
        {state ? <StatusBadge view={kindStatus(state.status, state.verouderd)} /> : null}
      </div>
      {error ? <ErrorPanel error={error} /> : null}
      {!state && loading ? <Loading /> : null}
      {state ? (
        <>
          <Freshness observedAt={state.observed_at} bron={state.bron?.methode ? `TrueNAS ${state.bron.methode}` : null} verouderd={state.verouderd} />
          {state.status !== "ok" ? (
            <div className="notice tone-unknown" data-testid={`onbekend-${id}`}>
              <p>
                <strong>{state.verouderd ? "Verouderd: hieronder de laatst bekende meting." : "Onbekend."}</strong> {state.melding}
              </p>
              {state.advies ? <p>{state.advies}</p> : null}
              {state.reason_code ? (
                <p className="meta">
                  Reden: <code>{state.reason_code}</code>
                </p>
              ) : null}
            </div>
          ) : null}
          {children}
        </>
      ) : null}
    </section>
  );
}
