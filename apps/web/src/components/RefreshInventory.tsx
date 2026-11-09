"use client";

import { useState } from "react";
import { apiRequest, HubApiError } from "@/lib/api";
import { hasRole, useRole } from "@/lib/session";
import type { Job } from "@/lib/types";
import { waitForJob } from "@/lib/use-api";
import { ErrorPanel } from "./ErrorPanel";

/** Inventaris vernieuwen (alleen-lezen op de NAS). Operator of hoger. */
export function RefreshInventory({ onDone }: { onDone: () => void }) {
  const role = useRole();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  if (!hasRole(role, "operator")) {
    return <p className="meta">Vernieuwen kan vanaf de rol operator.</p>;
  }
  const run = async () => {
    setBusy(true);
    setError(null);
    setMsg("Inventaris wordt alleen-lezen opgehaald…");
    try {
      const { data } = await apiRequest<Job>("/api/v1/inventory/refresh", { method: "POST" });
      const done = await waitForJob(data.id);
      const res = done.resultaat as { status?: string; reason_code?: string | null };
      setMsg(
        done.status === "done" && res.status === "ok"
          ? "Inventaris vernieuwd."
          : `Vernieuwen niet volledig gelukt${res.reason_code ? ` (${res.reason_code})` : ""}; zie de status per onderdeel.`,
      );
      onDone();
    } catch (e) {
      setMsg(null);
      setError(e instanceof HubApiError ? e : new HubApiError(0, "onbekend", String(e)));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="row">
        <button type="button" className="btn btn-primary" onClick={() => void run()} disabled={busy} data-testid="inventaris-vernieuwen">
          {busy ? "Bezig met vernieuwen…" : "Inventaris vernieuwen"}
        </button>
      </div>
      <p role="status" aria-live="polite" className="meta" data-testid="vernieuwen-status">
        {msg ?? ""}
      </p>
      {error ? <ErrorPanel error={error} /> : null}
    </div>
  );
}
