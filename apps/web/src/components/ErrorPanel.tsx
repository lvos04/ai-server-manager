"use client";

import { OctagonX, RotateCw, WifiOff } from "lucide-react";
import { HubApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import { KopieerVeld } from "./KopieerVeld";
import { Button } from "./ui/button";

/**
 * Foutpaneel (C-14): wat er gebeurde → waarom + wat je kunt doen → Code → Trace-ID (kopieerbaar) → Opnieuw proberen
 * → Technische details. Nooit geheimen. `role="alert"` alleen bij een nieuwe fout (`alert`), anders gewoon tekst.
 */
export function ErrorPanel({
  error,
  onRetry,
  title = "Er ging iets mis",
  alert = true,
  className,
  kind,
}: {
  error: unknown;
  onRetry?: () => void;
  title?: string;
  alert?: boolean;
  className?: string;
  kind?: boolean;
}) {
  const e = error instanceof HubApiError ? error : null;
  const message = e ? e.message : error instanceof Error ? error.message : "Onbekende fout.";
  const offline = e?.code === "network_error" || e?.code === "api_unavailable";
  const Icon = offline ? WifiOff : OctagonX;
  if (kind) {
    return (
      <div className={cn("flex flex-col gap-2 rounded-lg border-2 border-down bg-down-bg p-4 text-down-ink", className)} role={alert ? "alert" : undefined} data-testid="error-panel" data-code={e?.code}>
        <p className="font-bold">Er ging iets mis. Vraag het aan een volwassene.</p>
        <details>
          <summary className="min-h-touch cursor-pointer py-2 font-semibold">Details voor een volwassene</summary>
          <p>
            Code <code>{e?.code ?? "onbekend"}</code>
            {e?.traceId ? (
              <>
                {" "}
                · Trace-ID <code>{e.traceId}</code>
              </>
            ) : null}
          </p>
        </details>
      </div>
    );
  }
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-lg border-2 p-4 sm:flex-row",
        offline ? "border-dashed border-unknown bg-unknown-bg text-unknown-ink" : "border-down bg-down-bg text-down-ink",
        className,
      )}
      role={alert ? "alert" : undefined}
      data-testid="error-panel"
      data-code={e?.code}
    >
      <Icon aria-hidden="true" className={cn("size-5 shrink-0 sm:mt-0.5", offline ? "text-unknown" : "text-down")} />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="font-bold">{offline ? "Geen verbinding met de Hub" : title}</p>
        <p>{message}</p>
        {e ? (
          <>
            <dl className="meta !text-current">
              <div>
                <dt>Code</dt>
                <dd>
                  <code className="rounded-sm bg-card px-1.5 py-0.5 text-foreground">{e.code}</code>
                  {e.status ? ` · HTTP ${e.status}` : null}
                </dd>
              </div>
            </dl>
            {e.traceId ? <KopieerVeld label="Trace-ID" waarde={e.traceId} /> : null}
            {Object.keys(e.details).length ? (
              <details>
                <summary className="min-h-touch cursor-pointer py-2 font-semibold">Technische details</summary>
                <pre className="overflow-x-auto rounded-sm bg-card p-2 text-sm whitespace-pre-wrap text-foreground">{JSON.stringify(e.details, null, 2)}</pre>
              </details>
            ) : null}
          </>
        ) : null}
        {onRetry ? (
          <div>
            <Button onClick={onRetry}>
              <RotateCw aria-hidden="true" />
              Opnieuw proberen
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
