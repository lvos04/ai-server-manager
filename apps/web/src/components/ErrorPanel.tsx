"use client";

import { HubApiError } from "@/lib/api";

/** Foutmelding in het Nederlands, met code en trace-id (kopieerbaar voor een incident; nooit geheimen). */
export function ErrorPanel({ error, onRetry, title = "Er ging iets mis" }: { error: unknown; onRetry?: () => void; title?: string }) {
  const e = error instanceof HubApiError ? error : null;
  const message = e ? e.message : error instanceof Error ? error.message : "Onbekende fout.";
  const offline = e?.code === "network_error" || e?.code === "api_unavailable";
  return (
    <div className={`notice ${offline ? "tone-warn" : "tone-bad"}`} role="alert" data-testid="error-panel" data-code={e?.code}>
      <p>
        <strong>{offline ? "Geen verbinding met de Hub" : title}</strong>
      </p>
      <p>{message}</p>
      {e ? (
        <p className="meta">
          Code: <code>{e.code}</code>
          {e.status ? <> · HTTP {e.status}</> : null}
          {e.traceId ? (
            <>
              {" "}
              · trace-id: <code>{e.traceId}</code>
            </>
          ) : null}
        </p>
      ) : null}
      {onRetry ? (
        <button type="button" className="btn" onClick={onRetry}>
          Opnieuw proberen
        </button>
      ) : null}
    </div>
  );
}
